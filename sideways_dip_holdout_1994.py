"""Holdout check (rule fixed before looking): the 3 best cells of the exploratory grid (by 2000-25 net) are evaluated on
1994-07..1999-12, a period never used for evaluation in this project (warm-up only). Same definitions and universe."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
import sideways_dip_explore as ex
from mpstats import nw

top = ex.d.sort_values('net_2000-25', ascending=False).head(3)
rows = []
for r in top.itertuples():
    M = ex.base & ex.sides[r.sideways] & ex.strg[r.strength] & ex.dips[r.dip]
    X = (ex.lnO.shift(-r.h) - ex.lnP).where(M).loc['1994-01-01':'1999-12-31']
    s = X.mean(axis=1)
    m, se, n = nw(s.values, r.h)
    v = X.values[np.isfinite(X.values)]
    rows.append(dict(sideways=r.sideways, strength=r.strength, dip=r.dip, h=r.h, net_2000_25=r._5, events_1994_99=len(v),
                     net_B_1994_99=(m - .009) * 100 if len(v) else np.nan, t=(m - .009) / se if len(v) and se else np.nan,
                     event_weighted_net=(v.mean() - .009) * 100 if len(v) else np.nan))
out = pd.DataFrame(rows)
out.to_csv(ex.sd.OUT / 'holdout_1994_99.csv', index=False)
print(out.round(2).to_string(index=False))
