"""Trade quality as expectancy: our v2 main pick (unrestricted, realistic) vs Prototype Swinger ideal, scenario B,
2000-01-01..2025-08-15 (26 Oct 2026). Uses the trade ledgers of diagnose_winrate.py (same runs).
Expectancy E = WR x avg win - (1 - WR) x avg loss = mean net return per trade.
E_R = E / avg loss (expectancy per 1R, R = the average losing trade) = WR x (payout + 1) - 1.
E per bar = E / mean bars held. 95% CI of E: bootstrap over entry months (2,000 resamples), since trades in the same
month are not independent. Rough bridge to portfolio return: E x trades per year x position size
(ours 25% of equity per order, Swinger 10%); arithmetic, no compounding, ignores cash limits.
Conditions as in quality_vs_swinger_by_regime.py (label known before the entry day's Open; breakdown = market proxy's
previous Close a new 20-day low, overlapping slice). Writes quality_vs_swinger_results/expectancy.csv"""
from pathlib import Path
import zlib
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from analyze_portfolio_regimes import regime_proxy

ROOT = Path(__file__).resolve().parent
YEARS = (pd.Timestamp('2025-08-15') - pd.Timestamp('2000-01-01')).days / 365.25
SIZE = {'ours': .25, 'ours_realistic': .25, 'swinger_ideal': .10}
st, _ = engine.load_data('stocks')
rp = regime_proxy(st)
breakdown = (rp.proxy < rp.proxy.shift(1).rolling(20).min()).shift(1, fill_value=False)


def boot_ci(x, months, seed):
    g = pd.Series(x).groupby(months.to_numpy())
    sums, counts = g.sum().to_numpy(), g.size().to_numpy()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(sums), (2000, len(sums)))
    m = sums[idx].sum(1) / counts[idx].sum(1)
    return np.percentile(m, [2.5, 97.5])


rows = []
for name in SIZE:
    T = pd.read_csv(ROOT / 'winrate_diagnosis_results' / f'trades_{name}.csv', parse_dates=['entry_date'])
    T['breakdown'] = breakdown.reindex(T.entry_date).fillna(False).to_numpy(bool)
    T['period'] = pd.cut(T.entry_date.dt.year, [1999, 2007, 2015, 2020, 2025], labels=['2000-07', '2008-15', '2016-20', '2021-25'])
    slices = {'all': T, **{g: T[T.regime == g] for g in ['uptrend', 'sideways', 'downtrend']}, 'breakdown': T[T.breakdown],
              **{f'period {p}': T[T.period == p] for p in ['2000-07', '2008-15', '2016-20', '2021-25']}}
    for lab, x in slices.items():
        r = x.net
        w = r > 0
        wr, aw, al = w.mean(), r[w].mean(), -r[~w].mean()
        e = wr * aw - (1 - wr) * al
        assert np.isclose(e, r.mean())
        lo, hi = boot_ci(r.to_numpy(), x.entry_date.dt.to_period('M'), zlib.crc32(f'{name}-{lab}'.encode()))
        yrs = YEARS if not lab.startswith('period') else {'2000-07': 8, '2008-15': 8, '2016-20': 5, '2021-25': 4.62}[lab[7:]]
        rows.append(dict(system=name, slice=lab, trades=len(x), win_rate=wr, avg_win=aw, avg_loss=al, expectancy=e, ci95_low=lo, ci95_high=hi,
                         expectancy_R=e / al, mean_bars=x.bars.mean(), expectancy_per_bar=e / x.bars.mean(), trades_per_year=len(x) / yrs,
                         expectancy_x_trades_per_year=e * len(x) / yrs, approx_portfolio_contribution=e * len(x) / yrs * SIZE[name]))
D = pd.DataFrame(rows)
D.to_csv(ROOT / 'quality_vs_swinger_results' / 'expectancy.csv', index=False)
pd.set_option('display.width', 250)
print(D.round(4).to_string(index=False))
