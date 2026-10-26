"""How similar is V2's performance to Swinger ideal in up / sideways / down markets? (26 Oct 2026, descriptive)
Ratios V2 / Swinger ideal per market condition (label known before the day's Open): annual return on those days,
expectancy per trade, win rate, trades per year; plus the correlation of daily equity returns on those days.
Scenario B, 2000-01-01..2025-08-15. Uses the trade-level file from v2_quality_by_regime.py.
Writes quality_vs_swinger_results/v2_similarity.csv"""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
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
eq = {}
with np.errstate(invalid='ignore', divide='ignore'):
    for v in ('realistic', 'unrestricted'):
        eq[v] = run(G['fr'], start='2000-01-01', **dict(w.kw(v, True, None), failed_exit=None))[0].equity.loc[:'2025-08-15']
eq['swinger'] = run_portfolio(G['fr'], 'afl_ideal', slip=.0025)[0].equity.loc[:'2025-08-15']
r = pd.DataFrame({k: e.pct_change() for k, e in eq.items()}).dropna()
g = lab.reindex(r.index)
T = pd.read_csv('quality_vs_swinger_results/v2_trade_quality.csv')
T = T[T.kind == 'all']
rows = []
for rg in ('uptrend', 'sideways', 'downtrend', 'all'):
    x = r if rg == 'all' else r[g == rg]
    ann = {k: float((1 + x[k]).prod() ** (252 / len(x)) - 1) for k in x}
    sw = T[(T.system == 'Swinger ideal') & (T.regime == rg)].iloc[0]
    for v in ('realistic', 'unrestricted'):
        o = T[(T.system == f'V2 {v}') & (T.regime == rg)].iloc[0]
        rows.append(dict(regime=rg, version=v, ann_return=ann[v], swinger_ann_return=ann['swinger'], return_ratio=ann[v] / ann['swinger'],
                         log_growth_ratio=np.log1p(ann[v]) / np.log1p(ann['swinger']),
                         expectancy=o.expectancy, swinger_expectancy=sw.expectancy, expectancy_ratio=o.expectancy / sw.expectancy,
                         win_rate=o.win_rate, swinger_win_rate=sw.win_rate, win_rate_ratio=o.win_rate / sw.win_rate,
                         trades_per_year=o.trades_per_year, swinger_trades_per_year=sw.trades_per_year,
                         trades_ratio=o.trades_per_year / sw.trades_per_year, daily_corr=float(x[v].corr(x['swinger']))))
D = pd.DataFrame(rows)
D.to_csv('quality_vs_swinger_results/v2_similarity.csv', index=False)
pd.set_option('display.width', 250)
print(D.round(3).to_string(index=False))
