"""Exploratory (not pre-registered): what happens after a 'fade' day, the project's exit trigger
(Open - Low >= 2 x ATR14 of the previous bar, Wilder ATR as backtest_timehunter_atr.atr_previous)? If prices rebound
after fade days, selling at the next Open sells near a local low; if they keep lagging, the exit helps.
Measured for all stock-days and for 'held-like' days (an HHV20 Close breakout with ER20 >= 0.2 in the previous 60
days and Close above SMA30 the day before). Outputs: next-day overnight r_on[t+1] (bps), abnormal fo[5] and fo[20]
from the next Open (%), raw fo[20], per period, NW t. Writes results/X_fade_days.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel import load, universe, MAIN, SUBPERIODS
from mpstats import nw

P = load()
O, H, L, C, T = P['O'], P['H'], P['L'], P['C'], P['T']
lnP, lnH = P['lnP'], P['lnH']


def atr_prev(h, l, c, n=14):
    tr = h - l
    tr[1:] = np.maximum(tr[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    a = np.full(len(c), np.nan)
    if len(c) >= n:
        a[n - 1] = tr[:n].mean()
        for i in range(n, len(c)):
            a[i] = (a[i - 1] * (n - 1) + tr[i]) / n
    return np.r_[np.nan, a[:-1]]


ATR = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
for t in C.columns:
    ok = T[t].values & C[t].notna().values
    idx = C.index[ok]
    ATR.loc[idx, t] = atr_prev(H.loc[idx, t].values.astype(float), L.loc[idx, t].values.astype(float), C.loc[idx, t].values.astype(float))
fade = ((O - L) >= 2 * ATR) & (ATR > 0) & T
dl = lnP.diff().abs()
er20 = (lnP - lnP.shift(20)).abs() / dl.rolling(20).sum()
brk = (lnP > lnH.shift(1).rolling(20).max()) & (er20 >= .2) & T
recent_brk = brk.astype(float).rolling(60, min_periods=1).max().shift(1).fillna(0) > 0
above = (lnP > lnP.rolling(30).mean()).shift(1).fillna(False).astype(bool)
held_like = fade & recent_brk & above
rows = []
for u in ['all', 'pre2018']:
    c = universe(P, u)
    on_next = P['r_on'][c].shift(-1)
    meas = {'overnight_next_bps': (on_next.sub(on_next.mean(axis=1), axis=0), 1e4, 5),
            'abn_fo5_pct': (P['fo'][5][c].sub(P['fo'][5][c].mean(axis=1), axis=0), 100, 5),
            'abn_fo20_pct': (P['fo'][20][c].sub(P['fo'][20][c].mean(axis=1), axis=0), 100, 20),
            'raw_fo20_pct': (P['fo'][20][c], 100, 20)}
    for sel_name, sel in [('all_fade_days', fade[c]), ('held_like_fade_days', held_like[c])]:
        for mname, (fr, sc, lags) in meas.items():
            for per, (a, b) in {'MAIN': MAIN, **SUBPERIODS}.items():
                if u == 'pre2018' and per not in ('MAIN', 'P4'):
                    continue
                s = fr.where(sel).loc[a:b].mean(axis=1)
                m, se, n = nw(s.values, lags)
                rows.append(dict(id='X-F', selection=sel_name, universe=u, measure=mname, period=per, mean=m * sc,
                                 t=m / se if se else np.nan, days=n, events=int(sel.loc[a:b].values.sum())))
r = pd.DataFrame(rows)
r.to_csv(HERE / 'results' / 'X_fade_days.csv', index=False)
pd.set_option('display.width', 220)
print(r.pivot_table(index=['selection', 'universe', 'measure'], columns='period', values='mean').round(2).to_string())
print(r.pivot_table(index=['selection', 'universe', 'measure'], columns='period', values='t').round(1).to_string())
print(r[r.measure == 'raw_fo20_pct'].pivot_table(index=['selection', 'universe'], columns='period', values='events').to_string())
