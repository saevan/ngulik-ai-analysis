"""V1 with vs without the failed-breakout exit (26 Oct 2026, descriptive). Writes winrate_diagnosis_results/v1_failed_exit.csv"""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
import high_reset_exit as h

G = h.G
if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    cells = [('V1', {}), ('V1 no failed exit', dict(failed_exit=None))]
    with Pool(4) as p:
        D = pd.DataFrame(p.map(h.job, [(l, v, e) for l, e in cells for v in ('unrestricted', 'realistic')]))
    D.to_csv('winrate_diagnosis_results/v1_failed_exit.csv', index=False)
    print(D[['label', 'version', 'win_rate', 'cagr', 'cagr_train', 'cagr_test', 'records', 'mdd', 'breakout_wr', 'breakout_e']].round(3).to_string(index=False))
