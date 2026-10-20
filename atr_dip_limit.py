"""Buy-limit dips of x ATR: event study (plan: atr_dip_limit_results/PLAN.md)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent / 'market_properties_v2'))
from panel import load
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_sk5_regimes import regimes

OUT = Path(__file__).resolve().parent / 'atr_dip_limit_results'
P = load()
O, H, L, C, T = (P[k] for k in ['O', 'H', 'L', 'C', 'T'])
lnP = P['lnP']
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
elig = pd.DataFrame(False, index=C.index, columns=C.columns)
for t in C.columns:
    ok = pit[t] & stale[t]
    elig.loc[elig.index.isin(list(ok)), t] = True
reg = regimes(st)['er20']['regime'].reindex(C.index)


def atr_prev(h, l, c, n=14):
    tr = h - l
    tr[1:] = np.maximum(tr[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    a = np.full(len(c), np.nan)
    if len(c) >= n:
        a[n - 1] = tr[:n].mean()
        for i in range(n, len(c)):
            a[i] = (a[i - 1] * (n - 1) + tr[i]) / n
    return a  # ATR through bar i (use shift(1) for 'known before day t')


ATR = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
for t in C.columns:
    m = T[t].values & C[t].notna().values
    idx = C.index[m]
    ATR.loc[idx, t] = atr_prev(H.loc[idx, t].values.astype(float), L.loc[idx, t].values.astype(float), C.loc[idx, t].values.astype(float))
Cprev = C.where(T).ffill().shift(1)
ATRp = ATR.ffill().shift(1)
okday = T & ~P['bad'] & P['r_on'].notna()
PERIODS = {'2000-25': ('2000-01-01', '2025-08-15'), '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
           '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
EXITS = {'close_t': (0, 'C'), 'open_t1': (1, 'O'), 'close_t1': (1, 'C'), 'close_t5': (5, 'C'), 'close_t20': (20, 'C')}
lnO = P['lnO']
rows = []
for x in [1, 1.5, 2, 3]:
    lim = Cprev - x * ATRp
    for fillrule in ['through', 'touch']:
        hit = (L < lim) if fillrule == 'through' else (L <= lim)
        hit = hit & okday & (ATRp > 0)
        E = np.minimum(O, lim)
        lnE = lnP.shift(1) + np.log(E / Cprev)      # clean level of the fill price
        lnOpen = lnO
        for uni, U in [('realistic', elig), ('all', pd.DataFrame(True, index=C.index, columns=C.columns))]:
            ev = hit & U
            for ex, (h, kind) in EXITS.items():
                tgt = (lnP.shift(-h) if kind == 'C' else lnO.shift(-h))
                r = (tgt - lnE).where(ev)
                rc_ = (tgt - lnOpen).where(ev)          # control: same stock, bought at that day's Open
                for pn, (a, b) in PERIODS.items():
                    for rg in ['all', 'uptrend', 'sideways', 'downtrend']:
                        if rg != 'all' and pn != '2000-25':
                            continue
                        rr, cc = r.loc[a:b], rc_.loc[a:b]
                        if rg != 'all':
                            msk = (reg.loc[a:b] == rg).values[:, None]
                            rr, cc = rr.where(msk), cc.where(msk)
                        s = rr.mean(axis=1)
                        m, se, n = nw(s.values, max(h, 1))
                        mc, sec, _ = nw((rr - cc).mean(axis=1).values, max(h, 1))
                        rows.append(dict(x=x, fill=fillrule, universe=uni, exit=ex, period=pn, regime=rg,
                                         fills=int(rr.notna().values.sum()), fill_days=n,
                                         gross_pct=m * 100, t=m / se if se else np.nan,
                                         net_B_pct=(m - .009) * 100, t_net_B=(m - .009) / se if se else np.nan,
                                         net_A_pct=(m - .004) * 100,
                                         event_weighted_gross_pct=float(np.nanmean(rr.values)) * 100,
                                         win_rate_net_B=float(np.nanmean(rr.values > .009)) if rr.notna().values.any() else np.nan,
                                         vs_buy_at_open_pct=mc * 100, t_vs_open=mc / sec if sec else np.nan))
d = pd.DataFrame(rows)
d.to_csv(OUT / 'events.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
m = d[(d.fill == 'through') & (d.universe == 'realistic') & (d.regime == 'all')]
print(m.pivot_table(index=['x', 'exit'], columns='period', values='net_B_pct').round(2).to_string())
print(m[m.period == '2000-25'][['x', 'exit', 'fills', 'gross_pct', 't', 'net_B_pct', 't_net_B', 'event_weighted_gross_pct', 'win_rate_net_B', 'vs_buy_at_open_pct', 't_vs_open']].round(2).to_string(index=False))
r = d[(d.fill == 'through') & (d.universe == 'realistic') & (d.period == '2000-25') & (d.regime != 'all')]
print(r.pivot_table(index=['x', 'exit'], columns='regime', values='net_B_pct').round(2).to_string())
