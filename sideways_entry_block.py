"""Why does the main system rarely enter in sideways markets? Share of eligible stock-days passing the ER20 >= 0.2 filter,
touching the buy stop (HHV20 + 0.5%), and blocked by ER, by market condition (30 Oct 2026, descriptive)."""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_breakout_er import efficiency_ratio
from analyze_portfolio_regimes import regime_proxy
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
lab = regime_proxy(st)['regime']
rows = []
for t, f in fr.items():
    f = f[f.tradable].reset_index(drop=True)
    lvl = f.High.shift(1).rolling(20).max()
    er = efficiency_ratio(f.Close, 20).shift(1)
    d = pd.DataFrame({'date': f['Date/Time'], 'elig': f['Date/Time'].isin(pit[t] & stale[t]),
                      'er_ok': er >= .2, 'below_level': f.Close.shift(1) <= lvl, 'touch': f.High >= lvl * 1.005})
    d['regime'] = lab.reindex(d.date).to_numpy()
    rows.append(d[(d.date >= '2000-01-01') & (d.date <= '2025-08-15') & d.elig])
D = pd.concat(rows)
out = []
for g, x in D.groupby('regime'):
    armed = x.er_ok & x.below_level
    out.append(dict(regime=g, stock_days=len(x), er_ok=x.er_ok.mean(), armed=armed.mean(),
                    touch_given_below_level=x.touch[x.below_level].mean(), buy_signal=(armed & x.touch).mean(),
                    er_block_among_touch=1 - x.er_ok[x.below_level & x.touch].mean()))
print(pd.DataFrame(out).round(3).to_string(index=False))
