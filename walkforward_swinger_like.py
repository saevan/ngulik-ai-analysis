"""Honest out-of-sample estimate of the SEARCH PROCEDURE in search_swinger_like_system.py (same 361 configs).
Expanding folds: train 2000->2007/2011/2015/2020, test the next 4/4/5/4.6 years (fresh Rp1bn each test, chained).
Rules fixed before running: R_fee = max train fee CAGR with train fee MDD >= -30% (Swinger's cost basis);
R_s25 = max train CAGR under fee + 0.25%/side slippage with MDD >= -35% (realistic cost basis).
Each chosen config is tested under fee and s25. Swinger ideal over the same test years is the benchmark."""
from multiprocessing import Pool
import json
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_open_next import stats
import search_swinger_like_system as S
from evaluate_swinger_like_finalists import PropCosts
from backtest_idx_costs import Costs
FOLDS=[(('2000-01-01','2007-12-31'),('2008-01-01','2011-12-31')),(('2000-01-01','2011-12-31'),('2012-01-01','2015-12-31')),
       (('2000-01-01','2015-12-31'),('2016-01-01','2020-12-31')),(('2000-01-01','2020-12-31'),('2021-01-01','2025-08-15'))]
COST={'fee':Costs(),'s25':PropCosts(slip=.0025)}
CFGS=[S.BASE]+S.CONFIGS
FR=S.FR
def job(a):
    ci,(s,e),c=a;cfg=CFGS[ci]
    fr={t:g for t,f in FR.items() if len(g:=f[f['Date/Time']<=e])}
    with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(fr,cost_model=COST[c],start=s,**S.kwargs(cfg))
    st=stats(eq,tr);return dict(ci=ci,label=S.label(cfg),start=s,end=e,cost=c,cagr=st['cagr'],records=st['records'],mdd=st['mdd'],n=st['n'],wr=st['wr'],
        curve=None if (s,e) in [tr_ for tr_,_ in FOLDS] else [[str(d.date()),float(v)] for d,v in eq.equity.items()])
def main():
    st,_=engine.load_data('stocks')
    for k,f in st.groupby('Ticker',sort=True):FR[str(k)]=f.reset_index(drop=True)
    with Pool(4) as p:tr_rows=p.map(job,[(ci,trw,c) for trw,_ in FOLDS for ci in range(len(CFGS)) for c in COST],chunksize=8)
    T=pd.DataFrame(tr_rows).drop(columns='curve');T.to_csv(S.OUT/'walkforward_train.csv',index=False)
    picks=[]
    for trw,tsw in FOLDS:
        g=T[(T.start==trw[0])&(T.end==trw[1])]
        f=g[(g.cost=='fee')&(g.mdd>=-.30)];r=g[(g.cost=='s25')&(g.mdd>=-.35)]
        for rule,h in [('R_fee',f),('R_s25',r)]:
            b=h.loc[h.cagr.idxmax()];picks.append(dict(rule=rule,train=f'{trw[0]}..{trw[1]}',test=tsw,ci=int(b.ci),label=b.label,train_cagr=b.cagr))
    with Pool(4) as p:te=p.map(job,[(k['ci'],k['test'],c) for k in picks for c in COST])
    out=[];chains={}
    j=0
    for k in picks:
        for c in COST:
            r=te[j];j+=1
            out.append(dict(rule=k['rule'],train=k['train'],test=f"{k['test'][0]}..{k['test'][1]}",label=k['label'],train_cagr=k['train_cagr'],cost=c,test_cagr=r['cagr'],test_records=r['records'],test_mdd=r['mdd'],test_n=r['n']))
            key=(k['rule'],c);eq=pd.Series([v for _,v in r['curve']],index=pd.to_datetime([d for d,_ in r['curve']]))/1e9
            chains.setdefault(key,[]).append(eq)
    O=pd.DataFrame(out);O.to_csv(S.OUT/'walkforward_tests.csv',index=False)
    summ=[]
    for (rule,c),parts in chains.items():
        lvl=1.;seg=[]
        for p_ in parts:seg.append(p_*lvl);lvl*=float(p_.iloc[-1])
        ch=pd.concat(seg);yrs=(ch.index[-1]-pd.Timestamp('2008-01-01')).days/365.25
        peak=ch.cummax().clip(lower=1.);newh=ch>peak.shift(1).fillna(1.)+1e-12
        rec=newh.groupby(ch.index.to_period('M')).any()
        summ.append(dict(rule=rule,cost=c,cagr=float(ch.iloc[-1]**(1/yrs)-1),records=int(rec.sum()),months=len(rec),mdd=float((ch/ch.cummax()-1).min())))
    # Swinger ideal chained the same way (slices of its single run, rebased per test window)
    e=pd.read_csv(S.ROOT/'prototype_swinger_benchmark_results/afl_ideal_net_equity.csv',index_col=0,parse_dates=True).equity
    lvl=1.;seg=[]
    for _,(a,b) in FOLDS:
        prev=e[e.index<a];x=e[a:b]/float(prev.iloc[-1]);seg.append(x*lvl);lvl*=float(x.iloc[-1])
    ch=pd.concat(seg);yrs=(ch.index[-1]-pd.Timestamp('2008-01-01')).days/365.25;peak=ch.cummax().clip(lower=1.);newh=ch>peak.shift(1).fillna(1.)+1e-12
    rec=newh.groupby(ch.index.to_period('M')).any()
    summ.append(dict(rule='SWINGER_IDEAL',cost='fee',cagr=float(ch.iloc[-1]**(1/yrs)-1),records=int(rec.sum()),months=len(rec),mdd=float((ch/ch.cummax()-1).min())))
    pd.DataFrame(summ).to_csv(S.OUT/'walkforward_summary.csv',index=False)
    print(O.to_string());print(pd.DataFrame(summ).to_string());print('done')
if __name__=='__main__':main()
