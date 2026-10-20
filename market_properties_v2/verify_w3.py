"""Independent adversarial verification of family W3 (market regime and volatility timing), market-properties v2.

Re-derives the primary tests W3.1-W3.7 of PLAN.md with its own numpy code. It does NOT import w3_regime.py and does
NOT use mpstats.event_series / sort_series / row / Dummy / Mean / Diff; only mpstats.nw and mpstats.ols_nw are used
for HAC t-stats, and ols_nw is cross-checked against an independent slope-HAC implementation.

Inputs: the panel's raw adjusted C, O, V, T (returns and the EW index are rebuilt from them and compared with the
panel's r_cc / idx_ret) and the clean levels lnP, lnO (forward returns fo_h[t] = lnP[t+h] - lnO[t+1] rebuilt here).

Definitions (most literal causal reading of PLAN.md W3; every regime variable is known at the Close of day t):
  idx     EW mean of the clean simple daily returns (C_t / previous tradable C - 1, |r| >= 50% masked) of the universe
          stocks with a return that day; for pre2018 rebuilt from the 80 tickers. Level = cumprod(1 + idx).
  Y_h     forward variable = EW mean over universe stocks of fo_h[t] (raw, entry Open t+1, exit Close t+h).
  W3.1    OLS slope of |idx[t+1]| on |idx[t]| with intercept; NW lags 5.
  W3.2    sigma20[t] = std (ddof 1) of idx[t-19..t]; thresholds = expanding 1/3, 2/3 quantiles (linear) of all
          sigma20 up to and including t once >= 500 sigma20 values exist; top (> q2/3) = 1, bottom (< q1/3) = 0,
          middle excluded; Dummy regression of Y_20; NW lags 20; %.
  W3.3    e[t] = min(1.5, expanding median(sigma20)[t] / sigma20[t]); strategy return e[t] x idx[t+1] vs idx[t+1] on
          the same days; annualised Sharpe difference (ANN = market days per year in MAIN); t = difference / sd of
          2,000 paired CIRCULAR 20-day block bootstrap differences (the analyst used moving blocks, other seed).
  W3.4    level > SMA200(level, t-199..t) = 1 else 0; Dummy on Y_20; lags 20; %.
  W3.5    breadth = share of universe stocks with SMA50 defined (listed for 50 rows) whose lnP[t] exceeds the mean of
          lnP[t-49..t] (computed as mean(lnP[t] - lnP[t-k]) > 0 so a flat price is never 'above'); >= 60% = 1,
          < 40% = 0, middle excluded; Dummy on Y_20; lags 20; %.
  W3.6    dd = level / running max (since 1994) - 1 < -25% = 1 else 0; Dummy on Y_60; lags 60; %.
  W3.7    terciles of the 60-day mean traded value (C x V on tradable days, >= 40 valid of 60 rows) among stocks
          tradable at each month-end Close (>= 15 stocks), applied to rows after that month end through the next one;
          y[t] = EW fo_1 of the bottom tercile (Open->Close of t+1), x[t] = EW r_cc of the top tercile on day t;
          OLS slope; NW lags 5.
Writes results/verify_W3.csv (one row per primary test) and results/verify_W3_detail.csv (sensitivities, claim
checks, backtests, spot checks). Run: python market_properties_v2/verify_w3.py  (about 2-4 minutes).
"""
import bisect
import csv
import math
import pickle
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

warnings.filterwarnings('ignore', message='Mean of empty slice')
warnings.filterwarnings('ignore', message='invalid value encountered')
warnings.filterwarnings('ignore', message='Degrees of freedom')

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from panel import load, universe, SUBPERIODS, MAIN, P0     # noqa: E402
from mpstats import nw, ols_nw                              # noqa: E402

OUT = HERE / 'results'
RAW = ROOT / 'Data' / 'Data kompas 100.csv'
SYM = HERE / 'cache' / 'panel_sym.pkl'
PER = {'MAIN': MAIN, **SUBPERIODS, 'P0': P0}
TESTS = ('W3.1', 'W3.2', 'W3.3', 'W3.4', 'W3.5', 'W3.6', 'W3.7')
SCALE = {'W3.1': 1., 'W3.2': 100., 'W3.3': 1., 'W3.4': 100., 'W3.5': 100., 'W3.6': 100., 'W3.7': 1.}
COSTS = {'0': (0., 0.), 'A': (.0015, .0025), 'B': (.0040, .0050)}   # (buy, sell) per unit of exposure change
STRAY = ('1998-05-15', '2006-03-31', '2008-01-11', '2009-06-06')   # calendar rows with < 10 stocks (artefacts)
DETAIL = []
T0 = time.time()


def note(section, test_id, item, value=np.nan, t=np.nan, n=np.nan, ref=np.nan, comment=''):
    DETAIL.append(dict(section=section, test_id=test_id, item=item, value=value, t=t, n=n, analyst_ref=ref,
                       comment=comment))


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


# ====================================================================================== generic numerics
def rowmean(A):
    """Mean over columns of the finite entries; NaN where none. Returns (mean, count)."""
    ok = np.isfinite(A)
    k = ok.sum(1)
    s = np.where(ok, A, 0.).sum(1)
    out = np.full(len(A), np.nan)
    out[k > 0] = s[k > 0] / k[k > 0]
    return out, k


def shift(x, k):
    """x[t-k] at t (k > 0 lags, k < 0 leads), NaN padded; 1-D or 2-D along axis 0."""
    out = np.full_like(x, np.nan, dtype=float)
    if k > 0:
        out[k:] = x[:-k]
    elif k < 0:
        out[:k] = x[-k:]
    else:
        out[:] = x
    return out


def fwd(lnP, lnO, h):
    """fo_h[t] = lnP[t+h] - lnO[t+1] (entry next Open, exit Close h rows after t)."""
    n = len(lnP)
    out = np.full(lnP.shape, np.nan)
    out[:n - h] = lnP[h:] - lnO[1:n - h + 1]
    return out


def hac_slope(y, x, lags):
    """Independent slope + Newey-West t for y = a + b x (rows with NaN drop out, positions kept)."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    ok = np.isfinite(y) & np.isfinite(x)
    xm, ym = x[ok].mean(), y[ok].mean()
    sxx = ((x[ok] - xm) ** 2).sum()
    b = ((x[ok] - xm) * (y[ok] - ym)).sum() / sxx
    a = ym - b * xm
    u = np.where(ok, (np.where(ok, x, 0.) - xm) * (np.where(ok, y, 0.) - a - b * np.where(ok, x, 0.)), 0.) / sxx
    v = (u * u).sum()
    for k in range(1, lags + 1):
        v += 2 * (1 - k / (lags + 1)) * (u[k:] * u[:-k]).sum()
    return b, b / math.sqrt(v), int(ok.sum())


def sel(cal, a, b):
    return (cal >= pd.Timestamp(a)) & (cal <= pd.Timestamp(b))


def slope_test(y, x, lags, cal, a, b):
    m = sel(cal, a, b)
    ys, xs = y[m], x[m]
    ok = np.isfinite(ys) & np.isfinite(xs)
    if ok.sum() < 20:
        return np.nan, np.nan, int(ok.sum())
    coef, t, n = ols_nw(ys, np.column_stack([np.ones(len(ys)), xs]), lags)
    return coef[1], t[1], n


def dummy_test(y, D, lags, cal, a, b):
    """Effect = mean(y | D=1) - mean(y | D=0) (= OLS dummy coefficient), NW t via ols_nw with positions kept."""
    m = sel(cal, a, b)
    ys, Ds = y[m], D[m]
    ok = np.isfinite(ys) & np.isfinite(Ds)
    if ok.sum() < 20 or len(np.unique(Ds[ok])) < 2:
        return np.nan, np.nan, int(ok.sum())
    eff = ys[ok & (Ds == 1)].mean() - ys[ok & (Ds == 0)].mean()
    coef, t, n = ols_nw(ys, np.column_stack([np.ones(len(ys)), Ds]), lags)
    assert abs(coef[1] - eff) < 1e-9, (coef[1], eff)
    return eff, t[1], n


def expanding_quantiles(x, probs, min_n):
    """Expanding linear-interpolation quantiles of the finite values of x up to and including t (own insertion sort)."""
    out = {p: np.full(len(x), np.nan) for p in probs}
    srt = []
    for t, v in enumerate(x):
        if np.isfinite(v):
            bisect.insort(srt, float(v))
        k = len(srt)
        if k >= min_n:
            for p in probs:
                pos = p * (k - 1)
                lo = int(math.floor(pos))
                hi = min(lo + 1, k - 1)
                out[p][t] = srt[lo] + (pos - lo) * (srt[hi] - srt[lo])
    return out


def rolling_std(x, w):
    out = np.full(len(x), np.nan)
    W = sliding_window_view(x, w)
    out[w - 1:] = W.std(axis=1, ddof=1)          # NaN if any value in the window is NaN
    return out


def rolling_mean_strict(x, w):
    out = np.full(len(x), np.nan)
    out[w - 1:] = sliding_window_view(x, w).mean(axis=1)
    return out


def tri(c1, c0, defined):
    out = np.where(c1, 1., np.where(c0, 0., np.nan))
    return np.where(defined, out, np.nan)


# ====================================================================================== data rebuild
def rebuild_returns(C, O, T, sym=False):
    """Clean returns from raw adjusted Close/Open and the tradable flag: simple close-close (masked), its log,
    intraday log, bad mask. Prev = last tradable Close before t."""
    Ct = C.where(T)
    prev = Ct.ffill().shift(1)
    simple = Ct / prev - 1
    if sym:
        bad = np.log(Ct / prev).abs() >= math.log(1.5)
    else:
        bad = simple.abs() >= .5
    simple = simple.mask(bad)
    r_cc = np.log(Ct / prev).mask(bad)
    r_id = np.log(Ct / O.where(T)).mask(bad)
    r_on = np.log(O.where(T) / prev).mask(bad)
    return dict(simple=simple, r_cc=r_cc, r_id=r_id, r_on=r_on, bad=bad)


def rebuild_levels(C, R):
    listed = C.notna().cumsum() > 0
    lnP = R['r_cc'].fillna(0.).cumsum().where(listed)
    lnO = (lnP.shift(1) + R['r_on'])
    return lnP, lnO


class Uni:
    """All W3 building blocks for one universe (column list) on one panel variant."""

    def __init__(self, D, cols, label, opts=None):
        o = dict(dd_start=None, breadth_tradable_only=False, breadth_price=False, breadth_excl_t=False,
                 q_excl_t=False, q_min=500, vol_rms=False, sma_log=False, sma_excl_t=False,
                 terc_need_tradable=True, terc_same_row=False, terc_split='qcut', idx_override=None)
        o.update(opts or {})
        self.o, self.label, self.cols = o, label, list(cols)
        cal = D['cal']
        self.cal = cal
        c = self.cols
        simple = D['simple'][c].to_numpy()
        self.idx, self.idx_n = rowmean(simple)
        if o['idx_override'] is not None:
            self.idx = o['idx_override']
        lnP = D['lnP'][c].to_numpy()
        lnO = D['lnO'][c].to_numpy()
        self.lnP, self.lnO = lnP, lnO
        Tm = D['T'][c].to_numpy()
        self.T = Tm
        # forward EW means
        self.fo = {h: fwd(lnP, lnO, h) for h in (1, 20, 60)}
        self.Y = {h: rowmean(self.fo[h])[0] for h in (1, 20, 60)}
        self.Yn = {h: rowmean(self.fo[h])[1] for h in (1, 20, 60)}
        # EW intraday simple return (open-exec backtests)
        self.idr = rowmean(np.expm1(lnP - lnO))[0]
        # ---- W3.1/W3.2/W3.3
        ix = self.idx
        if o['vol_rms']:
            W = sliding_window_view(ix, 20)
            self.sig = np.full(len(ix), np.nan)
            self.sig[19:] = np.sqrt((W ** 2).mean(axis=1))
        else:
            self.sig = rolling_std(ix, 20)
        qs = expanding_quantiles(self.sig, (1 / 3, 2 / 3, .5), o['q_min'])
        self.q1, self.q2, self.med = qs[1 / 3], qs[2 / 3], qs[.5]
        if o['q_excl_t']:
            self.q1, self.q2 = shift(self.q1, 1), shift(self.q2, 1)
        defined = np.isfinite(self.q1) & np.isfinite(self.q2) & np.isfinite(self.sig)
        self.D32 = tri(self.sig > self.q2, self.sig < self.q1, defined)
        self.expo = np.minimum(1.5, self.med / self.sig)
        # ---- W3.4 / W3.6
        lvl = np.cumprod(1 + np.where(np.isfinite(ix), ix, 0.))
        self.lvl = lvl
        base = np.log(lvl) if o['sma_log'] else lvl
        sma = rolling_mean_strict(base, 200)
        if o['sma_excl_t']:
            sma = shift(rolling_mean_strict(base, 200), 1)
        self.sma200 = sma
        self.D34 = tri(base > sma, base <= sma, np.isfinite(sma))
        if o['dd_start'] is None:
            run = np.maximum.accumulate(lvl)
            self.dd = lvl / run - 1
        else:
            st = int(np.searchsorted(cal.values, np.datetime64(o['dd_start'])))
            dd = np.full(len(lvl), np.nan)
            dd[st:] = lvl[st:] / np.maximum.accumulate(lvl[st:]) - 1
            self.dd = dd
        self.D36 = tri(self.dd < -.25, self.dd >= -.25, np.isfinite(self.dd))
        # ---- W3.5 breadth (chunked; exact for flat prices)
        self.breadth, self.breadth_n = self._breadth(lnP, Tm)
        br = self.breadth
        self.D35 = tri(br >= .6, br < .4, np.isfinite(br))
        # ---- W3.7
        self._terciles(D, c)
        self.sgn20 = np.sign(np.log(lvl) - np.log(shift(lvl, 20)))

    def _breadth(self, lnP, Tm):
        o = self.o
        n, N = lnP.shape
        X = np.exp(lnP) if o['breadth_price'] else lnP
        above = np.zeros((n, N), bool)
        valid = np.zeros((n, N), bool)
        for s0 in range(49, n, 1000):
            s1 = min(n, s0 + 1000)
            if o['breadth_excl_t']:
                # SMA over t-50..t-1
                lo = s0 - 50
                if lo < 0:
                    continue
                W = sliding_window_view(X[lo:s1 - 1], 50, axis=0)        # windows ending t-1
                cur = X[s0:s1]
            else:
                W = sliding_window_view(X[s0 - 49:s1], 50, axis=0)       # (s1-s0, N, 50), windows ending t
                cur = X[s0:s1]
            diff = (cur[:, :, None] - W).mean(axis=2)                   # lnP[t] - mean(window)
            v = np.isfinite(diff)
            valid[s0:s1] = v
            above[s0:s1] = v & (diff > 0)
        if o['breadth_tradable_only']:
            valid &= Tm
            above &= Tm
        k = valid.sum(1)
        br = np.full(n, np.nan)
        br[k > 0] = above.sum(1)[k > 0] / k[k > 0]
        return br, k

    def _terciles(self, D, c):
        o = self.o
        cal = self.cal
        n = len(cal)
        val = D['value'][c].to_numpy()
        N = val.shape[1]
        v60 = np.full((n, N), np.nan)
        for s0 in range(59, n, 1500):
            s1 = min(n, s0 + 1500)
            W = sliding_window_view(val[s0 - 59:s1], 60, axis=0)         # (s1-s0, N, 60)
            ok = np.isfinite(W)
            cnt = ok.sum(2)
            sm = np.where(ok, W, 0.).sum(2)
            v60[s0:s1] = np.where(cnt >= 40, sm / np.maximum(cnt, 1), np.nan)
        self.v60 = v60
        per = cal.to_period('M')
        is_me = np.r_[per[1:] != per[:-1], True]                          # last market row of each month
        me_rows = np.flatnonzero(is_me)
        lab = np.full((n, N), np.nan)
        Tm = self.T
        self.nsort = {}
        for j, m in enumerate(me_rows):
            s = v60[m].copy()
            elig = np.isfinite(s) & (s > 0)
            if o['terc_need_tradable']:
                elig &= Tm[m]
            k = int(elig.sum())
            self.nsort[cal[m]] = k
            if k < 15:
                continue
            idx = np.flatnonzero(elig)
            order = idx[np.lexsort((idx, s[idx]))]                         # ascending value, ties by column order
            rank = np.empty(k)
            rank[np.searchsorted(idx, order)] = np.arange(1, k + 1)       # rank of each eligible column
            g = np.where(rank <= 1 + (k - 1) / 3, 0, np.where(rank > 1 + 2 * (k - 1) / 3, 2, 1))
            if o['terc_split'] == 'floor':
                nb = k // 3
                g = np.where(rank <= nb, 0, np.where(rank > k - nb, 2, 1))
            r0 = m if o['terc_same_row'] else m + 1
            r1 = me_rows[j + 1] + (0 if not o['terc_same_row'] else -1) if j + 1 < len(me_rows) else n - 1
            if o['terc_same_row']:
                r1 = me_rows[j + 1] - 1 if j + 1 < len(me_rows) else n - 1
            row = np.full(N, np.nan)
            row[idx] = g
            lab[r0:r1 + 1] = row
        self.lab = lab
        small, large = lab == 0, lab == 2
        rcc = D['r_cc'][c].to_numpy()
        self.small, self.large = small, large
        self.y7 = rowmean(np.where(small, self.fo[1], np.nan))[0]
        self.x7, self.n_large = rowmean(np.where(large, rcc, np.nan))
        self.n_small = small.sum(1)
        self.y7_on = rowmean(np.where(small, shift(D['r_on'][c].to_numpy(), -1), np.nan))[0]
        self.y7_cc = rowmean(np.where(small, shift(rcc, -1), np.nan))[0]


# ====================================================================================== tests
ANN = None


def sharpe(r):
    return r.mean() / r.std(ddof=1) * math.sqrt(ANN)


def boot_sharpe_diff(v, c, block=20, reps=2000, seed=777, scheme='circular'):
    n = len(v)
    rng = np.random.default_rng(seed)
    nb = -(-n // block)
    out = np.empty(reps)
    for k0 in range(0, reps, 200):
        m = min(200, reps - k0)
        if scheme == 'circular':
            st = rng.integers(0, n, size=(m, nb))
            ix = ((st[:, :, None] + np.arange(block)) % n).reshape(m, -1)[:, :n]
        else:
            st = rng.integers(0, n - block + 1, size=(m, nb))
            ix = (st[:, :, None] + np.arange(block)).reshape(m, -1)[:, :n]
        bv, bc = v[ix], c[ix]
        out[k0:k0 + m] = (bv.mean(1) / bv.std(1, ddof=1) - bc.mean(1) / bc.std(1, ddof=1)) * math.sqrt(ANN)
    return out


def w33(U, a, b, boot=True, scheme='circular', seed=777, ann=None):
    global ANN
    keep = ANN
    if ann is not None:
        ANN = ann
    rv = shift(U.expo, 1) * U.idx
    rc = U.idx
    m = sel(U.cal, a, b) & np.isfinite(rv) & np.isfinite(rc)
    v, c = rv[m], rc[m]
    d = sharpe(v) - sharpe(c)
    z, sd, lo, hi = np.nan, np.nan, np.nan, np.nan
    if boot and len(v) >= 200:
        bd = boot_sharpe_diff(v, c, scheme=scheme, seed=seed)
        sd = bd.std(ddof=1)
        z = d / sd
        lo, hi = np.percentile(bd, [2.5, 97.5])
    ANN = keep
    return d, z, int(m.sum()), dict(sd=sd, lo=lo, hi=hi, v=v, c=c)


def run_test(tid, U, a, b, lags=None):
    if tid == 'W3.1':
        x = np.abs(U.idx)
        return slope_test(shift(x, -1), x, lags or 5, U.cal, a, b)
    if tid == 'W3.2':
        return dummy_test(U.Y[20], U.D32, lags or 20, U.cal, a, b)
    if tid == 'W3.3':
        d, z, n, _ = w33(U, a, b)
        return d, z, n
    if tid == 'W3.4':
        return dummy_test(U.Y[20], U.D34, lags or 20, U.cal, a, b)
    if tid == 'W3.5':
        return dummy_test(U.Y[20], U.D35, lags or 20, U.cal, a, b)
    if tid == 'W3.6':
        return dummy_test(U.Y[60], U.D36, lags or 60, U.cal, a, b)
    if tid == 'W3.7':
        return slope_test(U.y7, U.x7, lags or 5, U.cal, a, b)
    raise KeyError(tid)


REG = {'W3.2': ('D32', 20), 'W3.4': ('D34', 20), 'W3.5': ('D35', 20), 'W3.6': ('D36', 60)}


# ====================================================================================== backtests
def backtest(e, U, mode='open', cost='B', cash=0.):
    """Daily net simple returns of the EW universe held with exposure e (decided at the Close of t).
    open: change at the Open of t+1 (overnight on the old exposure, intraday on the new one);
    close: change at the Close of t (PLAN W3.3 convention); nextclose: change at the Close of t+1.
    First defined day: position counts as already in place (no change, no cost). cash: annual rate on 1 - exposure
    (negative cash = financing of leverage at the same rate)."""
    e1, e2 = shift(e, 1), shift(e, 2)
    first = np.isfinite(e1) & ~np.isfinite(e2)
    e2 = np.where(first, e1, e2)
    ir, idr = U.idx, np.where(np.isfinite(U.idr), U.idr, 0.)
    if mode == 'close':
        gross, de, held = e1 * ir, e1 - e2, e1
    elif mode == 'open':
        gross, de, held = e2 * ir + (e1 - e2) * idr, e1 - e2, e1
    elif mode == 'nextclose':
        e3 = shift(e, 3)
        e3 = np.where(np.isfinite(e2) & ~np.isfinite(e3), e2, e3)
        gross, de, held = e2 * ir, e2 - e3, e2
    else:
        raise KeyError(mode)
    cb, cs = COSTS[cost]
    net = gross - cb * np.clip(de, 0, None) - cs * np.clip(-de, 0, None)
    if cash:
        net = net + (1 - held) * ((1 + cash) ** (1 / ANN) - 1)
    return net, de, held


def perf(r):
    r = r[np.isfinite(r)]
    n = len(r)
    V = np.cumprod(1 + r)
    peak = np.maximum.accumulate(np.maximum(V, 1.))
    return dict(cagr=V[-1] ** (ANN / n) - 1, mdd=float((V / peak - 1).min()), sharpe=sharpe(r), n=n)


def rules(U):
    one = np.ones(len(U.cal))
    vdef = np.isfinite(U.q1) & np.isfinite(U.sig)
    bdef = np.isfinite(U.breadth)
    return {
        'always_in': one,
        'W3.2:cash_when_vol_bottom_tercile': np.where(vdef, np.where(U.D32 == 0, 0., 1.), np.nan),
        'W3.2:cash_when_vol_top_tercile': np.where(vdef, np.where(U.D32 == 1, 0., 1.), np.nan),
        'W3.3:vol_target_cap1.5': U.expo,
        'W3.3:vol_target_cap1.0': np.minimum(1., U.med / U.sig),
        'W3.4:in_when_above_SMA200': U.D34,
        'W3.4:in_when_below_SMA200': 1 - U.D34,
        'W3.5:cash_when_breadth_lt40': np.where(bdef, np.where(U.D35 == 0, 0., 1.), np.nan),
        'W3.5:cash_when_breadth_ge60': np.where(bdef, np.where(U.D35 == 1, 0., 1.), np.nan),
        'W3.6:in_only_when_dd_lt25': U.D36,
        'W3.6:cash_when_dd_lt25': 1 - U.D36,
    }


def bt_stats(U, e, a, b, mode='open', cost='B', cash=0.):
    net, de, held = backtest(e, U, mode, cost, cash)
    m = sel(U.cal, a, b) & np.isfinite(net)
    base, _, _ = backtest(np.ones(len(U.cal)), U, mode, cost, cash)
    p, pb = perf(net[m]), perf(base[m])
    yrs = m.sum() / ANN
    return dict(cagr=p['cagr'], sharpe=p['sharpe'], mdd=p['mdd'], base_cagr=pb['cagr'], base_sharpe=pb['sharpe'],
                base_mdd=pb['mdd'], expo=float(np.nanmean(held[m])), changes_py=float((np.abs(de[m]) > 1e-12).sum() / yrs),
                n=int(m.sum()), mdd_date=U.cal[m][int(np.argmin(np.cumprod(1 + net[m]) / np.maximum.accumulate(
                    np.maximum(np.cumprod(1 + net[m]), 1.)) - 1))])


# ====================================================================================== panel variants
def make_data(P, sym=False, drop=()):
    C, O, V, T = P['C'], P['O'], P['V'], P['T']
    if drop:
        keep = ~C.index.isin(pd.DatetimeIndex(drop))
        C, O, V, T = C[keep], O[keep], V[keep], T[keep]
    R = rebuild_returns(C, O, T, sym=sym)
    if drop or sym:
        lnP, lnO = rebuild_levels(C, R)
        if sym and not drop:
            # use the stored symmetric panel levels (cross-checked)
            assert np.allclose(np.nan_to_num(lnP.values), np.nan_to_num(P['lnP'].values), atol=1e-9)
            lnP, lnO = P['lnP'], P['lnO']
    else:
        lnP, lnO = P['lnP'], P['lnO']
    value = (C.where(T) * V).where(T)
    return dict(cal=C.index, simple=R['simple'], r_cc=R['r_cc'], r_on=R['r_on'], r_id=R['r_id'], bad=R['bad'],
                lnP=lnP, lnO=lnO, T=T, value=value, C=C)


# ====================================================================================== raw file spot checks
def read_raw(tickers=None):
    rows = {}
    with open(RAW, newline='') as f:
        rd = csv.reader(f)
        hdr = [h.strip() for h in next(rd)]
        it, idt = hdr.index('Ticker'), hdr.index('Date/Time')
        io, ih, il, ic, iv = (hdr.index(k) for k in ('Open', 'High', 'Low', 'Close', 'Volume'))
        for r in rd:
            tk = r[it].strip()
            if tickers is not None and tk not in tickers:
                continue
            d = datetime.strptime(r[idt].strip(), '%d/%m/%Y')
            rows.setdefault(tk, []).append((d, float(r[io]), float(r[ih]), float(r[il]), float(r[ic]), float(r[iv])))
    for tk in rows:
        rows[tk].sort()
    return rows


def spot_checks(P, Ua, raw):
    """Hand computations from the raw CSV rows (python loops, no panel matrices) for individual W3 'events'."""
    cal_raw = sorted({d for tk in raw for (d, *_r) in raw[tk]})
    pos = {d: i for i, d in enumerate(cal_raw)}
    by = {tk: {d: (o, h, l, c, v) for (d, o, h, l, c, v) in raw[tk]} for tk in raw}
    universe_all = sorted(raw)
    out = []

    def prev_trad_close(tk, d):
        i = pos[d] - 1
        while i >= 0:
            x = by[tk].get(cal_raw[i])
            if x is not None and x[4] > 0:
                return x[3]
            i -= 1
        return None

    def simple_ret(tk, d):
        x = by[tk].get(d)
        if x is None or x[4] <= 0:
            return None
        pc = prev_trad_close(tk, d)
        if pc is None:
            return None
        r = x[3] / pc - 1
        return None if abs(r) >= .5 else r

    # S1: idx_ret on chosen days (EW of valid simple returns, all 100 tickers)
    for ds in ('2009-06-06', '2009-06-08', '2015-08-24', '2020-03-09', '2003-04-01'):
        d = datetime.strptime(ds, '%Y-%m-%d')
        rs = [r for tk in universe_all if (r := simple_ret(tk, d)) is not None]
        val = float(np.mean(rs))
        i = Ua.cal.get_loc(pd.Timestamp(ds))
        out.append(('S1 idx_ret', ds, val, Ua.idx[i], P['idx_ret'].iloc[i], len(rs)))
        note('spot', 'W3.1-6', f'S1 idx_ret {ds} raw-hand', val * 100, n=len(rs), ref=float(P['idx_ret'].iloc[i]) * 100,
             comment=f'EW simple return from raw rows by hand vs own idx {Ua.idx[i] * 100:.4f}% (ref = panel idx_ret, %)')

    # S2: W3.5 breadth on chosen days by hand: ln Close carried over market days, 50-row SMA incl. t
    def breadth_hand(ds):
        d = datetime.strptime(ds, '%Y-%m-%d')
        i = pos[d]
        win = cal_raw[i - 49:i + 1]
        n_valid = n_above = 0
        flagged = []
        for tk in universe_all:
            lv = []
            last = None
            started = False
            # carried clean log close; the window must start after listing
            j0 = None
            for dd in cal_raw[:i + 1]:
                x = by[tk].get(dd)
                if x is not None:
                    started = True
                if started and j0 is None:
                    j0 = dd
            if j0 is None or pos[j0] > i - 49:
                continue
            # rebuild clean log level over window with the >= 50% mask (jump removed)
            lvl = 0.
            seq = []
            pc = None
            k0 = pos[j0]
            for dd in cal_raw[k0:i + 1]:
                x = by[tk].get(dd)
                if x is not None and x[4] > 0:
                    if pc is not None:
                        r = x[3] / pc - 1
                        if abs(r) >= .5:
                            flagged.append((tk, dd.date()))
                        else:
                            lvl += math.log(x[3] / pc)
                    pc = x[3]
                seq.append(lvl)
            w = seq[-50:]
            n_valid += 1
            if sum(w[-1] - z for z in w) / 50 > 0:
                n_above += 1
        return n_above / n_valid, n_valid, flagged

    for ds in ('2008-10-10', '2013-06-28', '2019-11-15'):
        br, nv, fl = breadth_hand(ds)
        i = Ua.cal.get_loc(pd.Timestamp(ds))
        out.append(('S2 breadth', ds, br, Ua.breadth[i], np.nan, nv))
        note('spot', 'W3.5', f'S2 breadth {ds} raw-hand', br, n=nv, ref=Ua.breadth[i],
             comment=f'regime own {Ua.D35[i]}; masked jumps inside listing history {len(fl)}; ref = own matrix breadth')

    # S3: W3.7 on a chosen day: month-end sort by hand, x and y by hand
    def w37_hand(ds):
        d = datetime.strptime(ds, '%Y-%m-%d')
        i = pos[d]
        # previous month end strictly before d
        me = None
        for k in range(i - 1, -1, -1):
            if cal_raw[k].month != cal_raw[k + 1].month:
                me = k
                break
        win = cal_raw[me - 59:me + 1]
        vals = {}
        for tk in universe_all:
            x = by[tk].get(cal_raw[me])
            if x is None or x[4] <= 0:
                continue
            vv = [by[tk][dd][3] * by[tk][dd][4] for dd in win if dd in by[tk] and by[tk][dd][4] > 0]
            if len(vv) >= 40 and np.mean(vv) > 0:
                vals[tk] = float(np.mean(vv))
        k = len(vals)
        order = sorted(vals, key=lambda tk: (vals[tk], universe_all.index(tk)))
        small = [tk for r_, tk in enumerate(order, 1) if r_ <= 1 + (k - 1) / 3]
        large = [tk for r_, tk in enumerate(order, 1) if r_ > 1 + 2 * (k - 1) / 3]
        xs = []
        for tk in large:
            r = simple_ret(tk, d)
            if r is not None:
                xs.append(math.log(1 + r))
        dn = cal_raw[i + 1]
        ys = []
        for tk in small:
            x = by[tk].get(dn)
            if x is None or x[4] <= 0:
                continue
            r = simple_ret(tk, dn)
            if r is None:
                continue
            ys.append(math.log(x[3] / x[0]))
        return float(np.mean(xs)), float(np.mean(ys)), len(large), len(ys), cal_raw[me].date(), small, large

    for ds in ('2015-03-10', '2021-07-14'):
        xh, yh, nl, ny, me, small, large = w37_hand(ds)
        i = Ua.cal.get_loc(pd.Timestamp(ds))
        s_own = sorted(np.array(Ua.cols)[Ua.small[i]])
        l_own = sorted(np.array(Ua.cols)[Ua.large[i]])
        same = (s_own == sorted(small)) and (l_own == sorted(large))
        out.append(('S3 W3.7 x', ds, xh, Ua.x7[i], np.nan, nl))
        out.append(('S3 W3.7 y', ds, yh, Ua.y7[i], np.nan, ny))
        note('spot', 'W3.7', f'S3 x (large r_cc) {ds} raw-hand', xh, n=nl, ref=Ua.x7[i],
             comment=f'sort month end {me}; tercile membership identical to own matrix: {same}')
        note('spot', 'W3.7', f'S3 y (small next-day O->C) {ds} raw-hand', yh, n=ny, ref=Ua.y7[i],
             comment=f'small tercile {len(small)} stocks; large {len(large)}')

    # S4: EW fo20 by hand (entry Open t+1, exit Close t+20 carried), clean if no masked jump in the window
    for ds in ('2012-05-15', '2005-03-01'):
        d = datetime.strptime(ds, '%Y-%m-%d')
        i = pos[d]
        d1, d20 = cal_raw[i + 1], cal_raw[i + 20]
        fs, dirty = [], 0
        for tk in universe_all:
            x1 = by[tk].get(d1)
            if x1 is None or x1[4] <= 0:
                continue
            r1 = simple_ret(tk, d1)
            if r1 is None:
                continue                                   # data-error Open day -> no clean entry
            # walk forward from d1 to d20 multiplying clean returns; open->close of d1 then close-close after
            lv = math.log(x1[3] / x1[0])
            pc = x1[3]
            for dd in cal_raw[i + 2:i + 21]:
                x = by[tk].get(dd)
                if x is None or x[4] <= 0:
                    continue
                r = x[3] / pc - 1
                if abs(r) >= .5:
                    dirty += 1
                else:
                    lv += math.log(x[3] / pc)
                pc = x[3]
            fs.append(lv)
        val = float(np.mean(fs))
        i2 = Ua.cal.get_loc(pd.Timestamp(ds))
        out.append(('S4 EW fo20', ds, val, Ua.Y[20][i2], np.nan, len(fs)))
        note('spot', 'W3.2/4/5', f'S4 EW fo20 {ds} raw-hand', val * 100, n=len(fs), ref=Ua.Y[20][i2] * 100,
             comment=f'masked jumps inside windows {dirty}; ref = own Y20 (%)')

    # S5: sigma20 at a date from raw-hand idx returns
    for ds in ('2008-10-28', '2017-03-15'):
        d = datetime.strptime(ds, '%Y-%m-%d')
        i = pos[d]
        rr = []
        for dd in cal_raw[i - 19:i + 1]:
            rs = [r for tk in universe_all if (r := simple_ret(tk, dd)) is not None]
            rr.append(float(np.mean(rs)))
        sh = float(np.std(rr, ddof=1))
        i2 = Ua.cal.get_loc(pd.Timestamp(ds))
        out.append(('S5 sigma20', ds, sh, Ua.sig[i2], np.nan, 20))
        note('spot', 'W3.2/3', f'S5 sigma20 {ds} raw-hand', sh * 100, n=20, ref=Ua.sig[i2] * 100,
             comment=f'own regime D32={Ua.D32[i2]}, q1 {Ua.q1[i2] * 100:.3f}%, q2 {Ua.q2[i2] * 100:.3f}%, '
                     f'exposure {Ua.expo[i2]:.3f}')
    return out


# ====================================================================================== main
def main():
    global ANN
    P = load()
    cal = P['C'].index
    m_main = sel(cal, *MAIN)
    cm = cal[m_main]
    ANN = len(cm) / ((cm[-1] - cm[0]).days / 365.25)
    log('panel loaded; ANN', round(ANN, 2))
    D0 = make_data(P)
    # ---- rebuild checks against the panel
    chk = {}
    chk['r_cc'] = float(np.nanmax(np.abs(D0['r_cc'].values - P['r_cc'].values)))
    chk['r_cc_nan_mismatch'] = int((D0['r_cc'].isna() != P['r_cc'].isna()).values.sum())
    chk['bad_mismatch'] = int((D0['bad'] != P['bad']).values.sum())
    fo20 = fwd(P['lnP'].to_numpy(), P['lnO'].to_numpy(), 20)
    chk['fo20'] = float(np.nanmax(np.abs(fo20 - P['fo'][20].to_numpy())))
    chk['fo20_nan_mismatch'] = int((np.isfinite(fo20) != np.isfinite(P['fo'][20].to_numpy())).sum())
    lnP_r, lnO_r = rebuild_levels(D0['C'], rebuild_returns(P['C'], P['O'], P['T']))
    chk['lnP_rebuild'] = float(np.nanmax(np.abs(lnP_r.values - P['lnP'].values)))
    chk['lnO_rebuild'] = float(np.nanmax(np.abs(lnO_r.values - P['lnO'].values)))
    for k, v in chk.items():
        note('rebuild', 'all', k, v, comment='own rebuild vs panel (max abs diff or mismatch count)')
    log('rebuild checks', chk)
    assert chk['r_cc'] < 1e-12 and chk['r_cc_nan_mismatch'] == 0 and chk['bad_mismatch'] == 0
    assert chk['fo20'] < 1e-12 and chk['fo20_nan_mismatch'] == 0

    cols_all, cols_pre = universe(P, 'all'), universe(P, 'pre2018')
    Ua = Uni(D0, cols_all, 'all')
    Up = Uni(D0, cols_pre, 'pre2018')
    d_idx = np.nanmax(np.abs(Ua.idx - P['idx_ret'].to_numpy()))
    note('rebuild', 'all', 'idx_vs_panel_idx_ret', d_idx, comment='own EW index vs panel idx_ret')
    assert d_idx < 1e-14
    # ols_nw vs independent slope HAC
    for (y, x, L, nm) in ((shift(np.abs(Ua.idx), -1), np.abs(Ua.idx), 5, 'W3.1'), (Ua.y7, Ua.x7, 5, 'W3.7')):
        mm = m_main
        b1, t1, _ = hac_slope(y[mm], x[mm], L)
        b2, t2, _ = slope_test(y, x, L, cal, *MAIN)
        note('rebuild', nm, 'ols_nw_vs_own_hac_t_diff', abs(t1 - t2), comment=f'own HAC t {t1:.4f} vs ols_nw {t2:.4f}')
        assert abs(b1 - b2) < 1e-12 and abs(t1 - t2) < 1e-8
    log('universes built')

    ana = pd.read_csv(OUT / 'W3_tests.csv').set_index('test_id')

    # ---- primary recomputation (all periods, both universes)
    rec = {}
    for tid in TESTS:
        r = {}
        for k, (a, b) in PER.items():
            e, t, n = run_test(tid, Ua, a, b)
            r[k] = (e * SCALE[tid], t, n)
        e, t, n = run_test(tid, Up, *MAIN)
        r['pre2018'] = (e * SCALE[tid], t, n)
        rec[tid] = r
        sg = np.sign(r['MAIN'][0])
        r['signs'] = int(sum(np.sign(r[k][0]) == sg for k in SUBPERIODS))
        for k in list(PER) + ['pre2018']:
            ae = ana.loc[tid, f'eff_{k}']
            at = ana.loc[tid, f't_{k}']
            note('primary', tid, f'eff_{k}', r[k][0], r[k][1], r[k][2], ref=ae,
                 comment=f'analyst t {at:.4f}; diff eff {r[k][0] - ae:+.2e}, t {r[k][1] - at:+.2e}')
        log(tid, 'MAIN', [round(x, 4) for x in r['MAIN']], 'pre2018', [round(x, 4) for x in r['pre2018']],
            'signs', r['signs'], 'analyst', round(ana.loc[tid, 'eff_MAIN'], 4), round(ana.loc[tid, 't_MAIN'], 4))
    return P, D0, Ua, Up, rec, ana


if __name__ == '__main__':
    P, D0, Ua, Up, rec, ana = main()
