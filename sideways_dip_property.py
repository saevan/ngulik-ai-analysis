"""Second-logic property test: buy dips of strong stocks at the Close in sideways markets, sell at the Open h days later.
Plan: sideways_dip_property_results/PLAN.md (committed before results)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from panel import load
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_sk5_regimes import regimes

OUT = ROOT / 'sideways_dip_property_results'
P = load()
lnP, lnO, lnH, lnL, T = P['lnP'], P['lnO'], P['lnH'], P['lnL'], P['T']
cal = lnP.index
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
elig = pd.DataFrame(False, index=cal, columns=lnP.columns)
for t in lnP.columns:
    elig.loc[elig.index.isin(list(pit[t] & stale[t])), t] = True
mreg = regimes(st)['er20']['regime'].reindex(cal)
side_mkt = pd.DataFrame(np.repeat((mreg == 'sideways').values[:, None], lnP.shape[1], 1), index=cal, columns=lnP.columns)
dl = lnP.diff().abs()
er20 = (lnP - lnP.shift(20)).abs() / dl.rolling(20).sum()
side_stk = er20 < .3
sma200 = lnP.rolling(200, min_periods=200).mean()
strong, weak = lnP > sma200, lnP <= sma200
hh, ll = lnH.rolling(10, min_periods=8).max(), lnL.rolling(10, min_periods=8).min()
pos = (lnP - ll) / (hh - ll)
d1 = pos <= .2


def atr(h, l, c, n=14):
    tr = h - l
    tr[1:] = np.maximum(tr[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    a = np.full(len(c), np.nan)
    if len(c) >= n:
        a[n - 1] = tr[:n].mean()
        for i in range(n, len(c)):
            a[i] = (a[i - 1] * (n - 1) + tr[i]) / n
    return a


C, H, L = P['C'], P['H'], P['L']
ATR = pd.DataFrame(np.nan, index=cal, columns=lnP.columns)
for t in lnP.columns:
    m = T[t].values & C[t].notna().values
    idx = cal[m]
    ATR.loc[idx, t] = atr(H.loc[idx, t].values.astype(float), L.loc[idx, t].values.astype(float), C.loc[idx, t].values.astype(float))
Ct = C.where(T)
d2 = (Ct.rolling(10, min_periods=8).max() - Ct) >= 2 * ATR
base = T & ~P['bad'] & lnP.notna()
PER = {'2000-25': ('2000-01-01', '2025-08-15'), '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
       '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
rows = []
for uni, U in [('realistic', elig), ('all', pd.DataFrame(True, index=cal, columns=lnP.columns))]:
    for sdef, S in [('market_sideways', side_mkt), ('stock_er_lt_0.3', side_stk)]:
        for dname, D in [('D1_bottom20_of_10d_range', d1), ('D2_2atr_below_10d_high', d2)]:
            groups = {'strong_dip': base & U & S & strong & D, 'weak_dip': base & U & S & weak & D, 'all_sideways': base & U & S}
            for h in range(1, 11):
                rets = {'close_to_open': lnO.shift(-h) - lnP, 'open_to_open': lnO.shift(-(1 + h)) - lnO.shift(-1),
                        'close_to_close': lnP.shift(-h) - lnP}
                for g, M in groups.items():
                    if g == 'all_sideways' and dname.startswith('D2'):
                        continue
                    for rname, R in rets.items():
                        if g != 'strong_dip' and rname != 'close_to_open':
                            continue
                        X = R.where(M)
                        for pn, (a, b) in PER.items():
                            x = X.loc[a:b]
                            s = x.mean(axis=1)
                            m, se, n = nw(s.values, h)
                            v = x.values[np.isfinite(x.values)]
                            rows.append(dict(universe=uni, sideways=sdef, dip=dname, group=g, ret=rname, h=h, period=pn,
                                             events=len(v), dropped=int((M.loc[a:b] & R.loc[a:b].isna()).values.sum()),
                                             gross_pct=m * 100, t_gross=m / se if se else np.nan, net_B_pct=(m - .009) * 100,
                                             t_net_B=(m - .009) / se if se else np.nan, net_A_pct=(m - .004) * 100,
                                             event_weighted_gross_pct=v.mean() * 100 if len(v) else np.nan,
                                             p05_pct=np.percentile(v, 5) * 100 if len(v) else np.nan,
                                             p95_pct=np.percentile(v, 95) * 100 if len(v) else np.nan,
                                             win_rate_net_B=(v > .009).mean() if len(v) else np.nan))
d = pd.DataFrame(rows)
d.to_csv(OUT / 'results.csv', index=False)
# pre-registered pass check
prim = d[(d.universe == 'realistic') & (d.sideways == 'market_sideways') & (d.dip == 'D1_bottom20_of_10d_range') & (d.ret == 'close_to_open')]
verdict = []
for h in range(1, 11):
    s = prim[(prim.group == 'strong_dip') & (prim.h == h)].set_index('period')
    w = prim[(prim.group == 'weak_dip') & (prim.h == h)].set_index('period')
    subs = (s.loc[['2000-07', '2008-15', '2016-20', '2021-25'], 'net_B_pct'] > 0).sum()
    verdict.append(dict(h=h, net_B_pct=s.loc['2000-25', 'net_B_pct'], t_net_B=s.loc['2000-25', 't_net_B'], subperiods_positive=int(subs),
                        strong_minus_weak_pct=s.loc['2000-25', 'gross_pct'] - w.loc['2000-25', 'gross_pct'],
                        passes=bool(s.loc['2000-25', 'net_B_pct'] > 0 and s.loc['2000-25', 't_net_B'] >= 3.25 and subs >= 3
                                    and s.loc['2000-25', 'gross_pct'] > w.loc['2000-25', 'gross_pct'])))
V = pd.DataFrame(verdict)
V.to_csv(OUT / 'primary_verdict.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
print(V.round(3).to_string(index=False))
r = d[(d.universe == 'realistic') & (d.ret == 'close_to_open') & (d.period == '2000-25')]
print(r.pivot_table(index=['sideways', 'dip', 'group'], columns='h', values='gross_pct').round(2).to_string())
print(r.pivot_table(index=['sideways', 'dip', 'group'], columns='h', values='t_gross').round(1).to_string())
sp = d[(d.universe == 'realistic') & (d.sideways == 'market_sideways') & (d.group == 'strong_dip') & (d.ret == 'close_to_open')]
print(sp.pivot_table(index=['dip', 'h'], columns='period', values='net_B_pct').round(2).to_string())
ex = d[(d.universe == 'realistic') & (d.sideways == 'market_sideways') & (d.dip == 'D1_bottom20_of_10d_range') & (d.group == 'strong_dip') & (d.period == '2000-25')]
print(ex.pivot_table(index='h', columns='ret', values='gross_pct').round(2).to_string())
print(ex[ex.ret == 'close_to_open'][['h', 'events', 'dropped', 'event_weighted_gross_pct', 'p05_pct', 'p95_pct', 'win_rate_net_B']].round(2).to_string(index=False))
