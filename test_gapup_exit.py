"""Gap-up take-profit lever on candidate buy stop + gap_skip + gapdown_close + mom120."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_idx_costs import Costs
from exploit_market_properties import mom120, WINDOWS
from mitigate_swinger_gap import stats

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'gapup_exit_results'
SCEN={'fees':Costs(),'spread1':Costs(grid=True,ticks_per_side=1,round_lot=100),'spread2':Costs(grid=True,ticks_per_side=2,round_lot=100)}
LEVELS=[0.,.04,.07]

def main():
    OUT.mkdir(exist_ok=True)
    (OUT/'PLAN.json').write_text(json.dumps(dict(base='buy stop + gap_skip2% + gapdown_close2% + mom120, fade2',lever='sell held winner (Open > entry) at Open when Open gaps up > g; g none/4%/7%',
        selection='Train spread1: CAGR > base AND records >= base; max CAGR. Frozen; all levels reported in later windows.'),indent=2),encoding='utf-8')
    data,_=engine.load_data('stocks')
    frames={w:{str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)} for w,(_,end) in WINDOWS.items()}
    rows=[]
    for w in WINDOWS:
        for s,cm in SCEN.items():
            for g in LEVELS:
                with np.errstate(invalid='ignore'):
                    c,t=run(frames[w],entry_mode='buy_stop',cost_model=cm,start=WINDOWS[w][0],gap_skip=.02,gapdown_close=.02,priority=mom120,gapup_exit=g or None)
                rows.append(dict(gapup=g,window=w,scenario=s,**stats(c,t)))
                if w=='full':c.to_csv(OUT/f'full_{s}_g{g}_equity.csv');t.to_csv(OUT/f'full_{s}_g{g}_trades.csv',index=False)
    r=pd.DataFrame(rows);r.to_csv(OUT/'comparison.csv',index=False)
    tr=r[(r.window=='train')&(r.scenario=='spread1')];b=tr.iloc[0];ok=tr[(tr.cagr>b.cagr)&(tr.records>=b.records)].sort_values('cagr',ascending=False)
    (OUT/'FROZEN.json').write_text(json.dumps(dict(chosen=None if ok.empty else float(ok.iloc[0].gapup)),indent=2),encoding='utf-8')
    np.testing.assert_allclose(pd.read_csv(OUT/'full_spread1_g0.0_equity.csv').equity,pd.read_csv(ROOT/'cost_lever_results'/'full_spread1_t0.0_f2.0_mom120_equity.csv').equity,rtol=1e-10)
    print('FROZEN',None if ok.empty else ok.iloc[0].gapup);r['v']=r.apply(lambda x:f'{x.cagr*100:.1f}/{x.records}/{x.mdd*100:.0f}',axis=1)
    print(r.pivot_table(index=['scenario','gapup'],columns='window',values='v',aggfunc='first')[list(WINDOWS)].to_string())

if __name__=='__main__':main()
