"""F1 (Close > Close 120 bars ago and ER20 >= 0.3) + Close > SMA30 as the monthly filter, with (a) the existing exits and
(b) V2's own monthly exit (sell when Close > Close 120 fails at a month-end). 26 Oct 2026, descriptive follow-up.
Writes monthly_entry_main_exits_results/f1_sma30.csv"""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_open_next import stats
import wr_gap_v1 as w
import monthly_filter_grid as m1
import monthly_entry_sma_filter as ms
from monthly_trend_entry import trend

G = w.G


def kw(version, cell):
    k = dict(w.kw(version, True, None), failed_exit=None)       # V2 now (own monthly exit)
    sig = lambda f: w.me(f) & f.tradable.to_numpy(bool) & ms.base('F1', f) & ms.cond('C>SMA30', f)
    if cell == 'F1+SMA30, existing exits':
        k.update(extra_signal_fn=sig, extra_exit_signal_fn=None, extra_main_exits=True)
    elif cell == 'F1+SMA30, own monthly exit':
        k.update(extra_signal_fn=sig, extra_exit_signal_fn=lambda f: w.me(f) & ~trend('F_mom', f))
    elif cell == 'breakout only':
        for x in [x for x in k if x.startswith('extra_')]:
            k.pop(x)
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
    cells = ['V2 now', 'breakout only', 'F1+SMA30, existing exits', 'F1+SMA30, own monthly exit']
    with Pool(4) as p:
        D = pd.DataFrame(p.map(job, [(c_, v) for c_ in cells for v in ('realistic', 'unrestricted')], chunksize=1))
    D.to_csv('monthly_entry_main_exits_results/f1_sma30.csv', index=False)
    pd.set_option('display.width', 220)
    print(D.round(3).to_string(index=False))
