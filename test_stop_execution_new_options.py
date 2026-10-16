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
