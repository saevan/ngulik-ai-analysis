"""Portfolio test of price/time exits on the v2 main pick's entries (plan: winrate_diagnosis_results/PLAN.md, step 2).
Same entries, sizing, order book and costs (B); only exits change. B unrestricted + B realistic + subperiod CAGR slices,
holdout 1995-03..1999 (descriptive). Writes winrate_diagnosis_results/portfolio_price_time.csv"""
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_open_next import stats

OUT = Path(__file__).resolve().parent / 'winrate_diagnosis_results'
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
NONE = dict(fade=None, sma_len=None, failed_exit=None)
CELLS = {'V0': {}}
CELLS.update({f'TIME_{n}': dict(NONE, max_hold=n) for n in (10, 20, 40)})
CELLS.update({f'V0+CAP_{n}': dict(max_hold=n) for n in (20, 40, 60)})
CELLS.update({f'FAIL+TIME_{n}': dict(fade=None, sma_len=None, max_hold=n) for n in (20, 40)})
CELLS.update({f'TP{k}+TIME_{n}': dict(NONE, take_profit=float(k), max_hold=n) for k in (3, 6) for n in (10, 20, 40)})
PER = {'2000-07': ('2000', '2007'), '2008-15': ('2008', '2015'), '2016-20': ('2016', '2020'), '2021-25': ('2021', '2025')}
G = {}


def job(a):
    name, version = a
    k = dict(rc.kw(BASE, 'B'), **CELLS[name])
    fr, start = G['fr'], '2000-01-01'
    if version == 'realistic':
        k.update(liq_cap=.25, gate_dates=G['gate'])
    if version == 'holdout':
        fr, start = {t: g for t, f in fr.items() if len(g := f[f['Date/Time'] <= '1999-12-31'].reset_index(drop=True))}, '1995-03-01'
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(fr, start=start, **k)
    if version != 'holdout':
        c = c.loc[:'2025-08-15']
    s = stats(c, t)
    row = dict(cell=name, version=version, cagr=s['cagr'], record_months=s['records'], mdd=s['mdd'], trades=s['n'], win_rate=s['wr'],
               payout=s['payout'], avg_win=s['avg_win'], avg_loss=s['avg_loss'], mean_trade=s['mean'], bars_win=s['win_bars'],
               bars_loss=s['loss_bars'], invested=s['invested'])
    if version == 'unrestricted':
        eq = c.equity
        for pn, (a_, b_) in PER.items():
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
        rows = p.map(job, [(n, v) for n in CELLS for v in ('unrestricted', 'realistic', 'holdout')])
    D = pd.DataFrame(rows)
    D.to_csv(OUT / 'portfolio_price_time.csv', index=False)
    U = D[D.version == 'unrestricted'].set_index('cell')
    R = D[D.version == 'realistic'].set_index('cell')
    H = D[D.version == 'holdout'].set_index('cell')
    v0 = U.loc['V0']
    sub = sum((U[f'cagr_{p}'] >= v0[f'cagr_{p}']).astype(int) for p in PER)
    P = pd.DataFrame({'wr': U.win_rate, 'payout': U.payout, 'cagr': U.cagr, 'records': U.record_months, 'mdd': U.mdd, 'invested': U.invested,
                      'mean_trade': U.mean_trade, 'cagr_realistic': R.cagr, 'mdd_realistic': R.mdd, 'wr_realistic': R.win_rate,
                      'subperiods_ge_V0': sub, 'cagr_holdout_95_99': H.cagr, 'wr_holdout': H.win_rate,
                      **{f'cagr_{p}': U[f'cagr_{p}'] for p in PER}})
    P['passes'] = (P.wr >= .45) & (P.cagr >= v0.cagr) & (P.mdd >= v0.mdd - .05) & (P.cagr_realistic >= R.loc['V0', 'cagr']) & \
                  (P.subperiods_ge_V0 >= 3) & (P.records >= v0.record_months)
    P.loc['V0', 'passes'] = False
    P.to_csv(OUT / 'portfolio_price_time_summary.csv')
    pd.set_option('display.width', 250)
    print(P.round(3).to_string())
