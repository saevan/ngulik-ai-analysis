"""Overfitting battery for SK-5 (pre-registered pick) and the post-hoc candidate ER .2 + trail (CAND). Full 2000-01..2025-08, Rp1bn,
fee 0.15/0.25% (Swinger basis) unless stated; s25 = fee + 0.25%/side slippage. Record month = month with a new daily equity high.
T1 parameter sensitivity, one at a time, including values never in the search grid, plus a channel x ER heatmap.
T2 CSCV probability of backtest overfitting (Bailey et al.) over the 360-config search grid: monthly returns, 16 blocks, all 12,870 IS/OOS splits.
T3 deflated Sharpe ratio for N = 360 (grid) and N = 6,000 (all runs on this data, conservative).
T4 random-entry controls with the same exits, sizing and costs (50 seeds x 2 signal rates) and random ranking of the real signals (30 seeds).
T5 universe bootstrap: 50 random 80% subsets of the 100 tickers (SK-5, CAND, Swinger ideal on the same subsets).
T6 price noise: OHLC x (1+N(0,0.25%)) independently, 20 draws.
T7 calendar-year returns."""
from itertools import combinations
from multiprocessing import Pool
from pathlib import Path
from statistics import NormalDist
import json, math, zlib
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from backtest_open_next import stats
from backtest_idx_costs import Costs
import search_swinger_like_system as S
from evaluate_swinger_like_finalists import PropCosts

OUT=Path(__file__).resolve().parent/'overfit_results'
FEE=Costs();S25=PropCosts(slip=.0025)
SYS={'SK5':S.kwargs(dict(channel=5,er_min=.3,exit='cand',failed=0.,size_div=5)),
     'CAND':S.kwargs(dict(channel=5,er_min=.2,exit='cand_trail2',failed=0.,size_div=5))}
G={}

def summary(eq,tr):
    st=stats(eq,tr);return {k:st[k] for k in ['cagr','records','mdd','n','wr','payout','invested']}

def monthly(eq):
    me=eq.equity.resample('ME').last();return (me/me.shift(1).fillna(1e9)-1)

def job_run(a):
    tag,kw,cost,start,end,frkey=a
    fr=G[frkey];fr={t:g for t,f in fr.items() if len(g:=f[f['Date/Time']<=end])} if end else fr
    if 'rank_seed' in tag:kw=dict(kw,priority=rand_priority(tag['rank_seed']))  # built in the worker (closures do not pickle)
    with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(fr,cost_model=FEE if cost=='fee' else S25,start=start,**kw)
    return dict(tag,**summary(eq,tr)),monthly(eq) if tag.get('keep_monthly') else None

def job_swinger(a):
    tag,frkey=a
    eq,tr,_=run_portfolio(G[frkey],'afl_ideal');return dict(tag,**summary(eq,tr)),None

def noisy_frames(seed):
    rng=np.random.default_rng(1000+seed);out={}
    for t,f in G['all'].items():
        g=f.copy();px=g[['Open','High','Low','Close']].to_numpy(float)*(1+rng.normal(0,.0025,(len(g),4)))
        g['Open'],g['Close']=px[:,0],px[:,3];g['High']=px.max(axis=1);g['Low']=px.min(axis=1);out[t]=g
    return out

def rand_priority(seed):
    def f(fr):
        r=np.random.default_rng([seed,zlib.crc32(str(fr['Ticker'].iloc[0]).encode())]);return r.random(len(fr))
    return f

def cscv(M,S_=16,metric='geo'):
    T,N=M.shape;bounds=np.linspace(0,T,S_+1).astype(int);blocks=[np.arange(bounds[i],bounds[i+1]) for i in range(S_)]
    lr=np.log1p(M)
    def perf(idx):
        x=M[idx];
        if metric=='geo':return lr[idx].mean(axis=0)
        sd=x.std(axis=0,ddof=1);return np.where(sd>0,x.mean(axis=0)/sd,-np.inf)
    lam=[];is_best=[];oos_best=[];loss=0;n=0
    for comb in combinations(range(S_),S_//2):
        isx=np.concatenate([blocks[i] for i in comb]);oos=np.concatenate([blocks[i] for i in range(S_) if i not in comb])
        pi=perf(isx);po=perf(oos);k=int(np.argmax(pi))
        rank=(po<po[k]).sum()+.5*((po==po[k]).sum()-1)+1;w=rank/(N+1);lam.append(math.log(w/(1-w)))
        is_best.append(pi[k]);oos_best.append(po[k]);loss+=int(po[k]<0);n+=1
    lam=np.array(lam);ib=np.array(is_best);ob=np.array(oos_best);slope=np.polyfit(ib,ob,1)[0]
    return dict(metric=metric,splits=n,pbo=float((lam<=0).mean()),median_logit=float(np.median(lam)),prob_oos_loss=loss/n,
        mean_is_best=float(ib.mean()),mean_oos_of_is_best=float(ob.mean()),degradation_slope=float(slope))

def dsr(r,sr_trials,N):
    nd=NormalDist();r=np.asarray(r,float);T=len(r);sr=r.mean()/r.std(ddof=1)
    sk=((r-r.mean())**3).mean()/r.std(ddof=0)**3;ku=((r-r.mean())**4).mean()/r.std(ddof=0)**4
    g=0.5772156649;V=np.var(sr_trials,ddof=1)
    sr0=math.sqrt(V)*((1-g)*nd.inv_cdf(1-1/N)+g*nd.inv_cdf(1-1/(N*math.e)))
    z=(sr-sr0)*math.sqrt(T-1)/math.sqrt(1-sk*sr+(ku-1)/4*sr**2)
    psr0=(sr)*math.sqrt(T-1)/math.sqrt(1-sk*sr+(ku-1)/4*sr**2)
    return dict(N=N,months=T,sr_monthly=sr,sr_annual=sr*math.sqrt(12),skew=sk,kurt=ku,sr0_monthly=sr0,sr0_annual=sr0*math.sqrt(12),dsr=nd.cdf(z),psr_vs_zero=nd.cdf(psr0))

def main():
    OUT.mkdir(exist_ok=True)
    st,_=engine.load_data('stocks');G['all']={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}
    tickers=sorted(G['all'])
    # T1 sensitivity
    grid1={'channel':[3,4,5,6,7,8,10],'er_min':[None,.2,.25,.3,.35,.4],'fade':[1.5,2.,2.5,3.,None],'sma_len':[20,25,30,40,50],
           'gap_skip':[.01,.02,.03,None],'size_div':[4,5,6,7],'failed_exit':[None,0.,.01]}
    tasks=[]
    for sysn,kw in SYS.items():
        g1=dict(grid1);
        if sysn=='CAND':g1['trail_after']=[1.5,2.,3.]
        for k,vals in g1.items():
            for v in vals:
                kk=dict(kw);kk[k]=v
                for cost,start,end,win in [('fee','2000-01-01',None,'full'),('s25','2000-01-01',None,'full'),('fee','2016-01-01',None,'2016-25')]:
                    tasks.append((dict(test='T1',system=sysn,param=k,value=str(v),is_base=bool(kw.get(k)==v),cost=cost,window=win),kk,cost,start,end,'all'))
        for ch in [3,4,5,6,7,8,10]:
            for er in [None,.2,.25,.3,.35,.4]:
                kk=dict(kw,channel=ch,er_min=er);tasks.append((dict(test='T1heat',system=sysn,channel=ch,er_min=str(er),cost='fee',window='full'),kk,'fee','2000-01-01',None,'all'))
    # T2 grid monthly returns (fee and s25), full period
    for c in S.CONFIGS:
        for cost in ['fee','s25']:tasks.append((dict(test='T2',label=S.label(c),cost=cost,keep_monthly=True),S.kwargs(c),cost,'2000-01-01',None,'all'))
    # base runs with monthly returns
    for sysn,kw in SYS.items():
        for cost in ['fee','s25']:tasks.append((dict(test='base',system=sysn,cost=cost,keep_monthly=True),kw,cost,'2000-01-01',None,'all'))
    # T4 random entries and random ranking
    for sysn,kw in SYS.items():
        rk=dict(kw);[rk.pop(x,None) for x in ['strict_orders','presize','book_preopen','priority','channel','er_min','min_order_frac']]
        for p in [.005,.01]:
            for sd in range(50):tasks.append((dict(test='T4random',system=sysn,p=p,seed=sd),dict(rk,entry_mode='random',random_entry=(p,sd)),'fee','2000-01-01',None,'all'))
        for sd in range(30):tasks.append((dict(test='T4rank',system=sysn,seed=sd,rank_seed=sd),dict(kw,priority=None),'fee','2000-01-01',None,'all'))
    with Pool(4) as p:R=p.map(job_run,tasks,chunksize=4)
    rows=[r for r,_ in R];pd.DataFrame(rows).drop(columns=['keep_monthly'],errors='ignore').to_csv(OUT/'runs.csv',index=False)
    mon={};base_mon={}
    for (r,m) in R:
        if r['test']=='T2':mon[(r['label'],r['cost'])]=m
        if r['test']=='base':base_mon[(r['system'],r['cost'])]=m
    for cost in ['fee','s25']:
        M=pd.DataFrame({lab:m for (lab,c),m in mon.items() if c==cost});M.to_csv(OUT/f'grid_monthly_{cost}.csv')
    pd.DataFrame({f'{s}_{c}':m for (s,c),m in base_mon.items()}).to_csv(OUT/'base_monthly.csv')
    # T2 CSCV + T3 DSR
    res=[]
    for cost in ['fee','s25']:
        M=pd.read_csv(OUT/f'grid_monthly_{cost}.csv',index_col=0).to_numpy(float)
        for metric in ['geo','sharpe']:res.append(dict(cost=cost,**cscv(M,16,metric)))
    pd.DataFrame(res).to_csv(OUT/'cscv_pbo.csv',index=False)
    dres=[]
    for cost in ['fee','s25']:
        Mdf=pd.read_csv(OUT/f'grid_monthly_{cost}.csv',index_col=0);srs=(Mdf.mean()/Mdf.std(ddof=1)).to_numpy()
        for sysn in SYS:
            for N in [360,6000]:dres.append(dict(system=sysn,cost=cost,**dsr(base_mon[(sysn,cost)],srs,N)))
    pd.DataFrame(dres).to_csv(OUT/'deflated_sharpe.csv',index=False)
    # T5 universe bootstrap and T6 noise
    t5=[];sw=[]
    for b in range(50):
        rng=np.random.default_rng(500+b);keep=sorted(rng.choice(tickers,int(.8*len(tickers)),replace=False));G[f'u{b}']={t:G['all'][t] for t in keep}
        for sysn,kw in SYS.items():t5.append((dict(test='T5',system=sysn,draw=b),kw,'fee','2000-01-01',None,f'u{b}'))
        sw.append((dict(test='T5',system='SWINGER_ideal',draw=b),f'u{b}'))
    for d_ in range(20):
        G[f'n{d_}']=noisy_frames(d_)
        for sysn,kw in SYS.items():t5.append((dict(test='T6',system=sysn,draw=d_),kw,'fee','2000-01-01',None,f'n{d_}'))
    with Pool(4) as p:R5=p.map(job_run,t5,chunksize=2);RS=p.map(job_swinger,sw,chunksize=2)
    pd.DataFrame([r for r,_ in R5]+[r for r,_ in RS]).to_csv(OUT/'bootstrap_noise.csv',index=False)
    # T7 calendar years
    yr={}
    for sysn in SYS:
        m=base_mon[(sysn,'fee')];yr[sysn]=(1+m).groupby(m.index.year).prod()-1
    e=pd.read_csv(Path(__file__).resolve().parent/'prototype_swinger_benchmark_results/afl_ideal_net_equity.csv',index_col=0,parse_dates=True).equity
    ye=e.resample('YE').last();yr['SWINGER_ideal']=pd.Series((ye/ye.shift(1).fillna(1e9)-1).to_numpy(),index=ye.index.year)
    pd.DataFrame(yr).to_csv(OUT/'calendar_years.csv');print('done')

if __name__=='__main__':main()
