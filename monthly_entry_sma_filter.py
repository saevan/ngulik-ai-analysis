"""Round 2 of monthly_entry_main_exits_results/PLAN.md: which SMA position of the monthly picks performs (diagnostic), and a
grid of SMA filters for the monthly entry whose positions use the existing exits."""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_breakout_er import efficiency_ratio
from backtest_open_next import stats
import wr_gap_v1 as w
import monthly_filter_grid as m1

G = w.G
SMA_N = (10, 20, 30, 50, 100, 200)
CONDS = ['C>SMA10', 'C>SMA20', 'C>SMA30', 'C>SMA50', 'C>SMA100', 'C>SMA200', 'C>=1.03SMA30', 'C>=1.05SMA30', 'C>=1.10SMA30', 'stack']


def base(name, f):
    c = f.Close
    er = efficiency_ratio(c, 20)
    if name == 'none':
        return np.ones(len(f), bool)
    ok = ((c > c.shift(120)) & (er >= .3)) if name == 'F1' else ((er >= .4) & (c > c.shift(20)))
    return ok.fillna(False).to_numpy(bool)


def cond(name, f):
    c = f.Close
    sma = lambda n: c.rolling(n).mean()
    if name.startswith('C>SMA'):
        ok = c > sma(int(name[5:]))
    elif name.startswith('C>='):
        ok = c >= float(name[3:7]) * sma(30)
    else:
        ok = (sma(20) > sma(50)) & (sma(50) > sma(100)) & (c > sma(20))
    return ok.fillna(False).to_numpy(bool)


def kw(version, cell):
    k = dict(rc.kw(m1.BASE, 'B'), failed_exit=None)
    if cell == 'V2 now':
        k = dict(w.kw(version, True, None), failed_exit=None)
    elif cell != 'breakout only':
        b, cd = cell.split('|')
        k.update(extra_signal_fn=lambda f: w.me(f) & f.tradable.to_numpy(bool) & base(b, f) & (cond(cd, f) if cd != 'nofilter' else True),
                 extra_exit_signal_fn=None, extra_first=True, extra_main_exits=True, extra_size_div=10, extra_max_frac=.35)
    if version == 'realistic':
        k.update(liq_cap=.25, gate_dates=G['gate'])
    return k


def job(a):
    cell, version, keep = a
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(G['fr'], start='2000-01-01', **kw(version, cell))
    c = c.loc[:'2025-08-15']
    if 'kind' not in t:
        t['kind'] = 'main'
    s = stats(c, t)
    tr, _ = m1.piece(c.equity, '2000-01-01', '2015-12-31')
    te, _ = m1.piece(c.equity, '2016-01-01', '2025-08-15')
    x = t[t.kind == 'extra']
    row = dict(cell=cell, version=version, cagr=s['cagr'], cagr_train=tr, cagr_test=te, records=s['records'], mdd=s['mdd'], win_rate=s['wr'],
               monthly_trades=len(x), monthly_wr=(x.net_return > 0).mean() if len(x) else np.nan, monthly_e=x.net_return.mean() if len(x) else np.nan,
               monthly_bars=x.bars.mean() if len(x) else np.nan)
    return row, (t[t.kind == 'extra'] if keep else None)


def features(T):
    rows = []
    for r in T.itertuples():
        f = G['fr'][r.ticker]
        i = int(np.searchsorted(f['Date/Time'].values, np.datetime64(r.entry_date))) - 1   # month-end signal bar
        c = f.Close
        rows.append({**{f'd{n}': c.iloc[i] / c.iloc[max(0, i - n + 1):i + 1].mean() - 1 if i + 1 >= n else np.nan for n in SMA_N},
                     'net': r.net_return, 'bars': r.bars})
    return pd.DataFrame(rows)


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    cells = ['V2 now', 'breakout only'] + [f'{b}|{c_}' for b in ('none', 'F1', 'F2') for c_ in CONDS]
    jobs = [(c_, v, False) for c_ in cells for v in ('realistic', 'unrestricted')]
    jobs += [(f'{b}|nofilter', v, True) for b in ('F1', 'F2') for v in ('realistic', 'unrestricted')]
    with Pool(4) as p:
        res = p.map(job, jobs, chunksize=1)
    D = pd.DataFrame([r for r, _ in res])
    D.to_csv('monthly_entry_main_exits_results/sma_grid.csv', index=False)
    # Part 1 diagnostic
    diag = []
    for (r, T) in res:
        if T is None:
            continue
        F = features(T)
        for n in SMA_N:
            for side, m in (('above', F[f'd{n}'] > 0), ('below', F[f'd{n}'] <= 0)):
                x = F[m]
                diag.append(dict(run=r['cell'], version=r['version'], sma=n, bucket=side, trades=len(x), wr=(x.net > 0).mean(), expectancy=x.net.mean(),
                                 bars=x.bars.mean(), share_exit_le2=(x.bars <= 2).mean()))
        for lo, hi in ((0, .03), (.03, .05), (.05, .10), (.10, 9)):
            x = F[(F.d30 > lo) & (F.d30 <= hi)]
            diag.append(dict(run=r['cell'], version=r['version'], sma=30, bucket=f'{int(lo*100)}-{int(hi*100) if hi < 9 else "+"}% above', trades=len(x),
                             wr=(x.net > 0).mean(), expectancy=x.net.mean(), bars=x.bars.mean(), share_exit_le2=(x.bars <= 2).mean()))
    Dg = pd.DataFrame(diag)
    Dg.to_csv('monthly_entry_main_exits_results/sma_diagnostic.csv', index=False)
    R, U = D[D.version == 'realistic'].set_index('cell'), D[D.version == 'unrestricted'].set_index('cell')
    grid = [c_ for c_ in R.index if '|' in c_ and 'nofilter' not in c_]
    pick = R.loc[grid, 'cagr_train'].idxmax()
    b0 = 'breakout only'
    ok = (R.loc[pick, 'cagr_train'] > R.loc[b0, 'cagr_train']) and (R.loc[pick, 'cagr_test'] > R.loc[b0, 'cagr_test']) and \
         (U.loc[pick, 'cagr'] >= U.loc[b0, 'cagr'] - .05) and (R.loc[pick, 'mdd'] >= R.loc[b0, 'mdd'] - .05) and (U.loc[pick, 'mdd'] >= U.loc[b0, 'mdd'] - .05)
    pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
    print(Dg.round(3).to_string(index=False))
    S = R[['cagr_train', 'cagr_test', 'cagr', 'records', 'mdd', 'win_rate', 'monthly_trades', 'monthly_wr', 'monthly_e', 'monthly_bars']].join(
        U[['cagr', 'mdd', 'win_rate']], rsuffix='_U')
    print(S.sort_values('cagr_train', ascending=False).round(3).to_string())
    print('PICK:', pick, '| useful vs breakout only:', ok)
