"""Step 2 of monthly_trend_entry_results/PLAN.md: the month-start trend filter as a watchlist for the main pick's buy stop.
During month m a stock may be bought only if it passed the filter at its last Close of month m-1. Writes
monthly_trend_entry_results/watchlist_gate.csv"""
import zlib
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_open_next import stats
from monthly_trend_entry import trend, FILTERS, PER

OUT = Path(__file__).resolve().parent / 'monthly_trend_entry_results'
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
G = {}


def watchlist(f, filt, seed=None, p=None):
    """Allowed entry dates for one stock: all dates of month m when the filter held at the stock's last Close of month m-1."""
    mon = f['Date/Time'].dt.to_period('M')
    last = ~mon.duplicated(keep='last')
    if seed is None:
        ok = pd.Series(trend(filt, f), index=f.index)[last]
    else:
        rng = np.random.default_rng([seed, int(p * 100), zlib.crc32(str(f['Ticker'].iloc[0]).encode())])
        ok = pd.Series(rng.random(int(last.sum())) < p, index=f.index[last])
    allowed = set(mon[last][ok.to_numpy()] + 1)
    return set(f['Date/Time'][mon.isin(allowed)]), float(ok.mean())


def job(a):
    label, version, filt, seed, p = a
    gate, rates = {}, []
    for t, f in G['fr'].items():
        g, r = watchlist(f, filt, seed, p)
        gate[t] = g & G['pit'][t] if version == 'realistic' else g
        rates.append(r)
    k = rc.kw(BASE, 'B')
    k['gate_dates'] = gate
    if version == 'realistic':
        k['liq_cap'] = .25
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(G['fr'], start='2000-01-01', **k)
    c = c.loc[:'2025-08-15']
    s = stats(c, t)
    row = dict(label=label, version=version, pass_rate=float(np.mean(rates)), cagr=s['cagr'], records=s['records'], mdd=s['mdd'],
               trades=s['n'], win_rate=s['wr'], expectancy=s['mean'], e_R=s['mean'] / s['avg_loss'], payout=s['payout'], invested=s['invested'])
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
    jobs = [('V0_all', v, 'none', None, None) for v in ('unrestricted', 'realistic')]
    jobs += [(f, v, f, None, None) for f in FILTERS for v in ('unrestricted', 'realistic')]
    jobs += [(f'random_p{p}_s{s}', v, 'none', s, p) for p in (.5, .7) for s in (1, 2, 3) for v in ('unrestricted', 'realistic')]
    with Pool(4) as pool:
        D = pd.DataFrame(pool.map(job, jobs, chunksize=1))
    D.to_csv(OUT / 'watchlist_gate.csv', index=False)
    pd.set_option('display.width', 250)
    print(D.round(3).to_string(index=False))
