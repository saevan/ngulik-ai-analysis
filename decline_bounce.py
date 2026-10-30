"""Decline / bounce anatomy in sideways stocks (plan: decline_bounce_results/PLAN.md). Writes decline_bounce_results/*.csv"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl

OUT = ROOT / 'decline_bounce_results'
BUCK, BL = [0, .05, .10, .15, .20, .30, 9], ['0-5%', '5-10%', '10-15%', '15-20%', '20-30%', '>30%']
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
cal = pd.DatetimeIndex(sorted(st['Date/Time'].unique()))
rng = np.random.default_rng(20261030)


def er20(c):
    cc = pd.Series(c)
    return ((cc - cc.shift(20)).abs() / cc.diff().abs().rolling(20).sum()).to_numpy()


def legs(h, l, c, ok, er, m=3):
    hw = pd.Series(h).rolling(2 * m + 1, center=True).max().to_numpy()
    lw = pd.Series(l).rolling(2 * m + 1, center=True).min().to_numpy()
    piv = sorted([(k, 'H', h[k]) for k in np.flatnonzero(h == hw)] + [(k, 'L', l[k]) for k in np.flatnonzero(l == lw)])
    alt = []
    for p in piv:
        if alt and alt[-1][1] == p[1]:
            if (p[1] == 'H' and p[2] > alt[-1][2]) or (p[1] == 'L' and p[2] < alt[-1][2]):
                alt[-1] = p
        else:
            alt.append(p)
    out = []
    for a, b, e in zip(alt, alt[1:], alt[2:]):
        if a[1] == 'H' and ok[a[0]] and np.isfinite(er[a[0]]):
            out.append((1 - b[2] / a[2], e[2] / b[2] - 1, (e[2] - b[2]) / (a[2] - b[2]) if a[2] > b[2] else np.nan, b[0] - a[0], e[0] - b[0],
                        er[a[0]] < .2))
    return out


real, twin, ev, rnd = [], [], [], []
for t, f in fr.items():
    f = f[f.tradable].reset_index(drop=True)
    n = len(f)
    if n < 300:
        continue
    o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close'])
    d = f['Date/Time'].to_numpy()
    ok = np.isin(d, np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]')) & (d >= np.datetime64('2000-01-01')) & (d <= np.datetime64('2025-08-15'))
    er = er20(c)
    real += [(t,) + x for x in legs(h, l, c, ok, er)]
    r = np.r_[0, np.diff(np.log(c))]
    uh, ul = np.log(h / c), np.log(l / c)
    bad = np.abs(r) >= .4
    r[bad] = 0
    for s in range(3):
        p = rng.permutation(np.arange(1, n))
        p = np.r_[0, p]
        cs = c[0] * np.exp(np.cumsum(r[p]))
        hs, ls = cs * np.exp(uh[p]), cs * np.exp(ul[p])
        twin += [(t,) + x for x in legs(hs, ls, cs, ok, er20(cs))]
    # Part 2: real-time decline triggers
    hh = pd.Series(h).rolling(20).max().to_numpy()
    side = ok & (er < .2)
    for X in (.05, .10, .15, .20):
        below = c <= hh * (1 - X)
        trig = np.flatnonzero(side & below & ~np.r_[False, below[:-1]] & (np.arange(n) + 21 < n))
        for N in (10, 20):
            def fwd(ix):
                e = o[ix + 1]
                win_h = np.array([h[i + 1:i + 1 + N].max() for i in ix]) if len(ix) else np.array([])
                win_l = np.array([l[i + 1:i + 1 + N].min() for i in ix]) if len(ix) else np.array([])
                return win_h / e - 1, win_l / e - 1, c[ix + N] / e - 1
            if len(trig):
                mfe, mae, ret = fwd(trig)
                ev += [dict(ticker=t, date=d[i], X=X, N=N, mfe=a, mae=b, ret=cc_) for i, a, b, cc_ in zip(trig, mfe, mae, ret)]
            pool = np.flatnonzero(side & (np.arange(n) + 21 < n))
            for sd in range(5):
                if len(pool) and len(trig):
                    pick = np.random.default_rng([sd, int(X * 100), N, abs(hash(t)) % 10**6]).choice(pool, min(len(trig), len(pool)), replace=False)
                    mfe, mae, ret = fwd(pick)
                    rnd += [dict(ticker=t, X=X, N=N, mfe=a, mae=b, ret=cc_) for a, b, cc_ in zip(mfe, mae, ret)]
cols = ['ticker', 'decline', 'bounce', 'ratio', 'down_len', 'up_len', 'sideways']
R, Tw = pd.DataFrame(real, columns=cols), pd.DataFrame(twin, columns=cols)


def anatomy(D, label):
    D = D.copy()
    D['bucket'] = pd.cut(D.decline, BUCK, labels=BL)
    g = D.groupby(['sideways', 'bucket'], observed=True)
    return g.agg(legs=('decline', 'size'), median_down_len=('down_len', 'median'), median_bounce=('bounce', 'median'), mean_bounce=('bounce', 'mean'),
                 median_ratio=('ratio', 'median'), p_ratio_ge_half=('ratio', lambda s: (s >= .5).mean()),
                 p_new_high=('ratio', lambda s: (s >= 1).mean())).add_prefix(label + '_')
A = anatomy(R, 'real').join(anatomy(Tw, 'twin'))
A.to_csv(OUT / 'anatomy.csv')
E, Rn = pd.DataFrame(ev), pd.DataFrame(rnd)
S = E.groupby(['X', 'N']).agg(events=('ret', 'size'), mfe=('mfe', 'mean'), mae=('mae', 'mean'), ret=('ret', 'mean'), median_ret=('ret', 'median'),
                               p_mfe_ge_5=('mfe', lambda s: (s >= .05).mean())).join(
    Rn.groupby(['X', 'N']).agg(rnd_mfe=('mfe', 'mean'), rnd_mae=('mae', 'mean'), rnd_ret=('ret', 'mean'), rnd_p_mfe_ge_5=('mfe', lambda s: (s >= .05).mean())))
S['excess_ret'] = S.ret - S.rnd_ret
tt = []
for (X, N), x in E.groupby(['X', 'N']):
    dd = x.groupby('date').ret.mean().reindex(cal[(cal >= '2000') & (cal <= '2025-08-15')]) - Rn[(Rn.X == X) & (Rn.N == N)].ret.mean()
    m, se, _ = nw(dd.to_numpy(), N)
    tt.append(t_ := m / se if se else np.nan)
S['t_excess'] = tt
S.to_csv(OUT / 'realtime.csv')
pd.set_option('display.width', 260); pd.set_option('display.max_columns', 30)
print(A.round(3).to_string()); print((S * [1, 100, 100, 100, 100, 1, 100, 100, 100, 1, 100, 1]).round(2).to_string())
