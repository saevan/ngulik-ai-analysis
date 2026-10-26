"""Post-hoc robustness of the step-5 passing cell G2|X0|A35 (stock ER20 >= 0.3 at the month-end on top of F_mom, added
monthly entry, allowance 35%): stock-ER threshold 0.2..0.4 x allowance 25/35/45%, unrestricted and realistic; holdout
1995-03..1999 (unrestricted) for V0 and the 0.3 / 0.35 cells. Writes monthly_trend_entry_results/er_gate_robustness.csv"""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_breakout_er import efficiency_ratio
from backtest_open_next import stats
from monthly_trend_entry import trend, PER
import monthly_add_er_gate as m5

BASE = m5.BASE
G = m5.G


def job(a):
    thr, A, version = a
    fr, start = G['fr'], '2000-01-01'
    k = rc.kw(BASE, 'B')
    if version == 'realistic':
        k.update(liq_cap=.25, gate_dates=G['gate'])
    if version == 'holdout':
        fr, start = {t: g for t, f in fr.items() if len(g := f[f['Date/Time'] <= '1999-12-31'].reset_index(drop=True))}, '1995-03-01'
    if thr is not None:
        k.update(extra_signal_fn=lambda f: m5.me(f) & f.tradable.to_numpy(bool) & trend('F_mom', f) & (efficiency_ratio(f.Close, 20) >= thr).fillna(False).to_numpy(bool),
                 extra_exit_signal_fn=lambda f: m5.me(f) & ~trend('F_mom', f), extra_size_div=10, extra_first=True, extra_max_frac=A)
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(fr, start=start, **k)
    if version != 'holdout':
        c = c.loc[:'2025-08-15']
    s = stats(c, t)
    row = dict(er_thr=thr, allowance=A, version=version, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], win_rate=s['wr'])
    if version != 'holdout':
        eq = c.equity
        for pn, (a_, b_) in PER.items():
            x, prev = eq.loc[a_:b_], eq.loc[:str(int(a_) - 1)]
            st0 = prev.iloc[-1] if len(prev) else 1e9
            y = (x.index[-1] - (prev.index[-1] if len(prev) else x.index[0])).days / 365.25
            row[f'cagr_{pn}'] = float((x.iloc[-1] / st0) ** (1 / y) - 1)
    return row


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    jobs = [(None, None, v) for v in ('unrestricted', 'realistic', 'holdout')]
    jobs += [(thr, A, v) for thr in (.2, .25, .3, .35, .4) for A in (.25, .35, .45) for v in ('unrestricted', 'realistic')]
    jobs += [(thr, .35, 'holdout') for thr in (.25, .3, .35)]
    with Pool(4) as p:
        D = pd.DataFrame(p.map(job, jobs, chunksize=1))
    D.to_csv(m5.OUT / 'er_gate_robustness.csv', index=False)
    U = D[D.version == 'unrestricted'].pivot_table(index='er_thr', columns='allowance', values=['cagr', 'mdd'])
    R = D[D.version == 'realistic'].pivot_table(index='er_thr', columns='allowance', values=['cagr', 'mdd', 'records'])
    pd.set_option('display.width', 250)
    print(D[D.er_thr.isna()].round(3).to_string(index=False))
    print('realistic\n', R.round(3).to_string()); print('unrestricted\n', U.round(3).to_string())
    print(D[D.version == 'holdout'].round(3).to_string(index=False))
    sub = D[(D.version == 'realistic') & D.er_thr.notna()]
    v0 = D[(D.version == 'realistic') & D.er_thr.isna()].iloc[0]
    print('realistic cells >= V0 CAGR:', int((sub.cagr >= v0.cagr).sum()), 'of', len(sub), '| subperiods >= V0 (median):',
          sub.apply(lambda r: sum(r[f'cagr_{p}'] >= v0[f'cagr_{p}'] for p in PER), axis=1).median())
