"""Year-by-year breakdown of trades ENTERED in a sideways market: V2 vs Swinger ideal (26 Oct 2026, descriptive).
Per entry year: trades, expectancy (mean net return), median, win rate for V2 (all / breakout / monthly) and Swinger ideal;
V2's best trade of the year and how much of the year's summed returns it carries. Scenario B, 2000-2025.08.
Writes quality_vs_swinger_results/v2_sideways_yearly.csv, v2_sideways_top_trades.csv"""
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
S = {}
with np.errstate(invalid='ignore', divide='ignore'):
    for v in ('realistic', 'unrestricted'):
        S[v] = run(G['fr'], start='2000-01-01', **dict(w.kw(v, True, None), failed_exit=None))[1]
sw = run_portfolio(G['fr'], 'afl_ideal', slip=.0025)[1]
sw['kind'] = 'swinger'
S['swinger'] = sw
for k, t in S.items():
    t['entry_date'] = pd.to_datetime(t.entry_date)
    t = t[(t.entry_date <= '2025-08-15') & (lab.reindex(t.entry_date).to_numpy() == 'sideways')].copy()
    t['year'] = t.entry_date.dt.year
    S[k] = t
rows, tops = [], []
for y in range(2000, 2026):
    row = dict(year=y)
    s = S['swinger'][S['swinger'].year == y].net_return
    row.update(sw_n=len(s), sw_E=s.mean(), sw_median=s.median(), sw_wr=(s > 0).mean())
    for v in ('realistic', 'unrestricted'):
        t = S[v][S[v].year == y]
        p = v[0].upper()
        for kd, x in (('all', t), ('bo', t[t.kind == 'main']), ('mo', t[t.kind == 'extra'])):
            r = x.net_return
            row.update({f'{p}_{kd}_n': len(r), f'{p}_{kd}_E': r.mean() if len(r) else np.nan})
        r = t.net_return
        row.update({f'{p}_median': r.median(), f'{p}_wr': (r > 0).mean() if len(r) else np.nan,
                    f'{p}_E_without_best': r.sort_values().iloc[:-1].mean() if len(r) > 1 else np.nan})
        if len(t):
            b = t.loc[r.idxmax()]
            tops.append(dict(year=y, version=v, ticker=b.ticker, kind='monthly' if b.kind == 'extra' else 'breakout', entry=b.entry_date.date(),
                             net=b.net_return, bars=b.bars, share_of_year_sum=b.net_return / r.sum() if r.sum() > 0 else np.nan))
    rows.append(row)
D = pd.DataFrame(rows)
D.to_csv('quality_vs_swinger_results/v2_sideways_yearly.csv', index=False)
Tp = pd.DataFrame(tops)
Tp.to_csv('quality_vs_swinger_results/v2_sideways_top_trades.csv', index=False)
pd.set_option('display.width', 260); pd.set_option('display.max_columns', 40)
cols = ['year', 'sw_n', 'sw_E', 'R_all_n', 'R_all_E', 'R_bo_n', 'R_bo_E', 'R_mo_n', 'R_mo_E', 'R_E_without_best', 'R_median', 'U_all_E', 'U_bo_E', 'U_mo_E']
print((D[cols].set_index('year') * [1, 100, 1, 100, 1, 100, 1, 100, 100, 100, 100, 100, 100]).round(1).to_string())
print(Tp[Tp.version == 'realistic'].round(3).to_string(index=False))
for v, p in (('realistic', 'R'), ('unrestricted', 'U')):
    print(v, 'years V2 E > Swinger E:', int((D[f'{p}_all_E'] > D.sw_E).sum()), 'of', int(D[f'{p}_all_E'].notna().sum()),
          '| without the best trade of the year:', int((D[f'{p}_E_without_best'] > D.sw_E).sum()))
