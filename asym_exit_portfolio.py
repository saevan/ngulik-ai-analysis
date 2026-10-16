"""User's clarified rule ("jijik rugi, sayang untung"): breakout entry, asymmetric exit reference.
  in profit (previous Close > entry): exit on a fade from the LATEST Open: Low <= Open*(1-fp)   (reference updated every bar)
  in loss: exit on Low <= entry*(1-lp) (reference = entry), or after lt consecutive Closes in loss (time; clock resets when in profit)
Signals at the Close, fills at the next tradable Open. Entry: Close>HHV20 & ER20>=0.3 (same as time_price_portfolio.py).
Portfolio 10 slots, Rp1bn, compounding, fees 0.15/0.25% + 1 tick + 100-share lots. Grid pre-listed; selection on TRAIN only
(max CAGR among configs with records >= median), then holdout/full and a random-entry control for the chosen configs."""
from itertools import product
from multiprocessing import Pool
import json
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_open_next import run, stats
import time_price_portfolio as tpp
FR=tpp.FR;WIN=tpp.WIN
FP=[.03,.05,.08,.12];LP=[.03,.05,.08,.12,None];LT=[None,5,10,20]
P=None
def lab(fp,lp,lt):return f"fp{int(fp*100)}_lp{'-' if lp is None else int(lp*100)}_lt{'-' if lt is None else lt}"
def job(a):
    cfg,w,entry,seed=a
    fr={t:g for t,f in FR.items() if len(g:=f[f['Date/Time']<=WIN[w][1]])}
    sig=tpp.sig_breakout if entry=='breakout' else tpp.make_random(P,seed)
    with np.errstate(invalid='ignore',divide='ignore'):c,t=run(fr,signal=sig,stop=None,act=1e9,trail=0,asym=cfg,cost_model=tpp.COST,start=WIN[w][0])
    pnl=t.pnl.sort_values(ascending=False)
    return dict(cfg=lab(*cfg),fp=cfg[0],lp=cfg[1],lt=cfg[2],window=w,entry=entry,seed=seed,reasons=json.dumps(t.reason.value_counts().to_dict()),
        top5_share=float(pnl.head(5).sum()/pnl.sum()) if pnl.sum()>0 else np.nan,**stats(c,t))
def main():
    global P
    st,_=engine.load_data('stocks')
    for k,f in st.groupby('Ticker',sort=True):FR[str(k)]=f.reset_index(drop=True)
    P=sum(int(tpp.sig_breakout(f).sum()) for f in FR.values())/sum(int(f.tradable.sum()) for f in FR.values())
    cfgs=list(product(FP,LP,LT))
    with Pool(4) as p:rows=p.map(job,[(c,w,'breakout',0) for c in cfgs for w in WIN],chunksize=2)
    d=pd.DataFrame(rows)
    tr=d[d.window=='train'];ok=tr[tr.records>=tr.records.median()].sort_values('cagr',ascending=False)
    chosen=[(r.fp,None if pd.isna(r.lp) else r.lp,None if pd.isna(r.lt) else int(r.lt)) for r in ok.head(3).itertuples()]
    print('chosen on train',chosen,flush=True)
    with Pool(4) as p:rr=p.map(job,[(c,'full','random',s) for c in chosen for s in range(3)],chunksize=1)
    d=pd.concat([d,pd.DataFrame(rr)]);d['chosen_on_train']=d.cfg.isin([lab(*c) for c in chosen])
    d.to_csv(tpp.OUT/'asym_exit_portfolio.csv',index=False);print('done')
if __name__=='__main__':main()
