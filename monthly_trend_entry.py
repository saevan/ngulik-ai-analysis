"""Time element: buy trending stocks at the start of each month (plan: monthly_trend_entry_results/PLAN.md).
Signal at the market's last trading day of the month (Close), bought at the next tradable Open; trend filters, exits and
controls as in the plan. Scenario B. Writes monthly_trend_entry_results/results.csv, summary.csv, trades.csv.gz"""
import sys
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

OUT = Path(__file__).resolve().parent / 'monthly_trend_entry_results'
PER = {'2000-07': ('2000', '2007'), '2008-15': ('2008', '2015'), '2016-20': ('2016', '2020'), '2021-25': ('2021', '2025')}
FILTERS = ['F_sma30', 'F_sma120', 'F_er', 'F_high', 'F_mom']
EXITS = ['X_month', 'X_sys', 'X_both']
G = {}


def trend(name, f):
    c = f.Close
    if name == 'F_sma30':
        ok = c > c.rolling(30).mean()
    elif name == 'F_sma120':
        ok = c > c.rolling(120).mean()
    elif name == 'F_er':
        ok = (efficiency_ratio(c, 20) >= .3) & (c > c.shift(20))
    elif name == 'F_high':
        ok = c >= .95 * c.rolling(120).max()
    elif name == 'F_mom':
        ok = c > c.shift(120)
    else:
        ok = pd.Series(True, index=f.index)
    return ok.fillna(False).to_numpy(bool)


def month_end(f):
    return f['Date/Time'].isin(G['me']).to_numpy(bool)


def make_kw(filt, exit_, size, prio='mom', hold1m=False):
    k = rc.kw(dict(fam='F2', channel=20, er_min=None, exit='cand', failed=None, size_div=size), 'B')
    k['entry_mode'] = 'signal'
    k['signal_fn'] = lambda f: month_end(f) & f.tradable.to_numpy(bool) & trend(filt, f)
    if exit_ == 'X_month':
        k.update(fade=None, sma_len=None)
    if exit_ in ('X_month', 'X_both'):
        k['exit_signal_fn'] = lambda f: month_end(f) & ~trend(filt, f)
    if hold1m:   # control: hold until the next month-end Close, sell next Open
        k.update(fade=None, sma_len=None, exit_signal_fn=month_end)
    if prio != 'mom':
        seed = prio
        k['priority'] = lambda f: np.random.default_rng([seed, zlib.crc32(str(f['Ticker'].iloc[0]).encode())]).random(len(f))
    return k


def job(a):
    label, version, kwargs = a
    k = make_kw(**kwargs)
    fr, start = G['fr'], '2000-01-01'
    if version == 'realistic':
        k.update(liq_cap=.25, gate_dates=G['gate'])
    if version == 'holdout':
        fr, start = {t: g for t, f in fr.items() if len(g := f[f['Date/Time'] <= '1999-12-31'].reset_index(drop=True))}, '1995-03-01'
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(fr, start=start, **k)
    if version != 'holdout':
        c = c.loc[:'2025-08-15']
        t = t[pd.to_datetime(t.entry_date) <= '2025-08-15']
    s = stats(c, t)
    r = t.net_return
    yrs = (c.index[-1] - c.index[0]).days / 365.25
    sums = r.groupby(pd.to_datetime(t.entry_date).dt.to_period('M')).agg(['sum', 'size'])
    rng = np.random.default_rng(zlib.crc32(f'{label}-{version}'.encode()))
    idx = rng.integers(0, len(sums), (2000, len(sums)))
    bm = sums['sum'].to_numpy()[idx].sum(1) / sums['size'].to_numpy()[idx].sum(1)
    row = dict(label=label, version=version, **kwargs, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], trades=s['n'],
               trades_per_year=s['n'] / yrs, win_rate=s['wr'], payout=s['payout'], expectancy=s['mean'],
               e_ci_low=np.percentile(bm, 2.5), e_ci_high=np.percentile(bm, 97.5), e_R=s['mean'] / s['avg_loss'],
               median_trade=s['median'], mean_bars=s['mean_bars'], invested=s['invested'])
    if version != 'holdout':
        eq = c.equity
        for pn, (a_, b_) in PER.items():
            x, prev = eq.loc[a_:b_], eq.loc[:str(int(a_) - 1)]
            st0 = prev.iloc[-1] if len(prev) else 1e9
            y = (x.index[-1] - (prev.index[-1] if len(prev) else x.index[0])).days / 365.25
            row[f'cagr_{pn}'] = float((x.iloc[-1] / st0) ** (1 / y) - 1)
    t = t.assign(label=label, version=version)
    return row, t[['label', 'version', 'ticker', 'entry_date', 'exit_date', 'net_return', 'bars', 'reason']]


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    jobs = []
    for f_ in FILTERS:
        for x in EXITS:
            for s in (4, 10):
                for v in ('unrestricted', 'realistic', 'holdout'):
                    jobs.append((f'{f_}|{x}|s{s}', v, dict(filt=f_, exit_=x, size=s)))
    for v in ('unrestricted', 'realistic'):
        for seed in (1, 2, 3):
            jobs.append((f'C_random{seed}|X_sys|s4', v, dict(filt='none', exit_='X_sys', size=4, prio=seed)))
            jobs.append((f'C_random{seed}|hold1m|s4', v, dict(filt='none', exit_='X_sys', size=4, prio=seed, hold1m=True)))
        jobs.append(('C_mom|X_sys|s4', v, dict(filt='none', exit_='X_sys', size=4)))
    if len(sys.argv) > 1:
        jobs = jobs[:int(sys.argv[1])]
    with Pool(4) as p:
        res = p.map(job, jobs, chunksize=1)
    D = pd.DataFrame([r for r, _ in res])
    D.to_csv(OUT / 'results.csv', index=False)
    pd.concat([t for _, t in res]).to_csv(OUT / 'trades.csv.gz', index=False)
    R = D[D.version == 'realistic'].set_index('label')
    U = D[D.version == 'unrestricted'].set_index('label')
    H = D[D.version == 'holdout'].set_index('label')
    V0 = dict(cagr=.162, mdd=-.444, sub={'2000-07': .287, '2008-15': -.003, '2016-20': .255, '2021-25': .170})
    cells = [l for l in R.index if l.startswith('F_')]
    S = []
    for l in cells:
        r, u = R.loc[l], U.loc[l]
        fam = 'hold1m' if l.split('|')[1] == 'X_month' else 'X_sys'
        ctl = R.loc[[x for x in R.index if x.startswith('C_random') and f'|{fam}|' in x], 'cagr'].max()
        cmom = R.loc['C_mom|X_sys|s4', 'cagr'] if 'C_mom|X_sys|s4' in R.index else np.nan
        sub_ge = sum(r[f'cagr_{p}'] >= V0['sub'][p] for p in PER)
        S.append(dict(label=l, wr=r.win_rate, expectancy=r.expectancy, e_ci_low=r.e_ci_low, e_R=r.e_R, trades_per_year=r.trades_per_year,
                      cagr_real=r.cagr, records_real=r.records, mdd_real=r.mdd, invested_real=r.invested, ctl_random_best=ctl, ctl_mom=cmom,
                      sub_ge_V0=sub_ge, wr_unres=u.win_rate, cagr_unres=u.cagr, records_unres=u.records, mdd_unres=u.mdd,
                      unres_sub_pos=sum(u[f'cagr_{p}'] > 0 for p in PER), cagr_holdout=H.loc[l, 'cagr'] if l in H.index else np.nan,
                      wr_holdout=H.loc[l, 'win_rate'] if l in H.index else np.nan))
    S = pd.DataFrame(S)
    S['passes'] = (S.cagr_real >= V0['cagr']) & (S.mdd_real >= -.49) & (S.cagr_real > S.ctl_random_best) & (S.cagr_real > S.ctl_mom.fillna(-1)) & \
                  (S.sub_ge_V0 >= 3) & (S.unres_sub_pos == 4) & (S.wr >= .45) & (S.e_ci_low > 0)
    S.to_csv(OUT / 'summary.csv', index=False)
    pd.set_option('display.width', 260); pd.set_option('display.max_columns', 40)
    print(S.round(3).to_string(index=False))
    print(D[D.label.str.startswith('C_')][['label', 'version', 'cagr', 'records', 'mdd', 'win_rate', 'expectancy', 'trades_per_year']].round(3).to_string(index=False))
