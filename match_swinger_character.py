"""Copy Swinger trade character onto the candidate: small losses, profit protection, more positions."""
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
OUT=ROOT/'swinger_character_match_results'
SCEN={'fees':Costs(),'spread1':Costs(grid=True,ticks_per_side=1,round_lot=100),'spread2':Costs(grid=True,ticks_per_side=2,round_lot=100)}
LEVERS=dict(init_stop=['none','llv5','atr2'],trail_after=[0.,2.,4.],channel=[20,10])
CONFIGS=[dict(zip(LEVERS,v)) for v in product(*LEVERS.values())]
BASE=CONFIGS[0]

def label(c):return f'{c["init_stop"]}_tr{c["trail_after"]}_ch{c["channel"]}'

def main():
    OUT.mkdir(exist_ok=True)
    (OUT/'PLAN.json').write_text(json.dumps(dict(base='Candidate: buy stop HHV20 (prior ER20>=.3) + gap_skip2% + gapdown_close2% + mom120 ranking, fade2, SMA30',
        motivation='Diagnosis (full fees): candidate losers avg -6.5%, 19.6% of losers < -10%, 40.5% of losers were >+5% first, winners give back 14.6% from MFE, mean positions 7.4. Swinger ideal: -3.2%, 3.2%, 35%, 11.4%, 9.4.',
        levers=dict(init_stop='fixed intraday stop at LLV5 before entry (Swinger sup) or entry-2ATR',trail_after='after Close >= entry + k entry-ATR, intraday trailing stop at LLV5 (Swinger TSL) only for winners',channel='buy-stop HHV length 20 or 10 (more entries)'),
        configs=CONFIGS,selection='Train spread1: CAGR > base AND records >= base; max CAGR. Frozen; all configs reported on later windows; lever consistency table.'),indent=2),encoding='utf-8')
    data,_=engine.load_data('stocks')
    frames={w:{str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)} for w,(_,end) in WINDOWS.items()}
    rows=[]
    for w,s in [('train','spread1')]+[(w,s) for w in WINDOWS for s in SCEN if (w,s)!=('train','spread1')]:
        for c in CONFIGS:
            with np.errstate(invalid='ignore'):
                cur,t=run(frames[w],entry_mode='buy_stop',cost_model=SCEN[s],start=WINDOWS[w][0],gap_skip=.02,gapdown_close=.02,priority=mom120,
                    init_stop=None if c['init_stop']=='none' else c['init_stop'],trail_after=c['trail_after'] or None,channel=c['channel'])
            r=t.net_return;loss=r[r<=0]
            rows.append(dict(**c,window=w,scenario=s,**stats(cur,t),loss_lt10=(loss<-.1).mean(),positions=cur.positions.mean(),invested=(cur.market_value/cur.equity).mean()))
            if w=='full':cur.to_csv(OUT/f'{w}_{s}_{label(c)}_equity.csv');t.to_csv(OUT/f'{w}_{s}_{label(c)}_trades.csv',index=False)
        if (w,s)==('train','spread1'):
            tr=pd.DataFrame(rows);b=tr.iloc[0];ok=tr[(tr.cagr>b.cagr)&(tr.records>=b.records)].sort_values(['cagr','records'],ascending=False)
            chosen=None if ok.empty else dict(init_stop=ok.iloc[0].init_stop,trail_after=float(ok.iloc[0].trail_after),channel=int(ok.iloc[0].channel))
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
                    mdd_delta=(b.mdd-a.mdd).mean(),avg_loss_delta=(b.avg_loss-a.avg_loss).mean(),both_better=((b.cagr>a.cagr)&(b.records>=a.records)).mean()))
    pd.DataFrame(out).to_csv(OUT/'lever_consistency.csv',index=False)
    np.testing.assert_allclose(pd.read_csv(OUT/f'full_spread1_{label(BASE)}_equity.csv').equity,pd.read_csv(ROOT/'cost_lever_results'/'full_spread1_t0.0_f2.0_mom120_equity.csv').equity,rtol=1e-10);print('regression OK')

if __name__=='__main__':main()
