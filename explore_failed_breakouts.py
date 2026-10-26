"""Exploratory (26 Oct 2026, no rule adopted): can a failed breakout of the v2 main pick be told apart BEFORE the order?
Trades from diagnose_winrate.py (scenario B, 2000-2025, unrestricted and realistic). Failed = exit reason failed_breakout*
(entry-day Close below the HHV20 level). Features known before the entry day's Open (bar i-1 and earlier) plus the Open
itself. Per feature quintile: trades, failed rate, win rate, expectancy (mean net return). Also failed rate by period.
Writes winrate_diagnosis_results/failed_breakout_features.csv"""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from analyze_portfolio_regimes import regime_proxy

ROOT = Path(__file__).resolve().parent
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
rp = regime_proxy(st)
mret = rp.proxy_return.shift(1)   # market proxy return of the previous day, known at the Open


def atr(h, l, c, n=14):
    tr = h - l
    tr[1:] = np.maximum(tr[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


cache = {}
def feats(t, i, d):
    if t not in cache:
        f = fr[t]
        o, h, l, c, v = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close', 'Volume'])
        cc = pd.Series(c)
        cache[t] = (o, h, l, c, v, atr(h, l, c), ((cc - cc.shift(20)).abs() / cc.diff().abs().rolling(20).sum()).to_numpy())
    o, h, l, c, v, a, er = cache[t]
    win = h[i - 20:i]
    level = win.max()
    return dict(dist_atr=(level - c[i - 1]) / a[i - 1], er20=er[i - 1], atr_pct=a[i - 1] / c[i - 1],
                vol_ratio=v[i - 1] / v[i - 20:i].mean() if v[i - 20:i].mean() > 0 else np.nan, ret1=c[i - 1] / c[i - 2] - 1,
                mom120=np.log(c[i - 21] / c[i - 141]) if i >= 141 else np.nan, level_age=19 - int(np.argmax(win)),
                open_vs_level=o[i] / level - 1, market_ret1=mret.get(d, np.nan))


rows = []
for name in ['ours', 'ours_realistic']:
    T = pd.read_csv(ROOT / 'winrate_diagnosis_results' / f'trades_{name}.csv', parse_dates=['entry_date'])
    T['failed'] = T.reason.str.startswith('failed')
    F = pd.DataFrame([feats(r.ticker, int(r.i), r.entry_date) for r in T.itertuples()])
    T = pd.concat([T.reset_index(drop=True), F], axis=1)
    T['period'] = pd.cut(T.entry_date.dt.year, [1999, 2007, 2015, 2020, 2025], labels=['2000-07', '2008-15', '2016-20', '2021-25'])
    for p, x in T.groupby('period', observed=True):
        rows.append(dict(system=name, feature='period', bucket=str(p), trades=len(x), failed_rate=x.failed.mean(), win_rate=(x.net > 0).mean(),
                         expectancy=x.net.mean(), wr_non_failed=(x[~x.failed].net > 0).mean()))
    for g, x in T.groupby('regime'):
        rows.append(dict(system=name, feature='regime', bucket=g, trades=len(x), failed_rate=x.failed.mean(), win_rate=(x.net > 0).mean(),
                         expectancy=x.net.mean(), wr_non_failed=(x[~x.failed].net > 0).mean()))
    for ft in F.columns:
        q = pd.qcut(T[ft].rank(method='first'), 5, labels=False)
        for b, x in T.groupby(q):
            rows.append(dict(system=name, feature=ft, bucket=f'Q{int(b) + 1} ({x[ft].min():.3g}..{x[ft].max():.3g})', trades=len(x),
                             failed_rate=x.failed.mean(), win_rate=(x.net > 0).mean(), expectancy=x.net.mean(),
                             wr_non_failed=(x[~x.failed].net > 0).mean()))
D = pd.DataFrame(rows)
D.to_csv(ROOT / 'winrate_diagnosis_results' / 'failed_breakout_features.csv', index=False)
pd.set_option('display.width', 220); pd.set_option('display.max_rows', 300)
print(D.round(3).to_string(index=False))
