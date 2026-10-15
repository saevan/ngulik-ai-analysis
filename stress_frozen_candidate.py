"""Robustness of the frozen property candidate: ticks, price limits, random priority."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_idx_costs import Costs
from exploit_market_properties import mom120, WINDOWS
from mitigate_swinger_gap import stats

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'robustness_results'
CANDS={'base_buystop':dict(),'frozen':dict(gap_skip=.02,gapdown_close=.02),'frozen_mom120':dict(gap_skip=.02,gapdown_close=.02,priority=mom120)}

def rand_priority(seed):
    def f(fr):
        key=sum(map(ord,str(fr.Ticker.iloc[0])))
        return np.random.default_rng(seed*1000+key).random(len(fr))
    return f

def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks')
    frames={w:{str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)} for w,(_,end) in WINDOWS.items()}
    stresses={'spread1':dict(cost=Costs(grid=True,ticks_per_side=1,round_lot=100)),'spread2':dict(cost=Costs(grid=True,ticks_per_side=2,round_lot=100)),
        'spread3':dict(cost=Costs(grid=True,ticks_per_side=3,round_lot=100)),'spread1_limits':dict(cost=Costs(grid=True,ticks_per_side=1,round_lot=100),price_limits=True),
        'spread2_limits':dict(cost=Costs(grid=True,ticks_per_side=2,round_lot=100),price_limits=True)}
    rows=[]
    for w in ['validation','test','full']:
        for name,kw in CANDS.items():
            for st,sk in stresses.items():
                with np.errstate(invalid='ignore'):
                    c,t=run(frames[w],entry_mode='buy_stop',cost_model=sk['cost'],start=WINDOWS[w][0],price_limits=sk.get('price_limits',False),**kw)
                rows.append(dict(candidate=name,stress=st,window=w,**stats(c,t)));print(w,name,st,f"{rows[-1]['cagr']:.2%} {rows[-1]['records']}",flush=True)
            if name!='frozen_mom120':
                for seed in range(5):
                    with np.errstate(invalid='ignore'):
                        c,t=run(frames[w],entry_mode='buy_stop',cost_model=stresses['spread1']['cost'],start=WINDOWS[w][0],priority=rand_priority(seed),**kw)
                    rows.append(dict(candidate=name,stress=f'spread1_random{seed}',window=w,**stats(c,t)))
    r=pd.DataFrame(rows);r.to_csv(OUT/'stress.csv',index=False)

if __name__=='__main__':main()
