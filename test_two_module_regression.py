"""backtest_two_module with system 1 only must reproduce the published system-1 curves exactly."""
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from analyze_portfolio_regimes import regime_proxy
from backtest_open_next import atr14
from backtest_idx_costs import Costs
from backtest_two_module import run
import choppy_modules as cm

def setup():
    st,_=engine.load_data('stocks');proxy=regime_proxy(st)
    closes=st.pivot(index='Date/Time',columns='Ticker',values='Close').sort_index()
    atrp={}
    for t,f in st.groupby('Ticker',sort=True):f=f.reset_index(drop=True);atrp[t]=pd.Series(atr14(f)/f.Close.to_numpy(),index=f['Date/Time'])
    cm.set_context(proxy,closes,pd.DataFrame(atrp).sort_index())
    return {str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}

def main():
    frames=setup()
    for s,cost,ref in [('fees',Costs(),'full_fees_stock_and_market_er'),('spread1',Costs(grid=True,ticks_per_side=1,round_lot=100),'full_spread1_stock_and_market_er')]:
        with np.errstate(invalid='ignore'):c,t,_=run(frames,[cm.system1()],cost_model=cost)
        np.testing.assert_allclose(c.equity,pd.read_csv(f'er_gated_breakout_results/{ref}_equity.csv').equity,rtol=1e-10);print(s,'regression OK',len(t))

if __name__=='__main__':main()
