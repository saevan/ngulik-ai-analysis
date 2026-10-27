"""Confirmation of the wide-range lead (plan: wide_range_results/PLAN.md, last section)."""
from itertools import product
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
import wide_range as wr
from mpstats import nw

G = wr.G


def cell_stats(cell, a, b):
    T = wr.sim(cell)
    x = T[(T.signal >= np.datetime64(a)) & (T.signal <= np.datetime64(b))]
    daily = x.groupby('signal').net_B.mean().reindex(G['cal'].loc[a:b].index)
    m, se, _ = nw(daily.to_numpy(), 20)
    return dict(N=cell[0], width=f'{int(cell[1][0]*100)}-{int(cell[1][1]*100)}%', target=cell[2], period=f'{a[:4]}-{b[:4]}', trades=len(x),
                gross_pct=x.gross.mean() * 100, net_B_pct=m * 100, t=m / se if se else np.nan, net_B_event_pct=x.net_B.mean() * 100,
                win_rate=(x.net_B > 0).mean())


def job(a):
    return cell_stats(*a)


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
    G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['cache'] = {}
    orig = wr.prep
    def prep_all_dates(t, N):   # same as wide_range.prep but without the 2000 start, so the holdout can be measured
        key = (t, N, 'all')
        if key in G['cache']:
            return G['cache'][key]
        o, h, l, c, d, H, L, er, width, pos, ok = orig(t, N)
        ok = np.isin(d, G['ok'][t]) & (d <= np.datetime64('2025-08-15'))
        G['cache'][key] = (o, h, l, c, d, H, L, er, width, pos, ok)
        return G['cache'][key]
    wr.prep = prep_all_dates
    lead = [((20, (.4, .8), 'top', 'nostop'), '1995-07-01', '1999-12-31'), ((20, (.4, .8), 'mid', 'nostop'), '1995-07-01', '1999-12-31'),
            ((20, (.4, .8), 'top', 'nostop'), '2021-01-01', '2025-08-15')]
    neigh = [((n, w, 'top', 'nostop'), '2000-01-01', '2025-08-15') for n, w in product((15, 20, 30), ((.3, .6), (.4, .8), (.5, 1.0)))]
    with Pool(4) as p:
        R = pd.DataFrame(p.map(job, lead + neigh))
    R.to_csv('wide_range_results/confirm.csv', index=False)
    pd.set_option('display.width', 200)
    print(R.round(2).to_string(index=False))
    nb = R.iloc[3:]
    a_ = R.iloc[0].net_B_event_pct > 0
    b_ = (nb.net_B_pct > 0).sum() >= 7 and nb.t.median() >= 1.5
    c_ = R.iloc[2].net_B_pct > 0
    print(f'(a) holdout net>0: {a_} | (b) neighbours positive {(nb.net_B_pct > 0).sum()}/9, median t {nb.t.median():.2f}: {b_} | (c) 2021-25 net>0: {c_} | ACCEPTED: {a_ and b_ and c_}')
