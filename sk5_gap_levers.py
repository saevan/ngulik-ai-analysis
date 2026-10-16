"""Which characteristics close the SK-5 vs Swinger-ideal gap by regime? (written before running)

Part A (observational): the 360 grid configs of search_swinger_like_system (v2 pre-Open book; BASE not included), full 2000-2025, fee. For each: daily attribution by
ER20 regime (conditional annualized return, mean exposure = market value / equity at the start of the day, efficiency = sum of daily
returns / sum of exposure, annualized; NOTE: start-of-day exposure leaves entry-day P&L in 'efficiency', see decompose_sk5_gap.py) and
trade characteristics by entry regime. Correlations across configs (computed in the analysis, not in this script) are associations only.
Part B (experiment): SK-5 (HHV5, ER20>=0.3, fade2+SMA30, failed-breakout exit, 20% per entry) with levers aimed at the gaps found in
analyze_sk5_regimes.py (exposure; winners held shorter in sideways/downtrend):
  er_min {0.3, 0.2, none} x exit {cand, cand_smaarm (SMA30 exit only after a Close >= SMA30), tsl5_fade (LLV5 sell stop + fade2, no SMA),
  cand_trail2 (cand + LLV5 trail after +2 ATR), tsl5 (LLV5 sell stop only)} x size per entry {1/5, 1/4, 1/3}; 45 configs (SK-5 included).
  Note: cand_smaarm on SK-5 was looked at once (full fee 49.0%) while building the engine test, before this grid was fixed.
  Windows train 2000-15 / validation 2016-20 / test 2021-25 / full; costs fee and s25 (fee + 0.25%/side).
  Rules: R1 = max train fee CAGR with train fee MDD >= -35% and train fee records >= SK-5's; R2 = same with s25.
  Walk-forward of R1/R2 over the 45 configs with the folds of walkforward_swinger_like.py. Regime attribution of every full run."""
from itertools import product
from multiprocessing import Pool
from pathlib import Path
import json
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from analyze_portfolio_regimes import regime_proxy
from backtest_stop_execution import run
from backtest_open_next import stats
from backtest_idx_costs import Costs
import search_swinger_like_system as S
from evaluate_swinger_like_finalists import PropCosts
from walkforward_swinger_like import FOLDS
from analyze_sk5_regimes import regimes

OUT=Path(__file__).resolve().parent/'sk5_regime_results'
COST={'fee':Costs(),'s25':PropCosts(slip=.0025)}
EXB={'cand':dict(fade=2.,sma_len=30),'cand_smaarm':dict(fade=2.,sma_len=30,sma_arm=True),'tsl5_fade':dict(fade=2.,sma_len=None,llv=5),
     'cand_trail2':dict(fade=2.,sma_len=30,trail_after=2.),'tsl5':dict(fade=None,sma_len=None,llv=5)}
GRID=dict(er_min=[.3,.2,None],exit=list(EXB),size_div=[5,4,3])
CFGB=[dict(zip(GRID,v)) for v in product(*GRID.values())]
SK5=dict(er_min=.3,exit='cand',size_div=5)
G={}

def kw_b(c):
    return dict(entry_mode='buy_stop',strict_orders=True,presize=True,book_preopen=True,min_order_frac=1e-3,gap_skip=.02,gapdown_close=.02,
        priority=S.mom120,channel=5,er_min=c['er_min'],failed_exit=0.,size_div=c['size_div'],**EXB[c['exit']])
def lab_b(c):return f"er{c['er_min']}_{c['exit']}_s{c['size_div']}"

def regime_rows(eq,tr,tag):
    rows=[]
    for rdef,reg in G['reg'].items():
        r=eq.equity.pct_change().fillna(eq.equity.iloc[0]/1e9-1);w=(eq.market_value/eq.equity).shift(1).fillna(0.)
        lab=reg.regime.reindex(eq.index).fillna('unknown');lr=np.log1p(r)
        days=eq.index.to_series().diff().dt.days.fillna(0)
        t=tr.copy();t['regime']=reg.regime.reindex(pd.to_datetime(t.entry_date)).fillna('unknown').to_numpy()
        for state in ['uptrend','sideways','downtrend']:
            m=(lab==state).to_numpy();dur=days[m].sum();g=t[t.regime==state];x=g.net_return;wn=x>0
            rows.append(dict(**tag,regime_def=rdef,regime=state,cond_ann=float(np.expm1(lr[m].sum()*365.25/dur)),exposure=float(w[m].mean()),
                eff=float(r[m].sum()/w[m].sum()*252) if w[m].sum()>0 else np.nan,n=len(g),wr=float(wn.mean()) if len(g) else np.nan,
                avg_loss=float(-x[~wn].mean()) if (~wn).any() else np.nan,avg_win=float(x[wn].mean()) if wn.any() else np.nan,
                hold_win=float(g.bars[wn].mean()) if wn.any() else np.nan,hold_loss=float(g.bars[~wn].mean()) if (~wn).any() else np.nan))
    return rows

def job_a(c):
    with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(G['fr'],cost_model=COST['fee'],start='2000-01-01',**S.kwargs(c))
    tag=dict(label=S.label(c),**{k:c.get(k) for k in S.GRID});st=stats(eq,tr)
    return dict(tag,**{k:st[k] for k in ['cagr','records','mdd','wr','payout','invested','n']}),regime_rows(eq,tr,tag)

def job_b(a):
    c,(s,e),cost,full=a
    fr={t:g for t,f in G['fr'].items() if len(g:=f[f['Date/Time']<=e])}
    with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(fr,cost_model=COST[cost],start=s,**kw_b(c))
    st=stats(eq,tr);tag=dict(label=lab_b(c),**c,start=s,end=e,cost=cost)
    row=dict(tag,**st,loss_gt10=float((tr.net_return<-.1).mean()))
    return row,(regime_rows(eq,tr,tag) if full else []),([[str(d.date()),float(v)] for d,v in eq.equity.items()] if a[3]=='curve' else None)

def main():
    st,_=engine.load_data('stocks');G['fr']={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)};G['reg']=regimes(st)
    cfgs=[c for c in S.CONFIGS]
    with Pool(4) as p:A=p.map(job_a,cfgs,chunksize=4)
    pd.DataFrame([a for a,_ in A]).to_csv(OUT/'gridA_full_fee.csv',index=False);RA=pd.DataFrame([r for _,rr in A for r in rr]);RA.to_csv(OUT/'gridA_regimes.csv',index=False)
    W={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
    tasks=[(c,W[w],cost,w=='full') for c in CFGB for w in W for cost in COST]
    with Pool(4) as p:B=p.map(job_b,tasks,chunksize=2)
    rows=[];rr=[]
    for (c,win,cost,full),(row,reg,_) in zip(tasks,B):
        row['window']=[k for k,v in W.items() if v==win][0];rows.append(row);rr+=reg
    Bd=pd.DataFrame(rows);Bd.to_csv(OUT/'gridB_windows.csv',index=False);pd.DataFrame(rr).to_csv(OUT/'gridB_regimes.csv',index=False)
    tr=Bd[Bd.window=='train'];sk=lab_b(SK5);picks={}
    for rule,cost in [('R1','fee'),('R2','s25')]:
        g=tr[tr.cost==cost].set_index('label');ok=g[(g.mdd>=-.35)&(g.records>=g.loc[sk,'records'])]
        picks[rule]=ok.cagr.idxmax()
    (OUT/'gridB_FROZEN.json').write_text(json.dumps(dict(sk5=sk,picks=picks),indent=1));print('picks',picks,flush=True)
    # walk-forward of R1/R2 over the 45 configs
    wtasks=[(c,trw,cost,False) for trw,_ in FOLDS for c in CFGB for cost in COST]
    with Pool(4) as p:WB=p.map(job_b,wtasks,chunksize=2)
    Wd=pd.DataFrame([r for r,_,_ in WB]);Wd.to_csv(OUT/'gridB_walkforward_train.csv',index=False)
    sel=[]
    for trw,tsw in FOLDS:
        g=Wd[(Wd.start==trw[0])&(Wd.end==trw[1])]
        for rule,cost in [('R1','fee'),('R2','s25')]:
            h=g[g.cost==cost].set_index('label');base=h.loc[sk];ok=h[(h.mdd>=-.35)&(h.records>=base.records)]
            lb=ok.cagr.idxmax();c=[x for x in CFGB if lab_b(x)==lb][0];sel.append((rule,trw,tsw,c))
    ttasks=[(c,tsw,cost,'curve') for rule,trw,tsw,c in sel for cost in COST]+[(SK5,tsw,cost,'curve') for _,tsw in FOLDS for cost in COST]
    with Pool(4) as p:TT=p.map(job_b,ttasks,chunksize=1)
    out=[];chains={}
    keys=[(rule,tsw,cost,lab_b(c)) for rule,trw,tsw,c in sel for cost in COST]+[('SK5',tsw,cost,lab_b(SK5)) for _,tsw in FOLDS for cost in COST]
    for (rule,tsw,cost,lb),(row,_,curve) in zip(keys,TT):
        out.append(dict(rule=rule,test=f'{tsw[0]}..{tsw[1]}',label=lb,cost=cost,cagr=row['cagr'],records=row['records'],mdd=row['mdd']))
        chains.setdefault((rule,cost),[]).append(pd.Series([v for _,v in curve],index=pd.to_datetime([d for d,_ in curve]))/1e9)
    pd.DataFrame(out).to_csv(OUT/'gridB_walkforward_tests.csv',index=False)
    summ=[]
    for (rule,cost),parts in chains.items():
        lvl=1.;seg=[]
        for p_ in parts:seg.append(p_*lvl);lvl*=float(p_.iloc[-1])
        ch=pd.concat(seg);yrs=(ch.index[-1]-pd.Timestamp('2008-01-01')).days/365.25;peak=ch.cummax().clip(lower=1.);nh=ch>peak.shift(1).fillna(1.)+1e-12
        rec=nh.groupby(ch.index.to_period('M')).any()
        summ.append(dict(rule=rule,cost=cost,cagr=float(ch.iloc[-1]**(1/yrs)-1),records=int(rec.sum()),months=len(rec),mdd=float((ch/ch.cummax()-1).min())))
    pd.DataFrame(summ).to_csv(OUT/'gridB_walkforward_summary.csv',index=False);print(pd.DataFrame(summ).to_string());print('done')

if __name__=='__main__':main()
