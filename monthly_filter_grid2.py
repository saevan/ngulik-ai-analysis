"""Round 2 of monthly_filter_grid_results/PLAN.md: any uptrend confirmation as the monthly-module filter.
Writes monthly_filter_grid_results/grid2.csv, summary2.csv"""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_breakout_er import efficiency_ratio
from backtest_open_next import stats
import monthly_filter_grid as m1

G = m1.G


def slope_r2(c, n):
    y = np.log(c)
    x = pd.Series(np.arange(len(c)), index=c.index, dtype=float)
    cov = y.rolling(n).cov(x)
    vx, vy = x.rolling(n).var(), y.rolling(n).var()
    return cov / vx, cov ** 2 / (vx * vy)


def trend(name, f):
    c, h = f.Close, f.High
    sma = lambda n: c.rolling(n).mean()
    er = lambda n: efficiency_ratio(c, n)
    if name.startswith('C>SMA'):
        ok = c > sma(int(name[5:]))
    elif name == 'SMA20>50':
        ok = (sma(20) > sma(50)) & (c > sma(20))
    elif name == 'SMA50>200':
        ok = (sma(50) > sma(200)) & (c > sma(50))
    elif name == 'MACD>0':
        ok = c.ewm(span=12, adjust=False).mean() > c.ewm(span=26, adjust=False).mean()
    elif name.startswith('ER20>='):
        ok = (er(20) >= float(name[6:])) & (c > c.shift(20))
    elif name == 'ER60>=0.3':
        ok = (er(60) >= .3) & (c > c.shift(60))
    elif name == 'near52wHigh':
        ok = c >= .9 * h.rolling(250).max()
    elif name.startswith('slope'):
        b, r2 = slope_r2(c, int(name[5:]))
        ok = (b > 0) & (r2 >= .5)
    elif name.startswith('C>C'):
        ok = c > c.shift(int(name[3:]))
    return ok.fillna(False).to_numpy(bool)


BASEF = ['C>SMA20', 'C>SMA50', 'C>SMA100', 'C>SMA200', 'SMA20>50', 'SMA50>200', 'MACD>0', 'near52wHigh', 'slope60', 'slope120',
         'C>C20', 'C>C60', 'C>C120', 'C>C250']
ERF = ['ER20>=0.3', 'ER20>=0.4', 'ER20>=0.5', 'ER60>=0.3']
CELLS = [(b, ov) for b in BASEF for ov in (False, True)] + [(e, False) for e in ERF]


def kw(cell, version):
    k = rc.kw(m1.BASE, 'B')
    if cell != 'V0':
        name, ov = cell
        def ent(f):
            s = m1.me(f) & f.tradable.to_numpy(bool) & trend(name, f)
            if ov:
                s &= (efficiency_ratio(f.Close, 20) >= .3).fillna(False).to_numpy(bool)
            return s
        k.update(extra_signal_fn=ent, extra_exit_signal_fn=lambda f: m1.me(f) & ~trend(name, f), extra_size_div=10, extra_first=True,
                 extra_max_frac=.35)
    if version == 'realistic':
        k.update(liq_cap=.25, gate_dates=G['gate'])
    return k


def job(a):
    cell, version = a
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(G['fr'], start='2000-01-01', **kw(cell, version))
    c = c.loc[:'2025-08-15']
    if 'kind' not in t:
        t['kind'] = 'main'
    s = stats(c, t)
    tr, mtr = m1.piece(c.equity, '2000-01-01', '2015-12-31')
    te, mte = m1.piece(c.equity, '2016-01-01', '2025-08-15')
    row = dict(cell=str(cell), version=version, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], win_rate=s['wr'], cagr_train=tr,
               mdd_train=mtr, cagr_test=te, mdd_test=mte, breakout_trades=int((t.kind == 'main').sum()))
    if cell != 'V0':
        row.update(m1.early(t))
    return row


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    jobs = [(c_, v) for c_ in ['V0'] + CELLS for v in ('unrestricted', 'realistic')]
    with Pool(4) as p:
        D = pd.DataFrame(p.map(job, jobs, chunksize=1))
    D.to_csv(m1.OUT / 'grid2.csv', index=False)
    U, R = D[D.version == 'unrestricted'].set_index('cell'), D[D.version == 'realistic'].set_index('cell')
    S = R[['cagr_train', 'cagr_test', 'mdd_test', 'cagr', 'records', 'mdd', 'win_rate', 'monthly_trades', 'monthly_wr', 'monthly_e',
           'gain_before_breakout']].add_prefix('R_').join(U[['cagr_train', 'cagr_test', 'mdd_test', 'cagr', 'records', 'mdd', 'win_rate',
                                                            'breakout_trades']].add_prefix('U_'))
    S['kept'] = S.U_breakout_trades / U.loc['V0', 'breakout_trades']
    S.to_csv(m1.OUT / 'summary2.csv')
    elig = S.drop('V0')
    elig = elig[elig.kept >= .7]
    pick = elig.R_cagr_train.idxmax()
    v1 = str(('C>C120', True))
    ok = (S.loc[pick, 'R_cagr_test'] >= S.loc[v1, 'R_cagr_test']) & (S.loc[pick, 'U_cagr_test'] >= S.loc[v1, 'U_cagr_test'] - .05) & \
         (S.loc[pick, 'R_mdd_test'] >= S.loc[v1, 'R_mdd_test'] - .05)
    pd.set_option('display.width', 300); pd.set_option('display.max_columns', 40)
    print(S.sort_values('R_cagr_train', ascending=False)[['R_cagr_train', 'R_cagr_test', 'R_mdd_test', 'R_cagr', 'R_records', 'R_mdd', 'R_win_rate',
          'R_monthly_wr', 'R_gain_before_breakout', 'U_cagr_train', 'U_cagr_test', 'U_cagr', 'U_records', 'U_mdd', 'U_win_rate', 'kept']].round(3).to_string())
    print('PICK (train):', pick, '| V1:', v1, '| improves on V1 in test:', bool(ok))
