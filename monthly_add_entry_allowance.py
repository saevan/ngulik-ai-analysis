"""Step 4 of monthly_trend_entry_results/PLAN.md: the added monthly entry with a capital allowance A (P1, 10% orders).
Writes monthly_trend_entry_results/add_entry_allowance.csv, add_entry_allowance_summary.csv"""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
import monthly_add_entry as mae
from monthly_trend_entry import PER

if __name__ == '__main__':
    G = mae.G
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    jobs = [('V0', v, None) for v in ('unrestricted', 'realistic')]
    for A in (.2, .35, .5):
        for f_ in ('F_mom', 'F_sma120'):
            jobs += [(f'{f_}|A{A}', v, (f_, 10, True, None, A)) for v in ('unrestricted', 'realistic')]
        for seed in (1, 2, 3):
            jobs += [(f'random{seed}|A{A}', v, ('random', 10, True, seed, A)) for v in ('unrestricted', 'realistic')]
    with Pool(4) as p:
        res = p.map(mae.job, jobs, chunksize=1)
    D = pd.DataFrame([r for r, _ in res])
    D.to_csv(mae.OUT / 'add_entry_allowance.csv', index=False)
    U, R = D[D.version == 'unrestricted'].set_index('label'), D[D.version == 'realistic'].set_index('label')
    v0u, v0r = U.loc['V0'], R.loc['V0']
    S = []
    for l in [x for x in R.index if x.startswith('F_')]:
        r, u = R.loc[l], U.loc[l]
        A = l.split('|')[1]
        ctl = R.loc[[x for x in R.index if x.startswith('random') and x.endswith(A)], 'cagr'].max()
        S.append(dict(label=l, cagr_real=r.cagr, records_real=r.records, mdd_real=r.mdd, wr_real=r.win_rate, e_real=r.expectancy,
                      extra_wr_real=r.extra_wr, extra_e_real=r.extra_expectancy, extra_trades_real=r.extra_trades,
                      main_kept_real=r.main_trades / v0r.trades, invested_real=r.invested, ctl_random_best=ctl,
                      sub_ge_V0=sum(r[f'cagr_{p}'] >= v0r[f'cagr_{p}'] for p in PER), cagr_unres=u.cagr, records_unres=u.records,
                      mdd_unres=u.mdd, wr_unres=u.win_rate, main_kept_unres=u.main_trades / v0u.trades, extra_trades_unres=u.extra_trades,
                      **{f'real_{p}': r[f'cagr_{p}'] for p in PER}))
    S = pd.DataFrame(S)
    S['passes'] = (S.cagr_real >= v0r.cagr) & (S.mdd_real >= -.49) & (S.records_real >= v0r.records) & (S.sub_ge_V0 >= 3) & \
                  (S.cagr_unres >= v0u.cagr - .05) & (S.mdd_unres >= -.29) & (S.cagr_real > S.ctl_random_best) & \
                  (S.wr_real > v0r.win_rate) & (S.wr_unres > v0u.win_rate) & (S.main_kept_real >= .7) & (S.main_kept_unres >= .7)
    S.to_csv(mae.OUT / 'add_entry_allowance_summary.csv', index=False)
    pd.set_option('display.width', 270); pd.set_option('display.max_columns', 40)
    print(S.round(3).to_string(index=False))
    print(D[D.label.str.startswith('random')][['label', 'version', 'cagr', 'records', 'mdd', 'win_rate', 'main_trades', 'extra_trades']].round(3).to_string(index=False))
