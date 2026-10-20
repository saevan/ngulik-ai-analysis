"""Point-in-time liquidity eligibility for the v2 main pick (plan: pit_universe_results/PLAN.md)."""
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
from backtest_stop_execution import run
from backtest_open_next import stats

OUT = Path(__file__).resolve().parent / 'pit_universe_results'
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
W = {k: rc.W[k] for k in ['train', 'validation', 'test', 'full']}
G = {}


def eligibility(fr, frac):
    val = pd.DataFrame({t: f.set_index('Date/Time').eval('Close*Volume') for t, f in fr.items()}).sort_index()
    bars = val.notna().cumsum().shift(1)
    v = val.rolling(120, min_periods=60).mean().shift(1)
    rk = v.rank(axis=1, ascending=False)
    n = v.notna().sum(axis=1)
    ok = (bars >= 250) & (rk <= np.ceil(n * frac).values[:, None])
    return {t: set(ok.index[ok[t].fillna(False).values]) for t in fr}


def job(a):
    var, w, scen, uni = a
    s, e = W[w]
    src = G['fr'] if uni == 'all' else G['pre']
    fr = {t: g for t, f in src.items() if len(g := f[f['Date/Time'] <= e])}
    k = rc.kw(BASE, scen)
    if var != 'unrestricted':
        k['gate_dates'] = G['gate'][(var, uni)]
    with np.errstate(invalid='ignore', divide='ignore'):
        eq, tr = run(fr, start=s, **k)
    st = stats(eq, tr)
    return dict(variant=var, window=w, scen=scen, universe=uni, **{x: st[x] for x in ['cagr', 'records', 'months', 'mdd', 'n', 'wr', 'payout', 'invested']})


def main():
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    G['pre'] = {t: f for t, f in G['fr'].items() if f['Date/Time'].min() < pd.Timestamp('2018-01-01')}
    G['gate'] = {(v, u): eligibility(G['fr'] if u == 'all' else G['pre'], fr_)
                 for v, fr_ in [('pit_top_half', .5), ('pit_top_third', 1 / 3)] for u in ['all', 'pre2018']}
    jobs = [(v, w, s, u) for v in ['unrestricted', 'pit_top_half', 'pit_top_third'] for w in W for s in 'AB' for u in ['all', 'pre2018']]
    with Pool(4) as p:
        rows = p.map(job, jobs, chunksize=1)
    d = pd.DataFrame(rows)
    d.to_csv(OUT / 'results.csv', index=False)
    d['v'] = d.apply(lambda r: f"{r.cagr * 100:.1f}/{int(r.records)}/{r.mdd * 100:.0f}", axis=1)
    pd.set_option('display.width', 250)
    print(d.pivot_table(index=['universe', 'scen', 'variant'], columns='window', values='v', aggfunc='first').to_string())


if __name__ == '__main__':
    main()
