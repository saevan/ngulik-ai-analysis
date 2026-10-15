"""Condition-specific actions for Breakout+ER buy-stop; train-selected, frozen, then evaluated."""
from pathlib import Path
from itertools import product
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_idx_costs import Costs
from analyze_market_conditions import conditions
from mitigate_swinger_gap import stats

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'market_condition_results'
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
SCEN={'fees':Costs(),'spread':Costs(grid=True,ticks_per_side=1,round_lot=100)}
CONDS=['breadth_sempit','trend_bear','sempit_or_bear']
ACTIONS=['block_entry','half_size','derisk_exit','llv10_stop']
CONFIGS=[dict(cond='none',action='none')]+[dict(cond=c,action=a) for c,a in product(CONDS,ACTIONS)]
BASE=CONFIGS[0]

def label(c):return f'{c["cond"]}_{c["action"]}'

def main():
    OUT.mkdir(exist_ok=True)
    (OUT/'PLAN.json').write_text(json.dumps(dict(system='Breakout+ER buy stop at prior HHV20 (prior ER20>=.3), fade2 Close->next Open, SMA30, no market gate',
        conditions='breadth_sempit: <40% stocks above SMA50; trend_bear: equal-weight proxy below SMA200; labels from previous Close.',
        actions='block_entry: no new entries; half_size: new entries 5% equity; derisk_exit: sell all at Open AND block entries; llv10_stop: intraday LLV10 sell stop active only in condition.',
        configs=CONFIGS,windows=WINDOWS,selection='Train spread: CAGR > base AND records >= base; max CAGR. Frozen before evaluation. All configs also run on later windows and reported as post-freeze diagnostics.',
        caution='Conditions chosen after viewing full-history attribution (analyze_market_conditions.py) -> look-ahead in hypothesis selection; validation/test not independent.'),indent=2),encoding='utf-8')
    data,_=engine.load_data('stocks');cond,_,_=conditions(data)
    sets={'breadth_sempit':set(cond.index[cond.breadth=='sempit']),'trend_bear':set(cond.index[cond.trend=='bear'])}
    sets['sempit_or_bear']=sets['breadth_sempit']|sets['trend_bear']
    frames={w:{str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)} for w,(_,end) in WINDOWS.items()}
    rows=[]
    def go(c,w,s):
        kw={};d=sets.get(c['cond'])
        if c['action']=='block_entry':kw=dict(block_dates=d)
        elif c['action']=='half_size':kw=dict(size_dates=d,size_factor=.5)
        elif c['action']=='derisk_exit':kw=dict(derisk_dates=d,block_dates=d)
        elif c['action']=='llv10_stop':kw=dict(llv=10,llv_dates=d)
        with np.errstate(invalid='ignore'):
            cur,t=run(frames[w],entry_mode='buy_stop',cost_model=SCEN[s],start=WINDOWS[w][0],**kw)
        r=dict(**c,window=w,scenario=s,**stats(cur,t));rows.append(r)
        cur.to_csv(OUT/f'{w}_{s}_{label(c)}_equity.csv');t.to_csv(OUT/f'{w}_{s}_{label(c)}_trades.csv',index=False)
        print(w,s,label(c),f"CAGR{r['cagr']:.2%} rec{r['records']} MDD{r['mdd']:.2%}",flush=True);return r
    train=pd.DataFrame([go(c,'train','spread') for c in CONFIGS]);b=train.iloc[0]
    ok=train[(train.cagr>b.cagr)&(train.records>=b.records)].sort_values(['cagr','records'],ascending=False)
    chosen=None if ok.empty else dict(cond=ok.iloc[0]['cond'],action=ok.iloc[0]['action'])
    (OUT/'FROZEN.json').write_text(json.dumps(dict(chosen=chosen,base_train=dict(cagr=b.cagr,records=int(b.records))),indent=2),encoding='utf-8')
    print('FROZEN',chosen,flush=True)
    for c in CONFIGS:
        for w in ['validation','test','full']:
            for s in SCEN:go(c,w,s)
        go(c,'train','fees')
    res=pd.DataFrame(rows);res['frozen']=[chosen is not None and r['cond']==chosen['cond'] and r['action']==chosen['action'] for r in rows]
    res.to_csv(OUT/'comparison.csv',index=False)
    old=pd.read_csv(ROOT/'swinger_gap_results'/'diag_full_fees_gnone_buy_stop_close_llv0_equity.csv')
    np.testing.assert_allclose(pd.read_csv(OUT/'full_fees_none_none_equity.csv').equity,old.equity,rtol=1e-10);print('regression OK')

if __name__=='__main__':main()
