"""Is V0 + monthly F_mom entry with stock ER20 >= 0.3 (allowance 35%, 10% orders; step-5 cell G2|X0|A35) better than V0?
Scenario B, 2000-01-01..2025-08-15, unrestricted and realistic (26 Oct 2026). Paired comparison: headline, risk-adjusted
(daily Sharpe-like ratio, CAGR/|MDD|), calendar years, monthly return difference with Newey-West t (lag 6), subperiods.
Writes monthly_trend_entry_results/g2_vs_v0.csv, g2_vs_v0_yearly.csv"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_breakout_er import efficiency_ratio
from backtest_open_next import stats
from monthly_trend_entry import trend, PER

st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
ME = set(cal.groupby(cal.dt.to_period('M')).max())
me = lambda f: f['Date/Time'].isin(ME).to_numpy(bool)
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
gate = {t: pit[t] & stale[t] for t in fr}
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
EXTRA = dict(extra_signal_fn=lambda f: me(f) & f.tradable.to_numpy(bool) & trend('F_mom', f) & (efficiency_ratio(f.Close, 20) >= .3).fillna(False).to_numpy(bool),
             extra_exit_signal_fn=lambda f: me(f) & ~trend('F_mom', f), extra_size_div=10, extra_first=True, extra_max_frac=.35)
rows, Y = [], {}
for version in ('unrestricted', 'realistic'):
    k = rc.kw(BASE, 'B')
    if version == 'realistic':
        k.update(liq_cap=.25, gate_dates=gate)
    eqs = {}
    for name, kk in (('V0', k), ('V0+monthly_stockER', dict(k, **EXTRA))):
        with np.errstate(invalid='ignore', divide='ignore'):
            c, t = run(fr, start='2000-01-01', **kk)
        c = c.loc[:'2025-08-15']
        s = stats(c, t)
        dr = c.equity.pct_change().dropna()
        eqs[name] = c.equity
        row = dict(version=version, system=name, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], win_rate=s['wr'], invested=s['invested'],
                   ann_vol=dr.std() * np.sqrt(252), sharpe_like=dr.mean() / dr.std() * np.sqrt(252), cagr_over_mdd=s['cagr'] / -s['mdd'])
        eq = c.equity
        for pn, (a_, b_) in PER.items():
            x, prev = eq.loc[a_:b_], eq.loc[:str(int(a_) - 1)]
            st0 = prev.iloc[-1] if len(prev) else 1e9
            y = (x.index[-1] - (prev.index[-1] if len(prev) else x.index[0])).days / 365.25
            row[f'cagr_{pn}'] = float((x.iloc[-1] / st0) ** (1 / y) - 1)
        rows.append(row)
        e = pd.concat([pd.Series([1e9], index=[pd.Timestamp('1999-12-31')]), eq])
        Y[(version, name)] = e.resample('YE').last().pct_change().dropna()
    m0 = eqs['V0'].resample('ME').last().pct_change().dropna()
    m1 = eqs['V0+monthly_stockER'].resample('ME').last().pct_change().dropna()
    d = (np.log1p(m1) - np.log1p(m0)).dropna()
    mu, se, _ = nw(d.to_numpy(), 6)
    rows.append(dict(version=version, system='difference', monthly_log_diff_mean=mu, t_nw=mu / se, months_better=float((d > 0).mean()),
                     years_better=int(((Y[(version, 'V0+monthly_stockER')] - Y[(version, 'V0')]) > 0).sum()), years=len(Y[(version, 'V0')])))
D = pd.DataFrame(rows)
D.to_csv(ROOT / 'monthly_trend_entry_results' / 'g2_vs_v0.csv', index=False)
YY = pd.DataFrame(Y)
YY.index = YY.index.year
YY.to_csv(ROOT / 'monthly_trend_entry_results' / 'g2_vs_v0_yearly.csv')
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
print(D.round(4).to_string(index=False))
print((YY * 100).round(1).to_string())
