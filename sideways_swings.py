"""Bounces inside sideways ranges: zigzag anatomy and real-time catch (plan: sideways_swings_results/PLAN.md)."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy

OUT = Path(__file__).resolve().parent / 'sideways_swings_results'
A, B, COST = '2000-01-01', '2025-08-15', .009
YRS = (pd.Timestamp(B) - pd.Timestamp(A)).days / 365.25


def zigzag(c, x):
    """Pivots as (index, price, kind, confirm_index); kind +1 = swing high, -1 = swing low."""
    piv, trend, ext, ei = [], 1, c[0], 0
    for i in range(1, len(c)):
        if trend == 1:
            if c[i] > ext:
                ext, ei = c[i], i
            elif c[i] <= ext * (1 - x):
                piv.append((ei, ext, 1, i)); trend, ext, ei = -1, c[i], i
        else:
            if c[i] < ext:
                ext, ei = c[i], i
            elif c[i] >= ext * (1 + x):
                piv.append((ei, ext, -1, i)); trend, ext, ei = 1, c[i], i
    return piv


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
    lab = regime_proxy(st)['regime']
    legs, width = [], []
    with np.errstate(invalid='ignore', divide='ignore'):
        for t, f in fr.items():
            f = f[f.tradable].reset_index(drop=True)
            c, d = f.Close.to_numpy(float), f['Date/Time'].to_numpy(); C = pd.Series(c)
            er = ((C - C.shift(20)).abs() / C.diff().abs().rolling(20).sum()).to_numpy()
            okd = np.isin(d, np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]')) & (d >= np.datetime64(A)) & (d <= np.datetime64(B))
            cond = lab.reindex(pd.DatetimeIndex(d)).to_numpy()
            w = (f.High.rolling(20).max() / f.Low.rolling(20).min() - 1).to_numpy()
            width.append(pd.DataFrame({'condition': cond[okd], 'width': w[okd], 'choppy': er[okd] < .2}))
            for x in (.03, .05, .10):
                p = zigzag(c, x)
                for a, b, z in zip(p, p[1:], p[2:]):
                    if a[2] != 1 or b[2] != -1 or z[2] != 1:      # high a -> low b -> high z
                        continue
                    k = b[3]                                    # bar confirming the low (buy), z[3] confirms the high (sell)
                    if not okd[k]:
                        continue
                    legs.append(dict(ticker=t, X=x, confirm_date=d[k], condition=cond[k], choppy=er[k] < .2, drop=b[1] / a[1] - 1, bounce=z[1] / b[1] - 1,
                                     bars_low_to_high=z[0] - b[0], catch=c[z[3]] / c[k] - 1, bars_held=z[3] - k))
    L = pd.DataFrame(legs); L['catch_net'] = L.catch - COST
    L.to_csv(OUT / 'bounces.csv.gz', index=False)
    rows = []
    for x, g0 in L.groupby('X'):
        for sub, g1 in [('all stocks', g0), ('stock ER20 < 0.2', g0[g0.choppy])]:
            for cnd, g in list(g1.groupby('condition')) + [('all', g1)]:
                if cnd == 'unknown':
                    continue
                rows.append(dict(X=x, stocks=sub, condition=cnd, bounces_per_year=len(g) / YRS, drop_median=g['drop'].median(), bounce_median=g.bounce.median(),
                                 bounce_mean=g.bounce.mean(), bars_low_to_high=g.bars_low_to_high.median(), catch_mean=g.catch.mean(), catch_net_mean=g.catch_net.mean(),
                                 catch_net_median=g.catch_net.median(), share_catch_net_pos=(g.catch_net > 0).mean(), bars_held=g.bars_held.median()))
    R = pd.DataFrame(rows); R.to_csv(OUT / 'bounce_summary.csv', index=False)
    W = pd.concat(width); W = W[W.condition != 'unknown']
    WS = pd.concat([W.groupby('condition').width.median().rename('all stocks'), W[W.choppy].groupby('condition').width.median().rename('stock ER20 < 0.2')], axis=1)
    WS.to_csv(OUT / 'range_width.csv')
    pd.set_option('display.width', 250); print(R.round(3).to_string(index=False)); print(WS.round(3))
