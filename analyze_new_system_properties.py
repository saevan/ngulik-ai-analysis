"""Market/stock properties at the signal bar that relate to the fresh HHV55 system's trade outcomes.

System: Close > HHV55(previous), stop Close <= entry - 3 ATR, trailing 2.5 ATR armed after +2 ATR, Open(i+1) fills.
Part 1: base portfolio (10 slots, Rp1bn, compounding) per window and cost scenario.
Part 2: unconstrained trade sample (every signal taken, one position per ticker, fees) with features known at the
signal Close (or at the entry Open for gap). Buckets use thresholds from 2000-2015 signals only; a property counts as
stable when the top-vs-bottom difference keeps its sign in 2000-15, 2016-20, 2021-25 and crypto.
Part 3: early path - final outcome conditional on the trade's return at its 3rd/5th/10th Close.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_open_next import run, stats, atr14
from backtest_idx_costs import Costs
from backtest_breakout_er import efficiency_ratio
from analyze_portfolio_regimes import regime_proxy

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'new_system_property_results'
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
PER={'2000-15':('2000-01-01','2015-12-31'),'2016-20':('2016-01-01','2020-12-31'),'2021-25':('2021-01-01','2025-12-31')}

def load_crypto():
    cr=pd.concat([pd.read_csv(p,parse_dates=['Date/Time']) for p in sorted((ROOT/'Data'/'crypto_binance_daily').glob('*.csv'))],ignore_index=True)
    cr['tradable']=cr.Volume>0;return cr

def features(df,trades):
    """Attach signal-bar features to trades (all computable at the signal Close; gap at the entry Open)."""
    proxy=regime_proxy(df)
    C=df.pivot(index='Date/Time',columns='Ticker',values='Close').sort_index()
    sma50=C.rolling(50,min_periods=50).mean();above=(C>sma50).where(sma50.notna())
    breadth=above.sum(axis=1)/above.notna().sum(axis=1).replace(0,np.nan)
    mom=np.log(C.ffill().shift(20)/C.ffill().shift(140));mom_rank=mom.rank(axis=1,pct=True)
    prox60=np.log(proxy.proxy/proxy.proxy.shift(60))
    rows=[]
    for t,f in df.groupby('Ticker',sort=True):
        f=f.reset_index(drop=True);g=trades[trades.ticker==str(t)]
        if g.empty:continue
        c=f.Close;h=f.High;a=atr14(f);tr=pd.concat([h-f.Low,(h-c.shift()).abs(),(f.Low-c.shift()).abs()],axis=1).max(axis=1)
        x=pd.DataFrame(dict(date=f['Date/Time'],vol_surge=f.Volume/f.Volume.shift(1).rolling(20).mean(),
            new52=(c>h.shift(1).rolling(250).max()).astype(float).where(h.shift(1).rolling(250).max().notna()),
            atr_pct=a/c,contraction=tr.rolling(10).mean()/tr.rolling(50).mean(),chase=(c-h.shift(1).rolling(55).max())/a,
            er20=efficiency_ratio(c,20),rs60=np.log(c/c.shift(60)),price=c,
            value20=(c*f.Volume).rolling(20).mean(),fresh=(~(c.shift(1)>h.shift(2).rolling(55).max())).astype(float)))
        x['rs60']=x.rs60-x.date.map(prox60).to_numpy()
        x['breadth']=x.date.map(breadth).to_numpy();x['mom_rank']=[mom_rank.at[d,t] if d in mom_rank.index else np.nan for d in x.date]
        O=f.Open.to_numpy();Cl=c.to_numpy()
        for r in g.itertuples():
            si,k,q=int(r.sig_i),int(r.entry_i),int(r.exit_i);row=x.iloc[si].to_dict()
            row.update(ticker=t,ret=r.net_return,win=r.net_return>0,bars=r.bars,signal_date=x.date.iloc[si],gap=O[k]/Cl[si]-1,
                dow=pd.Timestamp(f['Date/Time'].iloc[k]).dayofweek,month=pd.Timestamp(f['Date/Time'].iloc[k]).month,
                regime=proxy.regime.get(f['Date/Time'].iloc[k],'unknown'))
            for n in (3,5,10):row[f'r{n}']=Cl[k+n-1]/O[k]-1 if k+n-1<q and k+n-1<len(Cl) else np.nan
            rows.append(row)
    return pd.DataFrame(rows)

def bucket_table(d,feat,edges):
    out=[];d=d.copy();d['b']=pd.cut(d[feat],edges,include_lowest=True,duplicates='drop')
    for (per,b),g in d.groupby(['period','b'],observed=True):
        r=g.ret;w=r>0
        out.append(dict(feature=feat,period=per,bucket=str(b),n=len(g),mean=r.mean(),wr=w.mean(),payout=r[w].mean()/-r[~w].mean() if (~w).any() else np.nan,bars=g.bars.mean()))
    return out

def main():
    OUT.mkdir(exist_ok=True)
    st,_=engine.load_data('stocks');frames={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}
    rows=[]
    for w,(a,b) in WINDOWS.items():
        fr={t:f[f['Date/Time']<=b] for t,f in frames.items()}
        for s,cm in {'fees':Costs(),'spread1':Costs(grid=True,ticks_per_side=1,round_lot=100)}.items():
            with np.errstate(invalid='ignore'):c,t=run(fr,cost_model=cm,start=a)
            rows.append(dict(window=w,scenario=s,**stats(c,t)))
            if w=='full':c.to_csv(OUT/f'base_full_{s}_equity.csv');t.to_csv(OUT/f'base_full_{s}_trades.csv',index=False)
    base=pd.DataFrame(rows);base.to_csv(OUT/'base_portfolio.csv',index=False)
    pd.set_option('display.width',250);print(base.round(4).to_string())
    # Part 2: unconstrained trade sample, stocks and crypto.
    with np.errstate(invalid='ignore'):_,ts=run(frames,cost_model=Costs(),slots=100000)
    fs=features(st,ts);fs['market']='stocks'
    fs['period']=np.select([fs.signal_date<=pd.Timestamp(PER['2000-15'][1]),fs.signal_date<=pd.Timestamp(PER['2016-20'][1])],['2000-15','2016-20'],'2021-25')
    cr=load_crypto();crf={str(k):f.reset_index(drop=True) for k,f in cr.groupby('Ticker',sort=True)}
    with np.errstate(invalid='ignore'):_,tc=run(crf,cost_model=Costs(buy_fee=.001,sell_fee=.001),slots=100000)
    fc=features(cr,tc);fc['market']='crypto';fc['period']='crypto'
    d=pd.concat([fs,fc],ignore_index=True);d.to_csv(OUT/'trade_features.csv',index=False)
    train=fs[fs.period=='2000-15'];tabs=[]
    for feat in ['vol_surge','atr_pct','contraction','chase','er20','rs60','mom_rank','breadth','value20','price','gap']:
        q=train[feat].quantile([.2,.4,.6,.8]).tolist();edges=[-np.inf]+q+[np.inf]
        tabs+=bucket_table(d,feat,edges)
    for feat,edges in {'new52':[-.5,.5,1.5],'fresh':[-.5,.5,1.5],'dow':[-.5,.5,1.5,2.5,3.5,4.5,6.5]}.items():tabs+=bucket_table(d,feat,edges)
    tb=pd.DataFrame(tabs);tb.to_csv(OUT/'feature_buckets.csv',index=False)
    # Stability summary: top bucket minus bottom bucket mean per period.
    summ=[]
    for feat,g in tb.groupby('feature'):
        for per,h in g.groupby('period'):
            h=h.reset_index(drop=True)
            summ.append(dict(feature=feat,period=per,bottom=h['mean'].iloc[0],top=h['mean'].iloc[-1],diff=h['mean'].iloc[-1]-h['mean'].iloc[0],
                wr_diff=h.wr.iloc[-1]-h.wr.iloc[0],n_top=h.n.iloc[-1],n_bottom=h.n.iloc[0]))
    sm=pd.DataFrame(summ);sm.to_csv(OUT/'feature_stability.csv',index=False)
    piv=sm.pivot(index='feature',columns='period',values='diff')[['2000-15','2016-20','2021-25','crypto']]
    piv['stable_sign']=(np.sign(piv).nunique(axis=1)==1)
    print(piv.round(4).to_string())
    # Part 3: early path.
    ep=[]
    for n in (3,5,10):
        for per,g in d.groupby('period'):
            g=g[g[f'r{n}'].notna()]
            for lab,h in {'<=0':g[g[f'r{n}']<=0],'>0':g[g[f'r{n}']>0]}.items():
                ep.append(dict(bar=n,period=per,state=lab,n=len(h),share=len(h)/len(g),final_mean=h.ret.mean(),final_wr=(h.ret>0).mean(),bars=h.bars.mean()))
    ep=pd.DataFrame(ep);ep.to_csv(OUT/'early_path.csv',index=False);print(ep.round(4).to_string())

if __name__=='__main__':main()
