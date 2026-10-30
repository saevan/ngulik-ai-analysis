"""High win-rate buy-below-range module (plan: high_wr_range_results/PLAN.md)."""
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

OUT = ROOT / 'high_wr_range_results'
GRID = list(product((.02, .03, .05, 'mid'), ('none', 'range low -5%', 'entry -10%'), (5, 10, 20)))
PER = {'2000-25': ('2000-01-01', '2025-08-15'), 'train 2000-15': ('2000-01-01', '2015-12-31'), 'test 2016-25': ('2016-01-01', '2025-08-15'),
       '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'), '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
G = {}


def prep(t):
    if t in G['cache']:
        return G['cache'][t]
    f = G['fr'][t]
    f = f[f.tradable].reset_index(drop=True)
    o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close'])
    d = f['Date/Time'].to_numpy()
    H = pd.Series(h).rolling(20).max().to_numpy(); L = pd.Series(l).rolling(20).min().to_numpy()
    cc = pd.Series(c)
    er = ((cc - cc.shift(20)).abs() / cc.diff().abs().rolling(20).sum()).to_numpy()
    ok = np.isin(d, G['ok'][t]) & (d >= np.datetime64('2000-01-01')) & (d <= np.datetime64('2025-08-15'))
    w = H / L - 1
    pos = (c - L) / (H - L)
    base = ok & (er < .2) & (w >= .10) & (w < .40)
    G['cache'][t] = (o, h, l, c, d, H, L, base, pos)
    return G['cache'][t]


def sim(cell, seed=None, counts=None):
    tg, stop, tmax = cell
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t in G['fr']:
        o, h, l, c, d, H, L, base, pos = prep(t)
        n = len(c)
        if rng is None:
            ks = np.flatnonzero(base & (pos <= .2))
        else:
            pool = np.flatnonzero(base & (pos <= .5))
            k_ = counts.get(t, 0)
            ks = np.sort(rng.choice(pool, min(k_, len(pool)), replace=False)) if k_ and len(pool) else np.array([], int)
        busy = -1
        for k in ks:
            i = k + 1
            if i <= busy or i + tmax >= n:
                continue
            e = o[i]
            tgt = (H[k] + L[k]) / 2 if tg == 'mid' else e * (1 + tg)
            if tgt <= e:
                continue
            sl = L[k] * .95 if stop == 'range low -5%' else (e * .90 if stop == 'entry -10%' else -np.inf)
            for j in range(i, i + tmax):
                if j > i and o[j] >= tgt:
                    px, je = o[j], j; break
                if h[j] >= tgt:
                    px, je = tgt, j; break
                if c[j] < sl and j + 1 < n:
                    px, je = o[j + 1], j + 1; break
                if j == i + tmax - 1:
                    px, je = c[j], j
            out.append((t, d[i], np.log(px / e), px / e - 1, je - i + 1))
            busy = je
    T = pd.DataFrame(out, columns=['ticker', 'entry', 'gross', 'simple', 'bars'])
    T['net_B'] = T.gross - .009
    return T


def run_cell(cell):
    T = sim(cell)
    counts = T.groupby('ticker').size().to_dict()
    C = pd.concat([sim(cell, zlib.crc32(f'{cell}-{s}'.encode()), counts) for s in range(5)])
    rows = []
    for pn, (a, b) in PER.items():
        x = T[(T.entry >= np.datetime64(a)) & (T.entry <= np.datetime64(b))]
        y = C[(C.entry >= np.datetime64(a)) & (C.entry <= np.datetime64(b))]
        dd = x.groupby('entry').net_B.mean().reindex(G['cal'].loc[a:b].index)
        m, se, _ = nw(dd.to_numpy(), cell[2])
        wn = x.net_B > 0
        aw, al = x.gross[wn].mean(), x.gross[~wn].mean()
        rows.append(dict(target=str(cell[0]), stop=cell[1], time=cell[2], period=pn, trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25),
                         win_rate=wn.mean(), breakeven_wr=(-al + .009) / (aw - al) if len(x) else np.nan, avg_win_pct=aw * 100, avg_loss_pct=al * 100,
                         net_B_pct=m * 100, t=m / se if se else np.nan, net_B_event_pct=x.net_B.mean() * 100, control_net_pct=y.net_B.mean() * 100,
                         control_wr=(y.net_B > 0).mean(), avg_bars=x.bars.mean(),
                         net_simple_event_pct=(x.simple.mean() - .009) * 100))
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
    D.to_csv(OUT / 'results_all.csv', index=False)
    key = ['target', 'stop', 'time']
    P = D.pivot_table(index=key, columns='period', values=['win_rate', 'net_B_pct', 't', 'control_net_pct'])
    full = D[D.period == '2000-25'].set_index(key)
    tr = D[D.period == 'train 2000-15'].set_index(key)
    te = D[D.period == 'test 2016-25'].set_index(key)
    subs = D[D.period.isin(['2000-07', '2008-15', '2016-20', '2021-25'])].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum()))
    elig = tr[tr.win_rate >= .65]
    pick = elig.net_B_pct.idxmax() if len(elig) else None
    S = full[['trades_per_year', 'win_rate', 'breakeven_wr', 'avg_win_pct', 'avg_loss_pct', 'net_B_pct', 't', 'control_net_pct', 'avg_bars', 'net_simple_event_pct']].join(
        tr[['win_rate', 'net_B_pct']].add_prefix('train_')).join(te[['win_rate', 'net_B_pct', 't']].add_prefix('test_')).join(subs.rename('subperiods_positive'))
    S.to_csv(OUT / 'summary.csv')
    pd.set_option('display.width', 260); pd.set_option('display.max_rows', 60)
    print(S.round(3).to_string())
    if pick is not None:
        r = te.loc[pick]
        ok = r.net_B_pct > 0 and r.t >= 2 and r.win_rate >= .65 and r.net_B_pct > r.control_net_pct and subs.loc[pick] >= 3
        print('PICK (train):', pick, '| test net %.2f%% t %.2f WR %.2f | subperiods %d | PASSES: %s' % (r.net_B_pct, r.t, r.win_rate, subs.loc[pick], ok))
    else:
        print('No cell has a training win rate >= 65%')
