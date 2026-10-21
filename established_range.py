"""Established ranges in sideways: buy the bottom zone, take profit at the top zone (plan: established_range_results/PLAN.md).
Per-trade standalone test on the realistic universe, comparison with not-established ranges, 20-seed random control,
and a year-to-year persistence check of stock-level range success."""
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

OUT = ROOT / 'established_range_results'
G = {}
GRID = list(product([40, 60], [.2, .25], [2, 3], ['close', 'limit'], ['stock_er', 'market']))
PER = {'2000-25': ('2000-01-01', '2025-08-15'), '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
       '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}


def atr_prev(h, l, c, n=14):
    tr = h - l
    tr[1:] = np.maximum(tr[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    a = np.full(len(c), np.nan)
    if len(c) >= n:
        a[n - 1] = tr[:n].mean()
        for i in range(n, len(c)):
            a[i] = (a[i - 1] * (n - 1) + tr[i]) / n
    return np.r_[np.nan, a[:-1]]  # through bar t-1


def visits(lo, hi, bot, top):
    lab = np.where(lo <= bot, 1, 0) + np.where(hi >= top, 2, 0)
    lab = lab[(lab == 1) | (lab == 2)]
    if len(lab) == 0:
        return 0, 0
    comp = lab[np.r_[True, lab[1:] != lab[:-1]]]
    return int((comp == 1).sum()), int((comp == 2).sum())


def sim(cell, mode, seed=None):
    """mode: 'established', 'not_established' or 'control'."""
    M, z, nmin, entry, side = cell
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t, f in G['fr'].items():
        f = f[f.tradable].reset_index(drop=True)
        n = len(f)
        if n < 300:
            continue
        o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close'])
        d = f['Date/Time'].to_numpy()
        U = pd.Series(h).shift(1).rolling(M).max().to_numpy()
        D = pd.Series(l).shift(1).rolling(M).min().to_numpy()
        R = U - D
        bot, top = D + z * R, U - z * R
        A = atr_prev(h, l, c)
        cc = pd.Series(c)
        er = ((cc - cc.shift(20)).abs() / cc.diff().abs().rolling(20).sum()).shift(1).to_numpy()
        ok = np.isin(d, G['ok'][t]) & (d >= np.datetime64('2000-01-01')) & (d <= np.datetime64('2025-08-15'))
        ok &= (er < .3) if side == 'stock_er' else np.isin(d, G['side'])
        ok &= np.isfinite(R) & (R > 0) & np.isfinite(A) & (top / bot - 1 >= .03)
        if mode == 'control':
            cand = np.flatnonzero(ok & (c <= D + .5 * R) & (c >= D - .5 * A))
            k = G['counts'].get((cell, t), 0)
            cand = np.sort(rng.choice(cand, min(k, len(cand)), replace=False)) if k and len(cand) else np.array([], int)
        else:
            touch = ok & (l <= bot) if entry == 'limit' else ok & (l <= bot) & (c >= D - .5 * A)
            if entry == 'limit':
                touch &= l < bot
            cand = []
            for i in np.flatnonzero(touch):
                nb, nt = visits(l[i - M:i], h[i - M:i], bot[i], top[i])
                est = nb >= nmin and nt >= nmin
                if est == (mode == 'established'):
                    cand.append(i)
            cand = np.array(cand, int)
        busy = -1
        for i in cand:
            if i <= busy or i + 1 >= n:
                continue
            epx = min(o[i], bot[i]) if (entry == 'limit' and mode != 'control') else c[i]
            tgt, stop = top[i], D[i] - .5 * A[i]
            res = None
            for j in range(i + 1, min(i + 21, n)):
                if h[j] >= tgt:
                    res = (j, max(o[j], tgt), 'target'); break
                if c[j] < stop and j + 1 < n:
                    res = (j + 1, o[j + 1], 'stop'); break
                if j == i + 20:
                    res = (j, c[j], 'time')
            if res is None:
                break
            out.append((t, d[i], np.log(res[1] / epx), res[2], res[0] - i))
            busy = res[0]
    T = pd.DataFrame(out, columns=['ticker', 'signal', 'gross', 'reason', 'bars'])
    T['net_B'] = T.gross - .009
    return T


def summarize(T, cell, mode, extra=None):
    rows = []
    for pn, (s, e) in PER.items():
        x = T[(T.signal >= np.datetime64(s)) & (T.signal <= np.datetime64(e))]
        daily = x.groupby('signal').net_B.mean().reindex(G['cal'].loc[s:e].index)
        m, se, _ = nw(daily.values, 20)
        rows.append(dict(M=cell[0], z=cell[1], n=cell[2], entry=cell[3], sideways=cell[4], mode=mode, period=pn, trades=len(x),
                         trades_per_year=len(x) / ((pd.Timestamp(e) - pd.Timestamp(s)).days / 365.25),
                         gross_pct=x.gross.mean() * 100, net_B_pct=m * 100, t_net_B=m / se if se else np.nan,
                         net_B_event_pct=x.net_B.mean() * 100, win_rate_B=(x.net_B > 0).mean(),
                         share_target=(x.reason == 'target').mean(), share_stop=(x.reason == 'stop').mean(),
                         avg_bars=x.bars.mean(), **(extra or {})))
    return rows


def run_cell(cell):
    E = sim(cell, 'established')
    NE = sim(cell, 'not_established')
    G['counts'] = E.groupby('ticker').size().to_dict()
    G['counts'] = {(cell, k): v for k, v in G['counts'].items()}
    ctl = [sim(cell, 'control', zlib.crc32(f'{cell}-{s}'.encode())).gross.mean() for s in range(20)]
    E['cell'] = str(cell)
    return summarize(E, cell, 'established', dict(control20_gross_pct=float(np.mean(ctl) * 100))) + summarize(NE, cell, 'not_established'), E


def persistence(E):
    E = E.copy()
    E['year'] = pd.to_datetime(E.signal).dt.year
    E['hit'] = (E.reason == 'target').astype(float)
    g = E.groupby(['ticker', 'year']).agg(n=('hit', 'size'), rate=('hit', 'mean'), ret=('gross', 'mean')).reset_index()
    g = g[g.n >= 3]
    rows = []
    for y in sorted(g.year.unique())[:-1]:
        a, b = g[g.year == y].set_index('ticker'), g[g.year == y + 1].set_index('ticker')
        common = a.index.intersection(b.index)
        if len(common) >= 8:
            rows.append(dict(year=y, stocks=len(common), rank_corr_hit=a.loc[common, 'rate'].rank().corr(b.loc[common, 'rate'].rank()),
                             rank_corr_ret=a.loc[common, 'ret'].rank().corr(b.loc[common, 'ret'].rank())))
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
    allE = pd.concat([E for _, E in res])
    allE.to_csv(OUT / 'trades_established.csv', index=False)
    key = ['M', 'z', 'n', 'entry', 'sideways']
    est = d[d['mode'] == 'established']
    subs = est[est.period != '2000-25'].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum())).rename('subperiods_positive')
    full = est[est.period == '2000-25'].merge(subs, on=key)
    ne = d[(d['mode'] == 'not_established') & (d.period == '2000-25')][key + ['gross_pct', 'trades']].rename(columns={'gross_pct': 'not_est_gross_pct', 'trades': 'not_est_trades'})
    full = full.merge(ne, on=key)
    full['passes'] = (full.net_B_pct > 0) & (full.t_net_B >= 3) & (full.subperiods_positive >= 3) & (full.gross_pct > full.not_est_gross_pct) & (full.gross_pct > full.control20_gross_pct)
    d.to_csv(OUT / 'results_all.csv', index=False)
    full.to_csv(OUT / 'results.csv', index=False)
    P_ = persistence(allE[allE.cell == str((40, .25, 2, 'close', 'stock_er'))])
    P_.to_csv(OUT / 'persistence.csv', index=False)
    pd.set_option('display.width', 270)
    print(full[key + ['trades_per_year', 'gross_pct', 'not_est_gross_pct', 'control20_gross_pct', 'net_B_pct', 't_net_B', 'win_rate_B',
                      'share_target', 'share_stop', 'avg_bars', 'subperiods_positive', 'passes']].round(2).to_string(index=False))
    print(est.pivot_table(index=key, columns='period', values='net_B_pct').round(2).to_string())
    print(P_.round(3).to_string(index=False), '\nmean rank corr hit', P_.rank_corr_hit.mean(), 'ret', P_.rank_corr_ret.mean())
