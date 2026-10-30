"""Addendum of buy_the_turn_results/PLAN.md: no target, exit by stop or time (10 / 20 bars)."""
import zlib
from itertools import product
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
import buy_the_turn as bt
from mpstats import nw

G = bt.G
GRID = list(product((.10, .15, .20), ('any ER', 'sideways ER<0.2'), (10, 20)))


def sim(cell, seed=None, counts=None):
    X, erv, tmax = cell
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t in G['fr']:
        o, h, l, c, d, hh20, dd, mdd10, low10, hh3p, er, ok = bt.prep(t)
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
            if i <= busy or i + tmax >= n or o[i] > c[k] * 1.02:
                continue
            lo = low10[k]
            for j in range(i, i + tmax):
                if c[j] < lo and j + 1 < n:
                    px, j_end = o[j + 1], j + 1; break
                if j == i + tmax - 1:
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
    for pn, (a, b) in bt.PER.items():
        x = T[(T.entry >= np.datetime64(a)) & (T.entry <= np.datetime64(b))]
        dd_ = x.groupby('entry').net_B.mean().reindex(G['cal'].loc[a:b].index)
        m, se, _ = nw(dd_.to_numpy(), cell[2])
        wn = x.net_B > 0
        rows.append(dict(X=cell[0], er=cell[1], time_stop=cell[2], period=pn, trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25),
                         gross_pct=x.gross.mean() * 100, net_B_pct=m * 100, t=m / se if se else np.nan, win_rate=wn.mean(),
                         avg_win_pct=x.gross[wn].mean() * 100, avg_loss_pct=x.gross[~wn].mean() * 100, avg_bars=x.bars.mean(), control_gross_pct=ctl * 100))
    return rows


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
    G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['cache'] = {}
    with Pool(4) as p:
        D = pd.DataFrame([r for rows in p.map(run_cell, GRID, chunksize=3) for r in rows])
    key = ['X', 'er', 'time_stop']
    subs = D[D.period != '2000-25'].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum())).rename('subperiods_positive')
    F = D[D.period == '2000-25'].merge(subs, on=key)
    nb = F.groupby(['er', 'time_stop']).net_B_pct.apply(lambda s: int((s > 0).sum())).rename('X_positive')
    F = F.merge(nb, on=['er', 'time_stop'])
    F['breakeven_wr'] = (-F.avg_loss_pct + .9) / (F.avg_win_pct - F.avg_loss_pct)
    F['passes'] = (F.net_B_pct > 0) & (F.t >= 3) & (F.subperiods_positive >= 3) & (F.gross_pct >= F.control_gross_pct + .5) & (F.X_positive >= 2)
    D.to_csv('buy_the_turn_results/notarget_all.csv', index=False); F.to_csv('buy_the_turn_results/notarget.csv', index=False)
    pd.set_option('display.width', 250)
    print(F[key + ['trades_per_year', 'gross_pct', 'control_gross_pct', 'net_B_pct', 't', 'win_rate', 'breakeven_wr', 'avg_win_pct', 'avg_loss_pct',
                   'avg_bars', 'subperiods_positive', 'passes']].round(2).to_string(index=False))
