"""V2 vs Swinger ideal by each stock's OWN ER (30 Oct 2026, descriptive).
1. Per-trade quality by the stock's ER20 at the previous Close before entry (<0.2, 0.2-0.3, 0.3-0.5, >=0.5).
2. Where the money is made while holding: every position-day's P&L (marked at Closes) attributed to the stock's ER20 at
   the PREVIOUS Close (state known before the day; using the same day's ER would be circular); per class: share of total P&L, share of position-days and the capital-weighted daily return.
Scenario B, 2000-01-01..2025-08-15, V2 realistic / unrestricted. Writes quality_vs_swinger_results/v2_by_stock_er*.csv"""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from backtest_breakout_er import efficiency_ratio
import wr_gap_v1 as w

G = w.G
st, _ = engine.load_data('stocks')
G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
YRS = (pd.Timestamp('2025-08-15') - pd.Timestamp('2000-01-01')).days / 365.25
ER = {t: pd.Series(efficiency_ratio(f.Close, 20).to_numpy(), index=f['Date/Time']) for t, f in G['fr'].items()}
CL = {t: f.set_index('Date/Time').Close for t, f in G['fr'].items()}
BINS, LAB = [-1, .2, .3, .5, 2], ['<0.2', '0.2-0.3', '0.3-0.5', '>=0.5']
S = {}
with np.errstate(invalid='ignore', divide='ignore'):
    for v in ('realistic', 'unrestricted'):
        S[f'V2 {v}'] = run(G['fr'], start='2000-01-01', **dict(w.kw(v, True, None), failed_exit=None))[1]
sw = run_portfolio(G['fr'], 'afl_ideal', slip=.0025)[1]
sw = sw.rename(columns={'quantity': 'q', 'entry_cost': 'notional'})
sw['kind'] = 'swinger'
S['Swinger ideal'] = sw
q_rows, d_rows = [], []
for name, t in S.items():
    t = t.copy()
    t['entry_date'] = pd.to_datetime(t.entry_date)
    t['exit_date'] = pd.to_datetime(t.exit_date)
    t = t[t.entry_date <= '2025-08-15']
    t['er_entry'] = [ER[r.ticker].shift(1).get(r.entry_date, np.nan) for r in t.itertuples()]
    t['er_cls'] = pd.cut(t.er_entry, BINS, labels=LAB)
    for kd in (['all'] + (['main', 'extra'] if name != 'Swinger ideal' else [])):
        x0 = t if kd == 'all' else t[t.kind == kd]
        for g, x in x0.groupby('er_cls', observed=False):
            r = x.net_return
            wn = r > 0
            q_rows.append(dict(system=name, kind=kd, er_at_entry=g, trades_per_year=len(x) / YRS, win_rate=wn.mean() if len(x) else np.nan,
                               expectancy=r.mean() if len(x) else np.nan, avg_loss=r[~wn].mean() if (~wn).any() else np.nan,
                               e_R=r.mean() / -r[~wn].mean() if (~wn).any() and len(x) else np.nan, mean_bars=x.bars.mean() if len(x) else np.nan))
    # daily P&L by the stock's ER class on each held day
    pnl = {c: 0. for c in LAB}; days = {c: 0 for c in LAB}; base = {c: 0. for c in LAB}
    for r in t.itertuples():
        c = CL[r.ticker].loc[r.entry_date:r.exit_date]
        if len(c) < 2:
            continue
        vals = r.q * c.to_numpy()
        p = np.empty(len(c)); p[0] = vals[0] - r.notional; p[1:-1] = np.diff(vals)[:-1]; p[-1] = (r.notional + r.pnl) - vals[-2]
        prevv = np.r_[r.notional, vals[:-1]]
        e = pd.cut(ER[r.ticker].shift(1).reindex(c.index), BINS, labels=LAB).astype(str).to_numpy()   # state known before the day
        for k in LAB:
            m = e == k
            pnl[k] += p[m].sum(); days[k] += int(m.sum()); base[k] += prevv[m].sum()
    tot = sum(pnl.values())
    for k in LAB:
        d_rows.append(dict(system=name, er_on_day=k, share_of_pnl=pnl[k] / tot, share_of_position_days=days[k] / sum(days.values()),
                           daily_return_on_capital_bps=pnl[k] / base[k] * 1e4 if base[k] else np.nan))
Q, Dd = pd.DataFrame(q_rows), pd.DataFrame(d_rows)
Q.to_csv('quality_vs_swinger_results/v2_by_stock_er_trades.csv', index=False)
Dd.to_csv('quality_vs_swinger_results/v2_by_stock_er_days.csv', index=False)
pd.set_option('display.width', 220); pd.set_option('display.max_rows', 100)
print(Q.round(3).to_string(index=False)); print(Dd.round(3).to_string(index=False))
