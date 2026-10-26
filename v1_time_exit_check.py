"""Does V1 mix price and time? Quick test (26 Oct 2026, exploratory): add a time element to V1's breakout trades -
(a) time cap: original exits + sell after n bars; (b) time only: fade / SMA30 / failed off, sell after n bars.
Monthly module unchanged (it is already time based: month-start entry, month-end checks). Scenario B 2000-2025.
Writes winrate_diagnosis_results/v1_time_exit.csv"""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_open_next import stats
import wr_gap_v1 as w

G = w.G


def job(a):
    label, version, extra = a
    k = dict(w.kw(version, True, None), **extra)
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(G['fr'], start='2000-01-01', **k)
    c = c.loc[:'2025-08-15']
    s = stats(c, t)
    m, x = t[t.kind == 'main'], t[t.kind == 'extra']
    return dict(label=label, version=version, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], win_rate=s['wr'], expectancy=s['mean'],
                breakout_wr=(m.net_return > 0).mean(), breakout_e=m.net_return.mean(), monthly_wr=(x.net_return > 0).mean())


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    cells = [('V1', {})] + [(f'V1 + cap {n}', dict(max_hold=n)) for n in (10, 20, 40)] + \
            [(f'V1 time only {n}', dict(max_hold=n, fade=None, sma_len=None, failed_exit=None)) for n in (10, 20, 40)] + \
            [(f'V1 failed + time {n}', dict(max_hold=n, fade=None, sma_len=None)) for n in (10, 20, 40)]
    with Pool(4) as p:
        D = pd.DataFrame(p.map(job, [(l, v, e) for l, e in cells for v in ('unrestricted', 'realistic')], chunksize=1))
    D.to_csv('winrate_diagnosis_results/v1_time_exit.csv', index=False)
    pd.set_option('display.width', 200)
    print(D.round(3).to_string(index=False))
