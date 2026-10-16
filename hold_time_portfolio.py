"""Portfolio test (10 slots, Rp1bn, compounding, Open(i+1), fees + 1 tick + lots) of "exit only when price falls from the latest Open".
Entry: Close > HHV20 and ER20 >= 0.3 -> next tradable Open (same as time_price_portfolio.py). Exit variants (listed before running):
  FADE_d      : exit signal Low[j] <= Open[j]*(1-d), evaluated at Close, filled next Open, any P&L
  FADEP_d     : same but the signal counts only while Close[j] > entry (still in profit); losers have no exit (reference of the claim)
  FADEP_d+SL3 : as FADEP_d plus a 3 ATR Close stop for losers
  FADEP_d+SL3+T120 : as above plus a 120-bar time stop (so no position is held forever)
References: T40 and SL3_T40 (time exits), HHV55 stop3/trail2.5 (earlier best). Windows train 2000-2015, holdout 2016-2025-08, full."""
from pathlib import Path
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_open_next import run, stats
from backtest_idx_costs import Costs
import time_price_portfolio as tpp

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'time_price_results'
WIN=tpp.WIN;COST=tpp.COST;FR=tpp.FR
D=[.03,.05,.08,.12,.20]
EX=[('T40',dict(stop=None,max_bars=40)),('SL3_T40',dict(stop=3,max_bars=40))]
for d in D:
    EX+=[(f'FADE_{int(d*100)}',dict(stop=None,fade=d)),(f'FADEP_{int(d*100)}',dict(stop=None,fade=d,fade_profit_only=True)),
         (f'FADEP_{int(d*100)}+SL3',dict(stop=3,fade=d,fade_profit_only=True)),(f'FADEP_{int(d*100)}+SL3+T120',dict(stop=3,fade=d,fade_profit_only=True,max_bars=120))]

def job(a):
    lab,kw,w=a
    fr={t:g for t,f in FR.items() if len(g:=f[f['Date/Time']<=WIN[w][1]])}
    with np.errstate(invalid='ignore',divide='ignore'):
        c,t=run(fr,signal=tpp.sig_breakout,act=1e9,trail=0,cost_model=COST,start=WIN[w][0],**kw)
    t=t.copy();t['gain']=t.net_return
    corr=float(np.corrcoef(t.bars,t.net_return)[0,1]) if len(t)>2 else np.nan
    return dict(exit=lab,window=w,reasons=t.reason.value_counts().to_dict(),corr_bars_return=corr,**stats(c,t))

def main():
    st,_=engine.load_data('stocks')
    for k,f in st.groupby('Ticker',sort=True):FR[str(k)]=f.reset_index(drop=True)
    tasks=[(l,kw,w) for l,kw in EX for w in WIN]
    with Pool(4) as p:rows=p.map(job,tasks,chunksize=1)
    d=pd.DataFrame(rows);d.to_csv(OUT/'hold_time_portfolio.csv',index=False);print('done',len(d))

if __name__=='__main__':main()
