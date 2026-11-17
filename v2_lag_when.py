"""When does V2 lag Swinger ideal on stocks? (plan: v2_lag_when_results/PLAN.md). Descriptive."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from analyze_portfolio_regimes import regime_proxy
import wr_gap_v1 as w

OUT = Path(__file__).resolve().parent / 'v2_lag_when_results'
A, B = '2000-01-01', '2025-08-15'
G = w.G
st, _ = engine.load_data('stocks')
G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
rp = regime_proxy(st); lab = rp.regime
with np.errstate(invalid='ignore', divide='ignore'):
    cv, _ = run(G['fr'], start=A, **dict(w.kw('realistic', True, None), failed_exit=None))
    cs, _, _ = run_portfolio(G['fr'], 'afl_ideal', slip=.0025)
cv, cs = cv.loc[:B], cs.loc[A:B]
idx = cv.index.intersection(cs.index)
lv = np.log(cv.equity.reindex(idx)).diff().fillna(np.log(cv.equity.reindex(idx).iloc[0] / 1e9))
ls = np.log(cs.equity.reindex(idx)).diff().fillna(np.log(cs.equity.reindex(idx).iloc[0] / 1e9))
gap = ls - lv; total = gap.sum()
g = lab.reindex(idx).fillna('unknown')
mret = np.log(rp.proxy).diff().reindex(idx)

# 1. per year
yr = idx.year
Y = pd.DataFrame({'V2': np.expm1(lv.groupby(yr).sum()), 'Swinger ideal': np.expm1(ls.groupby(yr).sum()), 'market EW': np.expm1(mret.groupby(yr).sum())})
Y['gap_pp'] = (Y['Swinger ideal'] - Y['V2']) * 100
for k in ('uptrend', 'sideways', 'downtrend'):
    Y[f'{k}_days'] = (g == k).groupby(yr).mean()
Y['log_gap_share'] = gap.groupby(yr).sum() / total
Y.to_csv(OUT / 'by_year.csv')

# 2. per condition
inv_v = (cv.market_value / cv.equity).reindex(idx); inv_s = (cs.market_value / cs.equity).reindex(idx)
C = pd.DataFrame([dict(condition=k, share_days=(g == k).mean(), V2_ann=np.expm1(lv[g == k].mean() * 252), swinger_ann=np.expm1(ls[g == k].mean() * 252),
                       V2_invested=inv_v[g == k].mean(), swinger_invested=inv_s[g == k].mean(), log_gap_share=gap[g == k].sum() / total)
                  for k in ('uptrend', 'sideways', 'downtrend')])
C.to_csv(OUT / 'by_condition.csv', index=False)

# 3. per market speed (proxy 20-day return known before the Open)
m20 = (rp.proxy / rp.proxy.shift(20) - 1).shift(1).reindex(idx)
q = pd.qcut(m20, 5, labels=['Q1 fast fall', 'Q2 fall', 'Q3 flat', 'Q4 rise', 'Q5 fast rise'])
S = pd.DataFrame([dict(bucket=k, market_20d_median=m20[q == k].median(), V2_ann=np.expm1(lv[q == k].mean() * 252), swinger_ann=np.expm1(ls[q == k].mean() * 252),
                       V2_invested=inv_v[q == k].mean(), log_gap_share=gap[q == k].sum() / total) for k in q.cat.categories])
S.to_csv(OUT / 'by_market_speed.csv', index=False)

# 4. per V2 position count
pc = pd.cut(cv.positions.reindex(idx), [-1, 2, 6, 99], labels=['0-2 positions', '3-6 positions', '7+ positions'])
P = pd.DataFrame([dict(state=k, share_days=(pc == k).mean(), V2_ann=np.expm1(lv[pc == k].mean() * 252), swinger_ann=np.expm1(ls[pc == k].mean() * 252),
                       log_gap_share=gap[pc == k].sum() / total) for k in pc.cat.categories])
P.to_csv(OUT / 'by_v2_positions.csv', index=False)
pd.set_option('display.width', 250)
for X in (Y, C, S, P):
    print(X.round(3).to_string()); print()
print('total log gap %.2f | V2 CAGR %.3f | Swinger CAGR %.3f' % (total, np.expm1(lv.sum() / (len(idx) / 252)), np.expm1(ls.sum() / (len(idx) / 252))))
