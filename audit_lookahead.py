"""Look-ahead audit for the two systems compared with Swinger:
 A. Model utuh (system 1 ER-gated breakout + choppy rs-breakout module, Open(i+1)), backtest_two_module.
 B. Kandidat buy stop (HHV20 buy stop, gap skip 2%, sell at Close on gap-down, mom120 priority), backtest_stop_execution.
Tests:
 1. Truncation: run on data cut at date X (proxy / ranks / indicators recomputed on the cut data) and on full data;
    every daily equity value and every trade closed before X must be identical.
 2. Regime proxy prefix: labels on cut data equal the full-history labels before X.
 3. Buy-stop fill selection: strict pre-Open order book (top-K by priority, K = free slots) vs engine default.
 4. Universe: listing / last dates of the 100 tickers (survivorship).
Fees-only for 1-3 (fill/cost model does not change causality); 3 also with spread 1 tick.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from analyze_portfolio_regimes import regime_proxy
from backtest_open_next import atr14
from backtest_idx_costs import Costs
from backtest_two_module import run as run_model
from backtest_stop_execution import run as run_bs
from exploit_market_properties import mom120
import choppy_modules as cm

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'lookahead_audit_results'
CUTS=['2008-06-30','2016-01-15','2021-03-31']

def frames_of(df):return {str(k):f.reset_index(drop=True) for k,f in df.groupby('Ticker',sort=True)}

def model(df,cost):
    proxy=regime_proxy(df);closes=df.pivot(index='Date/Time',columns='Ticker',values='Close').sort_index()
    atrp={t:pd.Series(atr14(f.reset_index(drop=True))/f.Close.to_numpy(),index=f['Date/Time'].to_numpy()) for t,f in df.groupby('Ticker',sort=True)}
    cm.set_context(proxy,closes,pd.DataFrame(atrp).sort_index())
    with np.errstate(invalid='ignore'):c,t,_=run_model(frames_of(df),[cm.system1(),cm.rs_breakout(.5,20,cap=5)],cost_model=cost)
    return c,t

def buystop(df,cost,strict=False):
    with np.errstate(invalid='ignore',divide='ignore'):
        return run_bs(frames_of(df),entry_mode='buy_stop',cost_model=cost,gap_skip=.02,gapdown_close=.02,priority=mom120,strict_orders=strict)

def stats(c,t):
    m=c.new_high.groupby(c.index.to_period('M')).any()
    return dict(cagr=(c.equity.iloc[-1]/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1,records=int(m.sum()),mdd=c.drawdown.min(),n=len(t))

def main():
    OUT.mkdir(exist_ok=True)
    st,_=engine.load_data('stocks');rows=[]
    full={'model':model(st,Costs()),'buystop':buystop(st,Costs())}
    pf=regime_proxy(st)
    for cut in CUTS:
        cutd=pd.Timestamp(cut);sub=st[st['Date/Time']<=cutd]
        pc=regime_proxy(sub);same=pc.regime.equals(pf.regime.loc[:cutd])
        rows.append(dict(test='regime proxy prefix',cut=cut,identical=bool(same)))
        for name,fn in [('model',lambda d:model(d,Costs())),('buystop',lambda d:buystop(d,Costs()))]:
            c,t=fn(sub);C,T=full[name]
            before=c.index<cutd
            eq_ok=np.allclose(c.equity[before].to_numpy(),C.equity.reindex(c.index[before]).to_numpy(),rtol=1e-12,atol=1e-6)
            tc=t[pd.to_datetime(t.exit_date)<cutd].drop(columns=[x for x in ['reason'] if x in t]).reset_index(drop=True)
            TC=T[pd.to_datetime(T.exit_date)<cutd].drop(columns=[x for x in ['reason'] if x in T]).reset_index(drop=True)
            tr_ok=len(tc)==len(TC) and np.allclose(tc.pnl.to_numpy(),TC.pnl.to_numpy(),rtol=1e-12,atol=1e-6) and (tc.ticker.values==TC.ticker.values).all()
            rows.append(dict(test=f'truncation {name}',cut=cut,identical=bool(eq_ok and tr_ok),days_compared=int(before.sum()),trades_compared=len(tc)))
            print(cut,name,'equity identical',eq_ok,'trades identical',tr_ok,flush=True)
    pd.DataFrame(rows).to_csv(OUT/'truncation_tests.csv',index=False)
    # 3. Buy-stop fill selection.
    fs=[]
    for s,cost in [('fees',Costs()),('spread1',Costs(grid=True,ticks_per_side=1,round_lot=100))]:
        for strict in [False,True]:
            c,t=buystop(st,cost,strict);fs.append(dict(scenario=s,strict_orders=strict,**stats(c,t)))
        c,t=model(st,cost);fs.append(dict(scenario=s,strict_orders='model utuh (Open(i+1))',**stats(c,t)))
    fs=pd.DataFrame(fs);fs.to_csv(OUT/'buystop_order_book.csv',index=False);print(fs.round(4).to_string())
    # 4. Universe.
    g=st.groupby('Ticker')['Date/Time'].agg(['min','max'])
    u=dict(tickers=len(g),first_bar_by_2000_01_31=int((g['min']<='2000-01-31').sum()),listed_after_2005=int((g['min']>'2005-12-31').sum()),
        last_bar_before_2025=int((g['max']<'2025-01-01').sum()),last_bar_before_2025_08=int((g['max']<'2025-08-01').sum()),data_end=str(g['max'].max().date()))
    pd.Series(u).to_csv(OUT/'universe.csv');print(u)

if __name__=='__main__':main()
