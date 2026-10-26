"""Add-on: Swinger ideal under the SAME realism limits as our realistic system (point-in-time liquidity + stale filter on
new entries, buys <= 25% ADV20), scenario B. run_portfolio has no entry gate, so its source is patched with one line
(skip a buy if the day is not in the stock's eligible set). Appends to compare_vs_swinger_results/."""
import inspect
import numpy as np, pandas as pd
import backtest_prototype_swinger as bps
import compare_vs_swinger as cv  # reuses data, gate and metric code (runs the main comparison once)
from backtest_open_next import stats

src = inspect.getsource(bps.run_portfolio)
a = "            if not signal or not d['tradable'][i]:continue\n            if reserved_count>=10"
assert a in src
src = src.replace(a, "            if not signal or not d['tradable'][i]:continue\n            if GATE is not None and day not in GATE.get(ticker,()):continue\n            if reserved_count>=10")
ns = dict(vars(bps)); ns['GATE'] = cv.gate
exec(src, ns)
c, t, _ = ns['run_portfolio'](cv.fr, 'afl_ideal', slip=.0025, liq_cap=.25)
c = c.loc['2000-01-01':'2025-08-15']
s = stats(c, t)
eq = c.equity
yr = eq.resample('YE').last().pct_change().dropna()
r = eq.pct_change().dropna()
lab = cv.reg.reindex(r.index)
row = dict(system='swinger_ideal_realistic_B', cagr=s['cagr'], record_months=s['records'], mdd=s['mdd'], trades=s['n'], win_rate=s['wr'],
           avg_win=s['avg_win'], avg_loss=s['avg_loss'], payout=s['payout'], invested=s['invested'], worst_year=yr.min(),
           losing_years=int((yr < 0).sum()), share_pnl_post2018_listings=float(t[t.ticker.isin(cv.post2018)].pnl.sum() / t.pnl.sum()))
for g in ['uptrend', 'sideways', 'downtrend']:
    x = r[lab == g]; e = (1 + x).cumprod(); row[f'ann_{g}'] = float(e.iloc[-1] ** (252 / len(x)) - 1)
pd.DataFrame([row]).to_csv(cv.OUT / 'swinger_ideal_realistic_B.csv', index=False)
print(pd.Series(row).to_string())
