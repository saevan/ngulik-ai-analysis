"""Small vs large sideways (plan: sideways_size_results/PLAN.md). Writes sideways_size_results/*.csv"""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
import wr_gap_v1 as w

OUT = 'sideways_size_results'
G = w.G
st, _ = engine.load_data('stocks')
G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
YRS = (pd.Timestamp('2025-08-15') - pd.Timestamp('2000-01-01')).days / 365.25
PB, PL = [-1, .10, .20, .40, 99], ['<10%', '10-20%', '20-40%', '>=40%']
AB, AL = [-1, 4, 6, 8, 999], ['<4 ATR', '4-6 ATR', '6-8 ATR', '>=8 ATR']


def atr(h, l, c, n=14):
    tr = h - l
    tr[1:] = np.maximum(tr[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


frames, state = [], {}
for t, f in G['fr'].items():
    f = f[f.tradable].reset_index(drop=True)
    n = len(f)
    if n < 300:
        continue
    o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close'])
    d = f['Date/Time']
    A = atr(h.copy(), l, c)
    H = pd.Series(h).rolling(20).max().to_numpy()
    L = pd.Series(l).rolling(20).min().to_numpy()
    cc = pd.Series(c)
    er = ((cc - cc.shift(20)).abs() / cc.diff().abs().rolling(20).sum()).to_numpy()
    wp, wa = H / L - 1, (H - L) / A
    # what follows (20 bars)
    fwd = np.log(np.r_[c[20:], np.full(20, np.nan)] / c)
    idx = np.arange(n)[:, None] + np.arange(1, 21)[None, :]
    valid = idx[:, -1] < n
    idx = np.where(valid[:, None], idx, 0)
    up = (h[idx] > (H + A)[:, None]); dn = (l[idx] < (L - A)[:, None])
    fu = np.where(up.any(1), up.argmax(1), 99); fd = np.where(dn.any(1), dn.argmax(1), 99)
    side = np.where(~valid, 'na', np.where((fu < fd), 'up first', np.where(fd < fu, 'down first', np.where(fu == 99, 'neither', 'same bar'))))
    er20 = np.r_[er[20:], np.full(20, np.nan)]
    wp20 = np.r_[wp[20:], np.full(20, np.nan)]
    elig = d.isin(pit[t] & stale[t]).to_numpy() & (d >= '2000-01-01').to_numpy() & (d <= '2025-08-15').to_numpy()
    frames.append(pd.DataFrame({'ticker': t, 'date': d, 'elig': elig, 'er': er, 'wp': wp, 'wa': wa, 'fwd_abs': np.abs(fwd), 'side': side,
                                'er20': er20, 'wp20': wp20}))
    state[t] = pd.DataFrame({'er_prev': pd.Series(er).shift(1).to_numpy(), 'wp_prev': pd.Series(wp).shift(1).to_numpy()}, index=d)
X = pd.concat(frames, ignore_index=True)
X = X[X.elig & np.isfinite(X.er) & np.isfinite(X.wp)]
X['grp'] = np.where(X.er < .2, 'choppy', np.where(X.er >= .3, 'trending', 'mid'))
X['pb'] = pd.cut(X.wp, PB, labels=PL)
X['ab'] = pd.cut(X.wa, AB, labels=AL)
# A. distribution
qa = X.groupby('grp').agg(days=('wp', 'size'), wp_p10=('wp', lambda s: s.quantile(.1)), wp_median=('wp', 'median'), wp_p90=('wp', lambda s: s.quantile(.9)),
                          wa_p10=('wa', lambda s: s.quantile(.1)), wa_median=('wa', 'median'), wa_p90=('wa', lambda s: s.quantile(.9)))
sh_p = pd.crosstab(X.grp, X.pb, normalize='index')
sh_a = pd.crosstab(X.grp, X.ab, normalize='index')
hist = pd.cut(X[X.grp == 'choppy'].wp, np.arange(0, 1.05, .025)).value_counts(normalize=True).sort_index()
qa.to_csv(f'{OUT}/a_quantiles.csv'); sh_p.to_csv(f'{OUT}/a_share_pct.csv'); sh_a.to_csv(f'{OUT}/a_share_atr.csv'); hist.to_csv(f'{OUT}/a_hist_choppy.csv')
# B. persistence and what follows (choppy days)
C = X[X.grp == 'choppy'].copy()
C['still_choppy_20'] = C.er20 < .2
C['same_bucket_20'] = pd.cut(C.wp20, PB, labels=PL).astype(str) == C.pb.astype(str)
B = C.groupby('pb', observed=True).agg(days=('wp', 'size'), still_choppy_20=('still_choppy_20', 'mean'), same_bucket_20=('same_bucket_20', 'mean'),
                                         fwd20_abs_ret=('fwd_abs', 'mean'))
B = B.join(pd.crosstab(C.pb, C.side, normalize='index'))
B.to_csv(f'{OUT}/b_follow.csv')
# C. who earns where
S = {}
with np.errstate(invalid='ignore', divide='ignore'):
    S['V2 realistic'] = run(G['fr'], start='2000-01-01', **dict(w.kw('realistic', True, None), failed_exit=None))[1]
sw = run_portfolio(G['fr'], 'afl_ideal', slip=.0025)[1].rename(columns={'quantity': 'q', 'entry_cost': 'notional'})
sw['kind'] = 'swinger'
S['Swinger ideal'] = sw
CL = {t: f.set_index('Date/Time').Close for t, f in G['fr'].items()}
rows_t, rows_d = [], []
for name, t in S.items():
    t = t.copy()
    t['entry_date'], t['exit_date'] = pd.to_datetime(t.entry_date), pd.to_datetime(t.exit_date)
    t = t[(t.entry_date <= '2025-08-15') & t.ticker.isin(state)]
    sp = [state[r.ticker].reindex([r.entry_date]).iloc[0] for r in t.itertuples()]
    t['er_prev'] = [s.er_prev for s in sp]; t['wp_prev'] = [s.wp_prev for s in sp]
    ch = t[t.er_prev < .2].copy()
    ch['pb'] = pd.cut(ch.wp_prev, PB, labels=PL)
    for g, x in ch.groupby('pb', observed=False):
        r = x.net_return
        rows_t.append(dict(system=name, width_at_entry=g, trades_per_year=len(x) / YRS, win_rate=(r > 0).mean() if len(x) else np.nan,
                           expectancy=r.mean() if len(x) else np.nan, mean_bars=x.bars.mean() if len(x) else np.nan))
    pnl = {k: 0. for k in PL + ['not choppy']}; base = dict(pnl); days = {k: 0 for k in pnl}
    for r in t.itertuples():
        c = CL[r.ticker].loc[r.entry_date:r.exit_date]
        if len(c) < 2:
            continue
        vals = r.q * c.to_numpy()
        p = np.empty(len(c)); p[0] = vals[0] - r.notional; p[1:-1] = np.diff(vals)[:-1]; p[-1] = (r.notional + r.pnl) - vals[-2]
        prevv = np.r_[r.notional, vals[:-1]]
        sdf = state[r.ticker].reindex(c.index)
        lab = np.where(sdf.er_prev.to_numpy() < .2, pd.cut(sdf.wp_prev, PB, labels=PL).astype(str).to_numpy(), 'not choppy')
        for k in pnl:
            m = lab == k
            pnl[k] += p[m].sum(); base[k] += prevv[m].sum(); days[k] += int(m.sum())
    tot, td = sum(pnl.values()), sum(days.values())
    for k in pnl:
        rows_d.append(dict(system=name, state_prev_day=k, share_of_position_days=days[k] / td, share_of_pnl=pnl[k] / tot,
                           daily_return_bps=pnl[k] / base[k] * 1e4 if base[k] else np.nan))
Ct, Cd = pd.DataFrame(rows_t), pd.DataFrame(rows_d)
Ct.to_csv(f'{OUT}/c_trades.csv', index=False); Cd.to_csv(f'{OUT}/c_days.csv', index=False)
pd.set_option('display.width', 220)
print(qa.round(3).to_string()); print(sh_p.round(3).to_string()); print(sh_a.round(3).to_string())
print(hist.round(3).to_string())
print(B.round(3).to_string()); print(Ct.round(3).to_string(index=False)); print(Cd.round(3).to_string(index=False))
