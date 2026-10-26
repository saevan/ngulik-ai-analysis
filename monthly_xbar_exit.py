"""Round 3 of monthly_entry_main_exits_results/PLAN.md: the x-bar exit as the monthly module's own exit."""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_open_next import stats
import wr_gap_v1 as w
import monthly_f1_sma30 as mf
import monthly_entry_sma_filter as ms
import monthly_filter_grid as m1
from monthly_trend_entry import trend

G = w.G


def kw(version, cell):
    if cell in ('V2 now', 'breakout only'):
        return mf.kw(version, cell)
    filt, ex = cell.split('|')
    k = mf.kw(version, 'breakout only')
    sig = (lambda f: w.me(f) & f.tradable.to_numpy(bool) & ms.base('F1', f)) if filt == 'F1' else \
          (lambda f: w.me(f) & f.tradable.to_numpy(bool) & ms.cond('C>SMA30', f))
    x = int(ex.split('x')[1])
    k.update(extra_signal_fn=sig, extra_first=True, extra_size_div=10, extra_max_frac=.35, extra_high_reset_bars=x,
             extra_exit_signal_fn=(lambda f: w.me(f) & ~trend('F_mom', f)) if ex.startswith('X+trend') else None)
    return k


def job(a):
    cell, version = a
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(G['fr'], start='2000-01-01', **kw(version, cell))
    c = c.loc[:'2025-08-15']
    if 'kind' not in t:
        t['kind'] = 'main'
    s = stats(c, t)
    tr, _ = m1.piece(c.equity, '2000-01-01', '2015-12-31')
    te, _ = m1.piece(c.equity, '2016-01-01', '2025-08-15')
    x = t[t.kind == 'extra']
    return dict(cell=cell, version=version, cagr=s['cagr'], cagr_train=tr, cagr_test=te, records=s['records'], mdd=s['mdd'], win_rate=s['wr'],
                monthly_trades=len(x), monthly_wr=(x.net_return > 0).mean() if len(x) else np.nan, monthly_e=x.net_return.mean() if len(x) else np.nan,
                monthly_bars=x.bars.mean() if len(x) else np.nan)


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    cells = ['V2 now', 'breakout only'] + [f'{f}|X x{x}' for f in ('F1', 'SMA30') for x in (10, 20, 30, 40, 60)] + \
            [f'{f}|X+trend x{x}' for f in ('F1', 'SMA30') for x in (20, 40)]
    with Pool(4) as p:
        D = pd.DataFrame(p.map(job, [(c_, v) for c_ in cells for v in ('realistic', 'unrestricted')], chunksize=1))
    R, U = D[D.version == 'realistic'].set_index('cell'), D[D.version == 'unrestricted'].set_index('cell')
    v = 'V2 now'
    ok = (R.cagr_train >= R.loc[v, 'cagr_train']) & (R.cagr_test >= R.loc[v, 'cagr_test']) & (U.cagr >= U.loc[v, 'cagr'] - .05) & \
         (R.mdd >= R.loc[v, 'mdd'] - .05) & (U.mdd >= U.loc[v, 'mdd'] - .05)
    S = R.drop(columns='version').join(U[['cagr', 'mdd', 'records', 'win_rate']], rsuffix='_U')
    S['better_than_V2'] = ok & ~S.index.isin(['V2 now', 'breakout only'])
    S.to_csv('monthly_entry_main_exits_results/xbar_exit.csv')
    pd.set_option('display.width', 250)
    print(S.round(3).to_string())
