"""Buy the turn after a decline (plan: buy_the_turn_results/PLAN.md)."""
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

OUT = ROOT / 'buy_the_turn_results'
GRID = list(product((.10, .15, .20), ('any ER', 'sideways ER<0.2'), (.5, 1.0)))
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
    hh20 = pd.Series(h).rolling(20).max().to_numpy()
    dd = 1 - c / hh20
    mdd10 = pd.Series(dd).rolling(10).max().to_numpy()
    low10 = pd.Series(l).rolling(10).min().to_numpy()
    hh3p = pd.Series(h).shift(1).rolling(3).max().to_numpy()
    cc = pd.Series(c)
    er = ((cc - cc.shift(20)).abs() / cc.diff().abs().rolling(20).sum()).to_numpy()
    ok = np.isin(d, G['ok'][t]) & (d >= np.datetime64('2000-01-01')) & (d <= np.datetime64('2025-08-15'))
    G['cache'][t] = (o, h, l, c, d, hh20, dd, mdd10, low10, hh3p, er, ok)
    return G['cache'][t]


def sim(cell, seed=None, counts=None):
    X, erv, frac = cell
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t in G['fr']:
        o, h, l, c, d, hh20, dd, mdd10, low10, hh3p, er, ok = prep(t)
        n = len(c)
        setup = ok & (mdd10 >= X) & (dd >= X / 2)
        if erv != 'any ER':
            setup &= er < .2
        if rng is None:
            ks = np.flatnonzero(setup & (c > hh3p))
        else:
            pool = np.flatnonzero(setup)
            k_ = counts.get(t, 0)
            ks = np.sort(rng.choice(pool, min(k_, len(pool)), replace=False)) if k_ and len(pool) else np.array([], int)
        busy = -1
        for k in ks:
            i = k + 1
            if i <= busy or i + 10 >= n:
                continue
            if o[i] > c[k] * 1.02:
                continue
            lo, tgt = low10[k], low10[k] + frac * (hh20[k] - low10[k])
            if o[i] >= tgt:      # target already reached before entry: no trade (bug fix before reading results)
                continue
            px, j_end = None, None
            for j in range(i, i + 10):
                if j > i and o[j] >= tgt:
                    px, j_end = o[j], j; break
                if h[j] >= tgt:
                    px, j_end = max(tgt, o[j]) if j > i else tgt, j; break
                if c[j] < lo and j + 1 < n:
                    px, j_end = o[j + 1], j + 1; break
                if j == i + 9:
                    px, j_end = c[j], j
            out.append((t, d[i], np.log(px / o[i]), j_end - i + 1))
            busy = j_end
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
        dd_ = x.groupby('entry').net_B.mean().reindex(G['cal'].loc[a:b].index)
        m, se, _ = nw(dd_.to_numpy(), 10)
        wn = x.net_B > 0
        rows.append(dict(X=cell[0], er=cell[1], target=cell[2], period=pn, trades=len(x), trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25),
                         gross_pct=x.gross.mean() * 100, net_B_pct=m * 100, t=m / se if se else np.nan, win_rate=wn.mean(),
                         avg_win_pct=x.gross[wn].mean() * 100, avg_loss_pct=x.gross[~wn].mean() * 100, avg_bars=x.bars.mean(), control_gross_pct=ctl * 100))
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
    key = ['X', 'er', 'target']
    subs = D[D.period != '2000-25'].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum())).rename('subperiods_positive')
    F = D[D.period == '2000-25'].merge(subs, on=key)
    nb = F.groupby(['er', 'target']).net_B_pct.apply(lambda s: int((s > 0).sum())).rename('X_positive')
    F = F.merge(nb, on=['er', 'target'])
    F['passes'] = (F.net_B_pct > 0) & (F.t >= 3) & (F.subperiods_positive >= 3) & (F.gross_pct >= F.control_gross_pct + .5) & (F.X_positive >= 2)
    D.to_csv(OUT / 'results_all.csv', index=False); F.to_csv(OUT / 'results.csv', index=False)
    pd.set_option('display.width', 250)
    print(F[key + ['trades_per_year', 'gross_pct', 'control_gross_pct', 'net_B_pct', 't', 'win_rate', 'avg_win_pct', 'avg_loss_pct', 'avg_bars',
                   'subperiods_positive', 'passes']].round(2).to_string(index=False))
    print(D.pivot_table(index=key, columns='period', values='net_B_pct').round(2).to_string())
