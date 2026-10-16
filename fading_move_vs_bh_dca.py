"""Test the "fading move" idea against buy-and-hold and DCA.

System (STRATEGY_NOTES.md definition): be in the stock at every Open; the reference is the CURRENT bar's Open (reset every bar).
Signal d: Low[t] <= Open[t]*(1-d). B (primary, project convention): signal known at the Close, sell at the next tradable Open,
re-enter at the earliest the bar after the sale (Open). A (aspirational): sell stop at Open[t]*(1-d) filled the same bar, re-enter next Open.
One sleeve per ticker (1/N of the capital, fractional shares, no rebalancing between sleeves); aggregate = sum of sleeves.
Modes: lump (all capital at the first bar) and monthly contributions (equal amount on the first tradable day of every month).
Comparison uses identical cash flows for all strategies. Equity is marked at Close net of the sell fee ("liquidation mark").
Costs (no tick grid: the prices are split-adjusted so IDX ticks do not apply; an earlier tick-based version carried a hidden rounding cost,
found by an independent audit): scenario name -> (buy fee, sell fee, proportional slippage per side): gross (0,0,0), fees (0.15%,0.25%,0),
s10/s25/s50 = fees + 0.10%/0.25%/0.50% slippage per side. Fills are clipped inside the bar's [Low, High] when slippage > 0.
"""
from itertools import product
from multiprocessing import Pool
from pathlib import Path
import json
import numpy as np
import pandas as pd
from uts.data import load_stocks, frames

OUT=Path(__file__).resolve().parent/'fading_move_results'
START='2000-01-01'
XS=[.01,.02,.03,.05,.08,.12]

def tick(p):
    return np.where(p<200,1.,np.where(p<500,2.,np.where(p<2000,5.,np.where(p<5000,10.,25.))))

def up(p,t):return np.ceil(p/t-1e-9)*t
def dn(p,t):return np.floor(p/t+1e-9)*t

SCEN={'gross':(0.,0.,0.),'fees':(.0015,.0025,0.),'s10':(.0015,.0025,.001),'s25':(.0015,.0025,.0025),'s50':(.0015,.0025,.005)}

def sim(f,variant,X,net,mode):
    """Return daily (equity, shares, contributed) arrays for one ticker sleeve, units of 1/N capital (lump: 1.0)."""
    d=f['Date/Time'].to_numpy();o,h,l,c=(f[k].to_numpy(float) for k in ['Open','High','Low','Close']);tr=f.tradable.to_numpy(bool)
    n=len(f);bf,sf,sl=SCEN[net]
    mon=pd.DatetimeIndex(d).to_period('M').to_numpy()
    first=np.where(d>=np.datetime64(START))[0]
    eq=np.full(n,np.nan);sh=np.zeros(n);con=np.zeros(n)
    if len(first)==0:return None
    i0=first[0];cash=1. if mode=='lump' else 0.;shares=0.;contrib=cash;pend=False;lastm=None
    for i in range(i0,n):
        if mode=='dca' and mon[i]!=lastm and tr[i]:
            cash+=1.;contrib+=1.;lastm=mon[i]
        elif mode=='dca' and mon[i]!=lastm:pass
        if tr[i]:
            if pend:
                px=o[i]*(1-sl);px=max(px,l[i]) if sl else px;cash+=shares*px*(1-sf);shares=0.;pend=False
            elif cash>1e-12:
                px=o[i]*(1+sl);px=min(px,h[i]) if sl else px
                shares+=cash*(1-bf)/px;cash=0.
            if variant=='A' and shares>0. and l[i]<=o[i]*(1-X) and not (shares*0):
                trig=o[i]*(1-X);px=trig*(1-sl);px=max(px,l[i]) if sl else px;cash+=shares*px*(1-sf);shares=0.
            elif variant=='B' and shares>0. and l[i]<=o[i]*(1-X):
                pend=True
        eq[i]=cash+shares*c[i]*(1-sf);sh[i]=shares;con[i]=contrib
    return d,eq,sh,con

def job(a):
    t,variant,X,net,mode=a
    r=sim(G[t],variant,X,net,mode)
    return (a,r)

def sim_bh(f,net,mode):
    return sim(f,'BH',0.,net,mode)

G={}
def aggregate(results,cal):
    E=pd.DataFrame(index=cal);S=E.copy();C=E.copy()
    for t,(d,eq,sh,con) in results.items():
        s=pd.Series(eq,index=pd.DatetimeIndex(d));E[t]=s.reindex(cal).ffill()
        C[t]=pd.Series(con,index=pd.DatetimeIndex(d)).reindex(cal).ffill()
        S[t]=pd.Series(sh,index=pd.DatetimeIndex(d)).reindex(cal).ffill()
    return E,C,S

def xirr(dates,flows):
    dd=np.array([np.datetime64(x,'D') for x in dates]);t=(dd-dd[0]).astype(float)/365.25;fl=np.array(flows,float)
    lo,hi=-.99,5.
    for _ in range(200):
        m=(lo+hi)/2;v=(fl/(1+m)**t).sum()
        if v>0:lo=m
        else:hi=m
    return (lo+hi)/2

def main():
    OUT.mkdir(exist_ok=True)
    fr=frames(load_stocks())
    for t,f in fr.items():G[t]=f
    tickers=sorted(G);N=len(tickers)
    cal=pd.DatetimeIndex(sorted(set().union(*[set(pd.DatetimeIndex(f['Date/Time'])[pd.DatetimeIndex(f['Date/Time'])>=START]) for f in G.values()])))
    cfgs=[('BH',0.,net,mode) for net in SCEN for mode in ('lump','dca')]
    cfgs+=[(v,X,net,mode) for v in 'AB' for X in XS for net in SCEN for mode in ('lump','dca')]
    rows=[];per_ticker=[]
    with Pool(4) as pool:
        for cfg in cfgs:
            v,X,net,mode=cfg
            res=dict(pool.map(_one,[(t,v,X,net,mode) for t in tickers],chunksize=5))
            res={t:r for t,r in res.items() if r is not None}
            E,C,S=aggregate(res,cal)
            # units: each ticker is 1 unit lump; aggregate lump capital = number of tickers; normalise by N
            if mode=='lump':
                tot=E.fillna(1.0).sum(axis=1)/len(res)  # a sleeve holds its unit of cash until its first bar
                yrs=(cal[-1]-cal[0]).days/365.25
                rows.append(dict(variant=v,X=X,scenario=net,mode=mode,final=float(tot.iloc[-1]),cagr=float(tot.iloc[-1]**(1/yrs)-1),mdd=float((tot/tot.cummax()-1).min()),
                    shares_ratio=float(np.nan)))
            else:
                tot=E.fillna(0).sum(axis=1);con=C.fillna(0).sum(axis=1)
                flows=con.diff().fillna(con.iloc[0]);dates=list(cal[flows.values>0]);fl=[-x for x in flows[flows>0]]
                dates.append(cal[-1]);fl.append(float(tot.iloc[-1]))
                rows.append(dict(variant=v,X=X,scenario=net,mode=mode,final=float(tot.iloc[-1]),contributed=float(con.iloc[-1]),multiple=float(tot.iloc[-1]/con.iloc[-1]),
                    xirr=xirr(dates,fl),mdd=float((tot/np.maximum.accumulate(tot.values)-1).min())))
            # per-ticker final for lump net (breadth)
            if mode=='lump':
                for t,(d,eq,sh,cn) in res.items():
                    per_ticker.append(dict(variant=v,X=X,scenario=net,ticker=t,final=float(eq[~np.isnan(eq)][-1]),shares_end=float(sh[-1])))
            print(cfg,flush=True)
    pd.DataFrame(rows).to_csv(OUT/'summary.csv',index=False);pd.DataFrame(per_ticker).to_csv(OUT/'per_ticker_lump.csv',index=False)
    print('done')

def _one(a):
    t,v,X,net,mode=a
    return t,sim(G[t],v,X,net,mode)

if __name__=='__main__':main()
