"""Main pick by market regime (uptrend / sideways / downtrend), unrestricted and realistic (point-in-time liquidity + stale
filter + 25% ADV20 cap), scenario B, 2000-2025, with Swinger ideal (B) and the equal-weight market proxy for reference.
Regimes as analyze_sk5_regimes.py: 'er20' (ER20 >= 0.3 and 20-day direction on the EW proxy) and 'ret60' (proxy 60-day
return > +5% / < -5%); labels use the previous Close. Writes regime_breakdown_results/by_regime.csv."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu
import pit_stale_liquidity as psl
from analyze_sk5_regimes import regimes
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio

OUT = Path(__file__).resolve().parent / 'regime_breakdown_results'
OUT.mkdir(exist_ok=True)
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
REG = regimes(st)
curves = {}
k = rc.kw(pu.BASE, 'B')
with np.errstate(invalid='ignore', divide='ignore'):
    curves['main_unrestricted'] = run(fr, start='2000-01-01', **k)[0].equity
    pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
    k2 = dict(k, liq_cap=.25, gate_dates={t: pit[t] & stale[t] for t in fr})
    curves['main_realistic'] = run(fr, start='2000-01-01', **k2)[0].equity
curves['swinger_ideal'] = run_portfolio(fr, 'afl_ideal', slip=.0025)[0].equity
rows = []
for rdef, p in REG.items():
    lab = p['regime']
    mk = p['proxy'].pct_change()
    for name, eq in list(curves.items()) + [('market_EW_proxy', None)]:
        r = (eq.pct_change() if eq is not None else mk).loc['2000-01-01':'2025-08-15']
        d = pd.DataFrame({'r': r, 'reg': lab.reindex(r.index)}).dropna()
        for g, x in d.groupby('reg'):
            e = (1 + x.r).cumprod()
            rows.append(dict(regime_def=rdef, system=name, regime=g, share_days=len(x) / len(d),
                             ann_return=float(e.iloc[-1] ** (252 / len(x)) - 1), pos_days=float((x.r > 0).mean()),
                             regime_chain_mdd=float((e / e.cummax() - 1).min())))
res = pd.DataFrame(rows)
res.to_csv(OUT / 'by_regime.csv', index=False)
res['v'] = res.apply(lambda r: f"{r.ann_return*100:.0f}% (mdd {r.regime_chain_mdd*100:.0f}%)", axis=1)
pd.set_option('display.width', 250)
for rdef in REG:
    x = res[res.regime_def == rdef]
    print(rdef, x.groupby('regime').share_days.first().round(3).to_dict())
    print(x.pivot_table(index='system', columns='regime', values='v', aggfunc='first').to_string())
