"""Did dropping the failed-breakout exit (V1 -> V2) lengthen our holding period? (26 Oct 2026, descriptive)
Scenario B 2000-2025.08, realistic and unrestricted. Holding bars by trade kind (all entries and sideways entries), and the
fate in V2 of the V1 trades that were cut by the failed-breakout exit (matched on ticker + entry date).
Writes quality_vs_swinger_results/v1_v2_holding.csv, v1_v2_failed_fate.csv"""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
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
rows, fate = [], []
for v in ('realistic', 'unrestricted'):
    T = {}
    with np.errstate(invalid='ignore', divide='ignore'):
        T['V1'] = run(G['fr'], start='2000-01-01', **w.kw(v, True, None))[1]
        T['V2'] = run(G['fr'], start='2000-01-01', **dict(w.kw(v, True, None), failed_exit=None))[1]
    for name, t in T.items():
        t = t[pd.to_datetime(t.entry_date) <= '2025-08-15'].copy()
        t['regime'] = lab.reindex(pd.to_datetime(t.entry_date)).to_numpy()
        for sub in ('all entries', 'sideways entries'):
            x0 = t if sub == 'all entries' else t[t.regime == 'sideways']
            for kd in ('all', 'main', 'extra'):
                x = x0 if kd == 'all' else x0[x0.kind == kd]
                rows.append(dict(version=v, system=name, subset=sub, kind=kd, trades=len(x), mean_bars=x.bars.mean(), median_bars=x.bars.median(),
                                 share_le_2_bars=(x.bars <= 2).mean(), mean_net=x.net_return.mean(), win_rate=(x.net_return > 0).mean()))
    t1, t2 = T['V1'], T['V2']
    cut = t1[t1.reason.str.startswith('failed')]
    m = cut.merge(t2, on=['ticker', 'entry_date'], suffixes=('_v1', '_v2'))
    fate.append(dict(version=v, v1_failed_trades=len(cut), found_in_v2=len(m), v1_mean_net=m.net_return_v1.mean(), v1_mean_bars=m.bars_v1.mean(),
                     v2_mean_net=m.net_return_v2.mean(), v2_median_net=m.net_return_v2.median(), v2_mean_bars=m.bars_v2.mean(),
                     v2_win_rate=(m.net_return_v2 > 0).mean(), v2_share_worse=(m.net_return_v2 < m.net_return_v1).mean()))
D, F = pd.DataFrame(rows), pd.DataFrame(fate)
D.to_csv('quality_vs_swinger_results/v1_v2_holding.csv', index=False)
F.to_csv('quality_vs_swinger_results/v1_v2_failed_fate.csv', index=False)
pd.set_option('display.width', 220)
print(D.round(3).to_string(index=False)); print(F.round(3).to_string(index=False))
