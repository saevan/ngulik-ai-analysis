"""Per-trade quality and yearly returns: our v2 main pick (unrestricted and realistic) vs Prototype Swinger ideal (26 Oct 2026).
Scenario B (fee 0.15/0.25% + 0.25%/side slippage), Rp1bn, compounding, 2000-01-01..2025-08-15.
Market condition at entry = label known before that day's Open (regime_proxy: EW proxy ER20 >= 0.3 with 20-day direction up /
down, else sideways). 'breakdown' (overlapping slice) = the proxy's previous Close was a new 20-day low (below the lowest of the
20 Closes before it). Per-trade figures by entry condition; portfolio daily returns by the day's condition; calendar-year
returns. Writes quality_vs_swinger_results/trade_quality.csv, portfolio_by_condition.csv, yearly.csv."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from analyze_portfolio_regimes import regime_proxy

OUT = Path(__file__).resolve().parent / 'quality_vs_swinger_results'
OUT.mkdir(exist_ok=True)
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
rp = regime_proxy(st)
lab = rp['regime']
breakdown = (rp.proxy < rp.proxy.shift(1).rolling(20).min()).shift(1, fill_value=False)
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
k = rc.kw(BASE, 'B')
S = {}
with np.errstate(invalid='ignore', divide='ignore'):
    S['ours'] = run(fr, start='2000-01-01', **k)
    S['ours_realistic'] = run(fr, start='2000-01-01', **dict(k, liq_cap=.25, gate_dates={t: pit[t] & stale[t] for t in fr}))
    c, t, _ = run_portfolio(fr, 'afl_ideal', slip=.0025)
    S['swinger_ideal'] = (c, t)
COND = ['uptrend', 'sideways', 'downtrend', 'breakdown', 'all']


def in_cond(dates, g):
    dates = pd.DatetimeIndex(dates)
    if g == 'all':
        return np.ones(len(dates), bool)
    if g == 'breakdown':
        return breakdown.reindex(dates).fillna(False).to_numpy(bool)
    return (lab.reindex(dates) == g).to_numpy()


tq, pc, yr = [], [], {}
for name, (c, t) in S.items():
    c = c.loc['2000-01-01':'2025-08-15']
    t = t[pd.to_datetime(t.entry_date) <= '2025-08-15']
    total_pnl = t.pnl.sum()
    for g in COND:
        x = t[in_cond(t.entry_date, g)]
        r = x.net_return
        w = r > 0
        tq.append(dict(system=name, condition=g, trades=len(x), share_trades=len(x) / len(t), win_rate=w.mean(), avg_win=r[w].mean(),
                       avg_loss=r[~w].mean(), payout=r[w].mean() / -r[~w].mean(), mean_trade=r.mean(), median_trade=r.median(),
                       mean_bars=x.bars.mean(), mean_per_bar=r.mean() / x.bars.mean(), share_pnl=x.pnl.sum() / total_pnl))
    dr = c.equity.pct_change().dropna()
    for g in COND:
        x = dr[in_cond(dr.index, g)]
        e = (1 + x).cumprod()
        pc.append(dict(system=name, condition=g, share_days=len(x) / len(dr), ann_return=float(e.iloc[-1] ** (252 / len(x)) - 1),
                       mean_daily_pct=x.mean() * 100, invested=float((c.market_value / c.equity).reindex(x.index).mean())))
    eq = pd.concat([pd.Series([1e9], index=[pd.Timestamp('1999-12-31')]), c.equity])
    yr[name] = eq.resample('YE').last().pct_change().dropna()
T, P = pd.DataFrame(tq), pd.DataFrame(pc)
Y = pd.DataFrame(yr)
Y.index = Y.index.year
Y['gap_ours_pp'] = (Y.ours - Y.swinger_ideal) * 100
Y['gap_realistic_pp'] = (Y.ours_realistic - Y.swinger_ideal) * 100
T.to_csv(OUT / 'trade_quality.csv', index=False)
P.to_csv(OUT / 'portfolio_by_condition.csv', index=False)
Y.to_csv(OUT / 'yearly.csv')
pd.set_option('display.width', 250)
print(T.round(4).to_string(index=False))
print(P.round(4).to_string(index=False))
print((Y * [100, 100, 100, 1, 1]).round(1).to_string())
print('years ours > swinger', int((Y.ours > Y.swinger_ideal).sum()), 'realistic > swinger', int((Y.ours_realistic > Y.swinger_ideal).sum()), 'of', len(Y))
print('median yearly: ours', Y.ours.median(), 'realistic', Y.ours_realistic.median(), 'swinger', Y.swinger_ideal.median())
print('mean gap pp', Y.gap_ours_pp.mean(), Y.gap_realistic_pp.mean(), 'median gap pp', Y.gap_ours_pp.median(), Y.gap_realistic_pp.median())
print('breakdown days share of downtrend:', (breakdown & (lab == 'downtrend')).sum() / breakdown.sum())
