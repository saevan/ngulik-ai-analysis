"""Frozen 1996-99 holdout for the breadth + limit family (plan addendum in sideways_bounce_grid_results/PLAN.md)."""
import sys, zlib
import numpy as np, pandas as pd
import sideways_bounce_grid as g
from sideways_bounce_grid import G, nw, engine, pu, psl, regime_proxy, OUT, COST

CELLS = [('T1 RSI2 < 10', 'F4 breadth < 30%', 'limit Close - 0.5 ATR', 'Close > SMA5'), ('T2 3 lower closes', 'F4 breadth < 30%', 'limit Close - 0.5 ATR', 'Close > SMA5')]
g.START, g.END = '1996-01-01', '1999-12-31'
st, _ = engine.load_data('stocks')
G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
G['lab'] = regime_proxy(st)['regime']
above = {}
for t, f in G['fr'].items():
    f = f[f.tradable].set_index('Date/Time'); above[t] = (f.Close > f.Close.rolling(20).mean()).where(f.Close.rolling(20).mean().notna())
G['breadth'] = pd.DataFrame(above).mean(axis=1)
rows = []
with np.errstate(invalid='ignore', divide='ignore'):
    G['cache'] = {t: g.prep(t) for t in G['fr']}
    for cell in CELLS:
        T = g.sim(cell); counts = T.groupby('ticker').size().to_dict()
        C = pd.concat([g.sim(cell, zlib.crc32(f'{cell}-{s}'.encode()), counts) for s in range(5)])
        dd = T.groupby('entry').net_B.mean().reindex(G['cal'].loc[g.START:g.END].index); m, se, _ = nw(dd.to_numpy(), 10)
        rows.append(dict(trigger=cell[0], filter=cell[1], entry=cell[2], exit=cell[3], trades=len(T), stocks=T.ticker.nunique(), win_rate=(T.net_B > 0).mean(),
                         net_B_pct=m * 100, t=m / se if se else np.nan, net_B_event_pct=T.net_B.mean() * 100, control_net_pct=C.net_B.mean() * 100))
R = pd.DataFrame(rows); R.to_csv(OUT / 'holdout_1996_99.csv', index=False)
pd.set_option('display.width', 250); print(R.round(3).to_string(index=False))
