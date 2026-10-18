"""Adversarial, independent re-computation of the pre-registered families A-D (PLAN.md) of market-properties v2.

Nothing is imported from abcd_battery.py, and mpstats.event_series / sort_series / row are NOT used. Only the raw
panel matrices O, H, L, C, V (plus the period constants) are taken from panel.py; returns, clean log levels, forward
returns, equal-weight indices, calendars (turn of month, Lebaran closures, pre-holiday days), rolling signals and
quintile sorts are rebuilt here with numpy. mpstats.nw / mpstats.ols_nw are used for the HAC t-stats (both are
cross-checked against independent implementations below). Six values are verified by hand against the raw CSV.
Interpretive caveats in the output are labelled as observation + hypothesis; they do not change a reproduced number.

Writes results/verify_ABCD.csv. Run: python market_properties_v2/verify_abcd.py  (about 20 seconds)
"""
import csv
import math
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from panel import load, SUBPERIODS, MAIN  # noqa: E402  (data + period constants only)
from mpstats import nw, ols_nw  # noqa: E402  (HAC helpers only)

RAW = ROOT / 'Data' / 'Data kompas 100.csv'
OUT = HERE / 'results' / 'verify_ABCD.csv'
PERIODS = {'MAIN': MAIN, **SUBPERIODS}
SUBS = list(SUBPERIODS)
T0 = time.time()
LOG = []


def say(*a):
    msg = ' '.join(str(x) for x in a)
    LOG.append(msg)
    print(msg, flush=True)


# ============================================================================ base matrices (own construction)
def shift(A, k):
    """Row shift on the market calendar: result[t] = A[t-k] (k>0 looks back, k<0 looks forward)."""
    out = np.full(A.shape, np.nan)
    if k > 0:
        out[k:] = A[:-k]
    elif k < 0:
        out[:k] = A[-k:]
    else:
        out[:] = A
    return out


def roll_sum(Z, w):
    """Trailing w-row sum (rows t-w+1..t); NaN for the first w-1 rows. Z must be NaN-free."""
    c = np.cumsum(np.vstack([np.zeros((1, Z.shape[1])), Z]), axis=0)
    out = np.full(Z.shape, np.nan)
    out[w - 1:] = c[w:] - c[:-w]
    return out


def roll_max(A, w, min_obs):
    """Trailing w-row max ignoring NaN; NaN where fewer than min_obs valid values."""
    ok = np.isfinite(A)
    cnt = roll_sum(ok.astype(float), w)
    out = np.full(A.shape, np.nan)
    X = np.where(ok, A, -np.inf)
    for j in range(A.shape[1]):
        v = np.lib.stride_tricks.sliding_window_view(X[:, j], w)
        out[w - 1:, j] = v.max(axis=1)
    out[~(cnt >= min_obs)] = np.nan
    out[~np.isfinite(out)] = np.nan
    return out


class Base:
    """Returns, clean levels and forward returns rebuilt from the raw panel O/H/L/C/V matrices."""

    def __init__(self, P, drop_dates=()):
        keep = ~P['C'].index.isin(pd.to_datetime(list(drop_dates)))
        self.dates = P['C'].index[keep]
        self.tick = np.array(P['C'].columns)
        O, H, L, C, V = (P[k].to_numpy(float)[keep] for k in ['O', 'H', 'L', 'C', 'V'])
        n, m = C.shape
        self.n, self.m = n, m
        T = np.isfinite(C) & (np.nan_to_num(V) > 0)
        rows = np.arange(n)[:, None]
        last_t = np.maximum.accumulate(np.where(T, rows, -1), axis=0)       # last tradable row <= t
        prev_t = np.vstack([np.full((1, m), -1), last_t[:-1]])               # last tradable row <= t-1
        colix = np.arange(m)[None, :]
        prevC = np.where(prev_t >= 0, C[np.clip(prev_t, 0, None), colix], np.nan)
        cff = np.where(last_t >= 0, C[np.clip(last_t, 0, None), colix], np.nan)
        with np.errstate(divide='ignore', invalid='ignore'):
            simple = np.where(T, C / prevC - 1, np.nan)
            bad = np.abs(np.nan_to_num(simple)) >= .5
            good = T & ~bad
            rcc = np.where(good & np.isfinite(prevC), np.log(C / prevC), np.nan)
            ron = np.where(good & np.isfinite(prevC), np.log(O / prevC), np.nan)
            rid = np.where(good, np.log(C / O), np.nan)
            listed = np.maximum.accumulate(np.isfinite(C), axis=0)
            lnP = np.where(listed, np.cumsum(np.nan_to_num(rcc), axis=0), np.nan)
            lnO = np.where(T & np.isfinite(ron), shift(lnP, 1) + ron, np.nan)
            lnH = np.where(T, lnP + np.log(H / C), np.nan)
        self.O, self.H, self.L, self.C, self.V, self.T = O, H, L, C, V, T
        self.prevC, self.cff, self.bad, self.simple = prevC, cff, bad, np.where(bad, np.nan, simple)
        self.rcc, self.ron, self.rid, self.lnP, self.lnO, self.lnH = rcc, ron, rid, lnP, lnO, lnH
        self.value = np.where(T, C * V, np.nan)
        self._fo = {}
        first = np.array([self.dates[np.flatnonzero(np.isfinite(C[:, j]))[0]] for j in range(m)])
        self.first = pd.Series(first, index=self.tick)
        post = self.first >= pd.Timestamp('2018-01-01')
        self.ucols = {'all': np.arange(m), 'pre2018': np.flatnonzero(~post.values)}
        self.post2018 = sorted(self.tick[post.values])
        self._idx = {}

    def fo(self, h):
        """fo[h] at row t = lnP[t+h] - lnO[t+1]: buy next Open (tradable then), exit Close t+h (last tradable carried)."""
        if h not in self._fo:
            self._fo[h] = shift(self.lnP, -h) - shift(self.lnO, -1)
        return self._fo[h]

    def idx(self, u):
        """Equal-weight daily simple return of universe u (bad prints excluded)."""
        if u not in self._idx:
            S = self.simple[:, self.ucols[u]]
            cnt = np.isfinite(S).sum(1)
            self._idx[u] = np.where(cnt > 0, np.nansum(S, 1) / np.maximum(cnt, 1), np.nan)
        return self._idx[u]

    def ser(self, x):
        return pd.Series(x, index=self.dates)


def xs_mean(M, valid=None):
    """Cross-sectional mean per row over finite (and valid) entries; NaN if none."""
    ok = np.isfinite(M) if valid is None else (valid & np.isfinite(M))
    cnt = ok.sum(1)
    return np.where(cnt > 0, np.where(ok, M, 0.).sum(1) / np.maximum(cnt, 1), np.nan)


# ============================================================================ statistics wrappers
def own_nw_se(x, lags):
    """Independent Newey-West SE of the mean (missing -> zero contribution at its position)."""
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    n = ok.sum()
    e = np.zeros(len(x))
    e[ok] = x[ok] - x[ok].mean()
    lrv = np.dot(e, e)
    for k in range(1, lags + 1):
        lrv += 2. * (1. - k / (lags + 1.)) * np.dot(e[k:], e[:-k])
    return math.sqrt(lrv) / n


def own_ols_hac_t(y, X, lags):
    """Independent OLS + Newey-West (Bartlett) sandwich; rows with NaN keep their position (zero score)."""
    ok = np.isfinite(y) & np.isfinite(X).all(1)
    Xo, yo = X[ok], y[ok]
    beta = np.linalg.lstsq(Xo, yo, rcond=None)[0]
    g = np.zeros_like(X)
    g[ok] = Xo * (yo - Xo @ beta)[:, None]
    S = g.T @ g
    for k in range(1, lags + 1):
        w = 1. - k / (lags + 1.)
        G = g[k:].T @ g[:-k]
        S += w * (G + G.T)
    A = np.linalg.inv(Xo.T @ Xo)
    return beta, beta / np.sqrt(np.diag(A @ S @ A))


def mean_stat(s, lags):
    def at(a, b):
        m, se, n = nw(s.loc[a:b].values, lags)
        return m, (m / se if se and se > 0 else np.nan), n
    return at


def dummy_stat(y, D, lags):
    def at(a, b):
        yy = y.loc[a:b]
        dd = D.reindex(yy.index).loc[a:b].astype(float)
        X = np.column_stack([np.ones(len(dd)), dd.values])
        b_, t_, n_ = ols_nw(yy.values, X, lags)
        return b_[1], t_[1], n_
    return at


def slope_stat(y, x, lags):
    def at(a, b):
        yy = y.loc[a:b]
        xx = x.reindex(yy.index).loc[a:b]
        b_, t_, n_ = ols_nw(yy.values, np.column_stack([np.ones(len(xx)), xx.values]), lags)
        return b_[1], t_[1], n_
    return at


def evaluate(make, scale):
    """make(u) -> at(a,b). Returns dict with MAIN all eff/t, pre2018 eff/t and P1-P4 effects."""
    st = make('all')
    r = {}
    for k, (a, b) in PERIODS.items():
        m, t, n = st(a, b)
        r[f'eff_{k}'], r[f't_{k}'], r[f'n_{k}'] = m * scale, t, n
    m, t, n = make('pre2018')(*MAIN)
    r['eff_pre'], r['t_pre'] = m * scale, t
    r['signs'] = ''.join('+' if r[f'eff_{k}'] > 0 else ('-' if r[f'eff_{k}'] < 0 else '0') for k in SUBS)
    return r


# ============================================================================ family A
def fam_a(B, lag_mult=1, zero_sign='keep', need_T=True):
    out = {}
    lnP, T = B.lnP, B.T

    def tsmom(u, past, h):
        c = B.ucols[u]
        s = np.sign(past[:, c])
        if need_T:
            s = np.where(T[:, c], s, np.nan)
        if zero_sign == 'drop':
            s = np.where(s == 0, np.nan, s)
        y = B.fo(h)[:, c]
        return B.ser(xs_mean(s * y))

    specs = {'A1.1': (B.rcc, 1, 5, 1e4),
             'A1.2': (lnP - shift(lnP, 5), 5, 5, 100),
             'A1.3': (lnP - shift(lnP, 20), 20, 20, 100),
             'A1.4': (lnP - shift(lnP, 60), 20, 20, 100),
             'A1.5': (shift(lnP, 21) - shift(lnP, 141), 20, 20, 100),
             'A1.6': (shift(lnP, 21) - shift(lnP, 252), 20, 20, 100)}
    for tid, (past, h, lags, sc) in specs.items():
        L = lags if tid == 'A1.1' else lags * lag_mult
        out[tid] = evaluate(lambda u, past=past, h=h, L=L: mean_stat(tsmom(u, past, h), L), sc)
    # A1.7 index AC1
    out['A1.7'] = evaluate(lambda u: slope_stat(B.ser(shift(B.idx(u), -1)), B.ser(B.idx(u)), 5), 1.)

    # A1.8 index TSMOM(20,20)
    def idx_ts(u):
        lvl = np.cumsum(np.log1p(np.nan_to_num(B.idx(u))))
        s = np.sign(lvl - shift(lvl[:, None], 20)[:, 0])
        y = xs_mean(B.fo(20)[:, B.ucols[u]])
        return B.ser(s * y)
    out['A1.8'] = evaluate(lambda u: mean_stat(idx_ts(u), 20 * lag_mult), 100)
    return out


# ============================================================================ family B
def fam_b(B, lag_mult=1, max_abs_ron=None):
    out = {}
    ron, rid = B.ron, B.rid
    out['B1'] = evaluate(lambda u: mean_stat(B.ser(xs_mean(ron[:, B.ucols[u]])), 5), 1e4)
    out['B2'] = evaluate(lambda u: mean_stat(B.ser(xs_mean(rid[:, B.ucols[u]])), 5), 1e4)

    def same_day(u, up):
        c = B.ucols[u]
        r_on, r_id = ron[:, c], rid[:, c]
        ab = r_id - xs_mean(r_id)[:, None]
        with np.errstate(invalid='ignore'):
            ev = (r_on > np.log(1.02)) if up else (r_on < np.log(.98))
        if max_abs_ron is not None:
            ev = ev & (np.abs(np.nan_to_num(r_on)) <= max_abs_ron)
        ev = ev & np.isfinite(r_id)
        return B.ser(xs_mean(ab, ev))
    out['B3'] = evaluate(lambda u: mean_stat(same_day(u, True), 5), 1e4)
    out['B4'] = evaluate(lambda u: mean_stat(same_day(u, False), 5), 1e4)

    def gap_fwd(u, up):
        c = B.ucols[u]
        r_on = ron[:, c]
        F = B.fo(5)[:, c]
        ab = F - xs_mean(F)[:, None]
        with np.errstate(invalid='ignore'):
            ev = ((r_on > np.log(1.02)) if up else (r_on < np.log(.98))) & B.T[:, c]
        if max_abs_ron is not None:
            ev = ev & (np.abs(np.nan_to_num(r_on)) <= max_abs_ron)
        return B.ser(xs_mean(ab, ev))
    out['B5'] = evaluate(lambda u: mean_stat(gap_fwd(u, True), 5 * lag_mult), 100)
    out['B6'] = evaluate(lambda u: mean_stat(gap_fwd(u, False), 5 * lag_mult), 100)
    return out


# ============================================================================ family C (own calendar)
def own_calendar(dates, longest='weekdays'):
    """Turn of month, closures, Lebaran pre/post windows and pre-holiday flags on the market calendar `dates`."""
    d = list(pd.to_datetime(dates))
    n = len(d)
    # turn of month: last trading day of each month + first 3 trading days
    tom = np.zeros(n, bool)
    start = 0
    for i in range(1, n + 1):
        if i == n or (d[i].year, d[i].month) != (d[start].year, d[start].month):
            tom[start:min(start + 3, i)] = True
            tom[i - 1] = True
            start = i
    # closures: consecutive market dates with >= 1 weekday strictly between them
    clos = []
    for i in range(n - 1):
        a, b = d[i], d[i + 1]
        between = [a + timedelta(days=k) for k in range(1, (b - a).days)]
        wk = sum(1 for x in between if x.weekday() < 5)
        if wk >= 1:
            xmas = any((x.month == 12 and x.day >= 24) or (x.month == 1 and x.day <= 2) for x in between)
            clos.append(dict(i0=i, i1=i + 1, d0=a, d1=b, weekdays=wk, caldays=(b - a).days - 1, xmas=xmas))
    cl = pd.DataFrame(clos)
    pre_h = np.zeros(n, bool)
    pre_h[cl.i0.values] = True
    leb = {}
    for _, r in cl[~cl.xmas].iterrows():
        y = r.d0.year
        key = r.weekdays if longest == 'weekdays' else r.caldays
        if y not in leb or key > leb[y][0]:          # strict '>' keeps the earliest closure on ties
            leb[y] = (key, r)
    pre_l = np.zeros(n, bool)
    post_l = np.zeros(n, bool)
    chosen = []
    for y, (_, r) in sorted(leb.items()):
        pre_l[max(0, r.i0 - 4):r.i0 + 1] = True
        post_l[r.i1:r.i1 + 5] = True
        chosen.append((y, r.d0.date(), r.d1.date(), r.weekdays, r.caldays))
    dw = np.array([x.weekday() for x in d])
    mo = np.array([x.month for x in d])
    flags = {'C1': tom, 'C2': dw == 0, 'C3': dw == 4, 'C4': mo == 12, 'C5': mo == 1, 'C6': pre_l, 'C7': post_l,
             'C8': pre_h}
    return flags, chosen, cl


def fam_c(B, longest='weekdays', drop_rows=None):
    flags, chosen, cl = own_calendar(B.dates, longest)
    out = {}
    for tid, D in flags.items():
        def make(u, D=D):
            y = B.ser(B.idx(u))
            if drop_rows is not None:
                y = y.copy()
                y[y.index.isin(drop_rows)] = np.nan
            return dummy_stat(y, pd.Series(D, index=B.dates), 5)
        out[tid] = evaluate(make, 1e4)
    return out, flags, chosen, cl


# ============================================================================ family D (own sorts)
def rebalance_rows(dates, freq):
    if freq == 'M':
        key = np.asarray(dates.year * 100 + dates.month)
    else:   # week ending Friday (Saturday..Friday), the Friday on or after the date
        key = np.asarray((dates + pd.to_timedelta((4 - dates.dayofweek) % 7, unit='D')).values)
    is_last = np.r_[key[1:] != key[:-1], True]
    return np.flatnonzero(is_last)


def sort_series_own(B, sig, u, freq='M', nq=5, min_n=25, tie='first', bounds='floor'):
    """Quintile sort at each rebalance Close (stock tradable, signal finite), hold next Open -> next rebalance Close.
    bounds='floor': i-th smallest (0-based) -> floor(i*5/k) (own convention, extra stocks go to the lower groups);
    bounds='qcut' : rank r (1-based) -> ceil((r-1)*5/(k-1)) - 1, floor 0 (= equal-width bins on ranks 1..k, which is
    what pandas.qcut on ranks does), written here in integer arithmetic."""
    c = B.ucols[u]
    rows = rebalance_rows(B.dates, freq)
    rec = []
    for i0, i1 in zip(rows[:-1], rows[1:]):
        s = sig[i0, c]
        ret = B.lnP[i1, c] - B.lnO[i0 + 1, c]
        ok = np.isfinite(s) & B.T[i0, c] & np.isfinite(ret)
        k = int(ok.sum())
        if k < min_n:
            continue
        sv, rv = s[ok], ret[ok]
        if tie == 'first':     # ties by column (ticker) order
            order = np.argsort(sv, kind='mergesort')
        else:                  # ties by reverse ticker order
            order = np.lexsort((-np.arange(k), sv))
        q = np.empty(k, int)
        if bounds == 'floor':
            q[order] = (np.arange(k) * nq) // k
        else:
            rk = np.arange(1, k + 1)
            q[order] = np.maximum(((rk - 1) * nq + (k - 1) - 1) // (k - 1) - 1, 0)
        top, bot = rv[q == nq - 1].mean(), rv[q == 0].mean()
        rec.append((B.dates[i0], top - bot, top - rv.mean(), k))
    df = pd.DataFrame(rec, columns=['date', 'hl', 'top_ex', 'n']).set_index('date')
    return df


def d_signals(B, u, d6_min=200, d8_min=15, d10_mode='traded40'):
    lnP, lnH, r = B.lnP, B.lnH, B.rcc
    ok_r = np.isfinite(r)
    sig = {}
    sig['D1'] = shift(lnP, 21) - shift(lnP, 252)
    sig['D2'] = shift(lnP, 21) - shift(lnP, 141)
    sig['D3'] = shift(lnP, 21) - shift(lnP, 84)
    sig['D4'] = lnP - shift(lnP, 21)
    sig['D5'] = lnP - shift(lnP, 5)
    sig['D6'] = lnP - roll_max(lnH, 252, d6_min)
    # D7 volatility: sample std of r_cc over 60 rows, >= 40 obs
    n60 = roll_sum(ok_r.astype(float), 60)
    s1 = roll_sum(np.where(ok_r, r, 0.), 60)
    s2 = roll_sum(np.where(ok_r, r * r, 0.), 60)
    with np.errstate(invalid='ignore', divide='ignore'):
        var = (s2 - s1 * s1 / n60) / (n60 - 1)
        sig['D7'] = np.where(n60 >= 40, np.sqrt(np.maximum(var, 0)), np.nan)
    sig['D8'] = roll_max(r, 21, d8_min)
    # D9 Amihud: mean |simple| / value over 60 rows, >= 40 obs
    with np.errstate(invalid='ignore', divide='ignore'):
        am = np.abs(B.simple) / B.value
    ok_a = np.isfinite(am)
    na = roll_sum(ok_a.astype(float), 60)
    sa = roll_sum(np.where(ok_a, am, 0.), 60)
    with np.errstate(invalid='ignore', divide='ignore'):
        sig['D9'] = np.where(na >= 40, sa / na, np.nan)
    # D10 liquidity: log mean traded value over 60 rows
    v = B.value
    if d10_mode == 'traded40':          # mean over traded days, >= 40 traded days (battery reading)
        ok_v = np.isfinite(v)
        nv, sv = roll_sum(ok_v.astype(float), 60), roll_sum(np.where(ok_v, v, 0.), 60)
        with np.errstate(invalid='ignore', divide='ignore'):
            sig['D10'] = np.where(nv >= 40, np.log(sv / nv), np.nan)
    else:                               # zero-volume listed days count as zero value (60 listed days)
        listed = np.isfinite(B.lnP)
        vz = np.where(listed, np.nan_to_num(v), np.nan)
        ok_v = np.isfinite(vz)
        nv, sv = roll_sum(ok_v.astype(float), 60), roll_sum(np.where(ok_v, vz, 0.), 60)
        with np.errstate(invalid='ignore', divide='ignore'):
            sig['D10'] = np.where((nv >= 60) & (sv > 0), np.log(sv / nv), np.nan)
    # D11 signed ER60
    dl = np.abs(lnP - shift(lnP, 1))
    ok_d = np.isfinite(dl)
    nd = roll_sum(ok_d.astype(float), 60)
    sd = roll_sum(np.where(ok_d, dl, 0.), 60)
    with np.errstate(invalid='ignore', divide='ignore'):
        sig['D11'] = np.where(nd >= 60, (lnP - shift(lnP, 60)) / sd, np.nan)
    sig['D11'][~np.isfinite(sig['D11'])] = np.nan
    # D12 beta of r_cc on log(1+idx_u), 60 rows, >= 40 paired obs
    x = np.log1p(B.idx(u))[:, None] * np.ones((1, B.m))
    okp = ok_r & np.isfinite(x)
    X, Y = np.where(okp, x, 0.), np.where(okp, r, 0.)
    nb = roll_sum(okp.astype(float), 60)
    sx, sy, sxy, sxx = (roll_sum(z, 60) for z in (X, Y, X * Y, X * X))
    with np.errstate(invalid='ignore', divide='ignore'):
        beta = (sxy - sx * sy / nb) / (sxx - sx * sx / nb)
    sig['D12'] = np.where(nb >= 40, beta, np.nan)
    return sig


D_FREQ = {k: ('W' if k == 'D5' else 'M') for k in ['D%d' % i for i in range(1, 13)]}


def fam_d(B, tie='first', bounds='floor', **kw):
    out, series = {}, {}
    sigs = {u: d_signals(B, u, **kw) for u in ('all', 'pre2018')}
    for tid in D_FREQ:
        ss = {u: sort_series_own(B, sigs[u][tid], u, D_FREQ[tid], tie=tie, bounds=bounds) for u in ('all', 'pre2018')}
        series[tid] = ss
        out[tid] = evaluate(lambda u, ss=ss: mean_stat(ss[u].hl, 2), 100)
    return out, series


# ============================================================================ raw-CSV spot checks (by hand)
def read_raw(tickers, all_from, all_to):
    """Full history of `tickers` plus every ticker's rows between all_from and all_to (csv module, no pandas)."""
    rows, dates, window = {}, set(), {}
    with open(RAW, newline='') as f:
        rd = csv.reader(f)
        next(rd)
        for t, dt, o, h, l, c, v in rd:
            if ':' in dt:          # one intraday row (TLKM 19/08/2025 08:58) is excluded by the loader too
                continue
            d = datetime.strptime(dt.strip(), '%d/%m/%Y')
            dates.add(d)
            rec = (float(o), float(h), float(l), float(c), float(v))
            if t in tickers:
                rows[(t, d)] = rec
            if all_from <= d <= all_to:
                window[(t, d)] = rec
    return rows, sorted(dates), window


def spot_checks(B, P):
    tick = ['BBCA', 'TLKM', 'ASII']
    raw, cal, win = read_raw(set(tick), datetime(2020, 1, 1), datetime(2020, 3, 31))
    pos = {d: i for i, d in enumerate(cal)}
    ti = {t: i for i, t in enumerate(B.tick)}
    res = []

    def last_tradable_close(t, i, src=raw):
        while i >= 0:
            r = src.get((t, cal[i]))
            if r and r[4] > 0:
                return r[3], cal[i]
            i -= 1
        return None, None

    assert len(cal) == len(B.dates) and all(pd.Timestamp(a) == b for a, b in zip(cal, B.dates)), 'calendar mismatch'
    # S1: BBCA overnight / intraday on its first gap-down (< -2%) day of 2015
    j = ti['BBCA']
    i = next(i for i in range(len(cal)) if cal[i].year == 2015 and np.isfinite(B.ron[i, j]) and B.ron[i, j] < np.log(.98))
    o, h, l, c, v = raw[('BBCA', cal[i])]
    pc, pd_ = last_tradable_close('BBCA', i - 1)
    r_on, r_id = math.log(o / pc), math.log(c / o)
    say(f'SPOT-1 BBCA {cal[i].date()}: raw O={o} C={c}, prev tradable C={pc} ({pd_.date()}) -> r_on={r_on:.6f} '
        f'r_id={r_id:.6f}; own {B.ron[i, j]:.6f}/{B.rid[i, j]:.6f}; panel {P["r_on"].iloc[i, j]:.6f}/{P["r_id"].iloc[i, j]:.6f}')
    res.append(('SPOT-1', f'BBCA {cal[i].date()} r_on of a gap-down event (B4/B6): raw O={o}, prev C={pc}', r_on,
                P['r_on'].iloc[i, j]))
    # S2: TLKM fo[5] at 2019-03-15: entry Open of next market day, exit last tradable Close at/before t+5
    j = ti['TLKM']
    i = pos[datetime(2019, 3, 15)]
    o1 = raw[('TLKM', cal[i + 1])][0]
    c5, d5 = last_tradable_close('TLKM', i + 5)
    fo5 = math.log(c5 / o1)
    say(f'SPOT-2 TLKM fo[5] at 2019-03-15: O[{cal[i + 1].date()}]={o1}, C[{d5.date()}]={c5} -> {fo5:.6f}; own '
        f'{B.fo(5)[i, j]:.6f}; panel {P["fo"][5].iloc[i, j]:.6f}')
    res.append(('SPOT-2', f'TLKM fo[5] at 2019-03-15 = ln(C[{d5.date()}]={c5} / O[{cal[i + 1].date()}]={o1})', fo5,
                P['fo'][5].iloc[i, j]))
    # S3/S4: ASII MOM12-1 (D1) at month-end 2015-06-30 and its holding return to 2015-07-31
    j = ti['ASII']
    i = pos[datetime(2015, 6, 30)]
    ca, _ = last_tradable_close('ASII', i - 21)
    cb, _ = last_tradable_close('ASII', i - 252)
    mom = math.log(ca / cb)
    i1 = pos[datetime(2015, 7, 31)]
    oe = raw[('ASII', cal[i + 1])][0]
    cx, _ = last_tradable_close('ASII', i1)
    hold = math.log(cx / oe)
    sig = d_signals(B, 'all')['D1']
    say(f'SPOT-3 ASII D1 at 2015-06-30: ln(C[{cal[i - 21].date()}]/C[{cal[i - 252].date()}]) = ln({ca}/{cb}) = {mom:.6f}; '
        f'own {sig[i, j]:.6f}; panel lnP-based {P["lnP"].iloc[i - 21, j] - P["lnP"].iloc[i - 252, j]:.6f}. Hold '
        f'O[{cal[i + 1].date()}]={oe} -> C[{cal[i1].date()}]={cx}: {hold:.6f}; own {B.lnP[i1, j] - B.lnO[i + 1, j]:.6f}')
    res.append(('SPOT-3', f'ASII MOM12-1 (D1) at 2015-06-30 = ln({ca}/{cb}) (Closes 21 and 252 market days back)', mom,
                P['lnP'].iloc[i - 21, j] - P['lnP'].iloc[i - 252, j]))
    res.append(('SPOT-4', f'ASII Jul-2015 holding return (D sorts) = ln(C 2015-07-31={cx} / O 2015-07-01={oe})', hold,
                P['lnP'].iloc[i1, j] - P['lnO'].iloc[i + 1, j]))
    # S5: Lebaran 2019 closure from the raw calendar
    a = max(d for d in cal if datetime(2019, 5, 25) <= d <= datetime(2019, 6, 4))
    b = min(d for d in cal if datetime(2019, 6, 4) <= d <= datetime(2019, 6, 20))
    say(f'SPOT-5 raw calendar: last trading day before Eid-2019 closure {a.date()}, first after {b.date()}')
    flags, _, _ = own_calendar(B.dates)
    pre_dates = [str(x.date()) for x in B.dates[flags['C6']] if x.year == 2019]
    post_dates = [str(x.date()) for x in B.dates[flags['C7']] if x.year == 2019]
    ok5 = pre_dates[-1] == str(a.date()) and post_dates[0] == str(b.date()) and len(pre_dates) == len(post_dates) == 5
    res.append(('SPOT-5', f'Lebaran 2019 closure {a.date()} -> {b.date()} from the raw calendar; C6 days {pre_dates}, '
                f'C7 days {post_dates}', 1. if ok5 else 0., 1.))
    # S6: equal-weight index return on 2020-03-24, by hand over every ticker in the raw file
    d = datetime(2020, 3, 24)
    i = pos[d]
    rets = []
    for t in B.tick:
        r = win.get((t, d))
        if not r or r[4] <= 0:
            continue
        pc, _ = last_tradable_close(t, i - 1, win)
        if pc is None:
            continue
        s = r[3] / pc - 1
        if abs(s) < .5:
            rets.append(s)
    ew = sum(rets) / len(rets)
    say(f'SPOT-6 EW index return 2020-03-24 by hand: {ew:.6f} over {len(rets)} stocks; panel idx_ret '
        f'{P["idx_ret"].loc["2020-03-24"]:.6f}; own {B.idx("all")[i]:.6f}')
    res.append(('SPOT-6', f'EW index (idx_ret) on 2020-03-24 by hand over {len(rets)} tradable tickers', ew,
                float(P['idx_ret'].loc['2020-03-24'])))
    return res


# ============================================================================ main
def material(e, t, e0, t0, abs_tol):
    changed = abs(e - e0) > max(.10 * abs(e0), abs_tol) or (abs(t - t0) > .5 and abs(t - t0) > .1 * abs(t0))
    flips = ((abs(t) >= 3) != (abs(t0) >= 3)) or (np.sign(e) != np.sign(e0))
    return changed, flips


def main():
    P = load()
    B = Base(P)
    say(f'base built {time.time() - T0:.1f}s; days {B.n} tickers {B.m}; own post2018 == panel post2018: '
        f'{B.post2018 == sorted(P["post2018"])}')
    # ---- panel cross-check (own construction vs panel.py)
    chk = {}
    for k, mine in [('T', B.T), ('r_cc', B.rcc), ('r_on', B.ron), ('r_id', B.rid), ('lnP', B.lnP), ('lnO', B.lnO),
                    ('lnH', B.lnH), ('value', B.value)]:
        pv = P[k].to_numpy(float)
        if k == 'T':
            chk[k] = (np.array_equal(pv.astype(bool), mine), 0.)
            continue
        both = np.isfinite(pv) & np.isfinite(mine)
        d_ = np.where(both, (pv - mine) / (pv if k == 'value' else 1.), 0.)
        chk[k] = (np.array_equal(np.isfinite(pv), np.isfinite(mine)), float(np.abs(d_).max()))
    for h in (1, 5, 20):
        pv, mine = P['fo'][h].to_numpy(float), B.fo(h)
        both = np.isfinite(pv) & np.isfinite(mine)
        chk[f'fo{h}'] = (np.array_equal(np.isfinite(pv), np.isfinite(mine)), float(np.abs(np.where(both, pv - mine, 0.)).max()))
    chk['idx_ret'] = (True, float(np.nanmax(np.abs(P['idx_ret'].to_numpy() - B.idx('all')))))
    say('panel cross-check (same NaN pattern, max abs diff):', {k: (a, f'{b:.2e}') for k, (a, b) in chk.items()})
    panel_ok = all(a and b < 1e-9 for a, b in chk.values())
    rs = np.random.default_rng(1).normal(size=3000)
    rs[::7] = np.nan
    m_, se_, _ = nw(rs, 20)
    say(f'nw cross-check: mpstats se {se_:.6e} vs own {own_nw_se(rs, 20):.6e}')
    yy = B.idx('all')
    DD = np.array([d.weekday() == 0 for d in B.dates], float)
    X_ = np.column_stack([np.ones(B.n), DD])
    b1, t1, _ = ols_nw(yy, X_, 5)
    b2, t2 = own_ols_hac_t(yy, X_, 5)
    say(f'ols_nw cross-check (idx on Monday dummy, full sample): mpstats b={b1[1]:.8f} t={t1[1]:.4f}; own b={b2[1]:.8f} t={t2[1]:.4f}')

    bat = pd.concat([pd.read_csv(HERE / 'results' / f'{f}_tests.csv') for f in 'ABCD'], ignore_index=True).set_index('test_id')

    # ---- recompute families
    res = {}
    res.update(fam_a(B))
    res.update(fam_b(B))
    c_res, flags, chosen, cl = fam_c(B)
    res.update(c_res)
    d_res, d_series = fam_d(B)
    res.update(d_res)
    d_qc, _ = fam_d(B, bounds='qcut')
    say(f'families recomputed {time.time() - T0:.1f}s')

    # ---- sensitivities / robustness (label, eff, t)
    sens = {k: [] for k in res}
    always = {k: [] for k in res}
    a2, b2 = fam_a(B, lag_mult=2), fam_b(B, lag_mult=2)
    for k in ['A1.2', 'A1.3', 'A1.4', 'A1.5', 'A1.6', 'A1.8']:
        always[k].append((f'NW lags 2h={2 * (5 if k == "A1.2" else 20)}', a2[k]['eff_MAIN'], a2[k]['t_MAIN']))
    for k in ['B5', 'B6']:
        always[k].append(('NW lags 2h=10', b2[k]['eff_MAIN'], b2[k]['t_MAIN']))
    az = fam_a(B, zero_sign='drop')
    for k in ['A1.1', 'A1.2', 'A1.3', 'A1.4', 'A1.5', 'A1.6']:
        sens[k].append(('stock-days with sign 0 dropped instead of counted as 0', az[k]['eff_MAIN'], az[k]['t_MAIN']))
    an = fam_a(B, need_T=False)
    for k in ['A1.2', 'A1.3', 'A1.4', 'A1.5', 'A1.6']:
        sens[k].append(('no tradable-at-t filter on the signal', an[k]['eff_MAIN'], an[k]['t_MAIN']))
    bx = fam_b(B, max_abs_ron=.25)
    for k in ['B3', 'B4', 'B5', 'B6']:
        sens[k].append(('events with |r_on|>25% (suspect opens) excluded', bx[k]['eff_MAIN'], bx[k]['t_MAIN']))
    spurious = pd.to_datetime(['2008-01-11', '2009-06-06'])
    cs, _, _, _ = fam_c(B, drop_rows=spurious)
    for k in cs:
        sens[k].append(('single-ticker dates 2008-01-11/2009-06-06 dropped from the regression', cs[k]['eff_MAIN'], cs[k]['t_MAIN']))
    cc, _, chosen_cal, _ = fam_c(B, longest='caldays')
    for k in ['C6', 'C7']:
        sens[k].append(('longest closure by calendar days', cc[k]['eff_MAIN'], cc[k]['t_MAIN']))
    B2 = Base(P, drop_dates=spurious)
    a_cl, b_cl = fam_a(B2), fam_b(B2)
    d_cl, _ = fam_d(B2)
    for src in (a_cl, b_cl, d_cl):
        for k in src:
            sens[k].append(('calendar rebuilt without the single-ticker dates', src[k]['eff_MAIN'], src[k]['t_MAIN']))
    d_tie, _ = fam_d(B, tie='reverse')
    for k in d_tie:
        sens[k].append(('reverse tie-break', d_tie[k]['eff_MAIN'], d_tie[k]['t_MAIN']))
    d_lit, _ = fam_d(B, d6_min=1, d8_min=1)
    d_full, _ = fam_d(B, d6_min=252, d8_min=21)
    for k in ['D6', 'D8']:
        always[k].append(('no min-obs (literal PLAN text)', d_lit[k]['eff_MAIN'], d_lit[k]['t_MAIN']))
        always[k].append(('full window required', d_full[k]['eff_MAIN'], d_full[k]['t_MAIN']))
    d_z, _ = fam_d(B, d10_mode='zero')
    always['D10'].append(('zero-volume listed days count as 0 traded value', d_z['D10']['eff_MAIN'], d_z['D10']['t_MAIN']))
    say(f'sensitivities done {time.time() - T0:.1f}s')

    # ---- diagnostics for the audit
    me_dates = B.dates[rebalance_rows(B.dates, 'M')]
    me_main = me_dates[(me_dates >= MAIN[0]) & (me_dates < B.dates[-1])]
    for tid in D_FREQ:
        if D_FREQ[tid] == 'M':
            miss = [str(d.date()) for d in me_main if d not in d_series[tid]['all'].index]
            say(f'{tid}: MAIN formation month-ends {len(me_main)}, used {len(me_main) - len(miss)}, skipped {miss[:8]}'
                + (' ...' if len(miss) > 8 else ''))
    say('Lebaran closures chosen (weekdays rule, MAIN):', [(y, str(a), str(b), w) for y, a, b, w, _ in chosen if y >= 2000])
    diffs = [(x, y) for x, y in zip(chosen, chosen_cal) if (x[1], x[2]) != (y[1], y[2])]
    say('years where a calendar-day "longest" rule picks another closure:', [(x[0], str(x[1]), str(y[1])) for x, y in diffs])
    say('days flagged in MAIN:', {k: int(pd.Series(v, index=B.dates).loc[MAIN[0]:MAIN[1]].sum()) for k, v in flags.items()})
    for k in sorted(res):
        for lab, e, t in always.get(k, []) + sens.get(k, []):
            say(f'  sens {k:5s} {lab:70s} eff {e:9.4f} t {t:7.2f}   (base eff {res[k]["eff_MAIN"]:.4f} t {res[k]["t_MAIN"]:.2f})')

    ctx = pd.read_csv(HERE / 'results' / 'ABCD_context.csv')
    cval = {(r.test_id, r.item): r.value for r in ctx.itertuples()}
    win = (B.dates >= MAIN[0]) & (B.dates <= MAIN[1])
    with np.errstate(invalid='ignore'):
        gu = (B.ron > np.log(1.02)) & np.isfinite(B.rid)
        gd = (B.ron < np.log(.98)) & np.isfinite(B.rid)
        gu5 = (B.ron > np.log(1.02)) & B.T & np.isfinite(B.fo(5))
        gd5 = (B.ron < np.log(.98)) & B.T & np.isfinite(B.fo(5))
    pre = B.ucols['pre2018']
    counts = {('B3', 'all_events_MAIN'): int(gu[win].sum()), ('B4', 'all_events_MAIN'): int(gd[win].sum()),
              ('B3', 'pre2018_events_MAIN'): int(gu[win][:, pre].sum()), ('B4', 'pre2018_events_MAIN'): int(gd[win][:, pre].sum()),
              ('B5', 'all_events'): int(gu5.sum()), ('B6', 'all_events'): int(gd5.sum()),
              ('B5', 'pre2018_events'): int(gu5[:, pre].sum()), ('B6', 'pre2018_events'): int(gd5[:, pre].sum())}
    for k, v in flags.items():
        counts[(k, 'days_flagged_MAIN')] = int(v[win].sum())
    cmp_ = {f'{a}:{b}': (v, int(float(cval.get((a, b), -1)))) for (a, b), v in counts.items()}
    say('event / flag counts own vs ABCD_context:', cmp_)
    count_ok = all(a == b for a, b in cmp_.values())
    ab = B.rid - xs_mean(B.rid)[:, None]
    open_low = B.O <= B.L * (1 + 1e-12)
    open_high = B.O >= B.H * (1 - 1e-12)
    split = {}
    for lab, ev in [('B4 open==low', gd & open_low), ('B4 open>low', gd & ~open_low),
                    ('B3 open==high', gu & open_high), ('B3 open<high', gu & ~open_high)]:
        m, t, n = mean_stat(B.ser(xs_mean(ab, ev)), 5)(*MAIN)
        split[lab] = (m * 1e4, t, int(ev[win].sum()))
    say('own Open-extreme split (MAIN, all, abnormal intraday bps, t, events):',
        {k: (round(a, 1), round(b, 2), c) for k, (a, b, c) in split.items()})
    spots = spot_checks(B, P)

    # ---- compare and write
    unit = {**{k: 'pct' for k in ['A1.2', 'A1.3', 'A1.4', 'A1.5', 'A1.6', 'A1.8', 'B5', 'B6'] + list(D_FREQ)},
            **{k: 'bps' for k in ['A1.1', 'B1', 'B2', 'B3', 'B4'] + ['C%d' % i for i in range(1, 9)]}, 'A1.7': 'slope'}
    tol_abs = {'pct': .05, 'bps': 1., 'slope': .005}
    a11 = pd.Series(xs_mean(np.where(B.T, np.sign(B.rcc), np.nan) * B.fo(1)), index=B.dates)
    we = B.dates[rebalance_rows(B.dates, 'W')]
    we_main = we[(we >= MAIN[0]) & (we < B.dates[-1])]
    d5_skip = int(sum(d not in d_series['D5']['all'].index for d in we_main))
    zero_share = float((B.rcc[win] == 0).sum() / np.isfinite(B.rcc[win]).sum())
    sub_c = {k: res[k]['eff_MAIN'] - cs[k]['eff_MAIN'] for k in cs}
    NOTES = {
        'A1.1': (f'single-ticker calendar dates (only CTRA has bars on 2008-01-11 and Saturday 2009-06-06, the latter '
                 f'O 373.39 H 460.79 C 413.12) make the A1.1 value of 2009-06-05 {a11.loc["2009-06-05"] * 1e4:.0f} bps and of '
                 f'2008-01-09 {a11.loc["2008-01-09"] * 1e4:.0f} bps from CTRA alone; rebuilt without those dates eff '
                 f'{a_cl["A1.1"]["eff_MAIN"]:.2f} t {a_cl["A1.1"]["t_MAIN"]:.2f} (inside tolerance); literal PLAN formula counts '
                 f'sign-0 stock-days as 0 ({zero_share:.0%} of MAIN stock-days have r_cc = 0), so {res["A1.1"]["eff_MAIN"]:.2f} '
                 f'bps is per stock-day incl. zeros; the P4 reversal ({res["A1.1"]["eff_P4"]:.2f}) is not a zero-share '
                 f'artifact (fewer zeros in P4 would raise, not lower, the measured effect)'),
        'A1.7': (f'hypothesis, not tested here: a positive AC1 of an equal-weight index of thin stocks is the textbook '
                 f'non-synchronous-trading signature; observation: P4 {res["A1.7"]["eff_P4"]:.3f}; close-to-close, '
                 f'descriptive only (as labelled)'),
        'B5': (f'fails the pre2018 criterion as reported ({res["B5"]["eff_pre"]:.3f} < 50% of {res["B5"]["eff_MAIN"]:.3f}): '
               f'about half of the MAIN gap-up drift comes from the 20 post-2018 listings'),
        'B6': ('entry next Open, so the same-day Open-print mechanics of B3/B4 do not enter; hypothesis: survivorship can '
               'inflate post-gap-down recoveries (stocks that kept falling and delisted are absent from the file)'),
        **{k: (f'single-ticker dates 2008-01-11/2009-06-06 enter idx_ret as one-stock returns; dropping them moves the '
               f'effect by {-sub_c[k]:+.2f} bps/day (inside tolerance)') for k in sub_c},
        **{k: ('the 2006-03-31 month-end (day after the 2006-03-30 closure) has 8 of 49 listed stocks tradable, so every '
               'monthly sort skips the Apr-2006 holding month; the other skipped month-ends (2000-2003) have < 25 eligible '
               'stocks, as pre-registered') for k in D_FREQ if D_FREQ[k] == 'M'},
        'D5': (f'weekly sort skips {d5_skip} of {len(we_main)} MAIN weeks, incl. formations on 2006-03-31 (8 tradable), '
               '2008-01-11 (only CTRA) and 2009-06-05 (next market day is the spurious Saturday 2009-06-06, so no stock but '
               'CTRA has an entry Open)'),
    }
    NOTES['D6'] = NOTES['D6'] + (f'; min 200 valid lnH in 252 rows is not in PLAN: it leaves {res["D6"]["n_MAIN"]} months '
                                 f'(vs {res["D4"]["n_MAIN"]} for D4), dropping 2002-2003; PLAN-literal and full-window '
                                 f'readings stay insignificant')
    NOTES['D8'] = NOTES['D8'] + '; min 15 obs in 21 rows is not in PLAN; insignificant under every reading'
    NOTES['D10'] = NOTES['D10'] + (f'; PLAN gives no min-obs for D10 (battery: >= 40 traded days, zero-volume days '
                                   f'excluded); counting zero-volume days as 0 value gives {d_z["D10"]["eff_MAIN"]:.2f} '
                                   f'(t {d_z["D10"]["t_MAIN"]:.2f})')
    rows = []
    order = ['A1.%d' % i for i in range(1, 9)] + ['B%d' % i for i in range(1, 7)] + ['C%d' % i for i in range(1, 9)] + list(D_FREQ)
    for tid in order:
        r, b = res[tid], bat.loc[tid]
        ta = tol_abs[unit[tid]]
        within = lambda x, y: abs(x - y) <= max(.10 * abs(y), ta)
        e_ok, t_ok, p_ok = within(r['eff_MAIN'], b.eff_MAIN), abs(r['t_MAIN'] - b.t_MAIN) <= .5, within(r['eff_pre'], b.eff_pre2018)
        bsig = ''.join('+' if b[f'eff_{k}'] > 0 else '-' for k in SUBS)
        s_ok = bsig == r['signs']
        issues, caveat = [], []
        if not e_ok:
            issues.append(f'MAIN effect differs ({r["eff_MAIN"]:.4f} vs battery {b.eff_MAIN:.4f})')
        if not t_ok:
            issues.append(f'MAIN t differs ({r["t_MAIN"]:.2f} vs battery {b.t_MAIN:.2f})')
        if not p_ok:
            issues.append(f'pre2018 effect differs ({r["eff_pre"]:.4f} vs battery {b.eff_pre2018:.4f})')
        if not s_ok:
            issues.append(f'subperiod signs differ ({r["signs"]} vs battery {bsig})')
        if int(r['n_MAIN']) != int(b.n_MAIN):
            issues.append(f'n differs ({int(r["n_MAIN"])} vs battery {int(b.n_MAIN)})')
        explained = False
        if tid in d_qc:
            q = d_qc[tid]
            q_ok = (within(q['eff_MAIN'], b.eff_MAIN) and abs(q['t_MAIN'] - b.t_MAIN) <= .5 and within(q['eff_pre'], b.eff_pre2018)
                    and q['signs'] == bsig)
            issues.append(f'own floor-quintile sort vs qcut-style bounds (own integer code): eff {q["eff_MAIN"]:.4f} t '
                          f'{q["t_MAIN"]:.2f} pre2018 {q["eff_pre"]:.4f} n {q["n_MAIN"]} -> qcut-style '
                          + ('reproduces the battery' if q_ok else 'does NOT reproduce the battery'))
            explained = q_ok and not (e_ok and t_ok and p_ok and s_ok)
            if explained:
                caveat.append('difference is only the quintile boundary convention (PLAN says "quintiles" without a rule; '
                              'both readings defensible); effect not distinguishable from 0 either way'
                              if abs(r['t_MAIN']) < 2 and abs(q['t_MAIN']) < 2 else
                              'difference is only the quintile boundary convention')
        for lab, e, t in always[tid]:
            ch, fl = material(e, t, r['eff_MAIN'], r['t_MAIN'], ta)
            issues.append(f'[{lab}] eff {e:.4f} t {t:.2f}' + (' -> flips |t|>=3 or sign' if fl else ''))
            if fl:
                caveat.append(f'{lab} flips the |t|>=3 criterion or sign')
        for lab, e, t in sens[tid]:
            ch, fl = material(e, t, r['eff_MAIN'], r['t_MAIN'], ta)
            if ch or fl:
                issues.append(f'sensitivity [{lab}]: eff {e:.4f} t {t:.2f}' + (' -> flips |t|>=3 or sign' if fl else ''))
                if fl:
                    caveat.append(f'{lab} flips the |t|>=3 criterion or sign')
        if tid in ('B3', 'B4'):
            k1, k2 = ('B4 open==low', 'B4 open>low') if tid == 'B4' else ('B3 open==high', 'B3 open<high')
            caveat.append(f'numbers reproduce; observation: the whole effect sits in events whose Open print is the day\'s '
                          f'extreme: own split {k1} {split[k1][0]:.0f} bps (t {split[k1][1]:.1f}, {split[k1][2]} ev) vs {k2} '
                          f'{split[k2][0]:.0f} bps (t {split[k2][1]:.1f}, {split[k2][2]} ev); interpretation (hypothesis): '
                          f'noise in the Open enters r_on and r_id with opposite signs, so the same-day reversal is a property '
                          f'of the Open print rather than a post-gap drift; logic: a rule that conditions on the Open print '
                          f'cannot also be sure to trade at it (main session X-B4-e: -182 bps net after tick+slippage+fees)')
        if tid in ('D9', 'D10'):
            caveat.append('numbers reproduce; hypothesis (cannot be tested with this file): the universe is today\'s Kompas100, '
                          'selected on recent liquidity/size and back-filled to 2000, so stocks that were illiquid at formation '
                          'are in the file because they later became liquid/large, which favours the illiquid quintile ex post; '
                          'observation consistent with it: the magnitude grows toward the selection date (P1..P4 '
                          f'{r["eff_P1"]:.2f}/{r["eff_P2"]:.2f}/{r["eff_P3"]:.2f}/{r["eff_P4"]:.2f} %/month); the pre2018 check '
                          'cannot detect this bias (the two universes are identical before 2018)')
        if tid.startswith('B') and not count_ok:
            issues.append('event counts differ from ABCD_context')
        if tid in NOTES:
            issues.append('NOTE: ' + NOTES[tid])
        if e_ok and t_ok and p_ok and s_ok:
            verdict = 'confirmed_with_caveat' if caveat else 'confirmed'
        else:
            verdict = 'confirmed_with_caveat' if explained else 'refuted'
        if caveat:
            issues.append('CAVEAT: ' + ' | '.join(caveat))
        rows.append(dict(test_id=tid, battery_eff=b.eff_MAIN, battery_t=b.t_MAIN, recomputed_eff=r['eff_MAIN'],
                         recomputed_t=r['t_MAIN'], recomputed_eff_pre2018=r['eff_pre'], verdict=verdict,
                         issues='; '.join(issues), unit=unit[tid], battery_eff_pre2018=b.eff_pre2018,
                         recomputed_t_pre2018=r['t_pre'], battery_signs_P1_P4=bsig, recomputed_signs_P1_P4=r['signs'],
                         recomputed_eff_P1=r['eff_P1'], recomputed_eff_P2=r['eff_P2'], recomputed_eff_P3=r['eff_P3'],
                         recomputed_eff_P4=r['eff_P4'], battery_n_MAIN=int(b.n_MAIN), recomputed_n_MAIN=int(r['n_MAIN']),
                         qcut_style_eff=d_qc[tid]['eff_MAIN'] if tid in d_qc else np.nan,
                         qcut_style_t=d_qc[tid]['t_MAIN'] if tid in d_qc else np.nan,
                         qcut_style_eff_pre2018=d_qc[tid]['eff_pre'] if tid in d_qc else np.nan))
    for sid, desc, raw_v, panel_v in spots:
        ok = abs(raw_v - panel_v) < 1e-9
        rows.append(dict(test_id=sid, battery_eff=panel_v, battery_t=np.nan, recomputed_eff=raw_v, recomputed_t=np.nan,
                         recomputed_eff_pre2018=np.nan, verdict='confirmed' if ok else 'refuted',
                         issues=f'raw-CSV spot check by hand: {desc} (battery_eff = panel/flag value, recomputed_eff = '
                                f'from the raw CSV rows)'))
    rows.append(dict(test_id='PANEL', battery_eff=np.nan, battery_t=np.nan, recomputed_eff=np.nan, recomputed_t=np.nan,
                     recomputed_eff_pre2018=np.nan, verdict='confirmed' if panel_ok else 'refuted',
                     issues='own rebuild of T, r_cc, r_on, r_id, lnP, lnO, lnH, value, fo[1,5,20], idx_ret from O/H/L/C/V vs '
                            'panel.py: ' + ', '.join(f'{k} same-NaN={a} maxdiff={b:.1e}' for k, (a, b) in chk.items())))
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    pd.set_option('display.width', 250)
    pd.set_option('display.max_colwidth', 600)
    say(out[['test_id', 'battery_eff', 'recomputed_eff', 'battery_t', 'recomputed_t', 'battery_eff_pre2018',
             'recomputed_eff_pre2018', 'battery_signs_P1_P4', 'recomputed_signs_P1_P4', 'qcut_style_eff', 'verdict']]
        .round(4).to_string(index=False))
    for _, r in out.iterrows():
        if r.issues:
            say(f'{r.test_id}: {r.issues}')
    say(f'total runtime {time.time() - T0:.1f}s; wrote {OUT}')


if __name__ == '__main__':
    main()
