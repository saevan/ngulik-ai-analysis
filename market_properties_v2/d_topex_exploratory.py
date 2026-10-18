"""Exploratory (not pre-registered), written after seeing D results: for a long-only ranking only the top quintile
matters. Top quintile minus universe mean (top_ex) with NW t, per period, for the momentum-type sorts.
Writes results/D_topex_exploratory.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel import load, MAIN, SUBPERIODS
from mpstats import Mean, sort_series

P = load()
lnP, lnH = P['lnP'], P['lnH']
dl = lnP.diff().abs()
sigs = {'D1': lnP.shift(21) - lnP.shift(252), 'D2': lnP.shift(21) - lnP.shift(141), 'D3': lnP.shift(21) - lnP.shift(84),
        'D4': lnP - lnP.shift(21), 'D6': lnP - lnH.rolling(252, min_periods=200).max(),
        'D11': (lnP - lnP.shift(60)) / dl.rolling(60).sum()}
rows = []
for k, s in sigs.items():
    for u in ['all', 'pre2018']:
        ss = sort_series(P, s, u)
        for per, (a, b) in {'MAIN': MAIN, **SUBPERIODS}.items():
            if u == 'pre2018' and per != 'MAIN':
                continue
            m, t, n = Mean(ss.top_ex, 2).at(a, b)
            rows.append(dict(id='X-D-topex', test=k, universe=u, period=per, top_minus_universe_pct_month=m * 100, t=t, n=n))
r = pd.DataFrame(rows)
r.to_csv(HERE / 'results' / 'D_topex_exploratory.csv', index=False)
print(r.pivot_table(index=['test', 'universe'], columns='period', values=['top_minus_universe_pct_month', 't']).round(2).to_string())
