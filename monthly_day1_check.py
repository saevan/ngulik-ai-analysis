"""Timing check of the 'buy on the first trading day of the month if above SMA30' rule (26 Oct 2026).
(a) as tested: condition at the last Close before the month starts, bought at the first Open of the month;
(b) condition checked with the first day's Open (Open > SMA30 of the previous 30 Closes), bought at that Open.
Existing exits, 10% orders, max 35%. Prints sample entries. Writes monthly_entry_main_exits_results/day1_check.csv"""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_open_next import stats
import wr_gap_v1 as w
import monthly_f1_sma30 as mf
import monthly_filter_grid as m1

G = w.G


def kw(version, cell):
    k = mf.kw(version, 'breakout only')
    if cell == '(a) prev Close > SMA30':
        sig = lambda f: w.me(f) & f.tradable.to_numpy(bool) & (f.Close > f.Close.rolling(30).mean()).fillna(False).to_numpy(bool)
    else:   # signal bar = last day of the month; condition uses the NEXT bar's Open (the Open we buy at)
        sig = lambda f: w.me(f) & (f.Open.shift(-1) > f.Close.rolling(30).mean()).fillna(False).to_numpy(bool)
    k.update(extra_signal_fn=sig, extra_exit_signal_fn=None, extra_main_exits=True, extra_first=True, extra_size_div=10, extra_max_frac=.35)
    return k


def job(a):
    cell, version = a
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(G['fr'], start='2000-01-01', **kw(version, cell))
    c = c.loc[:'2025-08-15']
    s = stats(c, t)
    tr, _ = m1.piece(c.equity, '2000-01-01', '2015-12-31')
    te, _ = m1.piece(c.equity, '2016-01-01', '2025-08-15')
    x = t[t.kind == 'extra']
    return dict(cell=cell, version=version, cagr=s['cagr'], cagr_train=tr, cagr_test=te, records=s['records'], mdd=s['mdd'], win_rate=s['wr'],
                monthly_trades=len(x), monthly_wr=(x.net_return > 0).mean(), monthly_e=x.net_return.mean(), monthly_bars=x.bars.mean()), x


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    first = set(cal.groupby(cal.dt.to_period('M')).min())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    cells = ['(a) prev Close > SMA30', '(b) day-1 Open > SMA30']
    with Pool(4) as p:
        res = p.map(job, [(c_, v) for c_ in cells for v in ('realistic', 'unrestricted')], chunksize=1)
    D = pd.DataFrame([r for r, _ in res])
    D.to_csv('monthly_entry_main_exits_results/day1_check.csv', index=False)
    x = res[0][1]
    ed = pd.to_datetime(x.entry_date)
    print('entries on the first trading day of the month:', round(float(ed.isin(first).mean()), 3))
    print(x.assign(entry_date=ed.dt.date)[['ticker', 'entry_date', 'exit_date', 'net_return', 'bars', 'reason']].tail(6).to_string(index=False))
    pd.set_option('display.width', 220)
    print(D.round(3).to_string(index=False))
