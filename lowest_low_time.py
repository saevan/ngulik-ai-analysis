"""Second logic: lowest-low-held-for-x-bars entry, no-new-trade-high-for-x-bars exit (plan: lowest_low_time_results/PLAN.md).
Per-trade standalone test on the realistic universe plus a random-entry control."""
import sys
from itertools import product
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy

OUT = ROOT / 'lowest_low_time_results'
G = {}
GRID = list(product([10, 20, 60], [3, 5, 10], ['sideways', 'none'], ['next_open', 'close']))
PER = {'2000-25': ('2000-01-01', '2025-08-15'), '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
       '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}


def exit_from(i0, h0, x, o, h, c, n):
    """Trade high starts at h0 on bar i0; exit at the next Open after x bars with no new high. Returns (exit_idx, price)."""
    hi, last = h0, i0
    j = i0 + 1
    while j < n:
        if h[j] > hi:
            hi, last = h[j], j
        if j - last >= x:
            return (j + 1, o[j + 1]) if j + 1 < n else (None, None)
        j += 1
    return None, None


def sim(cell, random_seed=None):
    N, x, filt, entry = cell
    trades = []
    rng = np.random.default_rng(random_seed) if random_seed is not None else None
    for t, f in G['fr'].items():
        f = f[f.tradable].reset_index(drop=True)
        n = len(f)
        if n < 300:
            continue
        o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close'])
        d = f['Date/Time'].to_numpy()
        ok = np.isin(d, G['ok'][t]) & (d >= np.datetime64('2000-01-01')) & (d <= np.datetime64('2025-08-15'))
        if filt in ('sideways', 'market_and_stock'):
            ok &= np.isin(d, G['side'])
        if filt in ('stock_er', 'market_and_stock'):
            cc = pd.Series(c)
            er = ((cc - cc.shift(20)).abs() / cc.diff().abs().rolling(20).sum()).to_numpy()
            ok &= er < .3
        prior = pd.Series(l).shift(1).rolling(N).min().to_numpy()
        newlow = l <= prior
        lows = np.flatnonzero(newlow)
        sig = np.zeros(n, bool)
        # signal at bar s + x when no new N-bar low happened in s+1..s+x
        nxt = np.r_[lows[1:], n + 10**6]
        for s, s2 in zip(lows, nxt):
            tt = s + x
            if tt < n and s2 > tt:
                sig[tt] = True
        sig &= ok
        if rng is not None:  # control: same number of entries on random eligible days of this stock
            pool = np.flatnonzero(ok)
            k = int(sig.sum())
            sig = np.zeros(n, bool)
            if k and len(pool):
                sig[rng.choice(pool, min(k, len(pool)), replace=False)] = True
        i = 0
        busy_until = -1
        for tt in np.flatnonzero(sig):
            if tt <= busy_until or tt + 1 >= n:
                continue
            if entry == 'next_open':
                e_i, e_px, h0 = tt + 1, o[tt + 1], h[tt + 1]
            else:
                e_i, e_px, h0 = tt, c[tt], c[tt]
            xi, xpx = exit_from(e_i, h0, x, o, h, c, n)
            if xi is None:
                break
            trades.append((t, d[tt], d[xi], np.log(xpx / e_px), xi - e_i))
            busy_until = xi
    T = pd.DataFrame(trades, columns=['ticker', 'signal', 'exit', 'gross', 'bars'])
    T['net_B'] = T.gross - .009
    return T


def summarize(T, cell, kind):
    N, x, filt, entry = cell
    rows = []
    for pn, (s, e) in PER.items():
        z = T[(T.signal >= np.datetime64(s)) & (T.signal <= np.datetime64(e))]
        daily = z.groupby('signal').net_B.mean().reindex(G['cal'].loc[s:e].index)
        m, se, nn = nw(daily.values, 20)
        rows.append(dict(N=N, x=x, filter=filt, entry=entry, kind=kind, period=pn, trades=len(z),
                         trades_per_year=len(z) / ((pd.Timestamp(e) - pd.Timestamp(s)).days / 365.25),
                         gross_pct=z.gross.mean() * 100, net_B_pct=m * 100, t_net_B=m / se if se else np.nan,
                         net_B_event_pct=z.net_B.mean() * 100, net_A_event_pct=(z.gross.mean() - .004) * 100,
                         win_rate_B=(z.net_B > 0).mean(), avg_win_pct=z.gross[z.gross > 0].mean() * 100,
                         avg_loss_pct=z.gross[z.gross <= 0].mean() * 100, avg_bars=z.bars.mean()))
    return rows


def run_cell(cell):
    T = sim(cell)
    R = sim(cell, random_seed=hash(cell) % 2**32)
    T['cell'] = str(cell)
    return summarize(T, cell, 'signal') + summarize(R, cell, 'random_control'), T


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
    reg = regime_proxy(st)['regime']
    G['side'] = np.array(reg.index[reg == 'sideways'], dtype='datetime64[ns]')
    G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    with Pool(4) as p:
        res = p.map(run_cell, GRID)
    d = pd.DataFrame([r for rows, _ in res for r in rows])
    pd.concat([T for _, T in res]).to_csv(OUT / 'trades.csv', index=False)
    key = ['N', 'x', 'filter', 'entry']
    sig = d[d.kind == 'signal']
    ctl = d[d.kind == 'random_control'].set_index(key + ['period'])
    flags = []
    for k_, g in sig.groupby(key):
        full = g[g.period == '2000-25'].iloc[0]
        subs = (g[g.period != '2000-25'].net_B_pct > 0).sum()
        c_ = ctl.loc[tuple(k_) + ('2000-25',)]
        flags.append(dict(zip(key, k_), passes=bool(full.net_B_pct > 0 and full.t_net_B >= 3 and subs >= 3 and full.net_B_pct > c_.net_B_pct),
                          subperiods_positive=int(subs), control_net_B_pct=c_.net_B_pct))
    F = pd.DataFrame(flags)
    d = d.merge(F, on=key, how='left')
    d.to_csv(OUT / 'results.csv', index=False)
    pd.set_option('display.width', 260); pd.set_option('display.max_rows', 100)
    v = d[(d.kind == 'signal') & (d.period == '2000-25')]
    print(v[key + ['trades_per_year', 'gross_pct', 'net_B_pct', 't_net_B', 'net_B_event_pct', 'win_rate_B', 'avg_win_pct', 'avg_loss_pct',
                   'avg_bars', 'subperiods_positive', 'control_net_B_pct', 'passes']].round(2).to_string(index=False))
    print(d[d.kind == 'signal'].pivot_table(index=key, columns='period', values='net_B_pct').round(2).to_string())
