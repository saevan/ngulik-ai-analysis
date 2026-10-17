"""Re-test under corrected execution and search for the causal system closest to Swinger ideal (CAGR and new-ATH months). Written before running.

Execution standard (after the 17 Oct 2026 audit): buy stops fill when the High TOUCHES the trigger (touch_fill=True); pre-Open order book with
fixed order sizes (no same-day information); orders < 0.1% of budget not placed. Scenarios: A = fee 0.15/0.25% only (Swinger's basis);
B = fee + 0.25%/side proportional slippage (selection basis); C = B + buy orders <= 25% of 20-day average traded value.
Families (1536 configs): F1 buy stop at HHV(N) [+ buffer b above the level] and F2 Close-confirmed breakout bought at the next Open;
N {3,5,10,20} x ER20 min {none,.2,.3} x exit {cand: fade 2 ATR + Close<SMA30; cand_trail2: + LLV5 trail after +2 ATR; tsl5 / tsl10: LLV sell stop}
x failed-breakout exit {off, on} x size per entry {1/10,1/7,1/5,1/4} [x F1 buffer {0, 0.5%, 1%}]. Fixed: momentum 120/20 priority, 2% gap rules.
Selection (train 2000-2015, scenario B): eligible = train MDD >= -40%; score = mean of the percentile ranks of train CAGR and train record months;
pick = max score (secondary pick = max train CAGR). Evaluation: validation 2016-20, test 2021-25, full; scenarios A/B/C; neighbourhood
median (configs one step away); walk-forward of the rule (expanding folds to 2007/2011/2015/2020). Benchmarks: Swinger ideal (fee, s25),
Swinger causal stop order with touch triggers and next Open."""
from itertools import product
from multiprocessing import Pool
from pathlib import Path
import json
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from backtest_open_next import stats
from backtest_idx_costs import Costs
from exploit_market_properties import mom120
from evaluate_swinger_like_finalists import PropCosts

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'realistic_chase_results'
W={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15'),
   'f2007':('2000-01-01','2007-12-31'),'f2011':('2000-01-01','2011-12-31'),'f2020':('2000-01-01','2020-12-31')}
FOLDS=[('f2007',('2008-01-01','2011-12-31')),('f2011',('2012-01-01','2015-12-31')),('train',('2016-01-01','2020-12-31')),('f2020',('2021-01-01','2025-08-15'))]
EX={'cand':dict(fade=2.,sma_len=30),'cand_trail2':dict(fade=2.,sma_len=30,trail_after=2.),'tsl5':dict(fade=None,sma_len=None,llv=5),'tsl10':dict(fade=None,sma_len=None,llv=10)}
AX=dict(channel=[3,5,10,20],er_min=[None,.2,.3],exit=list(EX),failed=[None,0.],size_div=[10,7,5,4])
CFG=[dict(fam='F1',buffer=b,**dict(zip(AX,v))) for v in product(*AX.values()) for b in [0.,.005,.01]]+[dict(fam='F2',buffer=None,**dict(zip(AX,v))) for v in product(*AX.values())]
G={}

def label(c):return f"{c['fam']}_ch{c['channel']}_er{c['er_min']}_{c['exit']}_f{c['failed']}_s{c['size_div']}"+(f"_b{c['buffer']}" if c['fam']=='F1' else '')
def kw(c,scen):
    k=dict(gap_skip=.02,gapdown_close=.02,priority=mom120,channel=c['channel'],er_min=c['er_min'],failed_exit=c['failed'],size_div=c['size_div'],min_order_frac=1e-3,**EX[c['exit']])
    if c['fam']=='F1':k.update(entry_mode='buy_stop',strict_orders=True,presize=True,book_preopen=True,touch_fill=True,stop_buffer=c['buffer'])
    else:k.update(entry_mode='close_breakout')
    k['cost_model']=Costs() if scen=='A' else PropCosts(slip=.0025)
    if scen=='C':k['liq_cap']=.25
    return k
def job(a):
    c,w,scen=a;s,e=W[w] if isinstance(w,str) else w
    fr={t:g for t,f in G['fr'].items() if len(g:=f[f['Date/Time']<=e])}
    with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(fr,start=s,**kw(c,scen))
    st=stats(eq,tr);out=dict(label=label(c),**c,window=w if isinstance(w,str) else f'{s}..{e}',scen=scen,**{k:st[k] for k in ['cagr','records','months','mdd','n','wr','payout','invested']})
    if a[1] in [x[1] for x in FOLDS] or (isinstance(w,str) and w in('validation','test','full') and G.get('curves')):pass
    return out
def job_curve(a):
    c,w,scen=a;s,e=w
    fr={t:g for t,f in G['fr'].items() if len(g:=f[f['Date/Time']<=e])}
    with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(fr,start=s,**kw(c,scen))
    return [[str(d.date()),float(v)] for d,v in eq.equity.items()]
def swinger(a):
    mode,scen,touch=a
    eq,tr,_=run_portfolio(G['fr'],mode,slip=0. if scen=='A' else .0025,touch=touch,liq_cap=.25 if scen=='C' else None)
    st=stats(eq,tr);return dict(label=f'SWINGER_{mode}'+('_touch' if touch else ''),scen=scen,window='full',**{k:st[k] for k in ['cagr','records','months','mdd','n','wr','payout','invested']})
def pick(df,w):
    g=df[(df.window==w)&(df.scen=='B')].copy();g=g[g.mdd>=-.40]
    g['score']=(g.cagr.rank(pct=True)+g.records.rank(pct=True))/2
    return g.sort_values(['score','cagr'],ascending=False).iloc[0].label,g.sort_values('cagr',ascending=False).iloc[0].label
def neighbours(c):
    out=[]
    for k,vals in list(AX.items())+([('buffer',[0.,.005,.01])] if c['fam']=='F1' else []):
        i=vals.index(c[k])
        for j in (i-1,i+1):
            if 0<=j<len(vals):d_=dict(c);d_[k]=vals[j];out.append(d_)
    return out
def main():
    OUT.mkdir(exist_ok=True);(OUT/'PLAN.json').write_text(json.dumps(dict(doc=__doc__,axes={k:[str(x) for x in v] for k,v in AX.items()},configs=len(CFG)),indent=1))
    st,_=engine.load_data('stocks');G['fr']={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}
    by={label(c):c for c in CFG}
    with Pool(4) as p:
        rows=p.map(job,[(c,'train','B') for c in CFG],chunksize=8)
        D=pd.DataFrame(rows);D.to_csv(OUT/'train_B.csv',index=False)
        main_pick,cagr_pick=pick(D,'train');frozen=dict(score_pick=main_pick,cagr_pick=cagr_pick)
        (OUT/'FROZEN.json').write_text(json.dumps(frozen,indent=1));print('FROZEN',frozen,flush=True)
        rows=p.map(job,[(c,'full',s) for c in CFG for s in ['A','B']],chunksize=8);pd.DataFrame(rows).to_csv(OUT/'full_AB.csv',index=False)
        ev=[by[main_pick],by[cagr_pick]];nb=[n for n in neighbours(by[main_pick]) if label(n) in by]
        rows=p.map(job,[(c,w,s) for c in ev for w in ['train','validation','test','full'] for s in ['A','B','C']]+[(c,w,'B') for c in nb for w in ['validation','test','full']],chunksize=2)
        pd.DataFrame(rows).to_csv(OUT/'picks_eval.csv',index=False)
        sw=p.map(swinger,[(m,s,t) for m,s,t in [('afl_ideal','A',False),('afl_ideal','B',False),('afl_ideal','C',False),('stop_order','A',True),('stop_order','B',True),('stop_order','C',True),('next_open','A',False),('next_open','B',False)]])
        pd.DataFrame(sw).to_csv(OUT/'swinger_refs.csv',index=False)
        # walk-forward of the rule
        rows=p.map(job,[(c,f,'B') for f,_ in FOLDS if f!='train' for c in CFG],chunksize=8);WF=pd.concat([D,pd.DataFrame(rows)]);WF.to_csv(OUT/'walkforward_train_B.csv',index=False)
        sel=[(f,ts,pick(WF,f)[0]) for f,ts in FOLDS]
        curves=p.map(job_curve,[(by[lb],ts,s) for f,ts,lb in sel for s in ['A','B']])
    out=[];chains={}
    for (f,ts,lb),s_,cv in zip([x for x in sel for _ in 'AB'],['A','B']*len(sel),curves):
        e=pd.Series([v for _,v in cv],index=pd.to_datetime([d for d,_ in cv]))/1e9;chains.setdefault(s_,[]).append(e)
        out.append(dict(fold_train=f,test=f'{ts[0]}..{ts[1]}',pick=lb,scen=s_,cagr=float(e.iloc[-1]**(365.25/(e.index[-1]-e.index[0]).days)-1)))
    summ=[]
    for s_,parts in chains.items():
        lvl=1.;seg=[]
        for p_ in parts:seg.append(p_*lvl);lvl*=float(p_.iloc[-1])
        ch=pd.concat(seg);yrs=(ch.index[-1]-pd.Timestamp('2008-01-01')).days/365.25;pk=ch.cummax().clip(lower=1.);nh=ch>pk.shift(1).fillna(1.)+1e-12
        rec=nh.groupby(ch.index.to_period('M')).any();summ.append(dict(scen=s_,cagr=float(ch.iloc[-1]**(1/yrs)-1),records=int(rec.sum()),months=len(rec),mdd=float((ch/ch.cummax()-1).min())))
    e=pd.read_csv(ROOT/'prototype_swinger_benchmark_results/afl_ideal_net_equity.csv',index_col=0,parse_dates=True).equity;lvl=1.;seg=[]
    for _,(a,b) in FOLDS:
        prev=e[e.index<a];x=e[a:b]/float(prev.iloc[-1]);seg.append(x*lvl);lvl*=float(x.iloc[-1])
    ch=pd.concat(seg);yrs=(ch.index[-1]-pd.Timestamp('2008-01-01')).days/365.25;pk=ch.cummax().clip(lower=1.);nh=ch>pk.shift(1).fillna(1.)+1e-12;rec=nh.groupby(ch.index.to_period('M')).any()
    summ.append(dict(scen='SWINGER_IDEAL_fee',cagr=float(ch.iloc[-1]**(1/yrs)-1),records=int(rec.sum()),months=len(rec),mdd=float((ch/ch.cummax()-1).min())))
    pd.DataFrame(out).to_csv(OUT/'walkforward_tests.csv',index=False);pd.DataFrame(summ).to_csv(OUT/'walkforward_summary.csv',index=False)
    print(pd.DataFrame(out).to_string());print(pd.DataFrame(summ).to_string());print('done')
if __name__=='__main__':main()
