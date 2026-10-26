"""V2 per-trade quality (expectancy) and portfolio return by market condition vs Swinger ideal (26 Oct 2026).
V2 = V1 without the failed-breakout exit. Scenario B, 2000-01-01..2025-08-15. Condition at entry = label known before the
entry day's Open (EW proxy ER20 >= 0.3 up/down, else sideways). Writes quality_vs_swinger_results/v2_*.csv"""
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
YRS = (pd.Timestamp('2025-08-15') - pd.Timestamp('2000-01-01')).days / 365.25
S = {}
with np.errstate(invalid='ignore', divide='ignore'):
    for v in ('realistic', 'unrestricted'):
        S[f'V2 {v}'] = run(G['fr'], start='2000-01-01', **dict(w.kw(v, True, None), failed_exit=None))
c, t, _ = run_portfolio(G['fr'], 'afl_ideal', slip=.0025)
t['kind'] = 'swinger'
S['Swinger ideal'] = (c, t)
rows, prow = [], []
for name, (c, t) in S.items():
    c = c.loc[:'2025-08-15']
    t = t[pd.to_datetime(t.entry_date) <= '2025-08-15'].copy()
    t['regime'] = lab.reindex(pd.to_datetime(t.entry_date)).to_numpy()
    for g in ('uptrend', 'sideways', 'downtrend', 'all'):
        for kd in (['all'] + (['main', 'extra'] if name != 'Swinger ideal' else [])):
            x = t if g == 'all' else t[t.regime == g]
            x = x if kd == 'all' else x[x.kind == kd]
            r = x.net_return
            wn = r > 0
            rows.append(dict(system=name, regime=g, kind=kd, trades_per_year=len(x) / YRS, win_rate=wn.mean(), avg_win=r[wn].mean(),
                             avg_loss=r[~wn].mean(), expectancy=r.mean(), e_R=r.mean() / -r[~wn].mean(), mean_bars=x.bars.mean()))
    dr = c.equity.pct_change().dropna()
    g_ = lab.reindex(dr.index)
    for g in ('uptrend', 'sideways', 'downtrend'):
        y = dr[g_ == g]
        prow.append(dict(system=name, regime=g, ann_return=float((1 + y).prod() ** (252 / len(y)) - 1),
                         invested=float((c.market_value / c.equity).reindex(y.index).mean())))
T, P = pd.DataFrame(rows), pd.DataFrame(prow)
T.to_csv('quality_vs_swinger_results/v2_trade_quality.csv', index=False)
P.to_csv('quality_vs_swinger_results/v2_portfolio_by_condition.csv', index=False)
pd.set_option('display.width', 220); pd.set_option('display.max_rows', 100)
print(T.round(3).to_string(index=False)); print(P.round(3).to_string(index=False))
