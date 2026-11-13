"""The midline as the reference for bounces in sideways markets (plan: midline_bounce_results/PLAN.md)."""
import sys, zlib, time
from itertools import product
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy
from sideways_swings import zigzag

OUT = ROOT / 'midline_bounce_results'
COST, COST_USER, W = .009, .006, 30
A, B = '2000-01-01', '2025-08-15'
GRID = [('B pullback to bounce mid', x, T, s) for x, T, s in product((.03, .05), (10, 20), (0., .03))] + \
       [('C reclaim range mid', n, T, s) for n, T, s in product((20, 40), (10, 20), ('range low', 'back below mid'))]
PER = {'2000-25': ('2000-01-01', '2025-08-15'), 'train 2000-15': ('2000-01-01', '2015-12-31'), 'test 2016-25': ('2016-01-01', '2025-08-15'),
       '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'), '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
KEY = ['family', 'p1', 'time', 'stop']
G = {}


def prep(t):
    f = G['fr'][t]; f = f[f.tradable].reset_index(drop=True)
    o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close']); d = f['Date/Time'].to_numpy()
    C = pd.Series(c); P = dict(o=o, h=h, l=l, c=c, d=d)
    P['er20'] = ((C - C.shift(20)).abs() / C.diff().abs().rolling(20).sum()).to_numpy()
    for n_ in (20, 40):
        P[f'H{n_}'] = pd.Series(h).rolling(n_).max().to_numpy(); P[f'L{n_}'] = pd.Series(l).rolling(n_).min().to_numpy()
    base = np.zeros(len(c), bool); nd = pd.DatetimeIndex(d[1:])
    base[:-1] = (G['lab'].reindex(nd).to_numpy() == 'sideways') & np.isin(d[1:], G['ok'][t]) & (d[1:] >= np.datetime64(A)) & (d[1:] <= np.datetime64(B))
    P['base'] = base                                    # market sideways and stock eligible on t+1
    P['lows'] = {}
    for x in (.03, .05):
        conf = {}                                       # confirmation bar -> (low index, low price)
        for idx, price, kind, cf in zigzag(c, x):
            if kind == -1:
                conf[cf] = (idx, price)
        P['lows'][x] = conf
    return P


def setups_B(P, x):
    """Per day t: (t, mid, H, L) when the pullback-to-mid setup holds for the latest confirmed swing low."""
    c = P['c']; n = len(c); out = []; p = L = None; H = -np.inf
    for t in range(n):
        if t in P['lows'][x]:
            p, L = P['lows'][x][t]; H = c[p:t + 1].max()
        if p is None:
            continue
        H = max(H, c[t])
        if t - p > W or c[t] <= L:
            continue
        mid = (L + H) / 2
        if H >= L * (1 + 2 * x) and mid < c[t] < H and P['base'][t]:
            out.append((t, mid, H, L))
    return out


def walk(P, i, e, tgt, stop_fn, T):
    o, h, c = P['o'], P['h'], P['c']
    for j in range(i, i + T):
        if j > i and h[j] > tgt:
            return max(o[j], tgt), j, 'target'
        if stop_fn(j) and j + 1 < len(c):
            return o[j + 1], j + 1, 'stop'
        if j == i + T - 1:
            return c[j], j, 'time'


def sim(cell, seed=None, counts=None):
    fam, p1, T, s = cell
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t in G['fr']:
        P = G['cache'][t]; o, h, l, c, d, er = P['o'], P['h'], P['l'], P['c'], P['d'], P['er20']; n = len(c)
        busy = -1
        if fam.startswith('B'):
            x = p1
            if rng is None:
                S = setups_B(P, x)
            else:
                pool = np.flatnonzero(P['base']); k_ = counts.get(t, 0)
                ks = np.sort(rng.choice(pool, min(k_, len(pool)), replace=False)) if k_ and len(pool) else []
                S = [(k, c[k] * (1 - x), c[k] * (1 + x), c[k] * (1 - 2 * x)) for k in ks]
            for k, mid, H, L in S:
                i = k + 1
                if i <= busy or i + T >= n or not l[i] < mid:
                    continue
                e = min(o[i], mid)
                if H <= e:
                    continue
                stp = L * (1 - s)
                px, je, why = walk(P, i, e, H, lambda j: c[j] < stp, T)
                out.append((t, d[i], np.log(px / e), je - i + 1, why, bool(er[k] < .2)))
                busy = je
        else:
            n_ = p1; H, L = P[f'H{n_}'], P[f'L{n_}']; mid = (H + L) / 2
            pool_mask = P['base'] & (er < .2) & np.isfinite(H)
            if rng is None:
                cross = np.zeros(n, bool); cross[1:] = (c[:-1] < mid[:-1]) & (c[1:] > mid[1:])
                ks = np.flatnonzero(pool_mask & cross)
            else:
                pool = np.flatnonzero(pool_mask); k_ = counts.get(t, 0)
                ks = np.sort(rng.choice(pool, min(k_, len(pool)), replace=False)) if k_ and len(pool) else []
            for k in ks:
                i = k + 1
                if i <= busy or i + T >= n:
                    continue
                e = o[i]; tgt = H[k]
                if tgt <= e:
                    continue
                lvl = L[k] if s == 'range low' else mid[k]
                px, je, why = walk(P, i, e, tgt, lambda j, lvl=lvl: c[j] < lvl, T)
                out.append((t, d[i], np.log(px / e), je - i + 1, why, True))
                busy = je
    R = pd.DataFrame(out, columns=['ticker', 'entry', 'gross', 'bars', 'why', 'choppy']); R['net_B'] = R.gross - COST
    return R


def stats(x, a, b, T):
    dd = x.groupby('entry').net_B.mean().reindex(G['cal'].loc[a:b].index); m, se, _ = nw(dd.to_numpy(), T)
    wn = x.net_B > 0; aw, al = x.gross[wn].mean(), x.gross[~wn].mean()
    return dict(trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25), win_rate=wn.mean(),
                breakeven_wr=(-al + COST) / (aw - al) if wn.any() and (~wn).any() else np.nan, avg_win_pct=aw * 100, avg_loss_pct=al * 100,
                gross_pct=x.gross.mean() * 100, net_B_pct=m * 100, t=m / se if se else np.nan, net_user_fee_pct=(x.gross.mean() - COST_USER) * 100,
                target_share=(x.why == 'target').mean(), stop_share=(x.why == 'stop').mean(), time_share=(x.why == 'time').mean(), avg_bars=x.bars.mean())


def run_cell(cell):
    X = sim(cell); counts = X.groupby('ticker').size().to_dict()
    C = pd.concat([sim(cell, zlib.crc32(f'{cell}-{s}'.encode()), counts) for s in range(5)])
    rows = []
    for pn, (a, b) in PER.items():
        x = X[(X.entry >= np.datetime64(a)) & (X.entry <= np.datetime64(b))]; y = C[(C.entry >= np.datetime64(a)) & (C.entry <= np.datetime64(b))]
        base = dict(zip(KEY, cell), period=pn)
        if len(x) < 5:
            rows.append(dict(base, trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25))); continue
        r = dict(base, **stats(x, a, b, cell[2]), control_net_pct=y.net_B.mean() * 100 if len(y) else np.nan)
        if cell[0].startswith('B'):
            r['choppy_share'] = x.choppy.mean(); r['net_choppy_pct'] = x.net_B[x.choppy].mean() * 100; r['net_trending_pct'] = x.net_B[~x.choppy].mean() * 100
        rows.append(r)
    return rows


if __name__ == '__main__':
    t0 = time.time()
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
    G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['lab'] = regime_proxy(st)['regime']
    with np.errstate(invalid='ignore', divide='ignore'):
        G['cache'] = {t: prep(t) for t in G['fr']}
        D = pd.DataFrame([r for cell in GRID for r in run_cell(cell)])
    D.to_csv(OUT / 'results_all.csv', index=False)
    full = D[D.period == '2000-25'].set_index(KEY); tr = D[D.period == 'train 2000-15'].set_index(KEY); te = D[D.period == 'test 2016-25'].set_index(KEY)
    subs = D[D.period.isin(['2000-07', '2008-15', '2016-20', '2021-25'])].groupby(KEY).net_B_pct.apply(lambda s: int((s > 0).sum()))
    S = full.drop(columns='period').join(tr[['trades_per_year', 'net_B_pct', 't']].add_prefix('train_')).join(
        te[['net_B_pct', 't', 'control_net_pct']].add_prefix('test_')).join(subs.rename('subperiods_positive'))
    S.to_csv(OUT / 'summary.csv')
    pd.set_option('display.width', 340); pd.set_option('display.max_rows', 100)
    print(S.round(2).to_string())
    for fam in ('B', 'C'):
        f_tr = tr[tr.index.get_level_values(0).str.startswith(fam)]; f_tr = f_tr[f_tr.trades_per_year >= 10]
        if not len(f_tr):
            print(fam, 'no cell with >= 10 trades/year in training'); continue
        pick = f_tr.net_B_pct.idxmax(); r = te.loc[pick]
        ok = r.net_B_pct > 0 and r.t >= 2 and r.net_B_pct > r.control_net_pct and subs.loc[pick] >= 3
        print('PICK', fam, pick, '| train net %.2f%% | test net %.2f%% t %.2f control %.2f%% | subperiods %d | PASSES: %s' % (
            f_tr.loc[pick, 'net_B_pct'], r.net_B_pct, r.t, r.control_net_pct, subs.loc[pick], ok))
    print('cells', len(S), '| net > 0:', int((S.net_B_pct > 0).sum()), '| gross > 0:', int((S.gross_pct > 0).sum()), '| above control:', int((S.net_B_pct > S.control_net_pct).sum()),
          '| test net > 0 & t >= 2:', int(((S.test_net_B_pct > 0) & (S.test_t >= 2)).sum()), '| %.0fs' % (time.time() - t0))
