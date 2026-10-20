"""Control for pit_universe.py (added after seeing its results): the liquidity rule also halves the candidate pool.
Random eligibility with the same number of eligible stocks per day (same >= 250-bar rule, 3 seeds) separates
'fewer candidates' from 'removing stocks that were illiquid at the time'. Scenario B, all universe."""
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
from backtest_stop_execution import run
from backtest_open_next import stats
import pit_universe as pu

OUT = Path(__file__).resolve().parent / 'pit_universe_results'
G = {}


def random_gate(fr, frac, seed):
    val = pd.DataFrame({t: f.set_index('Date/Time').eval('Close*Volume') for t, f in fr.items()}).sort_index()
    bars = val.notna().cumsum().shift(1)
    v = val.rolling(120, min_periods=60).mean().shift(1)
    n = v.notna().sum(axis=1)
    base = (bars >= 250) & v.notna()
    rng = np.random.default_rng(seed)
    # one random ordering per calendar month (positions persist like liquidity ranks do)
    key = val.index.to_period('M')
    rnd = pd.DataFrame(rng.random((key.nunique(), val.shape[1])), index=key.unique(), columns=val.columns).reindex(key)
    rnd.index = val.index
    rk = rnd.where(v.notna()).rank(axis=1)
    ok = base & (rk <= np.ceil(n * frac).values[:, None])
    return {t: set(ok.index[ok[t].fillna(False).values]) for t in fr}


def job(a):
    seed, w = a
    s, e = pu.W[w]
    fr = {t: g for t, f in G['fr'].items() if len(g := f[f['Date/Time'] <= e])}
    k = rc.kw(pu.BASE, 'B')
    k['gate_dates'] = G['gate'][seed]
    with np.errstate(invalid='ignore', divide='ignore'):
        eq, tr = run(fr, start=s, **k)
    st = stats(eq, tr)
    return dict(variant=f'random_half_seed{seed}', window=w, scen='B', universe='all', **{x: st[x] for x in ['cagr', 'records', 'mdd', 'n']})


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    G['gate'] = {s: random_gate(G['fr'], .5, s) for s in [1, 2, 3]}
    with Pool(4) as p:
        rows = p.map(job, [(s, w) for s in [1, 2, 3] for w in pu.W], chunksize=1)
    d = pd.DataFrame(rows)
    d.to_csv(OUT / 'control_random_half.csv', index=False)
    d['v'] = d.apply(lambda r: f"{r.cagr * 100:.1f}/{int(r.records)}/{r.mdd * 100:.0f}", axis=1)
    print(d.pivot_table(index='variant', columns='window', values='v', aggfunc='first').to_string())
