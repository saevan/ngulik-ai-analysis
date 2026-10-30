"""Executable swing trading inside medium/large sideways ranges (plan: swing_in_range_results/PLAN.md)."""
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

OUT = ROOT / 'swing_in_range_results'
WID = {'10-20%': (.10, .20), '20-40%': (.20, .40), '10-40%': (.10, .40)}
GRID = list(product(WID, ('any', 'lower half'), ('stop', 'stop+target')))
PER = {'2000-25': ('2000-01-01', '2025-08-15'), '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
       '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
G = {}


def prep(t):
    if t in G['cache']:
        return G['cache'][t]
    f = G['fr'][t]
    f = f[f.tradable].reset_index(drop=True)
    o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close'])
    d = f['Date/Time'].to_numpy()
    H = pd.Series(h).rolling(20).max().to_numpy(); L = pd.Series(l).rolling(20).min().to_numpy()
    hh5 = pd.Series(h).rolling(5).max().to_numpy(); ll5 = pd.Series(l).rolling(5).min().to_numpy()
    cc = pd.Series(c)
    er = ((cc - cc.shift(20)).abs() / cc.diff().abs().rolling(20).sum()).to_numpy()
    ok = np.isin(d, G['ok'][t]) & (d >= np.datetime64('2000-01-01')) & (d <= np.datetime64('2025-08-15'))
    G['cache'][t] = (o, h, l, c, d, H, L, hh5, ll5, er, ok)
    return G['cache'][t]


def exit_from(i, n, o, h, l, c, ll5, tgt):
    """Entry on bar i; sell stop at the previous 5-bar low from bar i+1; optional limit target; time stop 40 bars."""
    for j in range(i + 1, min(i + 41, n)):
        stop = ll5[j - 1]
        if tgt is not None and o[j] >= tgt:
            return j, o[j]
        if l[j] <= stop:
            return j, min(o[j], stop)
        if tgt is not None and h[j] >= tgt:
            return j, tgt
        if j == i + 40:
            return j, c[j]
    return None, None


def sim(cell, seed=None, counts=None):
    wkey, posf, ex = cell
    lo, hi = WID[wkey]
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t in G['fr']:
        o, h, l, c, d, H, L, hh5, ll5, er, ok = prep(t)
        n = len(c)
        w = H / L - 1
        cond = ok & (er < .2) & (w >= lo) & (w < hi)
        if posf == 'lower half':
            cond &= c <= (H + L) / 2
        ks = np.flatnonzero(cond)
        if rng is not None:
            k_ = counts.get(t, 0)
            ks = np.sort(rng.choice(ks, min(k_, len(ks)), replace=False)) if k_ and len(ks) else np.array([], int)
        busy = -1
        for k in ks:
            i = k + 1
            if i <= busy or i + 1 >= n:
                continue
            if rng is None:
                lvl = hh5[k]
                if not (h[i] >= lvl) or o[i] > lvl * 1.02:
                    continue
                px = max(o[i], lvl)
            else:
                px = o[i]
            j, xp = exit_from(i, n, o, h, l, c, ll5, H[k] if ex == 'stop+target' else None)
            if j is None:
                continue
            out.append((t, d[i], np.log(xp / px), j - i + 1))
            busy = j
    T = pd.DataFrame(out, columns=['ticker', 'entry', 'gross', 'bars'])
    T['net_B'] = T.gross - .009
    return T


def run_cell(cell):
    T = sim(cell)
    counts = T.groupby('ticker').size().to_dict()
    ctl = float(np.nanmean([sim(cell, zlib.crc32(f'{cell}-{s}'.encode()), counts).gross.mean() for s in range(5)]))
    rows = []
    for pn, (a, b) in PER.items():
        x = T[(T.entry >= np.datetime64(a)) & (T.entry <= np.datetime64(b))]
        dd = x.groupby('entry').net_B.mean().reindex(G['cal'].loc[a:b].index)
        m, se, _ = nw(dd.to_numpy(), 20)
        wn = x.net_B > 0
        rows.append(dict(width=cell[0], position=cell[1], exit=cell[2], period=pn, trades=len(x),
                         trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25), gross_pct=x.gross.mean() * 100,
                         net_B_pct=m * 100, t=m / se if se else np.nan, win_rate=wn.mean(), avg_win_pct=x.gross[wn].mean() * 100,
                         avg_loss_pct=x.gross[~wn].mean() * 100, avg_bars=x.bars.mean(), control_gross_pct=ctl * 100))
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
        res = p.map(run_cell, GRID, chunksize=3)
    D = pd.DataFrame([r for rows, _ in res for r in rows])
    pd.concat([T for _, T in res]).to_csv(OUT / 'trades.csv.gz', index=False)
    key = ['width', 'position', 'exit']
    subs = D[D.period != '2000-25'].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum())).rename('subperiods_positive')
    F = D[D.period == '2000-25'].merge(subs, on=key)
    F['passes_alone'] = (F.net_B_pct > 0) & (F.t >= 3) & (F.subperiods_positive >= 3) & (F.gross_pct >= F.control_gross_pct + .5)
    pos = F.groupby(['position', 'exit']).net_B_pct.apply(lambda s: int((s > 0).sum())).rename('widths_positive')
    F = F.merge(pos, on=['position', 'exit'])
    F['passes'] = F.passes_alone & (F.widths_positive >= 2)
    D.to_csv(OUT / 'results_all.csv', index=False); F.to_csv(OUT / 'results.csv', index=False)
    pd.set_option('display.width', 250)
    print(F[key + ['trades_per_year', 'gross_pct', 'control_gross_pct', 'net_B_pct', 't', 'win_rate', 'avg_win_pct', 'avg_loss_pct', 'avg_bars',
                   'subperiods_positive', 'passes']].round(2).to_string(index=False))
    print(D.pivot_table(index=key, columns='period', values='net_B_pct').round(2).to_string())
