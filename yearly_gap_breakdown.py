"""Year-by-year breakdown of our return vs Prototype Swinger ideal (26 Oct 2026). Scenario B, Rp1bn, compounding,
2000-01-01..2025-08-15 (2025 partial). Systems as in quality_vs_swinger_by_regime.py.
Per year: returns, gap in pp, growth ratio (1+ours)/(1+Swinger), year-end equity and cumulative multiple Swinger/ours,
and where the year's gap arose: log-return gap (Swinger - ours) split over uptrend / sideways / downtrend days
(label known before the day's Open), as shares of that year's log gap.
Writes quality_vs_swinger_results/yearly_breakdown.csv"""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from analyze_portfolio_regimes import regime_proxy

OUT = Path(__file__).resolve().parent / 'quality_vs_swinger_results'
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
lab = regime_proxy(st)['regime']
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
k = rc.kw(BASE, 'B')
with np.errstate(invalid='ignore', divide='ignore'):
    E = {'ours': run(fr, start='2000-01-01', **k)[0].equity,
         'ours_realistic': run(fr, start='2000-01-01', **dict(k, liq_cap=.25, gate_dates={t: pit[t] & stale[t] for t in fr}))[0].equity,
         'swinger_ideal': run_portfolio(fr, 'afl_ideal', slip=.0025)[0].equity}
E = pd.DataFrame({n: pd.concat([pd.Series([1e9], index=[pd.Timestamp('1999-12-31')]), e.loc['2000-01-01':'2025-08-15']]) for n, e in E.items()}).ffill()
L = np.log(E).diff().dropna()
L['regime'] = lab.reindex(L.index).fillna('unknown').to_numpy()
ye = E.resample('YE').last()
Y = ye.pct_change().dropna()
Y.index = Y.index.year
rows = []
for y in Y.index:
    r = dict(year=y, ours=Y.loc[y, 'ours'], ours_realistic=Y.loc[y, 'ours_realistic'], swinger_ideal=Y.loc[y, 'swinger_ideal'])
    r['gap_pp'] = (r['ours'] - r['swinger_ideal']) * 100
    r['gap_realistic_pp'] = (r['ours_realistic'] - r['swinger_ideal']) * 100
    r['growth_ratio'] = (1 + r['ours']) / (1 + r['swinger_ideal'])
    r['equity_ours_bn'] = ye.loc[str(y), 'ours'].iloc[0] / 1e9
    r['equity_swinger_bn'] = ye.loc[str(y), 'swinger_ideal'].iloc[0] / 1e9
    r['cum_multiple_swinger_over_ours'] = r['equity_swinger_bn'] / r['equity_ours_bn']
    x = L[L.index.year == y]
    gap = (x.swinger_ideal - x.ours).sum()
    for g in ['uptrend', 'sideways', 'downtrend']:
        r[f'gap_share_{g}'] = (x.swinger_ideal - x.ours)[x.regime == g].sum() / gap if gap > 0 else np.nan
        r[f'days_{g}'] = int((x.regime == g).sum())
    rows.append(r)
D = pd.DataFrame(rows)
D.to_csv(OUT / 'yearly_breakdown.csv', index=False)
pd.set_option('display.width', 250)
print(D.round(3).to_string(index=False))
tot = (L.swinger_ideal - L.ours)
print('whole period log gap share:', {g: round(tot[L.regime == g].sum() / tot.sum(), 3) for g in ['uptrend', 'sideways', 'downtrend', 'unknown']})
