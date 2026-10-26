"""Round 4 of monthly_entry_main_exits_results/PLAN.md: shorter trend lookback for the monthly module's entry/exit."""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_breakout_er import efficiency_ratio
import wr_gap_v1 as w
import monthly_f1_sma30 as mf
import monthly_xbar_exit as mx

G = w.G


def up(f, n):
    return (f.Close > f.Close.shift(n)).fillna(False).to_numpy(bool)


def kw(version, cell):
    if cell in ('V2 now', 'breakout only'):
        return mf.kw(version, cell)
    ne, nx = (int(v) for v in cell.split('/'))
    k = mf.kw(version, 'breakout only')
    k.update(extra_signal_fn=lambda f: w.me(f) & f.tradable.to_numpy(bool) & up(f, ne) & (efficiency_ratio(f.Close, 20) >= .3).fillna(False).to_numpy(bool),
             extra_exit_signal_fn=lambda f: w.me(f) & ~up(f, nx), extra_first=True, extra_size_div=10, extra_max_frac=.35)
    return k


if __name__ == '__main__':
    mx.kw = kw
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    cells = ['V2 now', 'breakout only'] + [f'{n}/{n}' for n in (20, 40, 60, 80, 100, 120)] + [f'120/{n}' for n in (20, 40, 60, 80, 100)]
    with Pool(4) as p:
        D = pd.DataFrame(p.map(mx.job, [(c_, v) for c_ in cells for v in ('realistic', 'unrestricted')], chunksize=1))
    R, U = D[D.version == 'realistic'].set_index('cell'), D[D.version == 'unrestricted'].set_index('cell')
    v = 'V2 now'
    ok = (R.cagr_train >= R.loc[v, 'cagr_train']) & (R.cagr_test >= R.loc[v, 'cagr_test']) & (U.cagr >= U.loc[v, 'cagr'] - .05) & \
         (R.mdd >= R.loc[v, 'mdd'] - .05) & (U.mdd >= U.loc[v, 'mdd'] - .05)
    S = R.drop(columns='version').join(U[['cagr', 'mdd', 'records', 'win_rate']], rsuffix='_U')
    S['better_than_V2'] = ok & ~S.index.isin(['V2 now', 'breakout only', '120/120'])
    S.to_csv('monthly_entry_main_exits_results/lookback.csv')
    pd.set_option('display.width', 250)
    print(S.round(3).to_string())
