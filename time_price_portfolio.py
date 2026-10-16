"""Portfolio test (10 slots, Rp1bn, compounding, Open(i+1)) of the claim: breakout entry, exit by price and/or by time.
Entry: Close > HHV20 (prior 20 Highs) and ER20 >= 0.3 at Close i -> buy at next tradable Open.
Exit grid pre-listed below (nothing chosen on the holdout). Costs: fees 0.15/0.25% + 1 IDX tick per side + 100-share lots.
Control: random entries with the same expected signal frequency, same exits. Windows: train 2000-2015, holdout 2016-2025-08, full."""
from pathlib import Path
from multiprocessing import Pool
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_open_next import run, stats
from backtest_idx_costs import Costs
from backtest_breakout_er import efficiency_ratio

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'time_price_results'
WIN={'train':('2000-01-01','2015-12-31'),'holdout':('2016-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
COST=Costs(grid=True,ticks_per_side=1,round_lot=100)
NOACT=1e9
# (label, stop ATR, tp ATR, max bars)
EXITS=[('T10',None,None,10),('T20',None,None,20),('T40',None,None,40),
 ('SL3_T20',3,None,20),('SL3_T40',3,None,40),('SL2_T20',2,None,20),
 ('SL3_TP3',3,3,None),('SL3_TP5',3,5,None),('TP5',None,5,None),
 ('SL3_TP3_T20',3,3,20),('SL3_TP3_T40',3,3,40),('SL2_TP2_T20',2,2,20),('SL3_TP5_T20',3,5,20),('SL3_TP5_T40',3,5,40),('SL2_TP3_T40',2,3,40),('SL1.5_TP1.5_T10',1.5,1.5,10)]
FR={}

def sig_breakout(f):
    return (f.Close>f.High.shift(1).rolling(20).max()).to_numpy(bool)&(efficiency_ratio(f.Close,20).to_numpy()>=.3)

def make_random(p,seed):
    def s(f):
        rng=np.random.default_rng(seed+len(f));return rng.random(len(f))<p
    return s

def job(a):
    entry,lab,stop,tp,T,w,seed=a
    fr={t:g for t,f in FR.items() if len(g:=f[f['Date/Time']<=WIN[w][1]])}
    sig=sig_breakout if entry=='breakout' else make_random(RAND_P,seed)
    with np.errstate(invalid='ignore',divide='ignore'):
        c,t=run(fr,signal=sig,stop=stop,act=NOACT,trail=0,tp=tp,max_bars=T,cost_model=COST,start=WIN[w][0])
    return dict(entry=entry,exit=lab,window=w,seed=seed,reasons=t.reason.value_counts().to_dict(),**stats(c,t))

RAND_P=None
def main():
    global RAND_P
    OUT.mkdir(exist_ok=True)
    st,_=engine.load_data('stocks')
    for k,f in st.groupby('Ticker',sort=True):FR[str(k)]=f.reset_index(drop=True)
    sg=sum(int(sig_breakout(f).sum()) for f in FR.values());td=sum(int(f.tradable.sum()) for f in FR.values());RAND_P=sg/td
    print('signal freq',RAND_P,flush=True)
    tasks=[('breakout',l,s,t,T,w,0) for l,s,t,T in EXITS for w in WIN]
    tasks+=[('random',l,s,t,T,'full',sd) for l,s,t,T in EXITS if l in('T20','T40','SL3_T20','SL3_T40','SL3_TP3_T20','SL3_TP5_T40','SL3_TP3') for sd in range(3)]
    with Pool(4) as p:rows=p.map(job,tasks,chunksize=1)
    d=pd.DataFrame(rows);d.to_csv(OUT/'portfolio.csv',index=False);print('done',len(d))

if __name__=='__main__':main()
