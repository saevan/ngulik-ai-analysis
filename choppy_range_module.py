"""Choppy-only range module (buy limit at the range bottom, sell limit at mid/top), per-trade standalone test.
Plan: choppy_range_module_results/PLAN.md."""
import sys
from itertools import product
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_breakout_er import efficiency_ratio
from analyze_sk5_regimes import regimes

OUT = Path(__file__).resolve().parent / 'choppy_range_module_results'
G = {}
GRID = list(product([10, 20], ['mid', 'top'], [.3, .2], [2., None]))
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


def sim(v):
    N, tgt, th, k = v
    trades = []
    for t, f in G['fr'].items():
        f = f[f.tradable].reset_index(drop=True)
        if len(f) < 300:
            continue
        o, h, l, c = (f[x].to_numpy(float) for x in ['Open', 'High', 'Low', 'Close'])
        d = f['Date/Time'].to_numpy()
        er = efficiency_ratio(f.Close, 20).shift(1).to_numpy()
        lb = f.Low.shift(1).rolling(N).min().to_numpy()
        ub = f.High.shift(1).rolling(N).max().to_numpy()
        a = atr(h, l, c)
        ok = np.isin(d, G['ok'][t])
        i = 0
        while i < len(f) - 1:
            if not (ok[i] and er[i] < th and np.isfinite(lb[i]) and d[i] >= np.datetime64('2000-01-01') and l[i] < lb[i]):
                i += 1; continue
            e = min(o[i], lb[i]); target = (lb[i] + ub[i]) / 2 if tgt == 'mid' else ub[i]
            stop = e - k * a[i] if k else -np.inf
            x, xi, why = None, None, None
            j = i
            if c[i] < stop:  # stop on the entry day's Close -> next Open
                x, xi, why = o[i + 1], i + 1, 'stop'
            j = i + 1
            while x is None and j < len(f):
                if h[j] > target:
                    x, xi, why = max(o[j], target), j, 'target'
                elif j - i >= 20:
                    x, xi, why = c[j], j, 'time'
                elif c[j] < stop and j + 1 < len(f):
                    x, xi, why = o[j + 1], j + 1, 'stop'
                j += 1
            if x is None:
                break
            trades.append((t, d[i], d[xi], np.log(x / e), why, xi - i))
            i = xi + 1
    T = pd.DataFrame(trades, columns=['ticker', 'entry', 'exit', 'gross', 'reason', 'bars'])
    T['net_B'] = T.gross - .009
    T['net_A'] = T.gross - .004
    rows = []
    for pn, (s, e_) in PER.items():
        x = T[(T.entry >= np.datetime64(s)) & (T.entry <= np.datetime64(e_))]
        daily = x.groupby('entry').net_B.mean().reindex(G['cal'].loc[s:e_].index)
        m, se, n = nw(daily.values, 20)
        rows.append(dict(N=N, target=tgt, er_th=th, stop=k, period=pn, trades=len(x), trades_per_year=len(x) / max(1e-9, (pd.Timestamp(e_) - pd.Timestamp(s)).days / 365.25),
                         gross_pct=x.gross.mean() * 100, net_B_pct=m * 100, t_net_B=m / se if se else np.nan,
                         net_B_event_pct=x.net_B.mean() * 100, net_A_event_pct=x.net_A.mean() * 100,
                         win_rate_B=(x.net_B > 0).mean(), avg_bars=x.bars.mean(),
                         share_target=(x.reason == 'target').mean(), share_stop=(x.reason == 'stop').mean()))
    T['variant'] = f'N{N}_{tgt}_er{th}_k{k}'
    return rows, T


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
    G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    with Pool(4) as p:
        res = p.map(sim, GRID)
    d = pd.DataFrame([r for rows, _ in res for r in rows])
    d.to_csv(OUT / 'variants.csv', index=False)
    pd.concat([T for _, T in res]).to_csv(OUT / 'trades.csv', index=False)
    d['passes'] = False
    for key, g in d.groupby(['N', 'target', 'er_th', 'stop'], dropna=False):
        full = g[g.period == '2000-25'].iloc[0]
        sub = g[g.period != '2000-25']
        d.loc[g.index, 'passes'] = bool(full.net_B_pct > 0 and full.t_net_B >= 3 and (sub.net_B_pct > 0).sum() >= 3)
    d.to_csv(OUT / 'variants.csv', index=False)
    pd.set_option('display.width', 250)
    print(d[d.period == '2000-25'].drop(columns=['period']).round(3).to_string(index=False))
    print(d.pivot_table(index=['N', 'target', 'er_th', 'stop'], columns='period', values='net_B_pct', dropna=False).round(2).to_string())
