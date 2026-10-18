"""Statistics helpers for market-properties v2 (numpy only).

t-stats are Newey-West (Bartlett) HAC on a series indexed by consecutive market days or rebalance dates; NaN = no
observation. Missing points contribute zero to every autocovariance, so a lag k always means k index positions.
Event tests aggregate per day first (mean over that day's events), which removes same-day cross-sectional
correlation from the t-stat; overlapping h-day windows are covered by lags >= h.
Differences between two event groups use t = (mA - mB) / sqrt(seA^2 + seB^2); positive covariance between groups
is ignored, which makes the test conservative.
"""
import math
import numpy as np
import pandas as pd
from panel import SUBPERIODS, MAIN, P0, universe

PERIODS = {'MAIN': MAIN, **SUBPERIODS, 'P0': P0}
COST_RT = {'A': .0040, 'B': .0090}   # round trip: fee .15% buy + .25% sell (A); A + .25% slippage per side (B)


def nw(x, lags):
    """(mean, standard error of the mean, n) with Newey-West lags; x may contain NaN."""
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    n = int(ok.sum())
    if n < 20:
        return np.nan, np.nan, n
    m = x[ok].mean()
    e = np.where(ok, x - m, 0.)
    v = (e * e).sum()
    for k in range(1, min(lags, len(e) - 1) + 1):
        v += 2 * (1 - k / (lags + 1)) * (e[k:] * e[:-k]).sum()
    return m, math.sqrt(max(v, 0.)) / n, n


def pval(t):
    return math.erfc(abs(t) / math.sqrt(2)) if np.isfinite(t) else np.nan


def bh_fdr(p):
    """Benjamini-Hochberg q-values (NaN kept)."""
    p = np.asarray(p, float)
    q = np.full(len(p), np.nan)
    ok = np.isfinite(p)
    ps = p[ok]
    order = np.argsort(ps)
    ranked = ps[order] * len(ps) / (np.arange(len(ps)) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(len(ps))
    out[order] = np.minimum(ranked, 1)
    q[ok] = out
    return q


def ols_nw(y, X, lags):
    """OLS coefficients, NW t-stats, n. Rows with NaN drop out but keep their position for the lag structure."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    ok = np.isfinite(y) & np.isfinite(X).all(1)
    Xo, yo = X[ok], y[ok]
    XtX = Xo.T @ Xo
    b = np.linalg.solve(XtX, Xo.T @ yo)
    u = np.zeros(len(y))
    u[ok] = yo - Xo @ b
    g = np.where(ok[:, None], X, 0.) * u[:, None]
    S = g.T @ g
    for k in range(1, lags + 1):
        G = g[k:].T @ g[:-k]
        S += (1 - k / (lags + 1)) * (G + G.T)
    iX = np.linalg.inv(XtX)
    se = np.sqrt(np.diag(iX @ S @ iX))
    return b, b / se, int(ok.sum())


class Mean:
    """Mean of a series (e.g. daily mean abnormal return of events)."""
    def __init__(self, s, lags):
        self.s, self.lags = s, lags

    def at(self, a, b):
        m, se, n = nw(self.s.loc[a:b], self.lags)
        return m, (m / se if se and se > 0 else np.nan), n


class Diff:
    """Difference of the means of two series (group A minus group B)."""
    def __init__(self, sa, sb, lags):
        self.sa, self.sb, self.lags = sa, sb, lags

    def at(self, a, b):
        ma, sea, na = nw(self.sa.loc[a:b], self.lags)
        mb, seb, nb = nw(self.sb.loc[a:b], self.lags)
        se = math.sqrt(sea ** 2 + seb ** 2) if np.isfinite(sea) and np.isfinite(seb) else np.nan
        return ma - mb, ((ma - mb) / se if se and se > 0 else np.nan), min(na, nb)


class Dummy:
    """y = a + b*D on a continuous series; effect = b (mean when D minus mean when not D)."""
    def __init__(self, y, D, lags):
        self.y, self.D, self.lags = y, D.astype(float), lags

    def at(self, a, b):
        y, D = self.y.loc[a:b], self.D.reindex(self.y.index).loc[a:b]
        if D.notna().sum() < 20 or D.nunique() < 2:
            return np.nan, np.nan, 0
        coef, t, n = ols_nw(y.values, np.column_stack([np.ones(len(D)), D.values]), self.lags)
        return coef[1], t[1], n


def event_series(P, mask, h, univ='all', adjust=True, base='fo'):
    """Daily mean (over that day's events) of the h-day forward return from next Open; abnormal = minus the same-day
    equal-weight mean of all stocks in the universe with a valid forward return. Returns (series, n_events)."""
    cols = universe(P, univ)
    F = P[base][h][cols]
    if adjust:
        F = F.sub(F.mean(axis=1), axis=0)
    M = mask.reindex(index=F.index, columns=cols).fillna(False).astype(bool) & F.notna()
    return F.where(M).mean(axis=1), int(M.values.sum())


def rebalance_dates(P, freq='M'):
    idx = P['C'].index
    key = idx.to_period('M') if freq == 'M' else idx.to_period('W-FRI')
    return pd.Series(idx, index=idx).groupby(key).max().tolist()


def sort_series(P, signal, univ='all', n=5, freq='M', min_stocks=25):
    """Sort stocks on `signal` at each rebalance Close (stock tradable that day), hold from next Open to the next
    rebalance Close. Returns DataFrame indexed by rebalance date: q0..q{n-1} means, hl (top-bottom), top_ex, bot_ex
    (top/bottom minus the universe mean), n_stocks."""
    dates = rebalance_dates(P, freq)
    cols = universe(P, univ)
    lnC = P['lnP'][cols]
    lnOn = P['lnO'][cols].shift(-1)
    T = P['T'][cols]
    S = signal.reindex(index=P['C'].index, columns=cols)
    rows = []
    for d0, d1 in zip(dates[:-1], dates[1:]):
        sig = S.loc[d0].where(T.loc[d0])
        fwd = lnC.loc[d1] - lnOn.loc[d0]
        ok = sig.notna() & fwd.notna()
        if ok.sum() < min_stocks:
            continue
        q = pd.qcut(sig[ok].rank(method='first'), n, labels=False)
        g = fwd[ok].groupby(q).mean()
        allm = fwd[ok].mean()
        rows.append(dict(date=d0, **{f'q{i}': g.iloc[i] for i in range(n)}, hl=g.iloc[-1] - g.iloc[0],
                         top_ex=g.iloc[-1] - allm, bot_ex=g.iloc[0] - allm, n_stocks=int(ok.sum())))
    return pd.DataFrame(rows).set_index('date')


def row(test_id, family, desc, unit, stat_all, stat_pre, scale=1., cost_note='', surv_risk='', exploit='', notes=''):
    """Standard result row. stat_* are Mean/Diff/Dummy objects (or None). Effects are multiplied by `scale`."""
    r = dict(test_id=test_id, family=family, description=desc, unit=unit)
    for k, (a, b) in PERIODS.items():
        m, t, n = stat_all.at(a, b)
        r[f'eff_{k}'], r[f't_{k}'], r[f'n_{k}'] = m * scale, t, n
    if stat_pre is not None:
        m, t, n = stat_pre.at(*MAIN)
        r['eff_pre2018'], r['t_pre2018'], r['n_pre2018'] = m * scale, t, n
    sgn = np.sign(r['eff_MAIN'])
    r['signs_P1_P4'] = int(sum(np.sign(r[f'eff_{k}']) == sgn for k in SUBPERIODS))
    r['p_MAIN'] = pval(r['t_MAIN'])
    r['pass_t3'] = bool(abs(r['t_MAIN']) >= 3) if np.isfinite(r['t_MAIN']) else False
    r['pass_stable'] = r['signs_P1_P4'] >= 3
    r['pass_pre2018'] = bool(np.sign(r.get('eff_pre2018', np.nan)) == sgn and abs(r.get('eff_pre2018', 0)) >= .5 * abs(r['eff_MAIN']))
    r.update(cost_note=cost_note, survivorship_risk=surv_risk, exploit_type=exploit, notes=notes)
    return r
