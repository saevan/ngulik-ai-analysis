"""Strengths and weaknesses of the current system versus the Prototype Swinger benchmark (26 Oct 2026).
Same data, Rp1bn, compounding, 2000-01-01..2025-08-15, scenario B (fee 0.15/0.25% + 0.25%/side slippage) unless stated.
Systems: our v2 main pick unrestricted and realistic (point-in-time liquidity + stale filter + buys <= 25% ADV20);
Swinger ideal (aspirational benchmark, fill at the prior TSL on the signal bar - not executable), Swinger ideal with the
same 25% ADV20 buy cap, and Swinger's causal versions (stop order with touch fills; signal at Close -> next Open).
Writes compare_vs_swinger_results/summary.csv, regimes.csv, periods.csv."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu
import pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from backtest_open_next import stats
from analyze_portfolio_regimes import regime_proxy

OUT = Path(__file__).resolve().parent / 'compare_vs_swinger_results'
OUT.mkdir(exist_ok=True)
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
post2018 = {t for t, f in fr.items() if f['Date/Time'].min() >= pd.Timestamp('2018-01-01')}
reg = regime_proxy(st)['regime']
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
gate = {t: pit[t] & stale[t] for t in fr}
S = {}
with np.errstate(invalid='ignore', divide='ignore'):
    for scen in ['A', 'B', 'D']:
        k = rc.kw(rc_base := dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4), scen)
        S[f'ours_unrestricted_{scen}'] = run(fr, start='2000-01-01', **k)
        S[f'ours_realistic_{scen}'] = run(fr, start='2000-01-01', **dict(k, liq_cap=.25, gate_dates=gate))
        slip = {'A': 0., 'B': .0025, 'D': .005}[scen]
        c, t, _ = run_portfolio(fr, 'afl_ideal', slip=slip)
        S[f'swinger_ideal_{scen}'] = (c, t)
    c, t, _ = run_portfolio(fr, 'afl_ideal', slip=.0025, liq_cap=.25)
    S['swinger_ideal_cap25_B'] = (c, t)
    c, t, _ = run_portfolio(fr, 'stop_order', slip=.0025, touch=True)
    S['swinger_stop_touch_B'] = (c, t)
    c, t, _ = run_portfolio(fr, 'next_open', slip=.0025)
    S['swinger_next_open_B'] = (c, t)

rows, regs, pers = [], [], []
for name, (c, t) in S.items():
    c = c.loc['2000-01-01':'2025-08-15']
    s = stats(c, t)
    eq = c.equity
    r = eq.pct_change().dropna()
    yr = eq.resample('YE').last().pct_change().dropna()
    mo = eq.resample('ME').last().pct_change().dropna()
    under = eq < eq.cummax()
    runs = (under != under.shift()).cumsum()
    longest_under = int(under.groupby(runs).sum().max())
    pnl = t.pnl if 'pnl' in t else t.net_return
    top10 = t.net_return.sort_values(ascending=False)
    share_top10 = float(t.loc[top10.index[:max(1, len(t) // 10)], 'pnl'].sum() / t.pnl.sum()) if 'pnl' in t and t.pnl.sum() > 0 else np.nan
    share_post2018 = float(t[t.ticker.isin(post2018)].pnl.sum() / t.pnl.sum()) if 'pnl' in t and t.pnl.sum() > 0 else np.nan
    rows.append(dict(system=name, cagr=s['cagr'], record_months=s['records'], months=s['months'], mdd=s['mdd'], trades=s['n'],
                     trades_per_year=s['n'] / 25.6, win_rate=s['wr'], avg_win=s['avg_win'], avg_loss=s['avg_loss'], payout=s['payout'],
                     mean_trade=s['mean'], median_trade=s['median'], bars_win=s['win_bars'], bars_loss=s['loss_bars'],
                     invested=s['invested'], full_slots=s['full_slots'], best_year=yr.max(), worst_year=yr.min(),
                     losing_years=int((yr < 0).sum()), positive_months=float((mo > 0).mean()), longest_underwater_days=longest_under,
                     share_pnl_top10pct_trades=share_top10, share_pnl_post2018_listings=share_post2018,
                     daily_vol_ann=float(r.std() * np.sqrt(252))))
    lab = reg.reindex(r.index)
    for g in ['uptrend', 'sideways', 'downtrend']:
        x = r[lab == g]
        e = (1 + x).cumprod()
        regs.append(dict(system=name, regime=g, ann_return=float(e.iloc[-1] ** (252 / len(x)) - 1), share_days=len(x) / len(r),
                         regime_mdd=float((e / e.cummax() - 1).min())))
    for pn, (a, b) in {'2000-07': ('2000', '2007'), '2008-15': ('2008', '2015'), '2016-20': ('2016', '2020'), '2021-25': ('2021', '2025')}.items():
        x = eq.loc[a:b]
        prev = eq.loc[:str(int(a) - 1)]
        start = prev.iloc[-1] if len(prev) else 1e9
        yrs = (x.index[-1] - (prev.index[-1] if len(prev) else x.index[0])).days / 365.25
        pers.append(dict(system=name, period=pn, cagr_slice=float((x.iloc[-1] / start) ** (1 / yrs) - 1)))
D = pd.DataFrame(rows)
D.to_csv(OUT / 'summary.csv', index=False)
R = pd.DataFrame(regs)
R.to_csv(OUT / 'regimes.csv', index=False)
P = pd.DataFrame(pers)
P.to_csv(OUT / 'periods.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
print(D.set_index('system').T.round(3).to_string())
print(R.pivot_table(index='system', columns='regime', values='ann_return').round(3).to_string())
print(P.pivot_table(index='system', columns='period', values='cagr_slice').round(3).to_string())
