"""Impact of ADDING the month-start entry (F_mom: Close > Close 120 bars ago; monthly positions <= A of equity, 10% orders,
monthly first at the Open) to the unchanged main pick, vs the main pick alone (V0). Scenario B, 2000-01-01..2025-08-15,
unrestricted and realistic (26 Oct 2026). Decomposes: headline, trade flow (breakout trades kept / displaced / new,
monthly trades), market condition (daily returns by regime label), calendar years.
Writes monthly_trend_entry_results/impact_*.csv"""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_open_next import stats
from analyze_portfolio_regimes import regime_proxy
from monthly_trend_entry import trend

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

head, flow, regs, years = [], [], [], {}
for version in ('unrestricted', 'realistic'):
    k0 = rc.kw(BASE, 'B')
    if version == 'realistic':
        k0.update(liq_cap=.25, gate_dates=gate)
    runs = {'V0': k0}
    for A in (.2, .35):
        runs[f'+monthly A{int(A * 100)}'] = dict(k0, extra_signal_fn=lambda f: me(f) & f.tradable.to_numpy(bool) & trend('F_mom', f),
                                                extra_exit_signal_fn=lambda f: me(f) & ~trend('F_mom', f), extra_size_div=10, extra_first=True,
                                                extra_max_frac=A)
    res = {}
    with np.errstate(invalid='ignore', divide='ignore'):
        for name, k in runs.items():
            c, t = run(fr, start='2000-01-01', **k)
            c = c.loc[:'2025-08-15']
            if 'kind' not in t:
                t['kind'] = 'main'
            res[name] = (c, t)
    c0, t0 = res['V0']
    key0 = set(zip(t0.ticker, t0.entry_date))
    for name, (c, t) in res.items():
        s = stats(c, t)
        yrs = (c.index[-1] - c.index[0]).days / 365.25
        head.append(dict(version=version, system=name, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], win_rate=s['wr'], expectancy=s['mean'],
                         trades_per_year=s['n'] / yrs, invested=s['invested'], cash_idle=1 - s['invested']))
        m, x = t[t.kind == 'main'], t[t.kind == 'extra']
        keyc = set(zip(m.ticker, m.entry_date))
        dropped = t0[[k_ not in keyc for k_ in zip(t0.ticker, t0.entry_date)]]
        new = m[[k_ not in key0 for k_ in zip(m.ticker, m.entry_date)]]
        kept = m[[k_ in key0 for k_ in zip(m.ticker, m.entry_date)]]
        flow.append(dict(version=version, system=name, breakout_trades=len(m), breakout_wr=(m.net_return > 0).mean(), breakout_e=m.net_return.mean(),
                         kept=len(kept), dropped=len(dropped), dropped_wr_in_V0=(dropped.net_return > 0).mean() if len(dropped) else np.nan,
                         dropped_e_in_V0=dropped.net_return.mean() if len(dropped) else np.nan, new_breakouts=len(new),
                         new_e=new.net_return.mean() if len(new) else np.nan, monthly_trades=len(x),
                         monthly_wr=(x.net_return > 0).mean() if len(x) else np.nan, monthly_e=x.net_return.mean() if len(x) else np.nan,
                         monthly_bars=x.bars.mean() if len(x) else np.nan, monthly_pnl_share=x.pnl.sum() / t.pnl.sum()))
        dr = c.equity.pct_change().dropna()
        g = lab.reindex(dr.index)
        for rg in ('uptrend', 'sideways', 'downtrend'):
            y = dr[g == rg]
            regs.append(dict(version=version, system=name, regime=rg, ann_return=float((1 + y).prod() ** (252 / len(y)) - 1),
                             invested=float((c.market_value / c.equity).reindex(y.index).mean())))
        eq = pd.concat([pd.Series([1e9], index=[pd.Timestamp('1999-12-31')]), c.equity])
        years[(version, name)] = eq.resample('YE').last().pct_change().dropna()
H, F, R = pd.DataFrame(head), pd.DataFrame(flow), pd.DataFrame(regs)
Y = pd.DataFrame(years)
Y.index = Y.index.year
for o, n in [(H, 'headline'), (F, 'trade_flow'), (R, 'regimes')]:
    o.to_csv(OUT / f'impact_{n}.csv', index=False)
Y.to_csv(OUT / 'impact_yearly.csv')
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
print(H.round(3).to_string(index=False)); print(F.round(3).to_string(index=False))
print(R.pivot_table(index=['version', 'system'], columns='regime', values=['ann_return', 'invested']).round(3).to_string())
print((Y * 100).round(1).to_string())
for v in ('unrestricted', 'realistic'):
    d = Y[(v, '+monthly A35')] - Y[(v, 'V0')]
    print(v, 'A35 better years', int((d > 0).sum()), 'of', len(d), 'median diff pp', round(d.median() * 100, 1), 'worst', d.idxmin(), round(d.min() * 100, 1), 'best', d.idxmax(), round(d.max() * 100, 1))
