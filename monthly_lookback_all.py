"""Round 5 of monthly_entry_main_exits_results/PLAN.md: all entry x exit trend-lookback combinations for the monthly module."""
from itertools import product
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
import wr_gap_v1 as w
import monthly_xbar_exit as mx
import monthly_lookback as ml

G = w.G
NS = (20, 40, 60, 80, 100, 120, 150, 180, 250)

if __name__ == '__main__':
    mx.kw = ml.kw
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    cells = ['breakout only'] + [f'{a}/{b}' for a, b in product(NS, NS)]
    with Pool(4) as p:
        D = pd.DataFrame(p.map(mx.job, [(c_, v) for c_ in cells for v in ('realistic', 'unrestricted')], chunksize=1))
    R, U = D[D.version == 'realistic'].set_index('cell'), D[D.version == 'unrestricted'].set_index('cell')
    S = R.drop(columns='version').join(U[['cagr', 'mdd', 'records', 'win_rate']], rsuffix='_U')
    S.to_csv('monthly_entry_main_exits_results/lookback_all.csv')
    v = '120/120'
    elig = S.drop('breakout only')
    elig = elig[(elig.cagr_U >= S.loc[v, 'cagr_U'] - .05) & (elig.mdd >= S.loc[v, 'mdd'] - .05) & (elig.mdd_U >= S.loc[v, 'mdd_U'] - .05)]
    pick = elig.cagr_train.idxmax()
    pd.set_option('display.width', 250)
    for col in ('cagr', 'cagr_train', 'cagr_test', 'mdd', 'cagr_U', 'mdd_U'):
        M = S.drop('breakout only')[col].copy()
        M.index = pd.MultiIndex.from_tuples([tuple(int(x) for x in i.split('/')) for i in M.index], names=['entry', 'exit'])
        print(col, '\n', (M.unstack() * 100).round(1).to_string())
    print('eligible', len(elig), '| PICK:', pick, S.loc[pick, ['cagr', 'cagr_train', 'cagr_test', 'mdd', 'records', 'win_rate', 'cagr_U', 'mdd_U']].round(3).to_dict())
    print('V2 now (120/120):', S.loc[v, ['cagr', 'cagr_train', 'cagr_test', 'mdd', 'records', 'win_rate', 'cagr_U', 'mdd_U']].round(3).to_dict())
    print('breakout only:', S.loc['breakout only', ['cagr', 'cagr_train', 'cagr_test', 'mdd', 'records', 'win_rate', 'cagr_U', 'mdd_U']].round(3).to_dict())
    print('improves on V2 in test:', bool(S.loc[pick, 'cagr_test'] >= S.loc[v, 'cagr_test']) and pick != v)
