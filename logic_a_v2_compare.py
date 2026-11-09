"""V2 (previous system, realistic) in the Logic A report next to Logic A1 and Swinger ideal (plan addendum in logic_a_swing5_results)."""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from analyze_portfolio_regimes import regime_proxy
import wr_gap_v1 as w
from logic_a_swing5 import report, OUT, B

G = w.G
st, _ = engine.load_data('stocks')
G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
lab = regime_proxy(st)['regime']
with np.errstate(invalid='ignore', divide='ignore'):
    c, t = run(G['fr'], start='2000-01-01', **dict(w.kw('realistic', True, None), failed_exit=None))
c = c.loc[:B]; t = t[pd.to_datetime(t.entry_date) <= B]
R = pd.DataFrame(report('V2 realistic', c, t, lab))
A = pd.read_csv(OUT / 'results.csv'); A = A[A.system.isin(['A1 realistic', 'Swinger ideal'])]
D = pd.concat([R, A], ignore_index=True); D.to_csv(OUT / 'v2_compare.csv', index=False)
pd.set_option('display.width', 250)
print(D[D.condition == 'all'][['system', 'CAGR', 'MDD', 'CAGR 2000-07', 'CAGR 2008-15', 'CAGR 2016-20', 'CAGR 2021-25']].round(3).to_string(index=False))
print(D[['system', 'condition', 'ann_return', 'invested', 'trades_per_year', 'win_rate', 'avg_win', 'avg_loss', 'payoff', 'expectancy', 'median_bars']].round(3).to_string(index=False))
y = c.equity.resample('YE').last(); y = pd.concat([pd.Series([c.equity.iloc[0]], index=[c.index[0]]), y]).pct_change().dropna()
print('V2 realistic negative years:', int((y < 0).sum()), 'of', len(y), (y[y < 0] * 100).round(1).to_dict())
