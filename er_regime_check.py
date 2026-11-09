"""Does ER at day t tell us what happens over t+1..t+20? (plan: er_regime_check_results/PLAN.md). Descriptive only."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy

OUT = Path(__file__).resolve().parent / 'er_regime_check_results'
A, B = '2000-01-01', '2025-08-15'
BINS, LABELS = [-np.inf, .1, .2, .3, .5, np.inf], ['< 0.1', '0.1-0.2', '0.2-0.3', '0.3-0.5', '>= 0.5']


def er(c, n=20):
    return (c - c.shift(n)).abs() / c.diff().abs().rolling(n).sum()


def future_features(c, h=None, l=None):
    r = np.log(c).diff()
    f = pd.DataFrame(index=c.index)
    e = er(c); f['er20'] = e; f['fut_er20'] = e.shift(-20)
    f['fut_ac1'] = r.rolling(20).corr(r.shift(1)).shift(-20)          # uses returns t+1..t+20 (lag pairs inside the window)
    r5 = np.log(c).diff(5)
    v1 = r.rolling(20).var().shift(-20)
    v5 = (np.log(c.shift(-5)) - np.log(c)).rolling(16).var().shift(-15)  # overlapping 5-day returns starting t..t+15, ending by t+20
    f['fut_vr5'] = v5 / (5 * v1)
    past, fut = np.log(c / c.shift(20)), np.log(c.shift(-20) / c)
    f['continuation'] = np.sign(past) * fut
    if h is not None:
        H, L = h.rolling(20).max(), l.rolling(20).min()
        fh, fl = h[::-1].rolling(20).max()[::-1].shift(-1), l[::-1].rolling(20).min()[::-1].shift(-1)
        up, dn = fh > H, fl < L
        f['stay'] = (~up & ~dn).astype(float); f['up_only'] = (up & ~dn).astype(float)
        f['down_only'] = (~up & dn).astype(float); f['both'] = (up & dn).astype(float)
        f['fut_width'] = fh / fl - 1
        f.loc[fh.isna() | H.isna(), ['stay', 'up_only', 'down_only', 'both', 'fut_width']] = np.nan
    return f


def summarize(F, key):
    F = F.dropna(subset=['er20', 'fut_er20'])
    F['bucket'] = pd.cut(F.er20, BINS, labels=LABELS, right=False)
    groups = [(str(k), x) for k, x in F.groupby('bucket', observed=True)] + [('all', F)]
    rows = []
    for k, x in groups:
        d = dict(level=key, er20_bucket=k, days=len(x), share=len(x) / len(F), median_future_er20=x.fut_er20.median(),
                 p_future_er_lt_02=(x.fut_er20 < .2).mean(), p_future_er_ge_03=(x.fut_er20 >= .3).mean(),
                 future_lag1_autocorr=x.fut_ac1.mean(), future_vr5=x.fut_vr5.median(), continuation_pct=x.continuation.mean() * 100)
        if 'stay' in x:
            d.update(stay_in_range=x.stay.mean(), break_up_only=x.up_only.mean(), break_down_only=x.down_only.mean(), break_both=x.both.mean(),
                     median_future_width=x.fut_width.median())
        rows.append(d)
    return rows


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
    parts = []
    with np.errstate(invalid='ignore', divide='ignore'):
        for t, f in fr.items():
            f = f[f.tradable].set_index('Date/Time')
            F = future_features(f.Close, f.High, f.Low)
            ok = F.index.isin(sorted(pit[t] & stale[t])) & (F.index >= A) & (F.index <= B)
            F = F[ok & F.fut_er20.notna()]
            parts.append(F)
        S = pd.concat(parts)
        rows = summarize(S, 'stock')
        rp = regime_proxy(st); M = future_features(rp.proxy)
        M = M[(M.index >= A) & (M.index <= B)]
        rows += summarize(M, 'market')
    R = pd.DataFrame(rows); R.to_csv(OUT / 'er_forward.csv', index=False)
    lab = rp.regime.shift(-1)          # label known before the Open of t+1 = state of the proxy at Close t
    T = pd.DataFrame({'now': lab, 'later': lab.shift(-20)}).loc[A:B].dropna()
    T = T[(T.now != 'unknown') & (T.later != 'unknown')]
    X = pd.crosstab(T.now, T.later, normalize='index'); X.to_csv(OUT / 'regime_transition_20d.csv')
    pd.set_option('display.width', 250)
    print(R.round(3).to_string(index=False)); print(X.round(3))
