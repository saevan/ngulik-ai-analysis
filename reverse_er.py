"""Reverse (signed) ER mirror entry for sideways markets (plan: reverse_er_results/PLAN.md)."""
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
from analyze_portfolio_regimes import regime_proxy

OUT = ROOT / 'reverse_er_results'
COST = .009
GRID = list(product((-.3, -.4, -.5), ('Close > SMA10', 'time 10', 'Close > SMA10 or time 20'), ('none', 'entry -10%')))
PER = {'2000-25': ('2000-01-01', '2025-08-15'), 'train 2000-15': ('2000-01-01', '2015-12-31'), 'test 2016-25': ('2016-01-01', '2025-08-15'),
       '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'), '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
G = {}


def prep(t):
    if t in G['cache']:
        return G['cache'][t]
    f = G['fr'][t]; f = f[f.tradable].reset_index(drop=True)
    o, c = f.Open.to_numpy(float), f.Close.to_numpy(float); d = f['Date/Time'].to_numpy()
    cc = pd.Series(c)
    ser = ((cc - cc.shift(20)) / cc.diff().abs().rolling(20).sum()).to_numpy()
    newlow = (cc <= cc.shift(1).rolling(20).min()).to_numpy()
    sma10 = cc.rolling(10).mean().to_numpy()
    side_next = np.zeros(len(c), bool)
    side_next[:-1] = (G['lab'].reindex(pd.DatetimeIndex(d[1:])).to_numpy() == 'sideways')
    ok_next = np.zeros(len(c), bool)
    ok_next[:-1] = np.isin(d[1:], G['ok'][t]) & (d[1:] >= np.datetime64('2000-01-01')) & (d[1:] <= np.datetime64('2025-08-15'))
    G['cache'][t] = (o, c, d, ser, newlow, sma10, side_next & ok_next)
    return G['cache'][t]


def sim(cell, seed=None, counts=None):
    thr, ex, stop = cell
    rng = np.random.default_rng(seed) if seed is not None else None
    tmax = 10 if ex == 'time 10' else (20 if 'time 20' in ex else 250)
    out = []
    for t in G['fr']:
        o, c, d, ser, newlow, sma10, base = prep(t)
        n = len(c)
        if rng is None:
            ks = np.flatnonzero(base & (ser <= thr) & newlow)
        else:
            pool = np.flatnonzero(base); k_ = counts.get(t, 0)
            ks = np.sort(rng.choice(pool, min(k_, len(pool)), replace=False)) if k_ and len(pool) else np.array([], int)
        busy = -1
        for k in ks:
            i = k + 1
            if i <= busy or i + 1 >= n:
                continue
            e = o[i]; px = je = None
            for j in range(i, min(n, i + tmax)):
                last = j == i + tmax - 1 or j == n - 1
                sig = ('SMA10' in ex and c[j] > sma10[j]) or (stop == 'entry -10%' and c[j] < e * .9)
                if sig and j + 1 < n:
                    px, je = o[j + 1], j + 1; break
                if last:
                    px, je = c[j], j; break
            out.append((t, d[i], np.log(px / e), je - i + 1))
            busy = je
    T = pd.DataFrame(out, columns=['ticker', 'entry', 'gross', 'bars'])
    T['net_B'] = T.gross - COST
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
        m, se, _ = nw(dd.to_numpy(), 10)
        wn = x.net_B > 0; aw, al = x.gross[wn].mean(), x.gross[~wn].mean()
        rows.append(dict(er_max=cell[0], exit=cell[1], stop=cell[2], period=pn, trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25),
                         win_rate=wn.mean(), breakeven_wr=(-al + COST) / (aw - al) if len(x) else np.nan, avg_win_pct=aw * 100, avg_loss_pct=al * 100,
                         net_B_pct=m * 100, t=m / se if se else np.nan, net_B_event_pct=x.net_B.mean() * 100, control_net_pct=y.net_B.mean() * 100,
                         avg_bars=x.bars.mean()))
    return rows


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
    G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['lab'] = regime_proxy(st)['regime']
    G['cache'] = {}
    with np.errstate(invalid='ignore', divide='ignore'), Pool(4) as p:
        D = pd.DataFrame([r for rows in p.map(run_cell, GRID, chunksize=2) for r in rows])
    D.to_csv(OUT / 'results_all.csv', index=False)
    key = ['er_max', 'exit', 'stop']
    full = D[D.period == '2000-25'].set_index(key); tr = D[D.period == 'train 2000-15'].set_index(key); te = D[D.period == 'test 2016-25'].set_index(key)
    subs = D[D.period.isin(['2000-07', '2008-15', '2016-20', '2021-25'])].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum()))
    S = full[['trades_per_year', 'win_rate', 'breakeven_wr', 'avg_win_pct', 'avg_loss_pct', 'net_B_pct', 't', 'control_net_pct', 'avg_bars']].join(
        tr[['net_B_pct']].add_prefix('train_')).join(te[['net_B_pct', 't', 'control_net_pct']].add_prefix('test_')).join(subs.rename('subperiods_positive'))
    S.to_csv(OUT / 'summary.csv')
    pick = tr.net_B_pct.idxmax(); r = te.loc[pick]
    ok = r.net_B_pct > 0 and r.t >= 2 and r.net_B_pct > r.control_net_pct and subs.loc[pick] >= 3
    pd.set_option('display.width', 250)
    print(S.round(2).to_string())
    print('PICK (train):', pick, '| test net %.2f%% t %.2f control %.2f%% | subperiods %d | PASSES: %s' % (r.net_B_pct, r.t, r.control_net_pct, subs.loc[pick], ok))
