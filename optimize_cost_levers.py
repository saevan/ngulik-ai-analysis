"""Reduce cost drag of the frozen property candidate: tick-cost filter, slower fading, momentum ranking."""
from pathlib import Path
from itertools import product
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_idx_costs import Costs
from exploit_market_properties import mom120, WINDOWS
from mitigate_swinger_gap import stats

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'cost_lever_results'
SCEN={'fees':Costs(),'spread1':Costs(grid=True,ticks_per_side=1,round_lot=100),'spread2':Costs(grid=True,ticks_per_side=2,round_lot=100)}
LEVERS=dict(tick=[0.,.01,.005],fade=[2.,3.,5.],rank=['alpha','mom120'])
CONFIGS=[dict(zip(LEVERS,v)) for v in product(*LEVERS.values())]
BASE=CONFIGS[0]  # = frozen property candidate

def label(c):return f't{c["tick"]}_f{c["fade"]}_{c["rank"]}'

def main():
    OUT.mkdir(exist_ok=True)
    (OUT/'PLAN.json').write_text(json.dumps(dict(base='buy stop HHV20 + gap_skip2% + gapdown_close2%, alphabetical (frozen in market_property_results)',
        levers=dict(tick='skip buys if tick(prior Close)/prior Close > x (none/1%/0.5%)',fade='fading ATR multiple 2/3/5',rank='alphabetical vs mom120'),
        configs=CONFIGS,selection='Train spread1: CAGR > base AND records >= base; max CAGR. Frozen. All configs run on later windows as diagnostics.',
        caution='mom120 already seen positive in later windows (post-freeze diagnostic earlier); tick grid applied counterfactually to adjusted history.'),indent=2),encoding='utf-8')
    data,_=engine.load_data('stocks')
    frames={w:{str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)} for w,(_,end) in WINDOWS.items()}
    rows=[];chosen=None
    order=[('train','spread1')]+[(w,s) for w in WINDOWS for s in SCEN if (w,s)!=('train','spread1')]
    for w,s in order:
        for c in CONFIGS:
            with np.errstate(invalid='ignore'):
                cur,t=run(frames[w],fade=c['fade'],entry_mode='buy_stop',cost_model=SCEN[s],start=WINDOWS[w][0],gap_skip=.02,gapdown_close=.02,
                    priority=mom120 if c['rank']=='mom120' else None,max_tick_frac=c['tick'] or None)
            rows.append(dict(**c,window=w,scenario=s,**stats(cur,t)))
            if w=='full' or (w,s)==('train','spread1'):cur.to_csv(OUT/f'{w}_{s}_{label(c)}_equity.csv');t.to_csv(OUT/f'{w}_{s}_{label(c)}_trades.csv',index=False)
        if (w,s)==('train','spread1'):
            tr=pd.DataFrame(rows);b=tr.iloc[0];ok=tr[(tr.cagr>b.cagr)&(tr.records>=b.records)].sort_values(['cagr','records'],ascending=False)
            chosen=None if ok.empty else dict(tick=float(ok.iloc[0].tick),fade=float(ok.iloc[0].fade),rank=ok.iloc[0]['rank'])
            (OUT/'FROZEN.json').write_text(json.dumps(dict(chosen=chosen,base_train=dict(cagr=b.cagr,records=int(b.records))),indent=2),encoding='utf-8')
            print('FROZEN',chosen,flush=True)
        print(w,s,'done',flush=True)
    res=pd.DataFrame(rows);res.to_csv(OUT/'comparison.csv',index=False)
    out=[]
    for lever,vals in LEVERS.items():
        others=[k for k in LEVERS if k!=lever]
        for v in vals[1:]:
            for (w,s),g in res.groupby(['window','scenario']):
                a=g[g[lever]==vals[0]].set_index(others);b=g[g[lever]==v].set_index(others)
                out.append(dict(lever=f'{lever}:{vals[0]}->{v}',window=w,scenario=s,cagr_delta=(b.cagr-a.cagr).mean(),records_delta=(b.records-a.records).mean(),
                    mdd_delta=(b.mdd-a.mdd).mean(),both_better=((b.cagr>a.cagr)&(b.records>=a.records)).mean()))
    pd.DataFrame(out).to_csv(OUT/'lever_consistency.csv',index=False)
    np.testing.assert_allclose(pd.read_csv(OUT/'full_spread1_t0.0_f2.0_alpha_equity.csv').equity,
        pd.read_csv(ROOT/'market_property_results'/'full_spread_buy_stop_gs0.02_gd0.02_alpha_equity.csv').equity,rtol=1e-10);print('regression OK')

if __name__=='__main__':main()
