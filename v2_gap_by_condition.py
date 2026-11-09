"""In which market conditions does Swinger ideal trade while V2 does not? (plan addendum in v2_gap_results/PLAN.md)."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from analyze_portfolio_regimes import regime_proxy
import wr_gap_v1 as w

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'v2_gap_results'
A, B = '2000-01-01', '2025-08-15'
YRS = (pd.Timestamp(B) - pd.Timestamp(A)).days / 365.25
G = w.G
st, _ = engine.load_data('stocks')
G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
rp = regime_proxy(st)
lab = rp['regime']
brk = (rp.proxy <= rp.proxy.rolling(20).min()).shift(1, fill_value=False)   # yesterday's proxy Close was a new 20-day low
S = {}
with np.errstate(invalid='ignore', divide='ignore'):
    for v in ('realistic', 'unrestricted'):
        S[f'V2 {v}'] = run(G['fr'], start=A, **dict(w.kw(v, True, None), failed_exit=None))
    c, t, _ = run_portfolio(G['fr'], 'afl_ideal', slip=.0025)
    S['Swinger ideal'] = (c, t)
for k, (c, t) in S.items():
    c = c.loc[:B]; t = t[pd.to_datetime(t.entry_date) <= B].copy()
    t['entry_date'] = pd.to_datetime(t.entry_date); t['exit_date'] = pd.to_datetime(t.exit_date)
    S[k] = (c, t)
FP = pd.read_csv(ROOT / 'swinger_fingerprint_results' / 'trades.csv.gz', parse_dates=['entry_date'])
sw = S['Swinger ideal'][1].merge(FP[['ticker', 'entry_date', 'c2c_net', 'stock_er20', 'vs_sma30']], on=['ticker', 'entry_date'], how='left')
assert sw.c2c_net.notna().all()
sw['condition'] = lab.reindex(sw.entry_date).to_numpy(); sw['breakdown'] = brk.reindex(sw.entry_date).fillna(False).to_numpy()


def cond_masks(idx):
    l = lab.reindex(idx); b = brk.reindex(idx).fillna(False)
    return {'uptrend': (l == 'uptrend').to_numpy(), 'sideways': (l == 'sideways').to_numpy(), 'downtrend': (l == 'downtrend').to_numpy(),
            'breakdown': b.to_numpy(bool), 'all': np.ones(len(idx), bool)}


def held(t):
    out = {}
    for r in t.itertuples():
        d = G['fr'][r.ticker]['Date/Time']
        out.setdefault(r.ticker, set()).update(d[(d >= r.entry_date) & (d <= r.exit_date)].tolist())
    return out


R1, R2, R3 = [], [], []
cs = S['Swinger ideal'][0]
for v in ('V2 realistic', 'V2 unrestricted'):
    cv, tv = S[v]
    idx = cs.index.intersection(cv.index)
    inv_s = (cs.market_value / cs.equity).reindex(idx); inv_v = (cv.market_value / cv.equity).reindex(idx)
    m = cond_masks(idx)
    tv = tv.copy(); tv['condition'] = lab.reindex(tv.entry_date).to_numpy(); tv['breakdown'] = brk.reindex(tv.entry_date).fillna(False).to_numpy()
    for g, mk in m.items():
        sel_s = sw if g == 'all' else (sw[sw.breakdown] if g == 'breakdown' else sw[sw.condition == g])
        sel_v = tv if g == 'all' else (tv[tv.breakdown] if g == 'breakdown' else tv[tv.condition == g])
        R1.append(dict(v2=v, condition=g, share_days=mk.mean(), swinger_trades_per_year=len(sel_s) / YRS, v2_trades_per_year=len(sel_v) / YRS,
                       swinger_invested=inv_s[mk].mean(), v2_invested=inv_v[mk].mean(), days_swinger_75_v2_below_25=((inv_s >= .75) & (inv_v < .25))[mk].mean()))
    hv = held(tv)
    cov = []
    for r in sw.itertuples():
        d = G['fr'][r.ticker]['Date/Time']; days = d[(d >= r.entry_date) & (d <= r.exit_date)]
        cov.append(any(x in hv.get(r.ticker, set()) for x in days))
    x = sw.assign(covered=cov)
    x['stock'] = np.where(x.stock_er20 < .2, 'stock ER20 < 0.2', 'stock ER20 >= 0.2')
    x['sma30'] = np.where(x.vs_sma30 > 0, 'above SMA30', 'below SMA30')
    for g in ('uptrend', 'sideways', 'downtrend', 'breakdown', 'all'):
        y = x if g == 'all' else (x[x.breakdown] if g == 'breakdown' else x[x.condition == g])
        for cv_, z in y.groupby('covered'):
            R2.append(dict(v2=v, condition=g, covered_by_v2=cv_, trades_per_year=len(z) / YRS, share=len(z) / len(y), win_rate=(z.net_return > 0).mean(),
                           avg_return=z.net_return.mean(), move_c2c_net=z.c2c_net.mean(), move_c2c_win_rate=(z.c2c_net > 0).mean()))
        u = y[~y.covered]
        for col in ('stock', 'sma30'):
            for k_, z in u.groupby(col):
                R3.append(dict(v2=v, condition=g, split=col, group=k_, trades_per_year=len(z) / YRS, share_of_uncovered=len(z) / len(u),
                               avg_return=z.net_return.mean(), move_c2c_net=z.c2c_net.mean(), move_c2c_win_rate=(z.c2c_net > 0).mean()))
D1, D2, D3 = pd.DataFrame(R1), pd.DataFrame(R2), pd.DataFrame(R3)
D1.to_csv(OUT / 'by_condition_activity.csv', index=False); D2.to_csv(OUT / 'by_condition_uncovered.csv', index=False); D3.to_csv(OUT / 'by_condition_uncovered_split.csv', index=False)
pd.set_option('display.width', 250)
for X in (D1, D2, D3):
    print(X[X.v2 == 'V2 realistic'].round(3).to_string(index=False))
