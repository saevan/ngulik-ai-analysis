"""Claim test: "combine time and price to reach WR ~50%; enter on breakout, exit by price or by time".

Signal-level study (each signal = one independent trade, overlap allowed; portfolio effects are NOT modelled here).
Signal at Close i (Close > HHV_N of previous N Highs, ER20 >= theta, ATR14 known) -> buy at the next tradable Open (bar j0).
Exits are evaluated at each Close j >= j0 and filled at the next Open (bar j+1): the user's Open(i+1) rule.
  price stop  : Close <= entry - s*ATR(signal)        price target: Close >= entry + t*ATR(signal)
  time exit   : bar count since entry >= T (exit at Open of bar j0+T)
Costs: buy 0.15% / sell 0.25%, no spread (stated). Control: random entries (same exits) on every tradable bar.
Periods: train 2000-2015, holdout 2016-2025 (nothing is selected on the holdout).
"""
from itertools import product
from pathlib import Path
import json
import numpy as np
import pandas as pd
from uts.data import load_stocks, frames
from uts.indicators import atr_previous, efficiency_ratio

OUT=Path(__file__).resolve().parent/'time_price_results'
H=61  # path length: exits at most 60 bars after entry
BUY,SELL=.0015,.0025
rng=np.random.default_rng(11)

def build(fr,N=20,theta=.3,use_er=True,random_p=None):
    rows=[]
    for t,f in fr.items():
        o,h,l,c=(f[x].to_numpy(float) for x in ['Open','High','Low','Close']);tr=f.tradable.to_numpy(bool);d=f['Date/Time'].to_numpy()
        n=len(f)
        if n<N+30:continue
        a=pd.Series(atr_previous(f)).shift(-1).to_numpy()  # ATR known at Close i = value stored at i+1 by atr_previous
        hh=pd.Series(h).shift(1).rolling(N).max().to_numpy()
        er=efficiency_ratio(pd.Series(c),20).to_numpy()
        sig=(c>hh)&np.isfinite(a)&(a>0)
        if use_er:sig&=(er>=theta)
        if random_p is not None:sig=np.isfinite(a)&(a>0)&(rng.random(n)<random_p)
        for i in np.where(sig)[0]:
            j0=i+1
            if j0+H+1>=n or not tr[j0]:continue
            rows.append((t,d[j0],o[j0],a[i],c[j0:j0+H],o[j0+1:j0+H+1],tr[j0+1:j0+H+1]))
    return rows

def pack(rows):
    return dict(date=np.array([r[1] for r in rows],dtype='datetime64[ns]'),entry=np.array([r[2] for r in rows]),atr=np.array([r[3] for r in rows]),
        C=np.vstack([r[4] for r in rows]),Onext=np.vstack([r[5] for r in rows]),T=np.vstack([r[6] for r in rows]),tick=np.array([r[0] for r in rows]))

def simulate(P,s,t,T):
    """Return (net return, bars held) arrays. s,t in ATR multiples (None=off), T bars (None=off, forced at 60)."""
    e=P['entry'][:,None];a=P['atr'][:,None];C=P['C']
    hit=np.zeros(C.shape,bool)
    if s is not None:hit|=C<=e-s*a
    if t is not None:hit|=C>=e+t*a
    cap=(T if T else H-1)
    hit[:,cap-1:]=True  # bar index k (0=entry bar): hold k+1 bars; exit evaluated at Close of bar k, fill Open of bar k+1
    hit&=P['T']   # exit only fills when the next bar is tradable; otherwise wait for the next one
    k=hit.argmax(axis=1);k=np.where(hit.any(axis=1),k,H-1)
    px=P['Onext'][np.arange(len(k)),k]
    r=px*(1-SELL)/(P['entry']*(1+BUY))-1
    return r,k+1

def stats(r,bars):
    w=r>0;n=len(r)
    if n==0:return {}
    aw=r[w].mean() if w.any() else np.nan;al=-r[~w].mean() if (~w).any() else np.nan
    return dict(n=n,wr=float(w.mean()),exp=float(r.mean()),median=float(np.median(r)),avg_win=float(aw),avg_loss=float(al),payout=float(aw/al) if al else np.nan,
        pf=float(r[w].sum()/-r[~w].sum()) if (~w).any() else np.inf,bars=float(bars.mean()),win_bars=float(bars[w].mean()) if w.any() else np.nan,loss_bars=float(bars[~w].mean()) if (~w).any() else np.nan)

def main():
    OUT.mkdir(exist_ok=True)
    fr=frames(load_stocks())
    sets={'breakout_er':build(fr),'breakout_noER':build(fr,use_er=False)}
    base=len(sets['breakout_er'])
    p=base/ sum(int(f.tradable.sum()) for f in fr.values())
    sets['random']=build(fr,random_p=p)
    print({k:len(v) for k,v in sets.items()},flush=True)
    P={k:pack(v) for k,v in sets.items()}
    SL=[None,1,1.5,2,3];TP=[None,.5,1,1.5,2,3,5];TM=[None,3,5,10,20,40]
    res=[]
    for name,pk in P.items():
        yr=pd.DatetimeIndex(pk['date']).year.to_numpy()
        for s,t,T in product(SL,TP,TM):
            if s is None and t is None and T is None:continue
            r,b=simulate(pk,s,t,T)
            for per,m in {'train_2000_2015':yr<=2015,'holdout_2016_2025':yr>=2016}.items():
                res.append(dict(entry=name,period=per,sl=s,tp=t,time=T,**stats(r[m],b[m])))
    df=pd.DataFrame(res);df.to_csv(OUT/'grid.csv',index=False)
    print('rows',len(df))

if __name__=='__main__':main()
