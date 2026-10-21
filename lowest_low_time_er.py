"""Addendum run: stock-level ER20 < 0.3 filter (and market + stock) for the lowest-low / no-new-trade-high logic,
with a 20-seed random control. Writes lowest_low_time_results/results_er_filter.csv."""
from itertools import product
from multiprocessing import Pool
import zlib
import numpy as np, pandas as pd
import lowest_low_time as L
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy

GRID = list(product([10, 20, 60], [3, 5, 10], ['stock_er', 'market_and_stock'], ['next_open', 'close']))


def run(cell):
    T = L.sim(cell)
    rows = L.summarize(T, cell, 'signal')
    ctl = []
    for s in range(20):
        R = L.sim(cell, random_seed=zlib.crc32(f'{cell}-{s}'.encode()))
        ctl.append(R.gross.mean())
    for r in rows:
        r['control20_gross_pct'] = float(np.mean(ctl) * 100)
    return rows


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    L.G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(L.G['fr'], .5), psl.stale_ok(L.G['fr'])
    L.G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in L.G['fr']}
    reg = regime_proxy(st)['regime']
    L.G['side'] = np.array(reg.index[reg == 'sideways'], dtype='datetime64[ns]')
    L.G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    with Pool(4) as p:
        d = pd.DataFrame([r for rows in p.map(run, GRID) for r in rows])
    key = ['N', 'x', 'filter', 'entry']
    subs = d[d.period != '2000-25'].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum())).rename('subperiods_positive')
    d = d.merge(subs, on=key)
    full = d[d.period == '2000-25'].copy()
    full['passes'] = (full.net_B_pct > 0) & (full.t_net_B >= 3) & (full.subperiods_positive >= 3) & (full.gross_pct > full.control20_gross_pct)
    d.to_csv(L.OUT / 'results_er_filter.csv', index=False)
    pd.set_option('display.width', 250)
    print(full[key + ['trades_per_year', 'gross_pct', 'control20_gross_pct', 'net_B_pct', 't_net_B', 'win_rate_B', 'avg_bars', 'subperiods_positive', 'passes']].round(2).to_string(index=False))
