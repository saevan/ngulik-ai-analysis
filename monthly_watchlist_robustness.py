"""Post-hoc robustness of the step-2 candidate (F_mom watchlist) - neighbours and holdout (26 Oct 2026, labelled post hoc).
Watchlist filters: Close > Close n bars ago (n = 60, 90, 120, 180, 250) and Close > SMA n (n = 60, 120, 200).
Unrestricted and realistic 2000-2025, plus unrestricted holdout 1995-03..1999 for the 120-bar filter vs no watchlist.
Writes monthly_trend_entry_results/watchlist_robustness.csv"""
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_open_next import stats
from monthly_trend_entry import PER

OUT = Path(__file__).resolve().parent / 'monthly_trend_entry_results'
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
G = {}


def ok(kind, n, f):
    c = f.Close
    if kind == 'none':
        return np.ones(len(f), bool)
    return ((c > c.shift(n)) if kind == 'mom' else (c > c.rolling(n).mean())).fillna(False).to_numpy(bool)


def gate_for(f, kind, n):
    mon = f['Date/Time'].dt.to_period('M')
    last = ~mon.duplicated(keep='last')
    allowed = set(mon[last][ok(kind, n, f)[last.to_numpy()]] + 1)
    return set(f['Date/Time'][mon.isin(allowed)])


def job(a):
    kind, n, version = a
    fr, start = G['fr'], '2000-01-01'
    if version == 'holdout':
        fr, start = {t: g for t, f in fr.items() if len(g := f[f['Date/Time'] <= '1999-12-31'].reset_index(drop=True))}, '1995-03-01'
    gate = {t: gate_for(f, kind, n) for t, f in fr.items()}
    if version == 'realistic':
        gate = {t: g & G['pit'][t] for t, g in gate.items()}
    k = dict(rc.kw(BASE, 'B'), gate_dates=gate)
    if version == 'realistic':
        k['liq_cap'] = .25
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(fr, start=start, **k)
    if version != 'holdout':
        c = c.loc[:'2025-08-15']
    s = stats(c, t)
    row = dict(filter=f'{kind}{n}', version=version, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], win_rate=s['wr'], expectancy=s['mean'])
    if version != 'holdout':
        eq = c.equity
        for pn, (a_, b_) in PER.items():
            x, prev = eq.loc[a_:b_], eq.loc[:str(int(a_) - 1)]
            st0 = prev.iloc[-1] if len(prev) else 1e9
            y = (x.index[-1] - (prev.index[-1] if len(prev) else x.index[0])).days / 365.25
            row[f'cagr_{pn}'] = float((x.iloc[-1] / st0) ** (1 / y) - 1)
    return row


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['pit'] = {t: set(pit[t] & stale[t]) for t in G['fr']}
    jobs = [(k_, n, v) for k_, ns in (('mom', (60, 90, 120, 180, 250)), ('sma', (60, 120, 200))) for n in ns for v in ('unrestricted', 'realistic')]
    jobs += [('none', 0, 'holdout'), ('mom', 120, 'holdout'), ('mom', 90, 'holdout'), ('mom', 180, 'holdout'), ('sma', 120, 'holdout')]
    with Pool(4) as pool:
        D = pd.DataFrame(pool.map(job, jobs, chunksize=1))
    D.to_csv(OUT / 'watchlist_robustness.csv', index=False)
    pd.set_option('display.width', 250)
    print(D.round(3).to_string(index=False))
