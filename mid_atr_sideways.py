"""Sideways mid-point + ATR logic by range width, with a separate 'last low' entry (plan: mid_atr_sideways_results/PLAN.md).
Per-trade standalone test on the realistic universe, 20-seed random control, and a mid-reversion property check."""
import sys
import zlib
from itertools import product
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw, ols_nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy

OUT = ROOT / 'mid_atr_sideways_results'
G = {}
WIDTH = {'narrow': (0, 4), 'medium': (4, 7), 'wide': (7, np.inf)}
ENTRIES = ['below_mid_1', 'below_mid_1.5', 'below_mid_2', 'last_low']
GRID = list(product(WIDTH, ENTRIES, ['stock_er', 'market']))
PER = {'2000-25': ('2000-01-01', '2025-08-15'), '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
       '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}


def atr(h, l, c, n=14):
    tr = h - l
    tr[1:] = np.maximum(tr[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    a = np.full(len(c), np.nan)
    if len(c) >= n:
        a[n - 1] = tr[:n].mean()
        for i in range(n, len(c)):
            a[i] = (a[i - 1] * (n - 1) + tr[i]) / n
    return a


def features(f):
    o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close'])
    H = pd.Series(h).rolling(20).max().to_numpy()
    L = pd.Series(l).rolling(20).min().to_numpy()
    A = atr(h, l, c)
    cc = pd.Series(c)
    er = ((cc - cc.shift(20)).abs() / cc.diff().abs().rolling(20).sum()).to_numpy()
    return o, h, l, c, H, L, (H + L) / 2, A, (H - L) / A, er


def trade(i, n, o, h, c, mid, L, A):
    """Buy Close i; sell at mid when High reaches it, stop Close < L-1ATR (next Open), time stop Close i+10."""
    tgt, stop = mid[i], L[i] - A[i]
    for j in range(i + 1, min(i + 11, n)):
        if h[j] >= tgt:
            return j, max(o[j], tgt), 'target'
        if c[j] < stop and j + 1 < n:
            return j + 1, o[j + 1], 'stop'
        if j == i + 10:
            return j, c[j], 'time'
    return None, None, None


def sim(cell, seed=None):
    width, ent, side = cell
    lo_w, hi_w = WIDTH[width]
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t, f in G['fr'].items():
        f = f[f.tradable].reset_index(drop=True)
        n = len(f)
        if n < 300:
            continue
        o, h, l, c, H, L, mid, A, W, er = features(f)
        d = f['Date/Time'].to_numpy()
        base = np.isin(d, G['ok'][t]) & (d >= np.datetime64('2000-01-01')) & (d <= np.datetime64('2025-08-15')) & np.isfinite(W) & (A > 0)
        base &= (er < .3) if side == 'stock_er' else np.isin(d, G['side'])
        base &= (W >= lo_w) & (W < hi_w)
        z = (c - mid) / A
        if ent == 'last_low':
            sig = base & ((c - L) <= .5 * A)
        else:
            sig = base & (z <= -float(ent.split('_')[-1]))
        if rng is not None:
            pool = np.flatnonzero(base & (c < mid))  # control: same stock, width class, sideways, below the mid
            k = int(sig.sum())
            sig = np.zeros(n, bool)
            if k and len(pool):
                sig[rng.choice(pool, min(k, len(pool)), replace=False)] = True
        busy = -1
        for i in np.flatnonzero(sig):
            if i <= busy:
                continue
            j, px, why = trade(i, n, o, h, c, mid, L, A)
            if j is None:
                break
            out.append((t, d[i], np.log(px / c[i]), why, j - i, W[i]))
            busy = j
    T = pd.DataFrame(out, columns=['ticker', 'signal', 'gross', 'reason', 'bars', 'width'])
    T['net_B'] = T.gross - .009
    return T


def run_cell(cell):
    T = sim(cell)
    ctl = [sim(cell, zlib.crc32(f'{cell}-{s}'.encode())).gross.mean() for s in range(20)]
    rows = []
    for pn, (s, e) in PER.items():
        z = T[(T.signal >= np.datetime64(s)) & (T.signal <= np.datetime64(e))]
        daily = z.groupby('signal').net_B.mean().reindex(G['cal'].loc[s:e].index)
        m, se, _ = nw(daily.values, 10)
        rows.append(dict(width=cell[0], entry=cell[1], sideways=cell[2], period=pn, trades=len(z),
                         trades_per_year=len(z) / ((pd.Timestamp(e) - pd.Timestamp(s)).days / 365.25),
                         gross_pct=z.gross.mean() * 100, net_B_pct=m * 100, t_net_B=m / se if se else np.nan,
                         net_B_event_pct=z.net_B.mean() * 100, win_rate_B=(z.net_B > 0).mean(),
                         share_target=(z.reason == 'target').mean(), share_stop=(z.reason == 'stop').mean(),
                         avg_bars=z.bars.mean(), control20_gross_pct=float(np.mean(ctl) * 100)))
    T['cell'] = str(cell)
    return rows, T


def property_check():
    """Slope of abnormal 10-day forward Close return on z, sideways stock-days (stock ER20 < 0.3), by width class."""
    recs = []
    for t, f in G['fr'].items():
        f = f[f.tradable].reset_index(drop=True)
        if len(f) < 300:
            continue
        o, h, l, c, H, L, mid, A, W, er = features(f)
        d = f['Date/Time'].to_numpy()
        ok = np.isin(d, G['ok'][t]) & (d >= np.datetime64('2000-01-01')) & (er < .3) & np.isfinite(W) & (A > 0)
        fwd = np.r_[np.log(c[10:] / c[:-10]), np.full(10, np.nan)]
        recs.append(pd.DataFrame(dict(ticker=t, date=d[ok], z=((c - mid) / A)[ok], W=W[ok], fwd=fwd[ok])))
    R = pd.concat(recs).dropna()
    R['abn'] = R.fwd - R.groupby('date').fwd.transform('mean')
    rows = []
    for wname, (a, b) in WIDTH.items():
        x = R[(R.W >= a) & (R.W < b)]
        # Fama-MacBeth style: daily cross-sectional slope, then NW over days
        sl = x.groupby('date').apply(lambda g: np.polyfit(g.z, g.abn, 1)[0] if len(g) >= 5 and g.z.std() > 0 else np.nan)
        sl = sl.reindex(G['cal'].loc['2000-01-01':'2025-08-15'].index)
        m, se, nd = nw(sl.values, 10)
        bucket = x.groupby(pd.cut(x.z, [-9, -2, -1.5, -1, -.5, 0, .5, 1, 1.5, 2, 9])).abn.mean() * 100
        rows.append(dict(width=wname, obs=len(x), slope_pct_per_ATR=m * 100, t=m / se if se else np.nan, days=nd,
                         **{f'abn10_z{k}': v for k, v in bucket.items()}))
    return pd.DataFrame(rows)


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
    key = ['width', 'entry', 'sideways']
    subs = d[d.period != '2000-25'].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum())).rename('subperiods_positive')
    d = d.merge(subs, on=key)
    full = d[d.period == '2000-25'].copy()
    full['passes'] = (full.net_B_pct > 0) & (full.t_net_B >= 3) & (full.subperiods_positive >= 3) & (full.gross_pct > full.control20_gross_pct)
    d = d.merge(full[key + ['passes']], on=key)
    d.to_csv(OUT / 'results.csv', index=False)
    P_ = property_check()
    P_.to_csv(OUT / 'property_mid_reversion.csv', index=False)
    pd.set_option('display.width', 260)
    print(full[key + ['trades_per_year', 'gross_pct', 'control20_gross_pct', 'net_B_pct', 't_net_B', 'win_rate_B', 'share_target',
                      'share_stop', 'avg_bars', 'subperiods_positive', 'passes']].round(2).to_string(index=False))
    print(P_.round(3).T.to_string())
