"""Confirmation test of 'no SMA30 + high-reset exit' (plan: high_reset_exit_results/PLAN.md, confirmation section)."""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_open_next import stats
import wr_gap_v1 as w

G = w.G


def job(a):
    label, version, extra, period = a
    k = dict(w.kw(version, True, None), **extra)
    fr, start = G['fr'], '2000-01-01'
    if period == 'holdout':
        fr, start = {t: g for t, f in fr.items() if len(g := f[f['Date/Time'] <= '1999-12-31'].reset_index(drop=True))}, '1996-01-01'
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(fr, start=start, **k)
    if period != 'holdout':
        c = c.loc[:'2025-08-15']
    s = stats(c, t)
    return dict(label=label, version=version, period=period, cagr=s['cagr'], mdd=s['mdd'], records=s['records'], win_rate=s['wr']), c.equity


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    cells = [('V1', {})] + [(f'x{x}', dict(sma_len=None, high_reset_bars=x)) for x in (16, 18, 20, 22, 25)]
    jobs = [(l, v, e, 'full') for l, e in cells for v in ('realistic', 'unrestricted')] + \
           [(l, v, e, 'holdout') for l, e in cells if l in ('V1', 'x20') for v in ('realistic', 'unrestricted')]
    with Pool(4) as p:
        res = p.map(job, jobs, chunksize=1)
    D = pd.DataFrame([r for r, _ in res])
    eq = {(r['label'], r['version'], r['period']): e for r, e in res}
    m0 = eq[('V1', 'realistic', 'full')].resample('ME').last()
    m1 = eq[('x20', 'realistic', 'full')].resample('ME').last()
    d = (np.log(m1).diff() - np.log(m0).diff()).dropna()
    mu, se, _ = nw(d.to_numpy(), 6)
    D.to_csv('high_reset_exit_results/no_sma30_confirm.csv', index=False)
    F = D[(D.period == 'full') & (D.version == 'realistic')].set_index('label')
    a = int(((F.drop('V1').cagr > F.loc['V1', 'cagr']) & (F.drop('V1').mdd >= F.loc['V1', 'mdd'])).sum())
    H = D[(D.period == 'holdout') & (D.version == 'realistic')].set_index('label')
    b = H.loc['x20', 'cagr'] > H.loc['V1', 'cagr']
    pd.set_option('display.width', 200)
    print(D.round(3).to_string(index=False))
    print(f'(a) neighbours beating V1 realistic: {a}/5 | (b) holdout x20 > V1: {b} | (c) monthly diff {mu*100:.3f}%/mo, t = {mu/se:.2f}')
    print('ACCEPTED:', a >= 4 and b and mu / se >= 1.5)
