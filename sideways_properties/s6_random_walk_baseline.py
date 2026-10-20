"""Addendum written AFTER seeing S6 (labelled as such): S6a/S6c compare levels at very different distances (the 20-day mid
is usually several ATR away, the 'break' level 1 ATR away), so 'support breaks more often' could be pure geometry.
Driftless random-walk baseline: from the touch day's Close, P(up level first | one is hit) = d_down / (d_up + d_down).
Excess = observed up-first indicator minus that baseline (events where neither level is hit in 10 days are dropped).
Positive excess = the level holds better than chance (support) / breakout continues better than chance (resistance)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import battery as b
from mpstats import nw

rows = []
for nm, fp, up, dn in [('support', b.fp_sup, b.mid, b.dn_lvl), ('resistance', b.fp_res, b.up_lvl, b.mid)]:
    du, dd = up - b.lnP, b.lnP - dn
    pr = dd / (du + dd)
    ok = (du > 0) & (dd > 0) & fp.notna() & (fp != 0)
    y = (fp == 1).astype(float)
    ex = (y - pr).where(ok)
    s = ex.mean(axis=1)
    for g in ['sideways', 'uptrend', 'downtrend']:
        m, se, n = nw(s.where(b.REG == g).loc[b.MAIN[0]:b.MAIN[1]].values, 10)
        obs = y.where(ok & pd.DataFrame(np.repeat((b.REG == g).values[:, None], len(b.cols), 1), index=b.cal, columns=b.cols)).loc[b.MAIN[0]:b.MAIN[1]]
        base = pr.where(obs.notna())
        row = dict(level=nm, regime=g, events=int(obs.notna().values.sum()), observed_up_first=float(np.nanmean(obs.values)),
                   random_walk_up_first=float(np.nanmean(base.values)), excess=m, t=m / se if se else np.nan)
        for k, (a, bb) in b.SUB.items():
            mm, _, _ = nw(s.where(b.REG == g).loc[a:bb].values, 10)
            row[k] = mm
        rows.append(row)
d = pd.DataFrame(rows)
d.to_csv(b.OUT / 's6_random_walk_baseline.csv', index=False)
print(d.round(3).to_string(index=False))
