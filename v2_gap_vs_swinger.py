"""Why is V2 not as strong as Swinger ideal? Descriptive gap analysis (plan: v2_gap_results/PLAN.md)."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from analyze_portfolio_regimes import regime_proxy
import wr_gap_v1 as w

OUT = Path(__file__).resolve().parent / 'v2_gap_results'
A, B = '2000-01-01', '2025-08-15'
YRS = (pd.Timestamp(B) - pd.Timestamp(A)).days / 365.25
G = w.G
st, _ = engine.load_data('stocks')
G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
lab = regime_proxy(st)['regime']
S = {}
with np.errstate(invalid='ignore', divide='ignore'):
    for v in ('realistic', 'unrestricted'):
        c, t = run(G['fr'], start=A, **dict(w.kw(v, True, None), failed_exit=None)); t['amount'] = t.notional
        S[f'V2 {v}'] = (c, t)
    c, t, _ = run_portfolio(G['fr'], 'afl_ideal', slip=.0025); t['amount'] = t.entry_cost
    S['Swinger ideal'] = (c, t)
for k, (c, t) in S.items():
    c = c.loc[:B]; t = t[pd.to_datetime(t.entry_date) <= B].copy()
    t['entry_date'] = pd.to_datetime(t.entry_date); t['exit_date'] = pd.to_datetime(t.exit_date)
    prev = c.equity.shift(1).fillna(1e9)
    t['w'] = t.amount.to_numpy() / prev.reindex(t.entry_date).to_numpy()
    t['regime'] = lab.reindex(t.entry_date).to_numpy()
    S[k] = (c, t)

# A + B + E
rows = []
for k, (c, t) in S.items():
    eq = c.equity; dr = eq.pct_change().dropna(); g_ = lab.reindex(dr.index); inv = c.market_value / c.equity
    free = c.cash / c.equity
    for g in ('uptrend', 'sideways', 'downtrend', 'all'):
        y = dr if g == 'all' else dr[g_ == g]; x = t if g == 'all' else t[t.regime == g]
        idx = y.index
        rows.append(dict(system=k, condition=g, share_days=len(y) / len(dr), ann_return=float((1 + y).prod() ** (252 / len(y)) - 1),
                         CAGR=(eq.iloc[-1] / eq.iloc[0]) ** (365.25 / (eq.index[-1] - eq.index[0]).days) - 1 if g == 'all' else np.nan,
                         trades_per_year=len(x) / YRS, avg_weight=x.w.mean(), weighted_return=(x.w * x.net_return).sum() / x.w.sum(),
                         contribution_per_year=(x.w * x.net_return).sum() / YRS, invested=float(inv.reindex(idx).mean()),
                         positions=float(c.positions.reindex(idx).mean()), days_cash_ge_25pct=float((free.reindex(idx) >= .25).mean()),
                         days_cash_ge_10pct=float((free.reindex(idx) >= .10).mean())))
M = pd.DataFrame(rows); M.to_csv(OUT / 'bridge_and_identity.csv', index=False)
dec = []
for v in ('V2 realistic', 'V2 unrestricted'):
    a = M[(M.system == v) & (M.condition == 'all')].iloc[0]; s = M[(M.system == 'Swinger ideal') & (M.condition == 'all')].iloc[0]
    parts = dict(trades=np.log(s.trades_per_year / a.trades_per_year), weight=np.log(s.avg_weight / a.avg_weight), quality=np.log(s.weighted_return / a.weighted_return))
    tot = np.log(s.contribution_per_year / a.contribution_per_year)
    dec.append(dict(system=v, contribution_v2=a.contribution_per_year, contribution_swinger=s.contribution_per_year, log_gap=tot,
                    **{f'{p}_log': x for p, x in parts.items()}, **{f'{p}_share': x / tot for p, x in parts.items()}))
DEC = pd.DataFrame(dec); DEC.to_csv(OUT / 'identity_decomposition.csv', index=False)

# C: missed big moves
def held_days(t, fr):
    out = {}
    for r in t.itertuples():
        d = fr[r.ticker]['Date/Time']
        out.setdefault(r.ticker, set()).update(d[(d >= r.entry_date) & (d <= r.exit_date)].tolist())
    return out
crow = []
sw = S['Swinger ideal'][1]
for v in ('V2 realistic', 'V2 unrestricted'):
    vt = S[v][1]
    for a_name, a_t, b_name, b_t in [('Swinger ideal', sw, v, vt), (v, vt, 'Swinger ideal', sw)]:
        top = a_t[a_t.net_return >= a_t.net_return.quantile(.95)]
        hb = held_days(b_t, G['fr'])
        shares = []
        for r in top.itertuples():
            d = G['fr'][r.ticker]['Date/Time']; days = d[(d >= r.entry_date) & (d <= r.exit_date)].tolist()
            shares.append(np.mean([x in hb.get(r.ticker, set()) for x in days]) if days else 0.)
        shares = np.array(shares)
        crow.append(dict(top5pct_of=a_name, held_by=b_name, trades=len(top), mean_return=top.net_return.mean(), share_days_held=shares.mean(),
                         share_trades_any_overlap=(shares > 0).mean(), share_trades_half_overlap=(shares >= .5).mean()))
C = pd.DataFrame(crow); C.to_csv(OUT / 'missed_big_moves.csv', index=False)

# D: V2 losses by exit reason
drow = []
for v in ('V2 realistic', 'V2 unrestricted'):
    t = S[v][1].copy()
    t['exit_group'] = np.select([t.reason.str.startswith('sma'), t.reason.str.startswith('fading'), t.reason.str.startswith('extra')],
                                ['Close < SMA30', 'fade 2 ATR', 'monthly module exit'], 'period end')
    L = t[t.net_return <= 0]
    for g, x in t.groupby('exit_group'):
        l = x[x.net_return <= 0]
        drow.append(dict(system=v, exit_group=g, share_trades=len(x) / len(t), win_rate=(x.net_return > 0).mean(), share_of_losers=len(l) / len(L),
                         avg_loss=l.net_return.mean(), avg_loss_bars=l.bars.mean(), losses_below_10pct=(l.net_return < -.10).mean()))
    drow.append(dict(system=v, exit_group='all', share_trades=1., win_rate=(t.net_return > 0).mean(), share_of_losers=1., avg_loss=L.net_return.mean(),
                     avg_loss_bars=L.bars.mean(), losses_below_10pct=(L.net_return < -.10).mean()))
sl = sw[sw.net_return <= 0]
drow.append(dict(system='Swinger ideal', exit_group='all', share_trades=1., win_rate=(sw.net_return > 0).mean(), share_of_losers=1., avg_loss=sl.net_return.mean(),
                 avg_loss_bars=sl.bars.mean(), losses_below_10pct=(sl.net_return < -.10).mean()))
D = pd.DataFrame(drow); D.to_csv(OUT / 'losses_by_exit.csv', index=False)
pd.set_option('display.width', 250)
for X in (M, DEC, C, D):
    print(X.round(3).to_string(index=False))
