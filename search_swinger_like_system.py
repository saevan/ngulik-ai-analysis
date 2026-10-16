"""New system aimed at the Swinger-ideal profile, built only from causal orders (levels known before the Open).

Benchmark (prototype_swinger_benchmark_results, afl_ideal_net, fee-only 0.15%/0.25%): full 2000-2025 CAGR 114.8%, 249/308 record
months, MDD -18.8%, WR 51.9%, payout 5.17. Its fills are not causal (12.8% of entries below the day's Low, 16.9% of exits above the High).

Fixed for every config: buy stop at HHV(N) of the previous N Highs, armed when the previous Close <= level; strict pre-Open order book
(top-K by momentum 120/20, K = free slots) with order sizes fixed before the Open (presize); skip when Open > level*1.02; a pending
Close-signal exit whose Open gaps down >2% is sold at that Close; max 10 positions; Rp1bn; compounding; long only.
Grid (360): channel N {5,10,20} x ER20 min {none,.2,.3,.4} x exit {cand: fade2 ATR from the running Open + Close<SMA30;
cand_trail2: cand + intraday trailing stop at LLV5 once a Close >= entry+2 ATR; tsl5 / tsl10: Swinger-style sell stop at LLV5 / LLV10 only;
sma30_trail2: Close<SMA30 + trailing LLV5 after +2 ATR} x failed-breakout exit {off, entry-bar Close < level -> next Open}
x size per entry {equity/10, /7, /5}.
Costs: fee (Swinger's basis) and spread1 (fee + 1 IDX tick per side + 100-share lots).
Selection (train 2000-2015 only, written before running): eligible = train fee records >= base AND train spread1 CAGR >= base
AND train fee MDD >= -30%; performance pick = max train fee CAGR. Character pick (secondary) = same plus train fee WR >= 50%.
Base = audited strict buy-stop candidate (channel 20, ER .3, cand, no failed exit, /10, presize off). Every config is also run on
validation 2016-2020, test 2021-2025-08 and full (post-freeze diagnostics).
v2 (16 Oct 2026, after an independent audit): the order book now uses only pre-Open information (book_preopen=True: no same-day
volume, a gapped name keeps its slot and reserved cash) and orders below 0.1% of the budget are not placed. Grid, rule and windows
unchanged. v1 results (book with same-day information) are kept in v1_book_lookahead/."""
from itertools import product
from multiprocessing import Pool
from pathlib import Path
import json
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_idx_costs import Costs
from backtest_open_next import stats
from exploit_market_properties import mom120

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'swinger_like_system_results'
WIN={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
COST={'fee':Costs(),'spread1':Costs(grid=True,ticks_per_side=1,round_lot=100)}
EXITS={'cand':dict(fade=2.,sma_len=30),'cand_trail2':dict(fade=2.,sma_len=30,trail_after=2.),'tsl5':dict(fade=None,sma_len=None,llv=5),
       'tsl10':dict(fade=None,sma_len=None,llv=10),'sma30_trail2':dict(fade=None,sma_len=30,trail_after=2.)}
GRID=dict(channel=[5,10,20],er_min=[None,.2,.3,.4],exit=list(EXITS),failed=[None,0.],size_div=[10,7,5])
CONFIGS=[dict(zip(GRID,v)) for v in product(*GRID.values())]
BASE=dict(channel=20,er_min=.3,exit='cand',failed=None,size_div=10,presize=False)
FR={}

def label(c):return f"ch{c['channel']}_er{c['er_min']}_{c['exit']}_f{c['failed']}_s{c['size_div']}"+('' if c.get('presize',True) else '_basepresizeoff')

def kwargs(c):
    return dict(entry_mode='buy_stop',strict_orders=True,presize=c.get('presize',True),book_preopen=True,min_order_frac=1e-3,gap_skip=.02,gapdown_close=.02,priority=mom120,
        channel=c['channel'],er_min=c['er_min'],failed_exit=c['failed'],size_div=c['size_div'],**EXITS[c['exit']])

def job(a):
    c,w,s=a
    fr={t:g for t,f in FR.items() if len(g:=f[f['Date/Time']<=WIN[w][1]])}
    with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(fr,cost_model=COST[s],start=WIN[w][0],**kwargs(c))
    st=stats(eq,tr);r=tr.net_return
    return dict(label=label(c),**{k:c.get(k) for k in GRID},presize=c.get('presize',True),window=w,cost=s,**st,
        loss_gt10=float((r<-.10).mean()),reasons=json.dumps(tr.reason.value_counts().to_dict()))

def swinger_windows():
    e=pd.read_csv(ROOT/'prototype_swinger_benchmark_results/afl_ideal_net_equity.csv',index_col=0,parse_dates=True)
    t=pd.read_csv(ROOT/'prototype_swinger_benchmark_results/afl_ideal_net_trades.csv',parse_dates=['entry_date','exit_date'])
    rows=[]
    for w,(a,b) in WIN.items():
        prev=e.equity[e.index<a];base=float(prev.iloc[-1]) if len(prev) else 1e9
        s=e.equity[a:b]/base;yrs=(s.index[-1]-(prev.index[-1] if len(prev) else s.index[0])).days/365.25
        peak=s.cummax().clip(lower=1.);newh=(s>peak.shift(1).fillna(1.)+1e-12)
        rec=newh.groupby(s.index.to_period('M')).any()
        tt=t[(t.entry_date>=a)&(t.entry_date<=b)];r=tt.net_return;wn=r>0
        rows.append(dict(label='SWINGER_IDEAL_fee',window=w,cost='fee',cagr=float(s.iloc[-1]**(1/yrs)-1),records=int(rec.sum()),months=len(rec),
            mdd=float((s/s.cummax()-1).min()),n=len(tt),wr=float(wn.mean()),avg_win=float(r[wn].mean()),avg_loss=float(-r[~wn].mean()),
            payout=float(r[wn].mean()/-r[~wn].mean()),mean=float(r.mean()),median=float(r.median()),mean_bars=float(tt.bars.mean()),
            win_bars=float(tt.bars[wn].mean()),loss_bars=float(tt.bars[~wn].mean()),invested=float((e.market_value/e.equity)[a:b].mean()),loss_gt10=float((r<-.10).mean())))
    return pd.DataFrame(rows)

def main():
    OUT.mkdir(exist_ok=True)
    (OUT/'PLAN.json').write_text(json.dumps(dict(doc=__doc__,grid=GRID,exits={k:{a:str(b) for a,b in v.items()} for k,v in EXITS.items()},base=BASE,windows=WIN),indent=1))
    st,_=engine.load_data('stocks')
    for k,f in st.groupby('Ticker',sort=True):FR[str(k)]=f.reset_index(drop=True)
    cfgs=[BASE]+CONFIGS
    with Pool(4) as p:train=p.map(job,[(c,'train',s) for c in cfgs for s in COST],chunksize=4)
    d=pd.DataFrame(train);d.to_csv(OUT/'train_grid.csv',index=False)
    fee=d[d.cost=='fee'].set_index('label');sp=d[d.cost=='spread1'].set_index('label')
    b=label(BASE);ok=fee[(fee.records>=fee.loc[b,'records'])&(sp.cagr.reindex(fee.index)>=sp.loc[b,'cagr'])&(fee.mdd>=-.30)].drop(index=b,errors='ignore')
    perf=ok.cagr.idxmax() if len(ok) else None
    okc=ok[ok.wr>=.5];charp=okc.cagr.idxmax() if len(okc) else None
    frozen=dict(base=b,base_train_fee=fee.loc[b,['cagr','records','mdd','wr']].to_dict(),base_train_spread1_cagr=float(sp.loc[b,'cagr']),
        eligible=int(len(ok)),performance_pick=perf,character_pick=charp,character_eligible=int(len(okc)))
    (OUT/'FROZEN.json').write_text(json.dumps(frozen,indent=1,default=float));print('FROZEN',frozen,flush=True)
    with Pool(4) as p:rest=p.map(job,[(c,w,s) for c in cfgs for w in ['validation','test','full'] for s in COST],chunksize=4)
    all_=pd.concat([d,pd.DataFrame(rest),swinger_windows()],ignore_index=True);all_.to_csv(OUT/'all_windows.csv',index=False)
    print('done',len(all_))

if __name__=='__main__':main()
