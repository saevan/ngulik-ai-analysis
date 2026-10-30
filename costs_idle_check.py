"""(1) Cost sensitivity with the user's broker fees (buy 0.25%, sell 0.35%) and different slippage assumptions;
(2) idle cash of V2 by market condition and the effect of parking idle cash at a money-market rate (illustrative 4%/yr).
V2 (V1 without failed exit), 2000-01-01..2025-08-15. Writes costs_idle_results/*.csv (30 Oct 2026, descriptive)."""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from backtest_open_next import stats
from evaluate_swinger_like_finalists import PropCosts
from analyze_portfolio_regimes import regime_proxy
import wr_gap_v1 as w

G = w.G
st, _ = engine.load_data('stocks')
G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
lab = regime_proxy(st)['regime']
SC = {'B (ours: fee .15/.25 + slip .25/side = 0.90% RT)': (.0015, .0025, .0025),
      'user fee .25/.35, no slippage (0.60% RT)': (.0025, .0035, 0.), 'user fee + slip .10/side (0.80% RT)': (.0025, .0035, .001),
      'user fee + slip .25/side (1.10% RT)': (.0025, .0035, .0025)}
rows, idle = [], []
with np.errstate(invalid='ignore', divide='ignore'):
    for name, (bf, sf, sl) in SC.items():
        for v in ('realistic', 'unrestricted'):
            k = dict(w.kw(v, True, None), failed_exit=None, cost_model=PropCosts(buy_fee=bf, sell_fee=sf, slip=sl))
            c, t = run(G['fr'], start='2000-01-01', **k)
            c = c.loc[:'2025-08-15']
            s = stats(c, t)
            rows.append(dict(scenario=name, system=f'V2 {v}', cagr=s['cagr'], records=s['records'], mdd=s['mdd'], win_rate=s['wr'], expectancy=s['mean']))
            if name.startswith('B'):
                inv = (c.market_value / c.equity)
                g = lab.reindex(c.index)
                for rg in ('uptrend', 'sideways', 'downtrend'):
                    idle.append(dict(system=f'V2 {v}', regime=rg, idle_cash_share=float(1 - inv[g == rg].mean())))
                idle.append(dict(system=f'V2 {v}', regime='all', idle_cash_share=float(1 - inv.mean())))
                r = c.equity.pct_change().fillna(0)
                for rate in (.03, .04, .05):
                    cash_share = (c.cash / c.equity).shift(1).fillna(1)
                    eq2 = (1 + r + cash_share * rate / 252).cumprod()
                    yrs = (c.index[-1] - c.index[0]).days / 365.25
                    rows.append(dict(scenario=f'B + idle cash parked at {rate:.0%}/yr', system=f'V2 {v}', cagr=eq2.iloc[-1] ** (1 / yrs) - 1,
                                     mdd=float((eq2 / eq2.cummax() - 1).min())))
        c, t, _ = run_portfolio(G['fr'], 'afl_ideal', buy_fee=bf, sell_fee=sf, slip=sl)
        c = c.loc[:'2025-08-15']
        s = stats(c, t)
        rows.append(dict(scenario=name, system='Swinger ideal', cagr=s['cagr'], records=s['records'], mdd=s['mdd'], win_rate=s['wr'], expectancy=s['mean']))
D, I = pd.DataFrame(rows), pd.DataFrame(idle)
D.to_csv('costs_idle_results/costs.csv', index=False); I.to_csv('costs_idle_results/idle.csv', index=False)
pd.set_option('display.width', 220); pd.set_option('display.max_colwidth', 60)
print(D.round(3).to_string(index=False)); print(I.round(3).to_string(index=False))
