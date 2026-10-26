"""Steps 3 and 4 of monthly_trend_entry_results/PLAN.md: ADD a monthly trend-filtered entry next to the unchanged breakout entry
(one portfolio, shared cash and slots). Monthly positions exit only when their filter fails at a month-end Close.
Scenario B, 2000-01-01..2025-08-15, unrestricted and realistic. Writes monthly_trend_entry_results/add_entry.csv,
add_entry_summary.csv"""
import zlib
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_open_next import stats
import monthly_trend_entry as mte
from monthly_trend_entry import trend, PER

OUT = Path(__file__).resolve().parent / 'monthly_trend_entry_results'
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
G = {}


def month_end(f):
    return f['Date/Time'].isin(G['me']).to_numpy(bool)


def slices(eq):
    out = {}
    for pn, (a_, b_) in PER.items():
        x, prev = eq.loc[a_:b_], eq.loc[:str(int(a_) - 1)]
        st0 = prev.iloc[-1] if len(prev) else eq.iloc[0]
        y = (x.index[-1] - (prev.index[-1] if len(prev) else x.index[0])).days / 365.25
        out[f'cagr_{pn}'] = float((x.iloc[-1] / st0) ** (1 / y) - 1)
    return out


def job(a):
    label, version, cfg = a
    k = rc.kw(BASE, 'B')
    if version == 'realistic':
        k.update(liq_cap=.25, gate_dates=G['gate'])
    if cfg is not None:
        filt, size, first, seed = cfg[:4]
        if len(cfg) > 4:
            k['extra_max_frac'] = cfg[4]
        if filt == 'random':
            k.update(extra_signal_fn=lambda f: month_end(f) & f.tradable.to_numpy(bool), extra_exit_signal_fn=month_end,
                     extra_priority=lambda f: np.random.default_rng([seed, zlib.crc32(str(f['Ticker'].iloc[0]).encode())]).random(len(f)))
        else:
            k.update(extra_signal_fn=lambda f: month_end(f) & f.tradable.to_numpy(bool) & trend(filt, f),
                     extra_exit_signal_fn=lambda f: month_end(f) & ~trend(filt, f))
        k.update(extra_size_div=size, extra_first=first)
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(G['fr'], start='2000-01-01', **k)
    c = c.loc[:'2025-08-15']
    if 'kind' not in t:
        t['kind'] = 'main'
    s = stats(c, t)
    row = dict(label=label, version=version, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], trades=s['n'], win_rate=s['wr'],
               expectancy=s['mean'], e_R=s['mean'] / s['avg_loss'], invested=s['invested'], **slices(c.equity))
    for kd in ('main', 'extra'):
        x = t[t.kind == kd].net_return
        row.update({f'{kd}_trades': len(x), f'{kd}_wr': (x > 0).mean() if len(x) else np.nan, f'{kd}_expectancy': x.mean() if len(x) else np.nan,
                    f'{kd}_pnl_share': t[t.kind == kd].pnl.sum() / t.pnl.sum()})
    return row, c.equity


def split_reference(version):
    """Fixed 50/50 capital split: V0 and the standalone F_mom monthly system (step 1, 25% orders), Rp0.5bn each."""
    k1 = rc.kw(BASE, 'B')
    mte.G['me'] = G['me']
    k2 = mte.make_kw('F_mom', 'X_month', 4)
    if version == 'realistic':
        for k in (k1, k2):
            k.update(liq_cap=.25, gate_dates=G['gate'])
    with np.errstate(invalid='ignore', divide='ignore'):
        e1 = run(G['fr'], start='2000-01-01', capital=5e8, **k1)[0].equity
        e2 = run(G['fr'], start='2000-01-01', capital=5e8, **k2)[0].equity
    eq = (e1 + e2.reindex(e1.index).ffill()).loc[:'2025-08-15']
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    rec = (eq > eq.cummax().shift(1).fillna(0)).groupby(eq.index.to_period('M')).any().sum()
    return dict(label='SPLIT50_V0+F_mom_month', version=version, cagr=(eq.iloc[-1] / 1e9) ** (1 / yrs) - 1, records=int(rec),
                mdd=float((eq / eq.cummax() - 1).min()), **slices(eq))


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    jobs = [('V0', v, None) for v in ('unrestricted', 'realistic')]
    for f_ in ('F_mom', 'F_sma120', 'F_er'):
        for size in (4, 10):
            for first in (True, False):
                jobs += [(f'{f_}|s{size}|{"P1" if first else "P2"}', v, (f_, size, first, None)) for v in ('unrestricted', 'realistic')]
    for size in (4, 10):
        for first in (True, False):
            for seed in (1, 2, 3):
                jobs += [(f'random{seed}|s{size}|{"P1" if first else "P2"}', v, ('random', size, first, seed)) for v in ('unrestricted', 'realistic')]
    with Pool(4) as p:
        res = p.map(job, jobs, chunksize=1)
    D = pd.DataFrame([r for r, _ in res])
    D = pd.concat([D, pd.DataFrame([split_reference(v) for v in ('unrestricted', 'realistic')])], ignore_index=True)
    D.to_csv(OUT / 'add_entry.csv', index=False)
    U, R = D[D.version == 'unrestricted'].set_index('label'), D[D.version == 'realistic'].set_index('label')
    v0u, v0r = U.loc['V0'], R.loc['V0']
    S = []
    for l in [x for x in R.index if x.startswith('F_')]:
        r, u = R.loc[l], U.loc[l]
        tag = l.split('|', 1)[1]
        ctl = R.loc[[x for x in R.index if x.startswith('random') and x.endswith(tag)], 'cagr'].max()
        S.append(dict(label=l, cagr_real=r.cagr, records_real=r.records, mdd_real=r.mdd, wr_real=r.win_rate, e_real=r.expectancy,
                      extra_wr_real=r.extra_wr, extra_e_real=r.extra_expectancy, extra_trades_real=r.extra_trades, main_trades_real=r.main_trades,
                      invested_real=r.invested, ctl_random_best=ctl, sub_ge_V0=sum(r[f'cagr_{p}'] >= v0r[f'cagr_{p}'] for p in PER),
                      cagr_unres=u.cagr, records_unres=u.records, mdd_unres=u.mdd, wr_unres=u.win_rate, main_trades_unres=u.main_trades))
    S = pd.DataFrame(S)
    S['passes'] = (S.cagr_real >= v0r.cagr) & (S.mdd_real >= -.49) & (S.records_real >= v0r.records) & (S.sub_ge_V0 >= 3) & \
                  (S.cagr_unres >= v0u.cagr - .05) & (S.mdd_unres >= -.29) & (S.cagr_real > S.ctl_random_best) & \
                  (S.wr_real > v0r.win_rate) & (S.wr_unres > v0u.win_rate)
    S.to_csv(OUT / 'add_entry_summary.csv', index=False)
    pd.set_option('display.width', 270); pd.set_option('display.max_columns', 40)
    print(S.round(3).to_string(index=False))
    print(D[~D.label.str.startswith('F_')][['label', 'version', 'cagr', 'records', 'mdd', 'win_rate', 'expectancy', 'invested']].round(3).to_string(index=False))
