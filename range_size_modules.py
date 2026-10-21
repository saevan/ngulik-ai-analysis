"""Separate fade / breakout logics for small (narrowing) and large sideways ranges
(plan: range_size_modules_results/PLAN.md). Per-trade standalone test, realistic universe, 20-seed random control."""
import sys
import zlib
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

OUT = ROOT / 'range_size_modules_results'
G = {}
GRID = [(s, lg, sd, True) for s, lg, sd in product(['small', 'large'], ['fade', 'breakout'], ['stock_er', 'market'])] + \
       [('small', lg, sd, False) for lg, sd in product(['fade', 'breakout'], ['stock_er', 'market'])]
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


def exit_fade(i, n, o, h, c, tgt, stop, maxb):
    for j in range(i + 1, min(i + maxb + 1, n)):
        if h[j] >= tgt:
            return j, max(o[j], tgt), 'target'
        if c[j] < stop and j + 1 < n:
            return j + 1, o[j + 1], 'stop'
        if j == i + maxb:
            return j, c[j], 'time'
    return None, None, None


def exit_break(e, n, o, h, c, mid):
    """Entry bar e. Exit next Open after 5 bars without a new trade high or a Close below the range mid; time stop 40."""
    hi, last = h[e], e
    if c[e] < mid and e + 1 < n:
        return e + 1, o[e + 1], 'mid'
    for j in range(e + 1, min(e + 41, n)):
        if h[j] > hi:
            hi, last = h[j], j
        if (c[j] < mid or j - last >= 5) and j + 1 < n:
            return j + 1, o[j + 1], 'mid' if c[j] < mid else 'no_new_high'
        if j == e + 40:
            return j, c[j], 'time'
    return None, None, None


def sim(cell, seed=None):
    size, logic, side, narrowing = cell
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t, f in G['fr'].items():
        f = f[f.tradable].reset_index(drop=True)
        n = len(f)
        if n < 300:
            continue
        o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close'])
        d = f['Date/Time'].to_numpy()
        H = pd.Series(h).rolling(20).max().to_numpy()
        L = pd.Series(l).rolling(20).min().to_numpy()
        A = atr(h, l, c)
        W = (H - L) / A
        W20 = np.r_[np.full(20, np.nan), W[:-20]]
        cc = pd.Series(c)
        er = ((cc - cc.shift(20)).abs() / cc.diff().abs().rolling(20).sum()).to_numpy()
        cond = np.isin(d, G['ok'][t]) & (d >= np.datetime64('2000-01-01')) & (d <= np.datetime64('2025-08-15')) & np.isfinite(W) & (A > 0)
        cond &= (er < .3) if side == 'stock_er' else np.isin(d, G['side'])
        cond &= (W < 4) if size == 'small' else (W >= 6)
        if size == 'small' and narrowing:
            cond &= W <= .7 * W20
        R = H - L
        mid = (H + L) / 2
        if logic == 'fade':
            sig = cond & (c <= L + .25 * R)
        else:
            sig = cond.copy()   # buy stop for the next bar at H + 0.1 ATR while the condition holds at the Close
        if rng is not None:
            k = int(sig.sum())
            pool = np.flatnonzero(cond)
            sig = np.zeros(n, bool)
            if k and len(pool):
                sig[rng.choice(pool, min(k, len(pool)), replace=False)] = True
        busy = -1
        for i in np.flatnonzero(sig):
            if i <= busy or i + 1 >= n:
                continue
            if logic == 'fade' or rng is not None:
                e, epx = i, c[i]
                if logic == 'fade':
                    tgt = (H[i] - .25 * R[i]) if size == 'small' else mid[i]
                    res = exit_fade(i, n, o, h, c, tgt, L[i] - .5 * A[i], 10 if size == 'small' else 20)
                else:
                    res = exit_break(e, n, o, h, c, mid[i])
            else:
                lvl = H[i] + .1 * A[i]
                if h[i + 1] < lvl:
                    continue
                e, epx = i + 1, max(o[i + 1], lvl)
                res = exit_break(e, n, o, h, c, mid[i])
            if res[0] is None:
                break
            out.append((t, d[i], np.log(res[1] / epx), res[2], res[0] - e))
            busy = res[0]
    T = pd.DataFrame(out, columns=['ticker', 'signal', 'gross', 'reason', 'bars'])
    T['net_B'] = T.gross - .009
    return T


def run_cell(cell):
    T = sim(cell)
    ctl = [sim(cell, zlib.crc32(f'{cell}-{s}'.encode())).gross.mean() for s in range(20)]
    rows = []
    for pn, (s, e) in PER.items():
        x = T[(T.signal >= np.datetime64(s)) & (T.signal <= np.datetime64(e))]
        daily = x.groupby('signal').net_B.mean().reindex(G['cal'].loc[s:e].index)
        m, se, _ = nw(daily.values, 20)
        rows.append(dict(size=cell[0], logic=cell[1], sideways=cell[2], narrowing=cell[3], period=pn, trades=len(x),
                         trades_per_year=len(x) / ((pd.Timestamp(e) - pd.Timestamp(s)).days / 365.25),
                         gross_pct=x.gross.mean() * 100, net_B_pct=m * 100, t_net_B=m / se if se else np.nan,
                         net_B_event_pct=x.net_B.mean() * 100, win_rate_B=(x.net_B > 0).mean(),
                         avg_win_pct=x.gross[x.net_B > 0].mean() * 100, avg_loss_pct=x.gross[x.net_B <= 0].mean() * 100,
                         avg_bars=x.bars.mean(), control20_gross_pct=float(np.nanmean(ctl) * 100),
                         **{f'share_{k}': v for k, v in x.reason.value_counts(normalize=True).items()}))
    T['cell'] = str(cell)
    return rows, T


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
    key = ['size', 'logic', 'sideways', 'narrowing']
    subs = d[d.period != '2000-25'].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum())).rename('subperiods_positive')
    full = d[d.period == '2000-25'].merge(subs, on=key)
    nn = full[full.narrowing == False].set_index(['size', 'logic', 'sideways']).gross_pct.rename('no_narrowing_gross_pct')
    full = full.join(nn, on=['size', 'logic', 'sideways'])
    full['passes'] = (full.net_B_pct > 0) & (full.t_net_B >= 3) & (full.subperiods_positive >= 3) & (full.gross_pct > full.control20_gross_pct) & \
                     ((full['size'] != 'small') | (~full.narrowing) | (full.gross_pct > full.no_narrowing_gross_pct))
    d.to_csv(OUT / 'results_all.csv', index=False)
    full.to_csv(OUT / 'results.csv', index=False)
    pd.set_option('display.width', 270)
    print(full[key + ['trades_per_year', 'gross_pct', 'control20_gross_pct', 'no_narrowing_gross_pct', 'net_B_pct', 't_net_B', 'win_rate_B',
                      'avg_win_pct', 'avg_loss_pct', 'avg_bars', 'subperiods_positive', 'passes']].round(2).to_string(index=False))
    print(d.pivot_table(index=key, columns='period', values='net_B_pct').round(2).to_string())
