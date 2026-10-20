"""Property-driven levers on the v2 main pick versus Swinger ideal (plan: property_levers_results/PLAN.md, committed first).
Base = v2 main pick F1_ch20_er0.2_cand_f0.0_s4_b0.005 built with search_realistic_chase_v2.kw; each variant overrides engine
arguments. Swinger ideal is re-run as a fresh Rp1bn start per window (run_portfolio's fixed 2000-01-01 start replaced by the
window start). Writes property_levers_results/results.csv."""
import inspect
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import backtest_prototype_swinger as bps
from backtest_stop_execution import run
from backtest_open_next import stats
from backtest_breakout_er import efficiency_ratio

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'property_levers_results'
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
KEYS = ['cagr', 'records', 'months', 'mdd', 'n', 'wr', 'payout', 'invested']


def er_rank(f):
    """Prior-bar ER20 (known at today's Open), the same quantity the ER filter uses."""
    return efficiency_ratio(f.Close, 20).shift(1).to_numpy(float)


VARIANTS = {'V0_base': {}, 'V1_no_gap_skip': dict(gap_skip=None), 'V2_no_failed_exit': dict(failed_exit=None),
            'V3_er0.3': dict(er_min=.3), 'V4_er0.5': dict(er_min=.5), 'V5_rank_er': dict(priority=er_rank),
            'V6_no_gapdown_close': dict(gapdown_close=None), 'V7_V1+V2': dict(gap_skip=None, failed_exit=None),
            'V8_V1+V2+V5': dict(gap_skip=None, failed_exit=None, priority=er_rank)}
W = {k: rc.W[k] for k in ['train', 'validation', 'test', 'full']}
SW_SRC = inspect.getsource(bps.run_portfolio).replace("np.datetime64('2000-01-01')", "np.datetime64(START)")
assert 'START' in SW_SRC


def frames(uni, end):
    src = rc.G['fr'] if uni == 'all' else rc.G['fr_pre2018']
    return {t: g for t, f in src.items() if len(g := f[f['Date/Time'] <= end])}


def job(a):
    v, w, scen, uni = a
    s, e = W[w]
    k = {**rc.kw(BASE, scen), **VARIANTS[v]}
    with np.errstate(invalid='ignore', divide='ignore'):
        eq, tr = run(frames(uni, e), start=s, **k)
    st = stats(eq, tr)
    return dict(variant=v, window=w, scen=scen, universe=uni, **{x: st[x] for x in KEYS})


def swinger(a):
    w, scen, uni = a
    s, e = W[w]
    ns = dict(vars(bps))
    ns['START'] = s
    exec(SW_SRC, ns)
    eq, tr, _ = ns['run_portfolio'](frames(uni, e), 'afl_ideal', slip=0. if scen == 'A' else .0025)
    st = stats(eq, tr)
    return dict(variant='SWINGER_ideal', window=w, scen=scen, universe=uni, **{x: st[x] for x in KEYS})


def main():
    OUT.mkdir(exist_ok=True)
    st, _ = engine.load_data('stocks')
    rc.G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    rc.G['fr_pre2018'] = {t: f for t, f in rc.G['fr'].items() if f['Date/Time'].min() < pd.Timestamp('2018-01-01')}
    jobs = [(v, w, s, 'all') for v in VARIANTS for w in W for s in 'AB'] + [(v, w, 'B', 'pre2018') for v in VARIANTS for w in ['test', 'full']]
    sw = [(w, s, 'all') for w in W for s in 'AB'] + [(w, 'B', 'pre2018') for w in ['test', 'full']]
    with Pool(4) as p:
        rows = p.map(swinger, sw, chunksize=1) + p.map(job, jobs, chunksize=1)
    d = pd.DataFrame(rows)
    d.to_csv(OUT / 'results.csv', index=False)
    d['v'] = d.apply(lambda r: f"{r.cagr * 100:.1f}/{int(r.records)}/{r.mdd * 100:.0f}", axis=1)
    pd.set_option('display.width', 250)
    print(d.pivot_table(index=['universe', 'scen', 'variant'], columns='window', values='v', aggfunc='first').to_string())


if __name__ == '__main__':
    main()
