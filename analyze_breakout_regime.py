"""Two portfolio-level properties for the fresh HHV55 system (all measures causal).

A. Breakout-success persistence: market-wide mean 10-bar outcome (Open(i+1) -> Close(i+10)) of HHV55 signals whose
   outcome was already known at the current signal Close (signals 11..70 bars earlier). Does it predict current trades?
B. Strategy momentum: base portfolio equity above/below its own 100-day mean (known at the Close) vs next-20-day return.
Thresholds from 2000-2015 only; stability judged in 2016-20, 2021-25 and crypto (A).
"""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from analyze_new_system_properties import load_crypto

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'new_system_property_results'
PER=[('2000-15','2000-01-01','2015-12-31'),('2016-20','2016-01-01','2020-12-31'),('2021-25','2021-01-01','2025-12-31')]

def success_index(df,lo=11,hi=70):
    """Per date: mean 10-bar outcome of signals fired lo..hi trading days earlier (outcome complete before today)."""
    sigs=[]
    for t,f in df.groupby('Ticker',sort=True):
        f=f.reset_index(drop=True);c=f.Close;s=(c>f.High.shift(1).rolling(55).max()).to_numpy();O=f.Open.to_numpy();C=c.to_numpy();D=f['Date/Time'].to_numpy()
        for i in np.flatnonzero(s):
            if i+10<len(C):sigs.append((D[i],D[i+10],C[i+10]/O[i+1]-1))
    s=pd.DataFrame(sigs,columns=['sig','known','fwd10'])
    days=np.sort(df['Date/Time'].unique());pos={d:k for k,d in enumerate(days)}
    s['sk']=s.sig.map(pos);s['kk']=s.known.map(pos)
    # A signal counts on day k only once its outcome is known (known day < k) and while it is recent (sig day >= k-hi).
    start=(s.kk+1).to_numpy();end=np.minimum((s.sk+hi+1).to_numpy(),len(days));ok=start<end
    tot=np.zeros(len(days)+1);cnt=np.zeros(len(days)+1)
    np.add.at(tot,start[ok],s.fwd10.to_numpy()[ok]);np.add.at(tot,end[ok],-s.fwd10.to_numpy()[ok])
    np.add.at(cnt,start[ok],1);np.add.at(cnt,end[ok],-1)
    tot,cnt=np.cumsum(tot)[:len(days)],np.cumsum(cnt)[:len(days)]
    val=tot/np.where(cnt>=5,cnt,np.nan)
    return pd.Series(val,index=pd.DatetimeIndex(days))

def main():
    st,_=engine.load_data('stocks');cr=load_crypto()
    tf=pd.read_csv(OUT/'trade_features.csv',parse_dates=['signal_date'])
    rows=[]
    for market,df in [('stocks',st),('crypto',cr)]:
        idx=success_index(df);g=tf[tf.market==market].copy();g['succ']=g.signal_date.map(idx)
        if market=='stocks':
            q=g[g.period=='2000-15'].succ.quantile([.2,.4,.6,.8]).tolist();edges=[-np.inf]+q+[np.inf];pers=PER
        else:pers=[('crypto','2017-01-01','2025-12-31')]
        g['b']=pd.cut(g.succ,edges,labels=['q1 lowest','q2','q3','q4','q5 highest'])
        for per,a,b in pers:
            h=g[(g.signal_date>=a)&(g.signal_date<=b)]
            for lab,x in h.groupby('b',observed=True):
                r=x.ret;w=r>0;rows.append(dict(market=market,period=per,bucket=lab,n=len(x),mean=r.mean(),wr=w.mean(),payout=r[w].mean()/-r[~w].mean()))
    A=pd.DataFrame(rows);A.to_csv(OUT/'breakout_success_persistence.csv',index=False)
    pd.set_option('display.width',250);print(A.round(4).to_string())
    # B: strategy momentum on base portfolio equity.
    rowsb=[]
    for s in ['fees','spread1']:
        c=pd.read_csv(OUT/f'base_full_{s}_equity.csv',parse_dates=['date']).set_index('date').equity
        above=c>c.rolling(100).mean();fwd=c.shift(-20)/c-1
        m=c.resample('ME').last().pct_change();ac=m.autocorr()
        for per,a,b in PER:
            x=pd.DataFrame(dict(above=above,fwd=fwd)).loc[a:b].dropna()
            for lab,h in x.groupby('above'):rowsb.append(dict(scenario=s,period=per,equity_above_ma100=lab,days=len(h),mean_fwd20=h.fwd.mean(),pos_share=(h.fwd>0).mean()))
        rowsb.append(dict(scenario=s,period='monthly autocorr full',equity_above_ma100=None,days=None,mean_fwd20=ac,pos_share=None))
    B=pd.DataFrame(rowsb);B.to_csv(OUT/'strategy_momentum.csv',index=False);print(B.round(4).to_string())

if __name__=='__main__':main()
