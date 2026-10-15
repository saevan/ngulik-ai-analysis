"""Fresh system search for the user's 7 criteria. All signals at Close i, fills at Open i+1.

Criteria (trade level, net of costs):
 C1 mean >> median: mean >= 2*median and mean - median >= 1pp (and mean > 0)
 C2 average winning-trade bars > average losing-trade bars
 C3 payout (avg win / |avg loss|) > 2
 C4 win rate > 50%
 C5 wins cover losses: expectancy > 0 and profit factor > 1
 C6 universal: C1-C5 hold separately on stocks, forex and crypto
 C7 execution at Open(i+1): by construction
Search ONLY on stocks 2000-2015 (fees); stocks 2016-2025, forex and crypto are held out.
"""
from pathlib import Path
from itertools import product
from multiprocessing import Pool
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_cross_market import forex_daily
from backtest_breakout_er import efficiency_ratio

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'new_system_results'
COST={'stocks':(.0015,.0025),'forex':(.00015,.00015),'crypto':(.001,.001)}  # buy, sell fractions

def rsi(c,n):
    d=c.diff();up=d.clip(lower=0).ewm(alpha=1/n,adjust=False).mean();dn=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+up/dn.replace(0,np.nan))

def features(f):
    c=f.Close;h=f.High;l=f.Low
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    x=dict(C=c.to_numpy(float),O=f.Open.to_numpy(float),atr=tr.rolling(14).mean().to_numpy(float),
        sma10=c.rolling(10).mean(),sma50=c.rolling(50).mean(),sma100=c.rolling(100).mean(),sma200=c.rolling(200).mean(),
        rsi2=rsi(c,2),er=efficiency_ratio(c,20),hhv20=h.shift(1).rolling(20).max(),hhv55=h.shift(1).rolling(55).max(),
        llc5=c.shift(1).rolling(5).min(),tradable=f.tradable.to_numpy(bool),date=f['Date/Time'].to_numpy())
    return x

def entry(x,name):
    c=pd.Series(x['C'])
    if name.startswith('rsi2'):
        _,th,L=name.split('_');sig=(c>x[L])&(x['rsi2']<float(th))
    elif name=='newlow5_sma200':sig=(c>x['sma200'])&(c<x['llc5'])
    elif name=='dip10_stack':sig=(c<x['sma10'])&(c>x['sma50'])&(x['sma50']>x['sma200'])
    elif name=='brk20_er':sig=(c>x['hhv20'])&(x['er']>=.3)
    elif name=='brk55':sig=c>x['hhv55']
    return sig.fillna(False).to_numpy(bool)

def simulate(x,sig,cfg,cost,start,end):
    C,O,A,T=x['C'],x['O'],x['atr'],x['tradable'];D=x['date'];n=len(C);out=[];i=0
    s,tm,a,m,mh=cfg['stop'],cfg['time'],cfg['act'],cfg['trail'],cfg['maxhold']
    while i<n-1:
        if not(sig[i] and D[i]>=start and D[i]<=end and np.isfinite(A[i]) and A[i]>0):i+=1;continue
        k=i+1
        while k<n and not T[k]:k+=1
        if k>=n:break
        e=O[k];a0=A[i];peak=C[k];armed=False;exit_j=None
        for j in range(k,n-1):
            peak=max(peak,C[j]);age=j-k+1
            if peak>=e+a*a0:armed=True
            if (s and C[j]<=e-s*a0) or (tm and age>=tm and C[j]<=e) or (armed and C[j]<=peak-m*a0) or (mh and age>=mh) or D[j]>end:
                exit_j=j;break
        if exit_j is None:
            # Still open at the end of the data: marked at the last Close (never dropped).
            r=C[n-1]*(1-cost[1])/(e*(1+cost[0]))-1;out.append((r,n-k,D[k]));break
        q=exit_j+1
        while q<n and not T[q]:q+=1
        if q>=n:
            r=C[n-1]*(1-cost[1])/(e*(1+cost[0]))-1;out.append((r,n-k,D[k]));break
        r=O[q]*(1-cost[1])/(e*(1+cost[0]))-1
        out.append((r,q-k,D[k]));i=q
    return out

def score(trades):
    if len(trades)<30:return None
    r=np.array([t[0] for t in trades]);b=np.array([t[1] for t in trades]);w=r>0
    if w.all() or (~w).all():return None
    s=dict(n=len(r),mean=r.mean(),median=np.median(r),wr=w.mean(),avg_win=r[w].mean(),avg_loss=-r[~w].mean(),
        win_bars=b[w].mean(),loss_bars=b[~w].mean(),pf=r[w].sum()/-r[~w].sum())
    s['payout']=s['avg_win']/s['avg_loss']
    s['c1']=bool(s['mean']>0 and s['mean']>=2*s['median'] and s['mean']-s['median']>=.01)
    s['c2']=bool(s['win_bars']>s['loss_bars']);s['c3']=bool(s['payout']>2);s['c4']=bool(s['wr']>.5)
    s['c5']=bool(s['mean']>0 and s['pf']>1);s['passes']=sum(s[k] for k in ['c1','c2','c3','c4','c5'])
    return s

ENTRIES=['rsi2_5_sma200','rsi2_10_sma200','rsi2_20_sma200','rsi2_10_sma100','newlow5_sma200','dip10_stack','brk20_er','brk55']
CONFIGS=[dict(entry=e,stop=s,time=t,act=a,trail=m,maxhold=h) for e,s,t,a,m,h in product(ENTRIES,[0,1.,2.],[0,3,5],[1.,2.],[2.,3.],[0,60])]
MK={}

def load():
    st,_=engine.load_data('stocks');fx,_=engine.load_data('forex')
    cr=pd.concat([pd.read_csv(p,parse_dates=['Date/Time']) for p in sorted((ROOT/'Data'/'crypto_binance_daily').glob('*.csv'))],ignore_index=True);cr['tradable']=cr.Volume>0
    return {'stocks':st,'forex':forex_daily(fx,0),'crypto':cr}

def run_cfg(args):
    cfg,market,start,end=args;tr=[]
    for x in MK[market]:
        tr+=simulate(x,entry(x,cfg['entry']),cfg,COST[market],np.datetime64(start),np.datetime64(end))
    return tr

def main():
    OUT.mkdir(exist_ok=True)
    for m,df in load().items():MK[m]=[features(f.reset_index(drop=True)) for _,f in df.groupby('Ticker',sort=True)]
    (OUT/'PLAN.json').write_text(json.dumps(dict(criteria=__doc__,configs=len(CONFIGS),entries=ENTRIES,
        exits='stop: Close <= entry - s*ATR14(signal bar); time: after T bars still <= entry; trail: once peak Close >= entry + a*ATR, exit when Close <= peak - m*ATR; all exits at next tradable Open',
        costs=COST,selection='Stocks 2000-2015 only: max criteria passed (C1-C5), tie -> expectancy. Frozen top-1 plus top-5 list; then held-out evaluation.'),indent=2,default=str),encoding='utf-8')
    with Pool(4) as p:train=p.map(run_cfg,[(c,'stocks','2000-01-01','2015-12-31') for c in CONFIGS],chunksize=4)
    rows=[]
    for c,t in zip(CONFIGS,train):
        s=score(t)
        if s:rows.append(dict(**c,**s))
    tr=pd.DataFrame(rows).sort_values(['passes','mean'],ascending=False);tr.to_csv(OUT/'train_stocks.csv',index=False)
    print(tr.passes.value_counts().sort_index().to_string());print(tr.head(15)[['entry','stop','time','act','trail','n','mean','median','wr','payout','win_bars','loss_bars','pf','passes']].round(4).to_string())
    top=tr.head(5)[list(CONFIGS[0])].to_dict('records')
    (OUT/'FROZEN.json').write_text(json.dumps(dict(top5=top),indent=2,default=float),encoding='utf-8')
    tests=[('stocks','2016-01-01','2025-12-31'),('forex','2000-01-01','2030-01-01'),('crypto','2000-01-01','2030-01-01')]
    ev=[]
    with Pool(4) as p:
        res=p.map(run_cfg,[(c,m,a,b) for c in top for m,a,b in tests])
    for (c,(m,a,b)),t in zip([(c,x) for c in top for x in tests],res):
        s=score(t) or {};ev.append(dict(**c,market=m,period=f'{a[:4]}-{b[:4]}',**s))
    ev=pd.DataFrame(ev);ev.to_csv(OUT/'holdout.csv',index=False)
    print(ev[['entry','stop','time','act','trail','market','n','mean','median','wr','payout','win_bars','loss_bars','pf','passes']].round(4).to_string())

if __name__=='__main__':main()
