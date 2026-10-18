"""Exploratory (not pre-registered), written after seeing B1/B2 and the overnight/intraday flip around 2013-2016:
does the execution moment around our own signal types matter? Measures the overnight return r_on[t+1] after
(1) HHV20 Close-breakout days with ER20 >= 0.2 (buy at Close t vs next Open), (2) exit-signal days Close < SMA30
crossing from above (sell at Close t vs next Open), and (3) the next-day intraday return when that exit day is
followed by a gap-down Open < -2% (sell at Open vs Close of t+1, the gapdown_close rule). Raw and abnormal (minus the
same-day EW mean) in bps, per period, NW t (lags 5). Writes results/X_execution_timing.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel import load, universe, MAIN, SUBPERIODS
from mpstats import nw

P = load()
lnP, lnH, T = P['lnP'], P['lnH'], P['T']
ron, rid = P['r_on'], P['r_id']
dl = lnP.diff().abs()
er20 = (lnP - lnP.shift(20)).abs() / dl.rolling(20).sum()
brk = (lnP > lnH.shift(1).rolling(20).max()) & (er20 >= .2) & T
sma = lnP.rolling(30).mean()
exitsig = (lnP < sma) & (lnP.shift(1) >= sma.shift(1)) & T
rows = []
for u in ['all', 'pre2018']:
    c = universe(P, u)
    on_next = ron[c].shift(-1)
    id_next = rid[c].shift(-1)
    on_ab = on_next.sub(on_next.mean(axis=1), axis=0)
    id_ab = id_next.sub(id_next.mean(axis=1), axis=0)
    gd_next = on_next < np.log(.98)
    cases = {'entry_breakout_overnight': (brk[c], on_next, on_ab),
             'exit_sma30_overnight': (exitsig[c], on_next, on_ab),
             'exit_sma30_then_gapdown_intraday': (exitsig[c] & gd_next, id_next, id_ab)}
    for name, (m, raw, ab) in cases.items():
        for per, (a, b) in {'MAIN': MAIN, **SUBPERIODS}.items():
            if u == 'pre2018' and per not in ('MAIN', 'P4'):
                continue
            for kind, fr in [('raw', raw), ('abnormal', ab)]:
                s = fr.where(m).loc[a:b].mean(axis=1)
                mu, se, n = nw(s.values, 5)
                rows.append(dict(id='X-E', case=name, universe=u, period=per, kind=kind, mean_bps=mu * 1e4,
                                 t=mu / se if se else np.nan, days=n, events=int(m.loc[a:b].values.sum())))
r = pd.DataFrame(rows)
r.to_csv(HERE / 'results' / 'X_execution_timing.csv', index=False)
pd.set_option('display.width', 220)
print(r.pivot_table(index=['case', 'universe', 'kind'], columns='period', values='mean_bps').round(1).to_string())
print(r.pivot_table(index=['case', 'universe', 'kind'], columns='period', values='t').round(1).to_string())
print(r[(r.kind == 'raw')].pivot_table(index=['case', 'universe'], columns='period', values='events').to_string())
