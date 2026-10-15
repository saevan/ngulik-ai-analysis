"""Grid research per market regime (uptrend / downtrend / choppy) to approach Swinger ideal.

Execution: signal at Close i, fill Open(i+1) (next tradable). Trade-level, one position per stock, fee .15/.25%.
Regime at signal bar from regime_proxy (ER20 of equal-weight proxy, lagged one bar).
Levers aimed at the diagnosed gaps vs Swinger ideal in choppy:
  stop distance (ATR on Close, or fixed LLV5/LLV10 of Lows before entry), earlier trailing activation,
  trailing width, entry-chase filter (skip if signal Close is > x ATR above the breakout level), channel 20/55.
Selection per regime on 2000-2015 only (C1-C5 passes, then mean). 2016-2025 and crypto are hold-out.
"""
from pathlib import Path
from itertools import product
from multiprocessing import Pool
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
import new_system_search as ns
from analyze_portfolio_regimes import regime_proxy

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'regime_grid_results'
LEV=dict(channel=[20,55],chase=[0.,.5,1.],stop=['atr1.5','atr2','atr3','llv5','llv10'],act=[.5,1.,2.],trail=[1.5,2.,2.5])
CONFIGS=[dict(zip(LEV,v)) for v in product(*LEV.values())]
REG=['uptrend','downtrend','sideways']
X={};RG={}

def prep(f):
    x=ns.features(f);L=f.Low
    x['L']=L.to_numpy(float);x['llv5']=L.rolling(5).min().to_numpy(float);x['llv10']=L.rolling(10).min().to_numpy(float)
    x['hhv20a']=x['hhv20'].to_numpy(float);x['hhv55a']=x['hhv55'].to_numpy(float)
    return x

def sim(x,cfgs,regs,cost):
    """cfgs: dict regime->cfg (same cfg for all regimes in the per-regime grid). Returns trades (ret,bars,entry_date,regime,signal_date)."""
    C,O,A,T,D=x['C'],x['O'],x['atr'],x['tradable'],x['date'];n=len(C);out=[];i=0
    while i<n-1:
        rg=regs[i]
        if rg not in cfgs:i+=1;continue
        c=cfgs[rg];lvl=x['hhv55a'][i] if c['channel']==55 else x['hhv20a'][i]
        if not(np.isfinite(lvl) and C[i]>lvl and np.isfinite(A[i]) and A[i]>0):i+=1;continue
        if c['chase'] and (C[i]-lvl)>c['chase']*A[i]:i+=1;continue
        k=i+1
        while k<n and not T[k]:k+=1
        if k>=n:break
        e=O[k];a0=A[i];s=c['stop']
        stop=e-float(s[3:])*a0 if s.startswith('atr') else x[s][i]
        peak=C[k];armed=False;ex=None
        for j in range(k,n-1):
            peak=max(peak,C[j])
            if peak>=e+c['act']*a0:armed=True
            if C[j]<=stop or (armed and C[j]<=peak-c['trail']*a0):ex=j;break
        q=None if ex is None else ex+1
        while q is not None and q<n and not T[q]:q+=1
        if q is None or q>=n:
            out.append((C[n-1]*(1-cost[1])/(e*(1+cost[0]))-1,n-k,D[k],rg,D[i]));break
        out.append((O[q]*(1-cost[1])/(e*(1+cost[0]))-1,q-k,D[k],rg,D[i]));i=q
    return out

def run_one(args):
    cfg,market=args;tr=[]
    for t,x in X[market].items():tr+=sim(x,{r:cfg for r in REG},RG[market][t],ns.COST[market])
    return tr

def summarize(tr,per,regime):
    if not tr:return None
    d=pd.DataFrame(tr,columns=['ret','bars','entry','regime','signal'])
    d=d[(d.regime==regime)&(d.signal>=np.datetime64(per[0]))&(d.signal<=np.datetime64(per[1]))]
    return ns.score(list(zip(d.ret,d.bars)))

def swinger_ref(reg):
    t=pd.read_csv(ROOT/'prototype_swinger_benchmark_results'/'afl_ideal_net_trades.csv',parse_dates=['entry_date']);t['regime']=t.entry_date.map(reg)
    rows=[]
    for r in REG:
        for pn,(a,b) in {'2000-2015':('2000-01-01','2015-12-31'),'2016-2025':('2016-01-01','2025-12-31')}.items():
            g=t[(t.regime==r)&(t.entry_date>=a)&(t.entry_date<=b)];s=ns.score(list(zip(g.net_return,g.bars)))
            rows.append(dict(system='Swinger ideal',regime=r,period=pn,**s))
    return rows

def load_market(name,df):
    reg=regime_proxy(df).regime
    X[name]={};RG[name]={}
    for t,f in df.groupby('Ticker',sort=True):
        f=f.reset_index(drop=True);X[name][t]=prep(f);RG[name][t]=pd.Series(f['Date/Time']).map(reg).fillna('unknown').to_numpy()
    return reg

def main():
    OUT.mkdir(exist_ok=True)
    data=ns.load();reg=load_market('stocks',data['stocks']);load_market('crypto',data['crypto'])
    (OUT/'PLAN.json').write_text(json.dumps(dict(doc=__doc__,levers=LEV,n_configs=len(CONFIGS),
        selection='Per regime on stocks 2000-2015: max passes (C1-C5), then mean. Combined system uses each regime own config chosen at the signal bar; evaluated 2016-2025 stocks and crypto (crypto regime from its own 8-coin proxy).'),indent=2),encoding='utf-8')
    with Pool(4) as p:res=p.map(run_one,[(c,'stocks') for c in CONFIGS],chunksize=4)
    rows=[]
    for c,tr in zip(CONFIGS,res):
        for r in REG:
            for pn,per in {'2000-2015':('2000-01-01','2015-12-31'),'2016-2025':('2016-01-01','2025-12-31')}.items():
                s=summarize(tr,per,r)
                if s:rows.append(dict(**c,regime=r,period=pn,**s))
    g=pd.DataFrame(rows);g.to_csv(OUT/'grid.csv',index=False)
    chosen={}
    for r in REG:
        tr=g[(g.regime==r)&(g.period=='2000-2015')].sort_values(['passes','mean'],ascending=False)
        chosen[r]={k:tr.iloc[0][k] for k in LEV};chosen[r]={k:(v if isinstance(v,str) else float(v)) for k,v in chosen[r].items()}
    (OUT/'FROZEN.json').write_text(json.dumps(chosen,indent=2),encoding='utf-8');print('FROZEN',chosen,flush=True)
    # Combined regime-switch system.
    ev=swinger_ref(reg)
    for market in ['stocks','crypto']:
        tr=[]
        for t,x in X[market].items():tr+=sim(x,chosen,RG[market][t],ns.COST[market])
        d=pd.DataFrame(tr,columns=['ret','bars','entry','regime','signal']);d.to_csv(OUT/f'combined_{market}_trades.csv',index=False)
        pers={'stocks':{'2000-2015':('2000-01-01','2015-12-31'),'2016-2025':('2016-01-01','2025-12-31')},'crypto':{'2017-2025':('2017-01-01','2025-12-31')}}[market]
        for pn,(a,b) in pers.items():
            for r in REG+['all']:
                h=d[(d.signal>=np.datetime64(a))&(d.signal<=np.datetime64(b))&((d.regime==r) if r!='all' else True)]
                s=ns.score(list(zip(h.ret,h.bars)))
                if s:ev.append(dict(system=f'Regime-switch ({market})',regime=r,period=pn,**s))
        # Base: previous single new system for comparison.
        base={r:dict(channel=55,chase=0.,stop='atr3',act=2.,trail=2.5) for r in REG}
        tb=[]
        for t,x in X[market].items():tb+=sim(x,base,RG[market][t],ns.COST[market])
        d=pd.DataFrame(tb,columns=['ret','bars','entry','regime','signal'])
        for pn,(a,b) in pers.items():
            for r in REG+['all']:
                h=d[(d.signal>=np.datetime64(a))&(d.signal<=np.datetime64(b))&((d.regime==r) if r!='all' else True)]
                s=ns.score(list(zip(h.ret,h.bars)))
                if s:ev.append(dict(system=f'Base HHV55 ({market})',regime=r,period=pn,**s))
    e=pd.DataFrame(ev);e.to_csv(OUT/'evaluation.csv',index=False)
    pd.set_option('display.width',250)
    print(e[['system','regime','period','n','mean','median','wr','avg_win','avg_loss','payout','win_bars','loss_bars','pf','passes']].round(4).to_string())

if __name__=='__main__':main()
