"""Exploratory follow-up for the win-rate discussion (26 Oct 2026): exit variants already in the v2 grid (unrestricted B),
re-run in the realistic version (point-in-time top-half liquidity + stale filter + buys <= 25% ADV20) with subperiod CAGR.
V0 = main pick; fNone = without the failed-breakout exit; trail2 = LLV5 trailing stop once a Close is 2 ATR above entry.
Writes winrate_diagnosis_results/exit_variants_realistic.csv"""
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_open_next import stats

OUT = Path(__file__).resolve().parent / 'winrate_diagnosis_results'
V = {'V0': dict(exit='cand', failed=0.), 'fNone': dict(exit='cand', failed=None), 'trail2_f0': dict(exit='cand_trail2', failed=0.),
     'trail2_fNone': dict(exit='cand_trail2', failed=None)}
G = {}


def job(a):
    name, version = a
    k = rc.kw(dict(fam='F1', buffer=.005, channel=20, er_min=.2, size_div=4, **V[name]), 'B')
    if version == 'realistic':
        k.update(liq_cap=.25, gate_dates=G['gate'])
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(G['fr'], start='2000-01-01', **k)
    c = c.loc[:'2025-08-15']
    s = stats(c, t)
    row = dict(variant=name, version=version, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], trades=s['n'], win_rate=s['wr'],
               payout=s['payout'], expectancy=s['mean'], invested=s['invested'])
    eq = c.equity
    for pn, (a_, b_) in {'2000-07': ('2000', '2007'), '2008-15': ('2008', '2015'), '2016-20': ('2016', '2020'), '2021-25': ('2021', '2025')}.items():
        x, prev = eq.loc[a_:b_], eq.loc[:str(int(a_) - 1)]
        st0 = prev.iloc[-1] if len(prev) else 1e9
        yrs = (x.index[-1] - (prev.index[-1] if len(prev) else x.index[0])).days / 365.25
        row[f'cagr_{pn}'] = float((x.iloc[-1] / st0) ** (1 / yrs) - 1)
    return row


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    with Pool(4) as p:
        D = pd.DataFrame(p.map(job, [(n, v) for n in V for v in ('unrestricted', 'realistic')]))
    D.to_csv(OUT / 'exit_variants_realistic.csv', index=False)
    pd.set_option('display.width', 220)
    print(D.round(3).to_string(index=False))
