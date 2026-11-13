"""Bounces when ER says the stock is choppy: descriptive distribution (plan: choppy_bounces_results/PLAN.md)."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy
from sideways_swings import zigzag

OUT = Path(__file__).resolve().parent / 'choppy_bounces_results'
A, B, COST = '2000-01-01', '2025-08-15', .009
BINS, LAB = [-np.inf, .1, .2, .3, np.inf], ['ER < 0.1', 'ER 0.1-0.2', 'ER 0.2-0.3', 'ER >= 0.3']
SBINS, SLAB = [.03, .05, .07, .10, .15, .20, np.inf], ['3-5%', '5-7%', '7-10%', '10-15%', '15-20%', '> 20%']


def table(g, days):
    b = g.bounce
    return dict(bounces=len(g), per_stock_year=len(g) / (days / 252) if days else np.nan, drop_median=g['drop'].median(),
                bounce_p25=b.quantile(.25), bounce_median=b.median(), bounce_p75=b.quantile(.75), bounce_p90=b.quantile(.9),
                share_ge_5=(b >= .05).mean(), share_ge_10=(b >= .10).mean(), share_ge_20=(b >= .20).mean(), bars_median=g.bars.median(),
                bounce_atr_median=g.bounce_atr.median(), bounce_vs_range_median=g.bounce_vs_range.median(), full_recovery=g.full_recovery.mean(),
                catch_median=g.catch.median(), catch_net_mean=(g.catch - COST).mean(), catch_net_pos=((g.catch - COST) > 0).mean())


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
    lab = regime_proxy(st)['regime']
    legs, days = [], []
    with np.errstate(invalid='ignore', divide='ignore'):
        for t, f in fr.items():
            f = f[f.tradable].reset_index(drop=True)
            c, h, l, d = f.Close.to_numpy(float), f.High.to_numpy(float), f.Low.to_numpy(float), f['Date/Time'].to_numpy()
            C, H, L = pd.Series(c), pd.Series(h), pd.Series(l)
            er = ((C - C.shift(20)).abs() / C.diff().abs().rolling(20).sum()).to_numpy()
            atr = pd.concat([H - L, (H - C.shift()).abs(), (L - C.shift()).abs()], axis=1).max(axis=1).rolling(14).mean().to_numpy()
            width = (H.rolling(20).max() / L.rolling(20).min() - 1).to_numpy()
            okd = np.isin(d, np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]')) & (d >= np.datetime64(A)) & (d <= np.datetime64(B))
            mk = lab.reindex(pd.DatetimeIndex(d)).to_numpy()
            days.append(pd.DataFrame({'er': er[okd], 'sideways': mk[okd] == 'sideways'}))
            for x in (.03, .05, .10):
                p = zigzag(c, x)
                for a, b, z in zip(p, p[1:], p[2:]):
                    if a[2] != 1 or b[2] != -1 or z[2] != 1:
                        continue
                    k = b[3]
                    if not okd[k] or not np.isfinite(er[k]):
                        continue
                    legs.append(dict(X=x, ticker=t, date=d[k], er=er[k], sideways=mk[k] == 'sideways', drop=b[1] / a[1] - 1, bounce=z[1] / b[1] - 1,
                                     bars=z[0] - b[0], bounce_atr=(z[1] - b[1]) / atr[k], bounce_vs_range=(z[1] / b[1] - 1) / width[k],
                                     full_recovery=z[1] >= a[1], catch=c[z[3]] / c[k] - 1, bars_held=z[3] - k))
    Lg = pd.DataFrame(legs); Lg['er_bucket'] = pd.cut(Lg.er, BINS, labels=LAB, right=False)
    Dy = pd.concat(days); Dy = Dy[np.isfinite(Dy.er)]; Dy['er_bucket'] = pd.cut(Dy.er, BINS, labels=LAB, right=False)
    Lg.to_csv(OUT / 'bounces.csv.gz', index=False)
    rows = []
    for x, g0 in Lg.groupby('X'):
        for bk, g in g0.groupby('er_bucket', observed=True):
            rows.append(dict(X=x, state=str(bk), **table(g, (Dy.er_bucket == bk).sum())))
        g = g0[(g0.er < .2)]; rows.append(dict(X=x, state='choppy (ER < 0.2), all markets', **table(g, (Dy.er < .2).sum())))
        g = g0[(g0.er < .2) & g0.sideways]; rows.append(dict(X=x, state='choppy + market sideways', **table(g, ((Dy.er < .2) & Dy.sideways).sum())))
        g = g0[(g0.er >= .2) & g0.sideways]; rows.append(dict(X=x, state='trending stock + market sideways', **table(g, ((Dy.er >= .2) & Dy.sideways).sum())))
    T = pd.DataFrame(rows); T.to_csv(OUT / 'bounce_by_er.csv', index=False)
    hg = Lg[(Lg.X == .03) & (Lg.er < .2)].copy(); hg['bin'] = pd.cut(hg.bounce, SBINS, labels=SLAB, right=False)
    Hs = hg.groupby('bin', observed=True).agg(share=('bounce', lambda s: len(s) / len(hg)), count=('bounce', 'size'), bars_median=('bars', 'median'),
                                              drop_median=('drop', 'median'), catch_net_mean=('catch', lambda s: (s - COST).mean()), catch_net_pos=('catch', lambda s: ((s - COST) > 0).mean()))
    Hs.to_csv(OUT / 'histogram_choppy_3pct.csv')
    pd.set_option('display.width', 320); pd.set_option('display.max_rows', 100)
    print(T.round(3).to_string(index=False)); print(Hs.round(3).to_string())
    print('eligible stock-days by bucket:', Dy.er_bucket.value_counts().sort_index().to_dict(), '| choppy & sideways:', int(((Dy.er < .2) & Dy.sideways).sum()))
