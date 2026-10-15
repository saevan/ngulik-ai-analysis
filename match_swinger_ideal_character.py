"""Target Swinger ideal trade character (WR>50%, small losses) with causal exits; check if CAGR/records follow."""
from pathlib import Path
from itertools import product
from multiprocessing import Pool
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_idx_costs import Costs
from exploit_market_properties import mom120, WINDOWS
from mitigate_swinger_gap import stats

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'swinger_ideal_character_results'
SCEN={'fees':Costs(),'spread1':Costs(grid=True,ticks_per_side=1,round_lot=100)}
LEVERS=dict(take_profit=[0.,3.,5.,8.],breakeven=[0.,1.,2.],trail_after=[0.,2.],channel=[20,10])
CONFIGS=[dict(zip(LEVERS,v)) for v in product(*LEVERS.values())]
BASE=CONFIGS[0]
TARGET=dict(source='prototype_swinger_benchmark_results afl_ideal_net, full 2000-2025, fees',cagr=1.1477,records=249,wr=.519,avg_win=.1651,avg_loss=.0319,payout=5.17,big_loss=.0154,mean_bars=19.0,n=3241,invested=.93)
FR={}

def label(c):return f'tp{c["take_profit"]}_be{c["breakeven"]}_tr{c["trail_after"]}_ch{c["channel"]}'

def job(a):
    c,w,s=a
    with np.errstate(invalid='ignore'):
        cur,t=run(FR[w],entry_mode='buy_stop',cost_model=SCEN[s],start=WINDOWS[w][0],gap_skip=.02,gapdown_close=.02,priority=mom120,
            channel=c['channel'],trail_after=c['trail_after'] or None,take_profit=c['take_profit'] or None,breakeven=c['breakeven'] or None)
    if w=='full':cur.to_csv(OUT/f'{w}_{s}_{label(c)}_equity.csv');t.to_csv(OUT/f'{w}_{s}_{label(c)}_trades.csv',index=False)
    return dict(**c,window=w,scenario=s,**stats(cur,t),invested=(cur.market_value/cur.equity).mean())

def main():
    OUT.mkdir(exist_ok=True)
    (OUT/'PLAN.json').write_text(json.dumps(dict(base='Candidate buy stop HHV20 + gap_skip + gapdown_close + mom120, fade2, SMA30',target=TARGET,
        levers=dict(take_profit='intraday sell limit at entry + k entry-ATR (none/3/5/8)',breakeven='intraday stop at entry once Close >= entry + b ATR (none/1/2)',
            trail_after='LLV5 trailing after +2 ATR (none/2)',channel='HHV 20/10'),configs=CONFIGS,
        selection='Train, FEES (same cost basis as Swinger ideal): eligible WR>50% AND CAGR > base AND records >= base; pick max CAGR. Frozen; evaluated on validation/test/full fees and spread1. Also report whether WR>50% configs as a group beat the base.'),indent=2),encoding='utf-8')
    data,_=engine.load_data('stocks')
    for w,(_,end) in WINDOWS.items():FR[w]={str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)}
    tasks=[(c,w,s) for w in WINDOWS for s in SCEN for c in CONFIGS]
    with Pool(4) as pool:rows=pool.map(job,tasks,chunksize=4)
    res=pd.DataFrame(rows);res.to_csv(OUT/'comparison.csv',index=False)
    tr=res[(res.window=='train')&(res.scenario=='fees')];b=tr[(tr.take_profit==0)&(tr.breakeven==0)&(tr.trail_after==0)&(tr.channel==20)].iloc[0]
    ok=tr[(tr.wr>.5)&(tr.cagr>b.cagr)&(tr.records>=b.records)].sort_values(['cagr','records'],ascending=False)
    chosen=None if ok.empty else {k:float(ok.iloc[0][k]) for k in LEVERS}
    (OUT/'FROZEN.json').write_text(json.dumps(dict(chosen=chosen,base_train_fees=dict(cagr=b.cagr,records=int(b.records),wr=b.wr),n_wr_over_50=int((tr.wr>.5).sum())),indent=2),encoding='utf-8')
    np.testing.assert_allclose(pd.read_csv(OUT/f'full_fees_{label(BASE)}_equity.csv').equity,pd.read_csv(ROOT/'cost_lever_results'/'full_fees_t0.0_f2.0_mom120_equity.csv').equity,rtol=1e-10)
    print('FROZEN',chosen,'regression OK')

if __name__=='__main__':main()
