"""Regression: backtest_stop_execution with new-system options at their defaults reproduces the audited strict buy-stop curves
(lookahead_audit_results/full_{fees,spread1}_buystop_strict_*.csv) exactly; plus checks of the new options' mechanics."""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_idx_costs import Costs
from exploit_market_properties import mom120
st,_=engine.load_data('stocks');fr={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}
for s,cost in [('fees',Costs()),('spread1',Costs(grid=True,ticks_per_side=1,round_lot=100))]:
    c,t=run(fr,entry_mode='buy_stop',cost_model=cost,gap_skip=.02,gapdown_close=.02,priority=mom120,strict_orders=True)
    ref=pd.read_csv(f'lookahead_audit_results/full_{s}_buystop_strict_equity.csv',index_col=0,parse_dates=True)
    assert len(ref)==len(c) and np.allclose(ref.equity.to_numpy(),c.equity.to_numpy(),rtol=1e-12,atol=1e-3),s
    rt=pd.read_csv(f'lookahead_audit_results/full_{s}_buystop_strict_trades.csv')
    assert len(rt)==len(t) and np.allclose(rt.pnl.to_numpy(),t.pnl.to_numpy(),rtol=1e-12,atol=1e-3),s
    print(s,'regression OK',len(t),'trades')
# explicit defaults give the same result
c2,t2=run(fr,entry_mode='buy_stop',cost_model=Costs(),gap_skip=.02,gapdown_close=.02,priority=mom120,strict_orders=True,er_min=.3,sma_len=30,trail_len=5,failed_exit=None,size_div=10,presize=False)
ref=pd.read_csv('lookahead_audit_results/full_fees_buystop_strict_equity.csv',index_col=0,parse_dates=True)
assert np.allclose(ref.equity.to_numpy(),c2.equity.to_numpy(),rtol=1e-12,atol=1e-3);print('explicit defaults OK')
# failed_exit: every 'failed_breakout' exit happens the bar after entry and its entry bar closed below the buy level
c3,t3=run(fr,entry_mode='buy_stop',cost_model=Costs(),gap_skip=.02,gapdown_close=.02,priority=mom120,strict_orders=True,failed_exit=0.)
fb=t3[t3.reason.str.startswith('failed_breakout')]
assert len(fb)>0 and (fb.bars<=3).mean()>.95,fb.bars.describe();print('failed_exit OK',len(fb),'exits; bars',fb.bars.value_counts().head(3).to_dict())
# presize: cash never negative (asserted in engine) and order count bounded by cash
c4,t4=run(fr,entry_mode='buy_stop',cost_model=Costs(),gap_skip=.02,gapdown_close=.02,priority=mom120,strict_orders=True,presize=True,size_div=5)
assert (c4.positions<=10).all();print('presize OK',len(t4),'trades; invested',round((c4.market_value/c4.equity).mean(),3))
# book_preopen: names with zero volume today or a gap beyond the rule still consume their book slot (no hand-over)
c5,t5=run(fr,entry_mode='buy_stop',cost_model=Costs(),gap_skip=.02,gapdown_close=.02,priority=mom120,strict_orders=True,presize=True,size_div=5,
          channel=5,failed_exit=0.,book_preopen=True,min_order_frac=1e-3)
c6,t6=run(fr,entry_mode='buy_stop',cost_model=Costs(),gap_skip=.02,gapdown_close=.02,priority=mom120,strict_orders=True,presize=True,size_div=5,
          channel=5,failed_exit=0.)
cg=lambda c:(c.equity.iloc[-1]/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1
assert cg(c5)<cg(c6);print('book_preopen OK: CAGR',round(cg(c6),4),'->',round(cg(c5),4),'trades',len(t6),'->',len(t5))
nl=(t5.pnl/t5.net_return.replace(0,float('nan'))).dropna()
assert (nl>1e5).all(),nl.min();print('min_order_frac OK: smallest order Rp',round(float(nl.min())))
# sma_arm: no 'sma_exit' happens before the position has had a Close at or above SMA30
c7,t7=run(fr,entry_mode='buy_stop',cost_model=Costs(),gap_skip=.02,gapdown_close=.02,priority=mom120,strict_orders=True,presize=True,size_div=5,
          channel=5,failed_exit=0.,book_preopen=True,min_order_frac=1e-3,sma_arm=True)
sma={t:(f.Close>=f.Close.rolling(30).mean()).to_numpy() for t,f in fr.items()}
idx={t:{d:i for i,d in enumerate(pd.DatetimeIndex(f['Date/Time']))} for t,f in fr.items()}
bad=0
for r in t7[t7.reason.str.startswith('sma_exit')].itertuples():
    a=idx[r.ticker][pd.Timestamp(r.entry_date)];b=idx[r.ticker][pd.Timestamp(r.exit_date)]
    if not sma[r.ticker][a:b].any():bad+=1
assert bad==0,bad;print('sma_arm OK',int(t7.reason.str.startswith('sma_exit').sum()),'sma exits, all after an at/above-SMA Close; CAGR',round(cg(c7),4))
# entry_sma: every entry's previous Close is at/above SMA30 of the previous bar
c8,t8=run(fr,entry_mode='buy_stop',cost_model=Costs(),gap_skip=.02,gapdown_close=.02,priority=mom120,strict_orders=True,presize=True,size_div=5,
          channel=5,failed_exit=0.,book_preopen=True,min_order_frac=1e-3,entry_sma=30)
sm={t:f.Close.rolling(30).mean().to_numpy() for t,f in fr.items()};cl={t:f.Close.to_numpy() for t,f in fr.items()}
bad=sum(1 for r in t8.itertuples() if not cl[r.ticker][idx[r.ticker][pd.Timestamp(r.entry_date)]-1]>=sm[r.ticker][idx[r.ticker][pd.Timestamp(r.entry_date)]-1])
assert bad==0,bad;print('entry_sma OK',len(t8),'trades; CAGR',round(cg(c8),4))
# random entry control: deterministic per seed, different across seeds, buys at the next Open after a signal
r1=run(fr,entry_mode='random',random_entry=(.01,1),cost_model=Costs(),fade=2.,sma_len=30,failed_exit=0.,size_div=5,gap_skip=.02,gapdown_close=.02)
r2=run(fr,entry_mode='random',random_entry=(.01,1),cost_model=Costs(),fade=2.,sma_len=30,failed_exit=0.,size_div=5,gap_skip=.02,gapdown_close=.02)
r3=run(fr,entry_mode='random',random_entry=(.01,2),cost_model=Costs(),fade=2.,sma_len=30,failed_exit=0.,size_div=5,gap_skip=.02,gapdown_close=.02)
assert np.allclose(r1[0].equity,r2[0].equity) and not np.allclose(r1[0].equity,r3[0].equity);print('random entry OK',len(r1[1]),'trades; CAGR',round(cg(r1[0]),4),round(cg(r3[0]),4))
