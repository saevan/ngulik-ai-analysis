"""Monthly entry whose positions use the existing exits (plan: monthly_entry_main_exits_results/PLAN.md)."""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_breakout_er import efficiency_ratio
from backtest_open_next import stats
import wr_gap_v1 as w
import monthly_filter_grid as m1

G = w.G


def filt(name, f):
    c = f.Close
    er = efficiency_ratio(c, 20)
    if name == 'F1':
        ok = (c > c.shift(120)) & (er >= .3)
    elif name == 'F2':
        ok = (er >= .4) & (c > c.shift(20))
    else:
        ok = (c > c.shift(120)) & (er >= .3) & (c > c.rolling(30).mean())
    return ok.fillna(False).to_numpy(bool)


def kw(version, cell):
    k = dict(rc.kw(m1.BASE, 'B'), failed_exit=None)
    if cell == 'V2 now':
        k = dict(w.kw(version, True, None), failed_exit=None)
    elif cell != 'breakout only':
        fn, size = cell.split('|')
        k.update(extra_signal_fn=lambda f: w.me(f) & f.tradable.to_numpy(bool) & filt(fn, f), extra_exit_signal_fn=None, extra_first=True,
                 extra_main_exits=True, extra_size_div=10 if size == 'S1' else 4, extra_max_frac=.35 if size == 'S1' else None)
    if version == 'realistic':
        k.update(liq_cap=.25, gate_dates=G['gate'])
    return k


def job(a):
    cell, version = a
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(G['fr'], start='2000-01-01', **kw(version, cell))
    c = c.loc[:'2025-08-15']
    if 'kind' not in t:
        t['kind'] = 'main'
    s = stats(c, t)
    tr, mtr = m1.piece(c.equity, '2000-01-01', '2015-12-31')
    te, mte = m1.piece(c.equity, '2016-01-01', '2025-08-15')
    x = t[t.kind == 'extra']
    return dict(cell=cell, version=version, cagr=s['cagr'], cagr_train=tr, cagr_test=te, records=s['records'], mdd=s['mdd'], win_rate=s['wr'],
                expectancy=s['mean'], mean_bars=s['mean_bars'], invested=s['invested'], breakout_trades=int((t.kind == 'main').sum()),
                monthly_trades=len(x), monthly_wr=(x.net_return > 0).mean() if len(x) else np.nan,
                monthly_e=x.net_return.mean() if len(x) else np.nan, monthly_bars=x.bars.mean() if len(x) else np.nan,
                monthly_exit_le2=(x.bars <= 2).mean() if len(x) else np.nan,
                monthly_reasons=x.reason.value_counts(normalize=True).round(2).to_dict() if len(x) else {})


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    cells = ['V2 now', 'breakout only'] + [f'{f}|{s}' for f in ('F1', 'F2', 'F3') for s in ('S1', 'S2')]
    with Pool(4) as p:
        D = pd.DataFrame(p.map(job, [(c_, v) for c_ in cells for v in ('realistic', 'unrestricted')], chunksize=1))
    D.to_csv('monthly_entry_main_exits_results/results.csv', index=False)
    R, U = D[D.version == 'realistic'].set_index('cell'), D[D.version == 'unrestricted'].set_index('cell')
    v = 'V2 now'
    ok = (R.cagr_train >= R.loc[v, 'cagr_train']) & (R.cagr_test >= R.loc[v, 'cagr_test']) & (U.cagr >= U.loc[v, 'cagr'] - .05) & \
         (R.mdd >= R.loc[v, 'mdd'] - .05) & (U.mdd >= U.loc[v, 'mdd'] - .05)
    D['candidate'] = D.cell.map(ok) & ~D.cell.isin(['V2 now', 'breakout only'])
    D.to_csv('monthly_entry_main_exits_results/results.csv', index=False)
    pd.set_option('display.width', 280); pd.set_option('display.max_columns', 30); pd.set_option('display.max_colwidth', 80)
    print(D.drop(columns='monthly_reasons').round(3).to_string(index=False))
    print(D[['cell', 'version', 'monthly_reasons']].to_string(index=False))
