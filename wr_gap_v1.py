"""What keeps our win rate below Swinger ideal? (plan: wr_gap_v1_results/PLAN.md). Part A: WR bridge on the trades of V1
and Swinger ideal (day-1 leg, holding leg, exit-fill leg). Part B: close-confirmed breakout bought at the Close.
Scenario B, 2000-01-01..2025-08-15. Writes wr_gap_v1_results/*.csv"""
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_breakout_er import efficiency_ratio
from backtest_prototype_swinger import run_portfolio
from backtest_open_next import stats
from monthly_trend_entry import trend, PER

OUT = Path(__file__).resolve().parent / 'wr_gap_v1_results'
SLIP, COST = .0025, .009
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
G = {}


def me(f):
    return f['Date/Time'].isin(G['me']).to_numpy(bool)


def extra():
    return dict(extra_signal_fn=lambda f: me(f) & f.tradable.to_numpy(bool) & trend('F_mom', f) & (efficiency_ratio(f.Close, 20) >= .3).fillna(False).to_numpy(bool),
                extra_exit_signal_fn=lambda f: me(f) & ~trend('F_mom', f), extra_size_div=10, extra_first=True, extra_max_frac=.35)


def kw(version, monthly=True, close_fill=None):
    k = rc.kw(BASE, 'B')
    if close_fill is not None:
        k.update(entry_mode='close_fill', stop_buffer=close_fill, buffer_grid=False, failed_exit=None)
    if monthly:
        k.update(extra())
    if version == 'realistic':
        k.update(liq_cap=.25, gate_dates=G['gate'])
    return k


def legs_ours(T):
    rows = []
    for r in T.itertuples():
        f = G['fr'][r.ticker]
        d = f['Date/Time'].values
        i, j = int(np.searchsorted(d, np.datetime64(r.entry_date))), int(np.searchsorted(d, np.datetime64(r.exit_date)))
        c = f.Close.values
        fill = r.entry_price / (1 + SLIP)
        close_exit = r.reason.endswith('gapdown_close') or r.reason.startswith('period_end')
        k = j if close_exit else max(i, j - 1)
        rows.append(dict(kind=getattr(r, 'kind', 'main'), reason=r.reason, net=r.net_return, day1=c[i] / fill - 1, hold=c[k] / c[i] - 1,
                         exit_leg=r.reference_exit_price / c[k] - 1))
    return pd.DataFrame(rows)


def legs_swinger(T):
    rows = []
    for r in T.itertuples():
        f = G['fr'][r.ticker]
        d = f['Date/Time'].values
        i, j = int(np.searchsorted(d, np.datetime64(r.entry_date))), int(np.searchsorted(d, np.datetime64(r.exit_date)))
        c = f.Close.values
        lin, lout = r.entry_price / (1 + SLIP), r.exit_price / (1 - SLIP)
        rows.append(dict(kind='swinger', reason=r.reason, net=r.net_return, day1=c[i] / lin - 1, hold=c[j] / c[i] - 1, exit_leg=lout / c[j] - 1,
                         entry_close_exit_level=(lout * (1 - SLIP) * (1 - .0025)) / (c[i] * (1 + SLIP) * (1 + .0015)) - 1,
                         entry_level_exit_close=(c[j] * (1 - SLIP) * (1 - .0025)) / (lin * (1 + SLIP) * (1 + .0015)) - 1))
    return pd.DataFrame(rows)


def summarize(L, system):
    out = []
    for kd, x in [('all', L)] + list(L.groupby('kind')):
        cc = (1 + x.hold) * (1 - COST) - 1
        row = dict(system=system, kind=kd, trades=len(x), wr_as_traded=(x.net > 0).mean(), e_as_traded=x.net.mean(),
                   day1_mean=x.day1.mean(), day1_share_negative=(x.day1 < 0).mean(), hold_mean=x.hold.mean(), hold_median=x.hold.median(),
                   exit_leg_mean=x.exit_leg.mean(), exit_leg_share_negative=(x.exit_leg < 0).mean(), wr_close_to_close=(cc > 0).mean(),
                   e_close_to_close=cc.mean())
        if 'entry_close_exit_level' in x:
            row.update(wr_entry_at_close=(x.entry_close_exit_level > 0).mean(), wr_exit_at_close=(x.entry_level_exit_close > 0).mean())
        out.append(row)
    return out


def job(a):
    label, version, monthly, cf = a
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(G['fr'], start='2000-01-01', **kw(version, monthly, cf))
    c = c.loc[:'2025-08-15']
    s = stats(c, t)
    row = dict(label=label, version=version, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], trades=s['n'], win_rate=s['wr'],
               expectancy=s['mean'], payout=s['payout'], invested=s['invested'])
    if 'kind' in t:
        x = t[t.kind == 'main'].net_return
        row.update(breakout_wr=(x > 0).mean(), breakout_e=x.mean(), breakout_trades=len(x))
    eq = c.equity
    for pn, (a_, b_) in PER.items():
        x, prev = eq.loc[a_:b_], eq.loc[:str(int(a_) - 1)]
        st0 = prev.iloc[-1] if len(prev) else 1e9
        y = (x.index[-1] - (prev.index[-1] if len(prev) else x.index[0])).days / 365.25
        row[f'cagr_{pn}'] = float((x.iloc[-1] / st0) ** (1 / y) - 1)
    return row, t


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    jobs = []
    for v in ('unrestricted', 'realistic'):
        jobs += [('V0 buy stop', v, False, None), ('V1 buy stop', v, True, None)]
        for b in (0., .005):
            jobs += [(f'V0 close fill b{b}', v, False, b), (f'V1 close fill b{b}', v, True, b)]
    with Pool(4) as p:
        res = p.map(job, jobs, chunksize=1)
    B = pd.DataFrame([r for r, _ in res])
    B.to_csv(OUT / 'close_fill_test.csv', index=False)
    # Part A on V1 (both versions) and Swinger ideal
    A = []
    for (r, t) in res:
        if r['label'] == 'V1 buy stop':
            A += summarize(legs_ours(t), f"V1 {r['version']}")
        if r['label'] == 'V1 close fill b0.0':
            A += summarize(legs_ours(t), f"V1 close fill {r['version']}")
    c, t, _ = run_portfolio(G['fr'], 'afl_ideal', slip=SLIP)
    A += summarize(legs_swinger(t), 'Swinger ideal')
    A = pd.DataFrame(A)
    A.to_csv(OUT / 'wr_bridge.csv', index=False)
    pd.set_option('display.width', 260); pd.set_option('display.max_columns', 30)
    print(A.round(4).to_string(index=False))
    print(B.round(3).to_string(index=False))
