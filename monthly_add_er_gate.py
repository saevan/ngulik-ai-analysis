"""Step 5 of monthly_trend_entry_results/PLAN.md: ER conditions on the added monthly F_mom entry (market ER20 and/or stock
ER20 >= 0.3 at the month-end Close; optional exit when the market ER20 < 0.3 at a month-end). Scenario B, 2000-2025.
Writes monthly_trend_entry_results/er_gate.csv, er_gate_summary.csv, er_gate_persistence.csv"""
import zlib
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_breakout_er import efficiency_ratio
from backtest_open_next import stats
from analyze_portfolio_regimes import regime_proxy
from monthly_trend_entry import trend, PER

OUT = Path(__file__).resolve().parent / 'monthly_trend_entry_results'
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
G = {}


def me(f):
    return f['Date/Time'].isin(G['me']).to_numpy(bool)


def mkt_trend(f):
    return f['Date/Time'].isin(G['mkt_trend']).to_numpy(bool)


def stock_er(f):
    return (efficiency_ratio(f.Close, 20) >= .3).fillna(False).to_numpy(bool)


def job(a):
    label, version, gate_, exit_, A, seed = a
    k = rc.kw(BASE, 'B')
    if version == 'realistic':
        k.update(liq_cap=.25, gate_dates=G['gate'])
    if gate_ is not None:
        def entry(f):
            s = me(f) & f.tradable.to_numpy(bool)
            if seed is None:
                s &= trend('F_mom', f)
            if gate_ in ('G1', 'G3'):
                s &= mkt_trend(f)
            if gate_ in ('G2', 'G3'):
                s &= stock_er(f)
            return s
        if seed is None:
            ex = (lambda f: me(f) & (~trend('F_mom', f) | ~mkt_trend(f))) if exit_ == 'X1' else (lambda f: me(f) & ~trend('F_mom', f))
        else:
            ex = me
        k.update(extra_signal_fn=entry, extra_exit_signal_fn=ex, extra_size_div=10, extra_first=True, extra_max_frac=A)
        if seed is not None:
            k['extra_priority'] = lambda f: np.random.default_rng([seed, zlib.crc32(str(f['Ticker'].iloc[0]).encode())]).random(len(f))
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(G['fr'], start='2000-01-01', **k)
    c = c.loc[:'2025-08-15']
    if 'kind' not in t:
        t['kind'] = 'main'
    s = stats(c, t)
    row = dict(label=label, version=version, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], win_rate=s['wr'], expectancy=s['mean'],
               invested=s['invested'], main_trades=int((t.kind == 'main').sum()), extra_trades=int((t.kind == 'extra').sum()),
               extra_wr=(t[t.kind == 'extra'].net_return > 0).mean() if (t.kind == 'extra').any() else np.nan,
               extra_e=t[t.kind == 'extra'].net_return.mean() if (t.kind == 'extra').any() else np.nan)
    eq = c.equity
    for pn, (a_, b_) in PER.items():
        x, prev = eq.loc[a_:b_], eq.loc[:str(int(a_) - 1)]
        st0 = prev.iloc[-1] if len(prev) else 1e9
        y = (x.index[-1] - (prev.index[-1] if len(prev) else x.index[0])).days / 365.25
        row[f'cagr_{pn}'] = float((x.iloc[-1] / st0) ** (1 / y) - 1)
    dr = eq.pct_change().dropna()
    g = G['lab'].reindex(dr.index)
    for rg in ('uptrend', 'sideways', 'downtrend'):
        y = dr[g == rg]
        row[f'ann_{rg}'] = float((1 + y).prod() ** (252 / len(y)) - 1)
    return row


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    rp = regime_proxy(st)
    G['lab'] = rp['regime']
    G['mkt_trend'] = set(rp.index[rp.er >= .3])          # ER20 of the market proxy at that Close (unshifted)
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    # how well does the month-end market ER predict trending days next month?
    lab = rp['regime'].loc['2000':'2025-08-15']
    mon = lab.index.to_period('M')
    trend_share = (lab != 'sideways').groupby(mon).mean()
    me_er = rp.er.reindex(sorted(G['me'])).dropna()
    me_state = pd.Series(me_er.to_numpy() >= .3, index=me_er.index.to_period('M') + 1)
    j = pd.DataFrame({'next_month_trend_share': trend_share, 'month_end_trending': me_state.reindex(trend_share.index)}).dropna()
    Pm = j.groupby('month_end_trending').next_month_trend_share.agg(['mean', 'size']).reset_index()
    Pm['unconditional'] = (lab != 'sideways').mean()
    Pm.to_csv(OUT / 'er_gate_persistence.csv', index=False)
    jobs = [('V0', v, None, None, None, None) for v in ('unrestricted', 'realistic')]
    for A in (.35, .5):
        for g_ in ('G0', 'G1', 'G2', 'G3'):
            for x in ('X0', 'X1'):
                jobs += [(f'{g_}|{x}|A{int(A * 100)}', v, g_, x, A, None) for v in ('unrestricted', 'realistic')]
    for seed in (1, 2, 3):
        jobs += [(f'random{seed}|G1|A35', v, 'G1', 'X0', .35, seed) for v in ('unrestricted', 'realistic')]
    with Pool(4) as p:
        D = pd.DataFrame(p.map(job, jobs, chunksize=1))
    D.to_csv(OUT / 'er_gate.csv', index=False)
    U, R = D[D.version == 'unrestricted'].set_index('label'), D[D.version == 'realistic'].set_index('label')
    v0u, v0r = U.loc['V0'], R.loc['V0']
    S = []
    for l in [x for x in R.index if x[:2] in ('G0', 'G1', 'G2', 'G3')]:
        g_, x, A = l.split('|')
        base = f'G0|{x}|{A}'
        r, u, rb, ub = R.loc[l], U.loc[l], R.loc[base], U.loc[base]
        ctl = R.loc[[y for y in R.index if y.startswith('random')], 'cagr'].max()
        S.append(dict(label=l, cagr_real=r.cagr, mdd_real=r.mdd, records_real=r.records, wr_real=r.win_rate, cagr_unres=u.cagr, mdd_unres=u.mdd,
                      records_unres=u.records, wr_unres=u.win_rate, extra_trades_real=r.extra_trades, extra_wr_real=r.extra_wr, extra_e_real=r.extra_e,
                      main_kept_real=r.main_trades / v0r.main_trades, main_kept_unres=u.main_trades / v0u.main_trades, invested_real=r.invested,
                      up_real=r.ann_uptrend, side_real=r.ann_sideways, down_real=r.ann_downtrend,
                      sub_ge_V0=sum(r[f'cagr_{p}'] >= v0r[f'cagr_{p}'] for p in PER), ctl_random_best=ctl,
                      er_helps=(g_ in ('G1', 'G3')) and (r.cagr > rb.cagr) and (r.mdd >= rb.mdd - .02) and (u.cagr > ub.cagr) and (u.mdd >= ub.mdd - .02)))
    S = pd.DataFrame(S)
    S['candidate'] = (S.cagr_real >= v0r.cagr) & (S.mdd_real >= -.49) & (S.records_real >= v0r.records) & (S.sub_ge_V0 >= 3) & \
                     (S.cagr_unres >= v0u.cagr - .05) & (S.mdd_unres >= -.29) & (S.cagr_real > S.ctl_random_best) & \
                     (S.wr_real > v0r.win_rate) & (S.wr_unres > v0u.win_rate) & (S.main_kept_real >= .7) & (S.main_kept_unres >= .7)
    S.to_csv(OUT / 'er_gate_summary.csv', index=False)
    pd.set_option('display.width', 280); pd.set_option('display.max_columns', 40)
    print(Pm.round(3).to_string(index=False))
    print(S.round(3).to_string(index=False))
    print(D[D.label.isin(['V0']) | D.label.str.startswith('random')][['label', 'version', 'cagr', 'records', 'mdd', 'win_rate', 'ann_uptrend', 'ann_sideways', 'ann_downtrend']].round(3).to_string(index=False))
