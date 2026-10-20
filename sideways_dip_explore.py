"""EXPLORATORY (written after the pre-registered test failed): is there ANY price+time variant of 'buy a dip of a strong
stock at the Close in a sideways market, sell at an Open h days later' whose average trade beats the 0.90% cost?
Grid: dip depth (Close >= k ATR below the 10-day high Close, k 1/2/3/4; or 10-day-range bottom 20%/10%) x strength
(above SMA200 / above SMA200 and SMA50 rising / 120-day momentum in the top quintile of the day) x sideways definition
(market / stock ER20 < 0.3) x h 1..10. Realistic universe. 360 cells -> heavy multiple testing: anything found is a
hypothesis for a later sample, not a result."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
import sideways_dip_property as sd  # reuses panel, eligibility, ATR, regimes (runs that script's computations once)
from mpstats import nw

lnP, lnO = sd.lnP, sd.lnO
Ct = sd.Ct
drop = Ct.rolling(10, min_periods=8).max() - Ct
dips = {f'{k}atr': drop >= k * sd.ATR for k in [1, 2, 3, 4]}
dips.update({'range20': sd.pos <= .2, 'range10': sd.pos <= .1})
sma50 = lnP.rolling(50, min_periods=50).mean()
mom = lnP.shift(21) - lnP.shift(141)
strg = {'sma200': sd.strong, 'sma200_sma50up': sd.strong & (sma50 > sma50.shift(10)),
        'mom_top20': mom.rank(axis=1, pct=True) >= .8}
sides = {'market': sd.side_mkt, 'stock_er': sd.side_stk}
base = sd.base & sd.elig
rows = []
for sn, S in sides.items():
    for gn, Gm in strg.items():
        for dn, D in dips.items():
            M = base & S & Gm & D
            for h in range(1, 11):
                X = (lnO.shift(-h) - lnP).where(M)
                out = dict(sideways=sn, strength=gn, dip=dn, h=h)
                for pn, (a, b) in sd.PER.items():
                    s = X.loc[a:b].mean(axis=1)
                    m, se, n = nw(s.values, h)
                    out[f'net_{pn}'] = (m - .009) * 100
                    if pn == '2000-25':
                        out['t_net'] = (m - .009) / se if se else np.nan
                        out['events'] = int(np.isfinite(X.loc[a:b].values).sum())
                        out['gross'] = m * 100
                rows.append(out)
d = pd.DataFrame(rows)
d['subs_pos'] = (d[[f'net_{p}' for p in ['2000-07', '2008-15', '2016-20', '2021-25']]] > 0).sum(axis=1)
d.to_csv(sd.OUT / 'exploratory_grid.csv', index=False)
pd.set_option('display.width', 250)
print('cells', len(d), 'net>0:', int((d['net_2000-25'] > 0).sum()), 'net>0 & t>=2:', int(((d['net_2000-25'] > 0) & (d.t_net >= 2)).sum()))
print(d.sort_values('net_2000-25', ascending=False).head(15).round(2).to_string(index=False))
