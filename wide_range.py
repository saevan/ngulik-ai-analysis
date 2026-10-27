"""Wider / longer ranges (plan: wide_range_results/PLAN.md). Fade the bottom 20% of a range-bound stock's N-bar range.
Writes wide_range_results/results.csv, trades.csv.gz"""
import sys, zlib
from itertools import product
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl

OUT = ROOT / 'wide_range_results'
NS = (20, 60, 120, 250)
WIDTHS = ((.10, .20), (.20, .40), (.40, .80), (.80, 99.))
GRID = list(product(NS, WIDTHS, ('mid', 'top'), ('stop', 'nostop')))
PER = {'2000-25': ('2000-01-01', '2025-08-15'), '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
       '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
G = {}


def prep(t, N):
    key = (t, N)
    if key in G['cache']:
        return G['cache'][key]
    f = G['fr'][t]
    f = f[f.tradable].reset_index(drop=True)
    o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close'])
    d = f['Date/Time'].to_numpy()
    H = pd.Series(h).rolling(N).max().to_numpy()
    L = pd.Series(l).rolling(N).min().to_numpy()
    cc = pd.Series(c)
    er = ((cc - cc.shift(N)).abs() / cc.diff().abs().rolling(N).sum()).to_numpy()
    pos = (c - L) / (H - L)
    ok = np.isin(d, G['ok'][t]) & (d >= np.datetime64('2000-01-01')) & (d <= np.datetime64('2025-08-15'))
    out = (o, h, l, c, d, H, L, er, H / L - 1, pos, ok)
    G['cache'][key] = out
    return out


def trade(i, n, o, h, c, H, L, N, target, stop):
    e = i + 1
    tgt = (H[i] + L[i]) / 2 if target == 'mid' else L[i] + .8 * (H[i] - L[i])
    tmax = max(1, N // 2)
    for j in range(e, min(e + tmax, n)):
        if h[j] >= tgt:
            return j, max(o[j], tgt) if j > e else max(o[e], tgt)
        if stop == 'stop' and c[j] < L[i] * .97 and j + 1 < n:
            return j + 1, o[j + 1]
        if j - e + 1 >= tmax:
            return j, c[j]
    return None, None


def sim(cell, seed=None, counts=None):
    N, (wlo, whi), target, stop = cell
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t in G['fr']:
        o, h, l, c, d, H, L, er, width, pos, ok = prep(t, N)
        n = len(c)
        cond = ok & (er < .3) & (width >= wlo) & (width < whi) & np.isfinite(pos)
        if rng is None:
            sig = np.flatnonzero(cond & (pos <= .2))
        else:
            pool = np.flatnonzero(cond & (pos <= .5))
            k = counts.get(t, 0)
            sig = np.sort(rng.choice(pool, min(k, len(pool)), replace=False)) if k and len(pool) else np.array([], int)
        busy = -1
        for i in sig:
            if i <= busy or i + 1 >= n:
                continue
            j, px = trade(i, n, o, h, c, H, L, N, target, stop)
            if j is None:
                break
            out.append((t, d[i], np.log(px / o[i + 1]), j - i))
            busy = j
    T = pd.DataFrame(out, columns=['ticker', 'signal', 'gross', 'bars'])
    T['net_B'], T['net_A'] = T.gross - .009, T.gross - .004
    return T


def run_cell(cell):
    T = sim(cell)
    counts = T.groupby('ticker').size().to_dict()
    ctl = [sim(cell, zlib.crc32(f'{cell}-{s}'.encode()), counts).gross.mean() for s in range(5)]
    rows = []
    for pn, (a, b) in PER.items():
        x = T[(T.signal >= np.datetime64(a)) & (T.signal <= np.datetime64(b))]
        daily = x.groupby('signal').net_B.mean().reindex(G['cal'].loc[a:b].index)
        m, se, _ = nw(daily.to_numpy(), 20)
        w = x.net_B > 0
        rows.append(dict(N=cell[0], width=f'{int(cell[1][0]*100)}-{int(cell[1][1]*100) if cell[1][1] < 9 else "+"}%', target=cell[2], stop=cell[3],
                         period=pn, trades=len(x), trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25),
                         gross_pct=x.gross.mean() * 100, net_B_pct=m * 100, t_net_B=m / se if se else np.nan, net_A_event_pct=x.net_A.mean() * 100,
                         win_rate_B=w.mean(), avg_win_pct=x.gross[w].mean() * 100, avg_loss_pct=x.gross[~w].mean() * 100, avg_bars=x.bars.mean(),
                         control_gross_pct=float(np.nanmean(ctl) * 100)))
    T['cell'] = str(cell)
    return rows, T


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
    G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['cache'] = {}
    with Pool(4) as p:
        res = p.map(run_cell, GRID, chunksize=4)
    D = pd.DataFrame([r for rows, _ in res for r in rows])
    pd.concat([T for _, T in res]).to_csv(OUT / 'trades.csv.gz', index=False)
    key = ['N', 'width', 'target', 'stop']
    subs = D[D.period != '2000-25'].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum())).rename('subperiods_positive')
    F = D[D.period == '2000-25'].merge(subs, on=key)
    F['passes'] = (F.net_B_pct > 0) & (F.t_net_B >= 3) & (F.subperiods_positive >= 3) & (F.gross_pct > F.control_gross_pct)
    D.to_csv(OUT / 'results_all.csv', index=False)
    F.to_csv(OUT / 'results.csv', index=False)
    pd.set_option('display.width', 250); pd.set_option('display.max_rows', 100)
    print(F[key + ['trades_per_year', 'gross_pct', 'control_gross_pct', 'net_B_pct', 't_net_B', 'net_A_event_pct', 'win_rate_B', 'avg_win_pct',
                   'avg_loss_pct', 'avg_bars', 'subperiods_positive', 'passes']].round(2).to_string(index=False))
