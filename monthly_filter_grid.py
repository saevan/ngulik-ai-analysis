"""Grid search of the monthly-module filter (plan: monthly_filter_grid_results/PLAN.md). Breakout entry unchanged; the
monthly entry buys stocks in trend (optionally just below their highs, not yet broken out) at the first Open of the month.
Train 2000-2015 selects; test 2016-2025.08. Writes monthly_filter_grid_results/grid.csv, early_capture.csv"""
from itertools import product
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_breakout_er import efficiency_ratio
from backtest_open_next import stats

OUT = Path(__file__).resolve().parent / 'monthly_filter_grid_results'
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
CELLS = list(product((60, 120, 250), (0., .2, .3, .4), (None, .05, .10)))
G = {}


def me(f):
    return f['Date/Time'].isin(G['me']).to_numpy(bool)


def up(f, n):
    return (f.Close > f.Close.shift(n)).fillna(False).to_numpy(bool)


def entry_fn(n, er, prox):
    def fn(f):
        s = me(f) & f.tradable.to_numpy(bool) & up(f, n)
        if er > 0:
            s &= (efficiency_ratio(f.Close, 20) >= er).fillna(False).to_numpy(bool)
        if prox is not None:
            hh60 = f.High.rolling(60).max()
            hh20 = f.High.rolling(20).max()   # level the breakout needs next day
            s &= ((f.Close >= (1 - prox) * hh60) & (f.Close <= hh20)).fillna(False).to_numpy(bool)
        return s
    return fn


def kw(cell, version):
    k = rc.kw(BASE, 'B')
    if cell != 'V0':
        n, er, prox = cell
        k.update(extra_signal_fn=entry_fn(n, er, prox), extra_exit_signal_fn=lambda f: me(f) & ~up(f, n), extra_size_div=10,
                 extra_first=True, extra_max_frac=.35)
    if version == 'realistic':
        k.update(liq_cap=.25, gate_dates=G['gate'])
    return k


def piece(eq, a, b):
    x = eq.loc[a:b]
    prev = eq.loc[:pd.Timestamp(a) - pd.Timedelta(days=1)]
    st0 = prev.iloc[-1] if len(prev) else 1e9
    yrs = (x.index[-1] - (prev.index[-1] if len(prev) else pd.Timestamp('1999-12-31'))).days / 365.25
    path = pd.concat([pd.Series([st0]), x])
    return float((x.iloc[-1] / st0) ** (1 / yrs) - 1), float((path / path.cummax() - 1).min())


def early(t):
    """Monthly trades: did the stock reach the breakout stop level while held, and gain from entry to that level."""
    x = t[t.kind == 'extra']
    hit, gain = [], []
    for r in x.itertuples():
        f = G['fr'][r.ticker]
        d = f['Date/Time'].values
        i, j = int(np.searchsorted(d, np.datetime64(r.entry_date))), int(np.searchsorted(d, np.datetime64(r.exit_date)))
        lvl = (f.High.shift(1).rolling(20).max() * 1.005).to_numpy()
        h = f.High.to_numpy()
        b = next((b for b in range(i, j + 1) if np.isfinite(lvl[b]) and h[b] >= lvl[b]), None)
        hit.append(b is not None)
        if b is not None:
            gain.append(lvl[b] / (r.entry_price / 1.0025) - 1)
    return dict(monthly_trades=len(x), share_hit_breakout=float(np.mean(hit)) if hit else np.nan,
                gain_before_breakout=float(np.mean(gain)) if gain else np.nan, monthly_wr=float((x.net_return > 0).mean()) if len(x) else np.nan,
                monthly_e=float(x.net_return.mean()) if len(x) else np.nan)


def job(a):
    cell, version = a
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(G['fr'], start='2000-01-01', **kw(cell, version))
    c = c.loc[:'2025-08-15']
    if 'kind' not in t:
        t['kind'] = 'main'
    s = stats(c, t)
    tr, mtr = piece(c.equity, '2000-01-01', '2015-12-31')
    te, mte = piece(c.equity, '2016-01-01', '2025-08-15')
    row = dict(cell=str(cell), version=version, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], win_rate=s['wr'], invested=s['invested'],
               cagr_train=tr, mdd_train=mtr, cagr_test=te, mdd_test=mte, breakout_trades=int((t.kind == 'main').sum()))
    if cell != 'V0':
        row.update(early(t))
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
    D.to_csv(OUT / 'grid.csv', index=False)
    U, R = D[D.version == 'unrestricted'].set_index('cell'), D[D.version == 'realistic'].set_index('cell')
    S = R[['cagr_train', 'cagr_test', 'mdd_test', 'cagr', 'records', 'mdd', 'win_rate', 'monthly_trades', 'monthly_wr', 'monthly_e',
           'share_hit_breakout', 'gain_before_breakout']].add_prefix('R_').join(
        U[['cagr_train', 'cagr_test', 'mdd_test', 'cagr', 'records', 'mdd', 'win_rate', 'breakout_trades']].add_prefix('U_'))
    S['kept'] = S.U_breakout_trades / U.loc['V0', 'breakout_trades']
    S.to_csv(OUT / 'summary.csv')
    elig = S.drop('V0')
    elig = elig[elig.kept >= .7]
    pick = elig.R_cagr_train.idxmax()
    v1 = str((120, .3, None))
    ok = (S.loc[pick, 'R_cagr_test'] >= S.loc[v1, 'R_cagr_test']) & (S.loc[pick, 'U_cagr_test'] >= S.loc[v1, 'U_cagr_test'] - .05) & \
         (S.loc[pick, 'R_mdd_test'] >= S.loc[v1, 'R_mdd_test'] - .05)
    pd.set_option('display.width', 300); pd.set_option('display.max_columns', 40)
    print(S.sort_values('R_cagr_train', ascending=False).round(3).to_string())
    print('PICK (train):', pick, '| V1:', v1, '| improves on V1 in test:', bool(ok))
