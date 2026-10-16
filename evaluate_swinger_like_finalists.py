"""Finalists of search_swinger_like_system.py under more cost assumptions, against Swinger with the same costs, plus checks.

Costs: fee (0.15%/0.25%, Swinger's basis); s10 / s25 = fee + 0.10% / 0.25% proportional slippage per side; spread1 = fee + 1 IDX tick
per side on split-ADJUSTED prices (pessimistic before ~2008: mean tick/price 1.7% per side in 2000-07 vs 0.5% in 2021-25).
Finalists: base (audited strict buy stop), the two pre-registered picks, the fee-only train #1, and the best full-period fee config
(chosen AFTER seeing every window: post-hoc, shown as a ceiling, not as an out-of-sample result).
Checks: truncation look-ahead test, liquidity of orders vs 20-day average traded value, crypto (8 coins) and forex (9 pairs)
with the same parameters, Swinger ideal/stop-order with the same proportional costs."""
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path
import json
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_idx_costs import Costs
from backtest_open_next import stats
from backtest_prototype_swinger import run_portfolio
from uts.data import load_crypto, load_forex, frames as uts_frames
import search_swinger_like_system as S

OUT=S.OUT

@dataclass
class PropCosts(Costs):
    slip:float=0.
    def quote(self,reference,previous_close,side):
        return float(reference)*(1+self.slip) if side=='buy' else float(reference)*(1-self.slip)

COST={'fee':Costs(),'s10':PropCosts(slip=.001),'s25':PropCosts(slip=.0025),'spread1':Costs(grid=True,ticks_per_side=1,round_lot=100)}
FIN={'base':S.BASE,
     'pre_registered_performance':dict(channel=10,er_min=.3,exit='cand',failed=0.,size_div=5),
     'pre_registered_character':dict(channel=20,er_min=.4,exit='tsl10',failed=None,size_div=5),
     'fee_only_train_best':dict(channel=5,er_min=.3,exit='cand',failed=0.,size_div=5),
     'post_hoc_best_full_fee':dict(channel=5,er_min=.2,exit='cand_trail2',failed=0.,size_div=5)}
FR=S.FR

def job(a):
    name,w,c=a;cfg=FIN[name]
    fr={t:g for t,f in FR.items() if len(g:=f[f['Date/Time']<=S.WIN[w][1]])}
    with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(fr,cost_model=COST[c],start=S.WIN[w][0],**S.kwargs(cfg))
    st=stats(eq,tr);r=tr.net_return
    return dict(system=name,window=w,cost=c,**st,loss_gt10=float((r<-.1).mean()))

def swinger_job(a):
    mode,c=a;slip={'fee':0.,'s10':.001,'s25':.0025}[c]
    cur,tr,cnt=run_portfolio(FR,mode,slip=slip);st=stats(cur,tr)
    return dict(system=f'SWINGER_{mode}',window='full',cost=c,**st,loss_gt10=float((tr.net_return<-.1).mean()))

def truncation(name):
    cfg=FIN[name];out=[]
    with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(FR,cost_model=COST['fee'],start='2000-01-01',**S.kwargs(cfg))
    for cut in ['2008-06-30','2016-01-15','2021-03-31']:
        fr={t:g for t,f in FR.items() if len(g:=f[f['Date/Time']<=cut])}
        with np.errstate(invalid='ignore',divide='ignore'):e,t=run(fr,cost_model=COST['fee'],start='2000-01-01',**S.kwargs(cfg))
        cutd=pd.Timestamp(cut);bef=e.index<cutd
        same=np.allclose(e.equity[bef].to_numpy(),eq.equity.reindex(e.index[bef]).to_numpy(),rtol=1e-12,atol=1e-3)
        t1=t[pd.to_datetime(t.exit_date)<cutd];t2=tr[pd.to_datetime(tr.exit_date)<cutd]
        same2=len(t1)==len(t2) and np.allclose(t1.pnl.to_numpy(),t2.pnl.to_numpy(),rtol=1e-12,atol=1e-3)
        out.append(dict(system=name,cut=cut,days=int(bef.sum()),trades=len(t1),identical=bool(same and same2)))
    # liquidity: order value vs 20-day average traded value (Close*Volume, bars before entry)
    adv={}
    for tk,f in FR.items():
        v=(f.Close*f.Volume).shift(1).rolling(20).mean();adv[tk]=pd.Series(v.to_numpy(),index=pd.DatetimeIndex(f['Date/Time']))
    ratio=np.array([r.notional/adv[r.ticker].get(pd.Timestamp(r.entry_date),np.nan) if 'notional' in tr else np.nan for r in tr.itertuples()]) if 'notional' in tr else None
    if ratio is None:
        # ledger has no notional column: rebuild from pnl/net_return
        notional=tr.pnl/tr.net_return.replace(0,np.nan)
        ratio=np.array([n/adv[tk].get(pd.Timestamp(d),np.nan) for n,tk,d in zip(notional,tr.ticker,tr.entry_date)])
    liq=dict(system=name,median_order_vs_adv=float(np.nanmedian(ratio)),share_gt5pct=float(np.nanmean(ratio>.05)),share_gt10pct=float(np.nanmean(ratio>.10)),share_gt25pct=float(np.nanmean(ratio>.25)))
    return out,liq

def cross_market():
    rows=[]
    cr=uts_frames(load_crypto());fx=uts_frames(load_forex(0))
    for mk,fr,cost,start in [('crypto',cr,Costs(buy_fee=.001,sell_fee=.001),'2017-01-01'),('forex',fx,Costs(buy_fee=.00015,sell_fee=.00015),'2023-01-01')]:
        for name,cfg in FIN.items():
            with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(fr,cost_model=cost,start=start,**S.kwargs(cfg))
            rows.append(dict(system=name,window=mk,cost='market_fee',**stats(eq,tr)))
        for mode in ['afl_ideal','stop_order','next_open']:
            fee=(.001,.001) if mk=='crypto' else (.00015,.00015)
            cur,tr,cnt=run_portfolio(fr,mode,buy_fee=fee[0],sell_fee=fee[1]);rows.append(dict(system=f'SWINGER_{mode}',window=mk,cost='market_fee',**stats(cur,tr)))
    return rows

def main():
    st,_=engine.load_data('stocks')
    for k,f in st.groupby('Ticker',sort=True):FR[str(k)]=f.reset_index(drop=True)
    tasks=[(n,w,c) for n in FIN for w in S.WIN for c in COST]
    with Pool(4) as p:
        rows=p.map(job,tasks,chunksize=2)
        rows+=p.map(swinger_job,[(m,c) for m in ['afl_ideal','stop_order','next_open'] for c in ['fee','s10','s25']])
        tl=p.map(truncation,['pre_registered_performance','post_hoc_best_full_fee','fee_only_train_best'])
    d=pd.DataFrame(rows+cross_market());d.to_csv(OUT/'finalists.csv',index=False)
    pd.DataFrame([x for o,_ in tl for x in o]).to_csv(OUT/'finalists_truncation.csv',index=False)
    pd.DataFrame([l for _,l in tl]).to_csv(OUT/'finalists_liquidity.csv',index=False)
    print('done')

if __name__=='__main__':main()
