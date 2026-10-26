"""Why does adding the month-start entry raise returns in up/down markets? (26 Oct 2026, exploratory decomposition)
Runs (scenario B, 2000-2025, unrestricted and realistic): V0; V0 + F_mom monthly (allowance 35%, 10% orders);
V0 + random monthly selection held one month (same allowance, 3 seeds) = same extra exposure without trend selection.
1. Daily P&L of every trade, marked at Closes, split by position kind (breakout / monthly) and by market condition of the
   day; contribution = P&L / previous-day equity, annualised as mean x 252 (arithmetic, so parts add up).
2. Market check without our system: equal-weight daily return of stocks passing F_mom at their last Close of the previous
   month vs those not passing, by market condition (realistic-eligible stocks).
Writes monthly_trend_entry_results/why_*.csv"""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from analyze_portfolio_regimes import regime_proxy
from monthly_trend_entry import trend
import zlib

st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
ME = set(cal.groupby(cal.dt.to_period('M')).max())
lab = regime_proxy(st)['regime']
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
gate = {t: pit[t] & stale[t] for t in fr}
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
me = lambda f: f['Date/Time'].isin(ME).to_numpy(bool)
OUT = __import__('pathlib').Path(__file__).resolve().parent / 'monthly_trend_entry_results'
closes = {t: f.set_index('Date/Time').Close for t, f in fr.items()}


def daily_pnl(T, idx):
    """Per-day P&L by kind from the ledger, marked at Closes; sums to each trade's pnl exactly."""
    out = {k: np.zeros(len(idx)) for k in ('main', 'extra')}
    pos = pd.Series(np.arange(len(idx)), index=idx)
    for r in T.itertuples():
        c = closes[r.ticker].loc[r.entry_date:r.exit_date]
        vals = r.q * c.to_numpy()
        pnl = np.empty(len(c))
        if len(c) == 1:
            pnl[0] = r.pnl
        else:
            pnl[0] = vals[0] - r.notional
            pnl[1:-1] = np.diff(vals)[:-1]
            pnl[-1] = (r.notional + r.pnl) - vals[-2]
        ii = pos.reindex(c.index).to_numpy()
        ok = ~np.isnan(ii)
        np.add.at(out[getattr(r, 'kind', 'main')], ii[ok].astype(int), pnl[ok])
    return out


rows, expo = [], []
for version in ('unrestricted', 'realistic'):
    k0 = rc.kw(BASE, 'B')
    if version == 'realistic':
        k0.update(liq_cap=.25, gate_dates=gate)
    runs = {'V0': k0,
            '+monthly F_mom': dict(k0, extra_signal_fn=lambda f: me(f) & f.tradable.to_numpy(bool) & trend('F_mom', f),
                                   extra_exit_signal_fn=lambda f: me(f) & ~trend('F_mom', f), extra_size_div=10, extra_max_frac=.35)}
    for seed in (1, 2, 3):
        runs[f'+monthly random{seed}'] = dict(k0, extra_signal_fn=lambda f: me(f) & f.tradable.to_numpy(bool), extra_exit_signal_fn=me,
                                              extra_size_div=10, extra_max_frac=.35,
                                              extra_priority=lambda f, s=seed: np.random.default_rng([s, zlib.crc32(str(f['Ticker'].iloc[0]).encode())]).random(len(f)))
    for name, k in runs.items():
        with np.errstate(invalid='ignore', divide='ignore'):
            c, t = run(fr, start='2000-01-01', **k)
        if 'kind' not in t:
            t['kind'] = 'main'
        idx = c.index
        P = daily_pnl(t, idx)
        prev_eq = c.equity.shift(1).fillna(1e9).to_numpy()
        g = lab.reindex(idx).to_numpy()
        keep = idx <= '2025-08-15'
        tot = c.equity.pct_change().fillna(c.equity.iloc[0] / 1e9 - 1).to_numpy()
        for rg in ('uptrend', 'sideways', 'downtrend'):
            m = keep & (g == rg)
            rows.append(dict(version=version, system=name, regime=rg, total_ann=tot[m].mean() * 252,
                             breakout_ann=(P['main'][m] / prev_eq[m]).mean() * 252, monthly_ann=(P['extra'][m] / prev_eq[m]).mean() * 252,
                             invested=float((c.market_value / c.equity).to_numpy()[m].mean())))
R = pd.DataFrame(rows)
R.to_csv(OUT / 'why_decomposition.csv', index=False)

# 2. market check: momentum basket vs the rest, by condition (realistic-eligible stocks, equal weight, daily Close returns)
ret, mem, elig = {}, {}, {}
for t, f in fr.items():
    s = f.set_index('Date/Time')
    ret[t] = s.Close.pct_change()
    mon = f['Date/Time'].dt.to_period('M')
    last = ~mon.duplicated(keep='last')
    ok = pd.Series(trend('F_mom', f), index=f.index)[last]
    passing = set(mon[last][ok.to_numpy()] + 1)
    mem[t] = pd.Series(mon.isin(passing).to_numpy(), index=s.index)
    elig[t] = pd.Series(s.index.isin(list(gate[t])), index=s.index)
RET, MEM, ELI = pd.DataFrame(ret), pd.DataFrame(mem).fillna(False), pd.DataFrame(elig).fillna(False)
RET = RET.loc['2000-01-01':'2025-08-15']
MEM, ELI = MEM.reindex(RET.index).fillna(False).astype(bool), ELI.reindex(RET.index).fillna(False).astype(bool)
mom_b = RET.where(MEM & ELI).mean(axis=1)
rest_b = RET.where(~MEM & ELI).mean(axis=1)
all_b = RET.where(ELI).mean(axis=1)
g = lab.reindex(RET.index)
M = pd.DataFrame([dict(regime=rg, momentum_basket_ann=mom_b[g == rg].mean() * 252, rest_ann=rest_b[g == rg].mean() * 252,
                       all_eligible_ann=all_b[g == rg].mean() * 252, days=int((g == rg).sum())) for rg in ('uptrend', 'sideways', 'downtrend')])
M.to_csv(OUT / 'why_market_check.csv', index=False)
pd.set_option('display.width', 220)
print(R.round(3).to_string(index=False))
print(M.round(3).to_string(index=False))
