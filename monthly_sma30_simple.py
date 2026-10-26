"""User's intended monthly entry (26 Oct 2026): at the month-end Close, if Close > SMA30 (optionally ER20 >= 0.2, the
system's existing ER threshold), buy at the first Open of the month (mom120 order); positions use the EXISTING exits only
(fade 2 ATR, Close < SMA30, gapdown_close; no failed exit = V2). Sizing 10% / max 35% or 25% (like breakouts).
Writes monthly_entry_main_exits_results/sma30_simple.csv"""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_breakout_er import efficiency_ratio
import wr_gap_v1 as w
import monthly_f1_sma30 as mf

G = w.G


def kw(version, cell):
    if cell in ('V2 now', 'breakout only'):
        return mf.kw(version, cell)
    filt, size = cell.split('|')
    k = mf.kw(version, 'breakout only')
    def sig(f):
        s = w.me(f) & f.tradable.to_numpy(bool) & (f.Close > f.Close.rolling(30).mean()).fillna(False).to_numpy(bool)
        if filt == 'SMA30+ER0.2':
            s &= (efficiency_ratio(f.Close, 20) >= .2).fillna(False).to_numpy(bool)
        return s
    k.update(extra_signal_fn=sig, extra_exit_signal_fn=None, extra_main_exits=True, extra_first=True,
             extra_size_div=10 if size == '10%' else 4, extra_max_frac=.35 if size == '10%' else None)
    return k


mf.kw_orig = mf.kw
def job(a):
    cell, version = a
    saved = mf.kw
    mf.kw = lambda v, c: kw(v, c) if '|' in c else saved(v, c)
    try:
        return mf.job(a)
    finally:
        mf.kw = saved


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    cells = ['V2 now', 'breakout only'] + [f'{f}|{s}' for f in ('SMA30', 'SMA30+ER0.2') for s in ('10%', '25%')]
    with Pool(4) as p:
        D = pd.DataFrame(p.map(job, [(c_, v) for c_ in cells for v in ('realistic', 'unrestricted')], chunksize=1))
    D.to_csv('monthly_entry_main_exits_results/sma30_simple.csv', index=False)
    pd.set_option('display.width', 220)
    print(D.round(3).to_string(index=False))
