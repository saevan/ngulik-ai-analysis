"""Run every UTS test for the Breakout Stop ER strategy and write uts/output/results.json (+ CSV data).

Pre-registered choices (written before running this file):
- In-sample = first 70% of the calendar span (2000-01-04 .. split), out-of-sample = remaining 30%.
- 5 optimized parameters: channel N, er_min, sma_exit, fade_atr, gap. Grid 3x3x3x3x3 = 243 combinations.
- Selection objective (in-sample only, after costs): mean CAGR of the combination and its one-step grid neighbours
  (plateau-seeking), among combinations with >= 100 trades and MDD > -50%.
- Walk-forward: rolling 6-year train / 3-year test windows, same grid and objective inside each train window; test
  windows start flat with the initial capital; combined OOS curve = chained test-window returns.
- Official execution: fee buy 0.15% / sell 0.25%, 1 tick each side at offer/bid, IDX tick grid, 100-share lots,
  ARA/ARB, no fills on zero-volume bars, order <= 5% of 20-day average traded value, Rp1,000,000,000, 10 slots, compounding.
"""
from dataclasses import replace, asdict
from itertools import product
from multiprocessing import Pool
from pathlib import Path
import hashlib, json, math
import numpy as np
import pandas as pd
from .data import load_stocks, load_crypto, load_forex, frames as to_frames
from .engine import run, Params, Execution
from . import metrics as M

OUT=Path(__file__).resolve().parent/'output'
CAPITAL=1e9
GRID=dict(channel=[15,20,30],er_min=[.2,.3,.4],sma_exit=[20,30,50],fade_atr=[1.5,2.,3.],gap=[.01,.02,.03])
KEYS=list(GRID)
OFFICIAL=Execution()
GROSS=Execution(buy_fee=0.,sell_fee=0.,ticks=0.)
DOUBLE=Execution(buy_fee=.003,sell_fee=.005,ticks=2.)
FREEZE_DATE='2026-10-16'
G={}

def P(cfg):return replace(Params(),**{k:cfg[k] for k in KEYS})

def quiet_run(fr,p,ex,start,end=None,market='stocks'):
    with np.errstate(invalid='ignore',divide='ignore'):return run(fr,p,ex,start=start,end=end,market=market)

def job(a):
    cfg,start,end=a
    eq,tr,op=quiet_run(G['fr'],P(cfg),OFFICIAL,start,end)
    m=M.compute(eq,tr,CAPITAL,op)
    return dict(**cfg,start=start,end=end,cagr=m['cagr'],mdd=m['mdd'],trades=m['trades'],record_month_pct=m['record_month_pct'],profit_factor=m.get('profit_factor'))

def smoothed_pick(rows):
    df=pd.DataFrame(rows);idx={k:{v:i for i,v in enumerate(GRID[k])} for k in KEYS}
    key=lambda r:tuple(idx[k][r[k]] for k in KEYS);by={key(r):r for r in df.to_dict('records')}
    sm=[]
    for r in df.to_dict('records'):
        kk=key(r);vals=[r['cagr']]
        for j in range(len(KEYS)):
            for s in (-1,1):
                nb=list(kk);nb[j]+=s
                if tuple(nb) in by:vals.append(by[tuple(nb)]['cagr'])
        sm.append(np.mean(vals))
    df['smoothed_cagr']=sm
    ok=df[(df.trades>=100)&(df.mdd>-.5)]
    best=ok.sort_values(['smoothed_cagr','cagr'],ascending=False).iloc[0]
    return {k:(int(best[k]) if k in('channel','sma_exit') else float(best[k])) for k in KEYS},df

def series(eq):return [[str(d.date()),round(float(v),2)] for d,v in eq.equity.items()]

def main():
    OUT.mkdir(exist_ok=True)
    st=load_stocks();fr=to_frames(st);G['fr']=fr
    # Backtest starts 2000-01-01 (research period); earlier bars (from 1994 for a few tickers) only warm up indicators.
    d0,d1=st.loc[st['Date/Time']>='2000-01-01','Date/Time'].min(),st['Date/Time'].max()
    split=(d0+pd.Timedelta(days=round((d1-d0).days*.7))).normalize()
    START=str(d0.date());SPLIT=str(split.date());OOS0=str((split+pd.Timedelta(days=1)).date());END=str(d1.date())
    res=dict(meta=dict(start=START,end=END,is_end=SPLIT,oos_start=OOS0,freeze_date=FREEZE_DATE,capital=CAPITAL,grid=GRID,
        official=asdict(OFFICIAL),gross=asdict(GROSS),double=asdict(DOUBLE),tickers=int(st.Ticker.nunique()),bars=int(len(st))))
    # Benchmark: equal-weight daily-rebalanced index of the same 100 stocks (not IHSG; IHSG not reachable offline).
    closes=st.pivot(index='Date/Time',columns='Ticker',values='Close').sort_index().ffill()
    closes=closes.loc['2000-01-01':]
    bench_rebal=(1+closes.pct_change(fill_method=None).mean(axis=1).fillna(0)).cumprod()*CAPITAL  # daily rebalanced, cost-free (reference only)
    # True buy-and-hold: 1/N of the capital per ticker; a ticker's slice stays in cash until its first available close, then is bought and never rebalanced.
    raw=st.pivot(index='Date/Time',columns='Ticker',values='Close').sort_index().loc['2000-01-01':]
    first=raw.bfill().iloc[0]*0+raw.apply(lambda c:c.dropna().iloc[0] if c.notna().any() else np.nan)
    rel=raw.ffill()/first;rel=rel.where(raw.ffill().notna(),1.0).fillna(1.0)
    bench=(rel.mean(axis=1))*CAPITAL
    G['bench']=bench
    # A1. In-sample grid + selection.
    combos=[dict(zip(KEYS,v)) for v in product(*GRID.values())]
    with Pool(4) as pool:is_rows=pool.map(job,[(c,START,SPLIT) for c in combos],chunksize=4)
    chosen,isdf=smoothed_pick(is_rows);isdf.to_csv(OUT/'is_grid.csv',index=False)
    res['chosen']=chosen;print('chosen',chosen,flush=True)
    p=P(chosen)
    def full(ex,start=START,end=None,pp=p):
        eq,tr,op=quiet_run(fr,pp,ex,start,end);return eq,tr,op,M.compute(eq,tr,CAPITAL,op,bench)
    eq,tr,op,mm=full(OFFICIAL);res['main']=mm
    eq.to_csv(OUT/'equity_main.csv');tr.to_csv(OUT/'trades_main.csv',index=False);op.to_csv(OUT/'open_positions_main.csv',index=False)
    res['monthly_returns']={str(k.date()):float(v) for k,v in M.monthly_returns(eq,CAPITAL).items()}
    res['yearly_returns']={str(k.year):float(v) for k,v in M.yearly_returns(eq,CAPITAL).items()}
    res['bench_rebal_cagr']=float((bench_rebal.iloc[-1]/bench_rebal.iloc[0])**(365.25/(bench_rebal.index[-1]-bench_rebal.index[0]).days)-1);res['bench_rebal_mdd']=float((bench_rebal/bench_rebal.cummax()-1).min())
    res['bench_yearly']={str(k.year):float(v) for k,v in (bench.resample('YE').last()/bench.resample('YE').last().shift(1).fillna(bench.iloc[0])-1).items()}
    res['without_top5']=M.without_top_trades(eq,tr,CAPITAL,5)
    res['bootstrap']=M.bootstrap(tr,eq,CAPITAL)
    # A1 side by side: IS and OOS (fresh capital at OOS start, indicators warmed with earlier data).
    for name,(a,b) in {'in_sample':(START,SPLIT),'out_of_sample':(OOS0,None)}.items():
        e,t,o,m=full(OFFICIAL,a,b);res[name]=m;e.to_csv(OUT/f'equity_{name}.csv')
        res[name+'_continuous']=M.slice_metrics(eq,tr,a,b)  # same numbers recomputable from equity_main / trades_main
    # D. Cost scenarios, delay, diagnostics, capital capacity.
    for name,ex in {'gross':GROSS,'double_cost':DOUBLE,'delay_1bar':replace(OFFICIAL,delay=1),'no_liquidity_cap':replace(OFFICIAL,liquidity=None),
                    'no_price_limits':replace(OFFICIAL,price_limits=False),'capital_100m':replace(OFFICIAL,capital=1e8),'capital_10bn':replace(OFFICIAL,capital=1e10)}.items():
        cap=ex.capital;e,t,o=quiet_run(fr,p,ex,START);m=M.compute(e,t,cap,o,bench);res[name]=m
        if name in('gross','double_cost','delay_1bar'):e.to_csv(OUT/f'equity_{name}.csv')
        print(name,round(m['cagr'],4),flush=True)
    for name,(a,b) in {'delay_1bar_oos':(OOS0,None),'double_cost_oos':(OOS0,None)}.items():
        ex=replace(OFFICIAL,delay=1) if 'delay' in name else DOUBLE
        e,t,o,m=full(ex,a,b);res[name]=m
    research=dict(channel=20,er_min=.3,sma_exit=30,fade_atr=2.,gap=.02)
    e,t,o,m=full(OFFICIAL,pp=P(research));res['research_default']=dict(params=research,**m)
    # A2. Walk-forward.
    wf=[];chain=[];level=1.
    tests=[('2009-01-01','2011-12-31'),('2012-01-01','2014-12-31'),('2015-01-01','2017-12-31'),('2018-01-01','2020-12-31'),('2021-01-01','2023-12-31'),('2024-01-01',END)]
    with Pool(4) as pool:
        for a,b in tests:
            ta=str(pd.Timestamp(a).replace(year=pd.Timestamp(a).year-6).date());tb=str((pd.Timestamp(a)-pd.Timedelta(days=1)).date())
            rows=pool.map(job,[(c,ta,tb) for c in combos],chunksize=4);pick,_=smoothed_pick(rows)
            tr_row=[r for r in rows if all(r[k]==pick[k] for k in KEYS)][0]
            e,t,o=quiet_run(fr,P(pick),OFFICIAL,a,b);m=M.compute(e,t,CAPITAL,o,bench)
            wf.append(dict(train=f'{ta}..{tb}',test=f'{a}..{b}',params=pick,train_cagr=tr_row['cagr'],test_cagr=m['cagr'],test_mdd=m['mdd'],
                test_trades=m['trades'],test_win_ratio=m.get('win_ratio'),test_pf=m.get('profit_factor'),test_record_pct=m['record_month_pct']))
            r=e.equity/CAPITAL;chain+= [[str(d.date()),round(level*float(v)*CAPITAL,2)] for d,v in r.items()];level*=float(r.iloc[-1])
            print('WF',a,pick,round(m['cagr'],4),flush=True)
    res['walk_forward']=wf
    ce=pd.Series([v for _,v in chain],index=pd.to_datetime([d for d,_ in chain]));yrs=(ce.index[-1]-pd.Timestamp(tests[0][0])).days/365.25
    res['walk_forward_combined']=dict(cagr=(ce.iloc[-1]/CAPITAL)**(1/yrs)-1,mdd=float((ce/ce.cummax()-1).min()),start=tests[0][0],end=END)
    res['walk_forward_curve']=chain
    # A3. Sensitivity: each parameter x0.5/0.8/1.2/1.5 (full period and OOS), plus channel x er_min heatmap.
    sens=[];mult=[.5,.8,1.,1.2,1.5]
    def val(k,x):return int(round(chosen[k]*x)) if k in('channel','sma_exit') else round(chosen[k]*x,4)
    tasks=[]
    for k in KEYS:
        for x in mult:tasks.append(({**chosen,k:val(k,x)},k,x))
    heat=[({**chosen,'channel':val('channel',a),'er_min':val('er_min',b)},a,b) for a in mult for b in mult]
    with Pool(4) as pool:
        sr=pool.map(job,[(c,START,None) for c,_,_ in tasks],chunksize=2);so=pool.map(job,[(c,OOS0,None) for c,_,_ in tasks],chunksize=2)
        hr=pool.map(job,[(c,START,None) for c,_,_ in heat],chunksize=2)
    for (c,k,x),r,o in zip(tasks,sr,so):sens.append(dict(param=k,mult=x,value=c[k],cagr=r['cagr'],mdd=r['mdd'],record_pct=r['record_month_pct'],trades=r['trades'],oos_cagr=o['cagr']))
    res['sensitivity']=sens;res['heatmap']=[dict(channel=c['channel'],er_min=c['er_min'],ch_mult=a,er_mult=b,cagr=r['cagr'],mdd=r['mdd']) for (c,a,b),r in zip(heat,hr)]
    # A4. Robustness extras: random entries (same exits/sizing), other markets with the same parameters.
    trig=sum(int((d_:=__import__('uts.engine',fromlist=['prepare']).prepare(f,p,OFFICIAL))['armed'].sum()) for f in fr.values())
    tdays=int(st.tradable.sum());prob=trig/tdays*.25
    rand=[]
    for s in range(20):
        e,t,o=quiet_run(fr,p,replace(OFFICIAL,entry='random',random_p=prob,seed=s),START);m=M.compute(e,t,CAPITAL,o)
        rand.append(dict(seed=s,cagr=m['cagr'],mdd=m['mdd'],trades=m['trades'],record_pct=m['record_month_pct']))
    res['random_entry']=dict(prob=prob,runs=rand)
    cr=to_frames(load_crypto());e,t,o=quiet_run(cr,p,Execution(buy_fee=.001,sell_fee=.001,ticks=0,lot=0,grid=False,spread_pct=.0005,liquidity=None,price_limits=False),'2017-01-01',market='crypto')
    res['crypto']=M.compute(e,t,CAPITAL,o)
    fx=to_frames(load_forex(0));e,t,o=quiet_run(fx,p,Execution(buy_fee=0,sell_fee=0,ticks=0,lot=0,grid=False,spread_pct=.00015,liquidity=None,price_limits=False),'2023-01-01',market='forex')
    res['forex']=M.compute(e,t,CAPITAL,o)
    # C. Look-ahead truncation test on the official configuration.
    trunc=[]
    for cut in ['2008-06-30','2016-01-15','2021-03-31']:
        e,t,o=quiet_run(fr,p,OFFICIAL,START,cut);bef=e.index<pd.Timestamp(cut)
        ok=np.allclose(e.equity[bef].to_numpy(),eq.equity.reindex(e.index[bef]).to_numpy(),rtol=1e-12,atol=1e-6)
        tc=t[pd.to_datetime(t.exit_date)<pd.Timestamp(cut)];TC=tr[pd.to_datetime(tr.exit_date)<pd.Timestamp(cut)]
        ok2=len(tc)==len(TC) and np.allclose(tc.pnl.to_numpy(),TC.pnl.to_numpy(),rtol=1e-12,atol=1e-6)
        trunc.append(dict(cut=cut,days=int(bef.sum()),trades=len(tc),identical=bool(ok and ok2)))
    res['truncation_test']=trunc
    # Research effort disclosure: rows in earlier result tables of the repository + this pipeline.
    root=Path(__file__).resolve().parent.parent;n=0
    skip=['trades','equity','daily','proxy','months','features','anatomy','decomposition','yearly','buckets','attribution','choppy_days']
    for f in root.glob('*_results/*.csv'):  # one row = one simulation summary; ledgers/curves excluded
        if any(x in f.name for x in skip):continue
        if any(x in f.name for x in ['comparison','grid','train','holdout','stress','evaluation','summary']):
            try:n+=len(pd.read_csv(f,usecols=[0]))
            except Exception:pass
    res['research_runs_logged']=n;res['pipeline_runs']=dict(is_grid=len(combos),walk_forward=len(combos)*len(tests),sensitivity=len(tasks)*2+len(heat),random=20)
    h=hashlib.sha256()
    for f in ['engine.py','indicators.py','data.py','metrics.py']:h.update((Path(__file__).resolve().parent/f).read_bytes())
    res['frozen']=dict(date=FREEZE_DATE,params=chosen,code_sha256=h.hexdigest(),forward_status='no data after 2025-08-15 available in this environment')
    json.dump(res,open(OUT/'results.json','w'),indent=1,default=lambda o:None if (isinstance(o,float) and not math.isfinite(o)) else str(o))
    bench.to_csv(OUT/'benchmark.csv');pd.DataFrame(isdf).to_csv(OUT/'is_grid.csv',index=False)
    print('done')

if __name__=='__main__':main()
