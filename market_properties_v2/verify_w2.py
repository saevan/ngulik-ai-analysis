"""Independent adversarial verification of family W2 (trade path after breakout entries), market-properties v2.

Re-derives the primary tests W2.1-W2.5 of PLAN.md from the panel's clean levels. It does NOT import w2_tradepath.py
and does NOT use mpstats.event_series / sort_series / row; only mpstats.nw (Newey-West) is used, and nw itself is
cross-checked against an independent autocovariance implementation. The implementation path differs on purpose
from the analyst's: per-ticker numpy sliding windows for the signal, explicit per-event loops for the path-dependent
parts (W2.3 trigger, W2.5 trailing exit), per-event benchmark rows, bincount day means.

Definitions (most literal causal reading of PLAN.md):
  Entry  W1.1 Close breakout lnP[t] > max(lnH[t-20..t-1]) (market days, non-tradable days have no High and are
         skipped; stock listed at t-20; day t tradable) AND ER20 = |lnP[t]-lnP[t-20]| / sum_{s=t-19..t}|lnP[s]-lnP[s-1]|
         >= 0.2 AND a valid clean Open lnO[t+1] (tradable, not a data-error bar). Every event is a trade.
  W2.1   u5 = lnP[t+5]-lnO[t+1]; z = lnP[t+60]-lnO[t+6] (needs a valid Open t+6); mean z of u5 >= ln1.05 minus mean z
         of u5 <= ln0.95; raw; day means by signal day; Diff t = (mA-mB)/sqrt(seA^2+seB^2); lags 20; %.
  W2.2   same at day 20 (u20, z = lnP[t+60]-lnO[t+21]).
  W2.3   g = first day in t+1..t+20 with lnP[g]-lnO[t+1] >= ln1.10; abnormal (lnP[t+60]-lnO[g+1]) minus the EW mean of
         the identical window over universe stocks with both ends valid; lags 60 (window ends at t+60; PLAN.md states
         no lag for W2.3, general rule lags = h); %.
  W2.4   (lnP[t+60]-lnP[t+20]) minus EW mean of the same window over listed universe stocks, / 40, bps/day; lags 40.
  W2.5   trailing exit: first tradable Close in bars t+1..t+119 with lnP[d] < min(lnL[d-10..d-1]) (NaN skipped), sell
         at the next valid Open; otherwise exit at lnP[t+120] (cap 120 bars). Fixed arm lnP[t+20]-lnO[t+1]. Raw paired
         per-trade difference; only events with t+120 inside the data; lags 20; %.
Writes results/verify_W2.csv (one row per primary test) and results/verify_W2_detail.csv (sensitivities, claim
checks, spot checks).
"""
import math
import sys
import time
from pathlib import Path

import warnings

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

warnings.filterwarnings('ignore', message='Mean of empty slice')

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from panel import load, universe, SUBPERIODS, MAIN, P0     # noqa: E402
from mpstats import nw                                      # noqa: E402

OUT = HERE / 'results'
RAW = ROOT / 'Data' / 'Data kompas 100.csv'
PER = {'MAIN': MAIN, **SUBPERIODS, 'P0': P0}
LN105, LN095, LN110 = math.log(1.05), math.log(0.95), math.log(1.10)
CAP = 120
LAGS = {'W2.1': 20, 'W2.2': 20, 'W2.3': 60, 'W2.4': 40, 'W2.5': 20}
LAGS_WINDOW = {'W2.1': 60, 'W2.2': 60, 'W2.3': 60, 'W2.4': 60, 'W2.5': 120}
SCALE = {'W2.1': 100., 'W2.2': 100., 'W2.3': 100., 'W2.4': 1e4, 'W2.5': 100.}
TESTS = ('W2.1', 'W2.2', 'W2.3', 'W2.4', 'W2.5')
DETAIL = []


def note(section, test_id, metric, value=np.nan, t=np.nan, n=np.nan, ref=np.nan, comment=''):
    DETAIL.append(dict(section=section, test_id=test_id, metric=metric, value=value, t=t, n=n, analyst_ref=ref,
                       comment=comment))


# ------------------------------------------------------------------------------------------------ statistics
def nw_check(x, lags):
    """Independent Newey-West SE of the mean: Bartlett-weighted autocovariances of the zero-filled demeaned series."""
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    n = ok.sum()
    m = x[ok].mean()
    e = np.zeros(len(x))
    e[ok] = x[ok] - m
    g0 = np.dot(e, e)
    s = g0 + sum(2. * (1. - k / (lags + 1.)) * np.dot(e[:-k], e[k:]) for k in range(1, lags + 1))
    return m, math.sqrt(s) / n


class Calendar:
    def __init__(self, idx):
        self.idx = idx
        self.N = len(idx)

    def mask(self, period):
        a, b = PER[period]
        return np.asarray((self.idx >= pd.Timestamp(a)) & (self.idx <= pd.Timestamp(b)))

    def dser(self, t, v):
        """Mean of v over the events of each signal day t, on the full market calendar (NaN = no event)."""
        ok = np.isfinite(v)
        s = np.bincount(t[ok], weights=v[ok], minlength=self.N)
        c = np.bincount(t[ok], minlength=self.N)
        with np.errstate(invalid='ignore', divide='ignore'):
            return np.where(c > 0, s / c, np.nan)

    def mean_stat(self, s, period, lags):
        m, se, n = nw(s[self.mask(period)], lags)
        return m, (m / se if se and se > 0 else np.nan), n

    def diff_stat(self, sa, sb, period, lags):
        k = self.mask(period)
        ma, sea, na = nw(sa[k], lags)
        mb, seb, nb = nw(sb[k], lags)
        se = math.sqrt(sea ** 2 + seb ** 2)
        return ma - mb, (ma - mb) / se, min(na, nb)


# ------------------------------------------------------------------------------------------------ levels
def symmetric_levels(P):
    """Clean levels rebuilt with a symmetric data-error rule |ln(1+r)| >= ln 1.5 (both legs of a spike masked)."""
    O, H, L, C, T = P['O'], P['H'], P['L'], P['C'], P['T']
    Ct = C.where(T)
    prev = Ct.ffill().shift(1)
    lr = np.log(Ct / prev)
    bad = lr.abs() >= math.log(1.5)
    r_cc = lr.mask(bad)
    r_on = np.log(O.where(T) / prev).mask(bad)
    listed = C.notna().cumsum() > 0
    lnP = r_cc.fillna(0.).cumsum().where(listed)
    lnO = (lnP.shift(1) + r_on).where(T)
    lnH = (lnP + np.log(H / C)).where(T)
    lnL = (lnP + np.log(L / C)).where(T)
    return dict(LP=lnP.values, LO=lnO.values, LH=lnH.values, LL=lnL.values, n_bad=int(bad.sum().sum()))


# ------------------------------------------------------------------------------------------------ entries
def build_entries(LP, LO, LH, TT, strict=False, er_min=0.2):
    """Per-ticker windows. Returns arrays t (row), j (column), er20 and a flag for a fully tradable 20-day lookback."""
    N, K = LP.shape
    out_t, out_j, out_er, out_full = [], [], [], []
    for j in range(K):
        p, o, h, tt = LP[:, j], LO[:, j], LH[:, j], TT[:, j]
        fin = np.flatnonzero(np.isfinite(p))
        if len(fin) == 0:
            continue
        f = fin[0]
        t = np.arange(f + 20, N - 1)                     # listed at t-20; the entry bar t+1 exists
        if len(t) == 0:
            continue
        hw = sliding_window_view(h, 20)[t - 20]          # h[t-20 .. t-1]
        nvalid = np.isfinite(hw).sum(1)
        hmax = np.where(np.isfinite(hw), hw, -np.inf).max(1)
        hhv = np.where(nvalid == 20 if strict else nvalid > 0, hmax, np.nan)
        dp = np.abs(np.diff(p))                          # dp[k] = |p[k+1]-p[k]|
        den = sliding_window_view(dp, 20)[t - 20].sum(1)  # dp[t-20 .. t-1]  = |p[s]-p[s-1]|, s = t-19..t
        num = np.abs(p[t] - p[t - 20])
        with np.errstate(invalid='ignore', divide='ignore'):
            er = np.where(den > 0, num / den, np.nan)
            ok = tt[t] & np.isfinite(hhv) & (p[t] > hhv) & (er >= er_min) & np.isfinite(o[t + 1])
        out_t.append(t[ok])
        out_j.append(np.full(ok.sum(), j))
        out_er.append(er[ok])
        out_full.append(nvalid[ok] == 20)
    t = np.concatenate(out_t)
    j = np.concatenate(out_j)
    order = np.lexsort((j, t))
    return dict(t=t[order], j=j[order], er20=np.concatenate(out_er)[order], fullwin=np.concatenate(out_full)[order])


def take(A, r, j):
    out = np.full(len(r), np.nan)
    ok = (r >= 0) & (r < A.shape[0])
    out[ok] = A[r[ok], j[ok]]
    return out


def trade_path(E, LP, LO, LL, TT, cols_for_bench, own_bars=False, cap_open=False, z_next_open=False):
    """All per-event quantities for W2.1-W2.5 (raw) plus the W2.3 / W2.4 benchmarks for each universe in
    cols_for_bench ({name: column index array})."""
    t, j = E['t'], E['j']
    N = LP.shape[0]
    n = len(t)
    ent = take(LO, t + 1, j)
    R = dict(ent=ent)
    p60 = take(LP, t + 60, j)

    def open_at(r):
        if not z_next_open:
            return take(LO, r, j)
        # sensitivity: next valid Open on or after r
        out = np.full(n, np.nan)
        for q in range(n):
            rr = r[q]
            while rr < N and not np.isfinite(LO[rr, j[q]]):
                rr += 1
            if rr < N:
                out[q] = LO[rr, j[q]]
        return out

    R['u5'] = take(LP, t + 5, j) - ent
    R['z5'] = p60 - open_at(t + 6)
    R['u20'] = take(LP, t + 20, j) - ent
    R['z20'] = p60 - open_at(t + 21)
    # W2.3 trigger: explicit scan of the first 20 Closes after entry
    g = np.zeros(n, int)
    for k in range(1, 21):
        with np.errstate(invalid='ignore'):
            hit = (g == 0) & ((take(LP, t + k, j) - ent) >= LN110)
        g[hit] = k
    R['g'] = g
    r23 = np.full(n, np.nan)
    trig = g > 0
    r23[trig] = p60[trig] - take(LO, (t + g + 1)[trig], j[trig])
    R['r23'] = r23
    R['d24'] = p60 - take(LP, t + 20, j)
    R['f20'] = take(LP, t + 20, j) - ent
    R['f60'] = p60 - ent
    # benchmarks: EW mean over the universe of the identical window (both ends valid)
    for name, U in cols_for_bench.items():
        b23 = np.full(n, np.nan)
        b24 = np.full(n, np.nan)
        b20 = np.full(n, np.nan)
        ok = trig & (t + 60 <= N - 1)
        rows_e, rows_s = (t + 60)[ok], (t + g + 1)[ok]
        W = LP[rows_e][:, U] - LO[rows_s][:, U]
        b23[ok] = np.nanmean(W, axis=1)
        ok = t + 60 <= N - 1
        W = LP[(t + 60)[ok]][:, U] - LP[(t + 20)[ok]][:, U]
        b24[ok] = np.nanmean(W, axis=1)
        ok = t + 20 <= N - 1
        W = LP[(t + 20)[ok]][:, U] - LO[(t + 1)[ok]][:, U]
        b20[ok] = np.nanmean(W, axis=1)
        R['b23_' + name], R['b24_' + name], R['b20_' + name] = b23, b24, b20
    # W2.5 trailing exit: explicit per-event loop
    r_tr = np.full(n, np.nan)
    bars = np.full(n, np.nan)
    capped = np.zeros(n, bool)
    exit_row = np.full(n, -1)
    for q in range(n):
        tq, jq = t[q], j[q]
        if tq + CAP > N - 1 or not np.isfinite(ent[q]):
            continue
        lpc, loc_, llc, ttc = LP[:, jq], LO[:, jq], LL[:, jq], TT[:, jq]
        done = False
        for k in range(1, CAP):
            d = tq + k
            if not ttc[d]:
                continue
            if own_bars:
                prior = llc[:d][np.isfinite(llc[:d])][-10:]
            else:
                prior = llc[d - 10:d]
                prior = prior[np.isfinite(prior)]
            if len(prior) == 0:
                continue
            if lpc[d] < prior.min():
                e = d + 1
                while e <= N - 1 and not np.isfinite(loc_[e]):
                    e += 1
                if e <= N - 1:
                    r_tr[q] = loc_[e] - ent[q]
                    bars[q] = e - (tq + 1)
                    exit_row[q] = e
                done = True
                break
        if not done:
            if cap_open:
                e = tq + CAP + 1
                while e <= N - 1 and not np.isfinite(loc_[e]):
                    e += 1
                if e <= N - 1:
                    r_tr[q] = loc_[e] - ent[q]
                    bars[q] = e - (tq + 1)
                    exit_row[q] = e
            else:
                r_tr[q] = lpc[tq + CAP] - ent[q]
                bars[q] = CAP
                exit_row[q] = tq + CAP
            capped[q] = np.isfinite(r_tr[q])
    R['r_tr'], R['bars'], R['capped'], R['exit_row'] = r_tr, bars, capped, exit_row
    R['r_fix'] = R['f20']
    d25 = r_tr - R['f20']
    d25[~np.isfinite(r_tr)] = np.nan
    R['d25'] = d25
    return R


# ------------------------------------------------------------------------------------------------ tests
def test_series(cal, E, R, sel, univ):
    """Day-mean series per test (dict tid -> ('mean', s) or ('diff', sa, sb)) on events selected by `sel`."""
    t = E['t']
    S = {}
    for tid, u, z in (('W2.1', 'u5', 'z5'), ('W2.2', 'u20', 'z20')):
        uu, zz = R[u], R[z]
        with np.errstate(invalid='ignore'):
            up = sel & (uu >= LN105) & np.isfinite(zz)
            dn = sel & (uu <= LN095) & np.isfinite(zz)
        S[tid] = ('diff', cal.dser(t[up], zz[up]), cal.dser(t[dn], zz[dn]), up, dn)
    v = R['r23'] - R['b23_' + univ]
    m = sel & np.isfinite(v)
    S['W2.3'] = ('mean', cal.dser(t[m], v[m]), m)
    v = (R['d24'] - R['b24_' + univ]) / 40.
    m = sel & np.isfinite(v)
    S['W2.4'] = ('mean', cal.dser(t[m], v[m]), m)
    v = R['d25']
    m = sel & np.isfinite(v)
    S['W2.5'] = ('mean', cal.dser(t[m], v[m]), m)
    return S


def evaluate(cal, S, tid, period, lags=None):
    x = S[tid]
    lg = LAGS[tid] if lags is None else lags
    if x[0] == 'diff':
        e, tt, n = cal.diff_stat(x[1], x[2], period, lg)
    else:
        e, tt, n = cal.mean_stat(x[1], period, lg)
    return e * SCALE[tid], tt, n


def run_variant(cal, P, LP, LO, LH, LL, TT, label, cols, **kw):
    """Primary statistics (MAIN all + MAIN pre2018) for an alternative definition or panel."""
    strict = kw.pop('strict', False)
    E = build_entries(LP, LO, LH, TT, strict=strict)
    U = {'all': np.arange(len(cols)), 'pre2018': np.flatnonzero(np.isin(cols, universe(P, 'pre2018')))}
    R = trade_path(E, LP, LO, LL, TT, U, **kw)
    res = {}
    for univ in ('all', 'pre2018'):
        sel = np.isin(np.asarray(cols)[E['j']], universe(P, univ))
        S = test_series(cal, E, R, sel, univ)
        for tid in TESTS:
            res[(tid, univ)] = evaluate(cal, S, tid, 'MAIN')
    nm = int((cal.mask('MAIN')[E['t']]).sum())
    for tid in TESTS:
        e, t, n = res[(tid, 'all')]
        ep, tp, _ = res[(tid, 'pre2018')]
        note('sensitivity', tid, label, e, t, n, comment=f'pre2018 {ep:.3f} (t {tp:.2f}); MAIN entries {nm}')
    return res, E, R


def exposure_backtest(cal, E, R, LP, LO, sel, cost_in, cost_out):
    """Indicative simple exposure backtest (verifier's check of PLAN criterion 4 for a timing rule; not
    pre-registered): every selected trade holds an equal share of the portfolio on each day it is open (daily equal
    weight across open trades, cash = 0 when none). Position return: entry Open -> Close on the entry day, Close ->
    Close afterwards, previous Close -> exit price on the exit day (next Open for a trailing exit, Close for the fixed
    20-bar or capped exit); cost_in charged on the entry day, cost_out on the exit day."""
    N = cal.N
    out = {}
    for arm in ('tr', 'fix'):
        s = np.zeros(N)
        c = np.zeros(N)
        for q in np.flatnonzero(sel):
            t, j = E['t'][q], E['j'][q]
            e0 = t + 1
            if arm == 'tr':
                x, via_open = int(R['exit_row'][q]), not R['capped'][q]
            else:
                x, via_open = t + 20, False
            r = np.empty(x - e0 + 1)
            r[0] = LP[e0, j] - LO[e0, j]
            r[1:] = np.diff(LP[e0:x + 1, j])
            if via_open:
                r[-1] = LO[x, j] - LP[x - 1, j]
            sr = np.expm1(r)
            sr[0] -= cost_in
            sr[-1] -= cost_out
            s[e0:x + 1] += sr
            c[e0:x + 1] += 1
        out[arm] = np.where(c > 0, s / np.maximum(c, 1), 0.)
        out['n_' + arm] = c
    return out


# ------------------------------------------------------------------------------------------------ spot checks
def spot_checks(P, E, R, cal, cols):
    """Recompute a few events by hand from the raw CSV (prices as in the file; High/Low widened to include Open and
    Close exactly as the engine's loader does). Only events whose ticker has a raw row on every market day of
    [t-25, t+125] with Volume > 0 and no |simple return| >= 50% are eligible, so raw logs equal clean log levels."""
    raw = pd.read_csv(RAW)
    raw.columns = raw.columns.str.strip()
    raw['Date'] = pd.to_datetime(raw['Date/Time'], format='mixed', dayfirst=True)
    raw = raw[raw['Date'] == raw['Date'].dt.normalize()]          # the engine drops non-daily timestamps too
    idx = cal.idx
    t, j = E['t'], E['j']
    tick = np.asarray(cols)[j]
    rng = np.random.default_rng(20261018)
    years = [2003, 2011, 2017, 2022]
    picks = []
    for y in years:
        cand = np.flatnonzero((idx[t].year == y) & np.isfinite(R['d25']) & np.isfinite(R['z5']))
        rng.shuffle(cand)
        for q in cand:
            g = raw[raw.Ticker == tick[q]].set_index('Date').sort_index()
            lo_, hi_ = t[q] - 25, t[q] + 125
            if lo_ < 0 or hi_ > len(idx) - 1:
                continue
            days = idx[lo_:hi_ + 1]
            if not days.isin(g.index).all():
                continue
            w = g.loc[days]
            if (w.Volume <= 0).any() or (w.Close.pct_change().abs() >= .5).any():
                continue
            picks.append((q, w))
            break
    rows = []
    for q, w in picks:
        o = w.Open.values
        c = w.Close.values
        h = np.maximum.reduce([w.Open.values, w.High.values, w.Low.values, w.Close.values])
        lo = np.minimum.reduce([w.Open.values, w.High.values, w.Low.values, w.Close.values])
        r = 25                                            # position of t inside the window
        hhv = h[r - 20:r].max()
        er = abs(math.log(c[r] / c[r - 20])) / np.abs(np.diff(np.log(c[r - 20:r + 1]))).sum()
        ent = o[r + 1]
        hand = dict(breakout=bool(c[r] > hhv), er20=er, u5=math.log(c[r + 5] / ent), z5=math.log(c[r + 60] / o[r + 6]),
                    u20=math.log(c[r + 20] / ent), z20=math.log(c[r + 60] / o[r + 21]),
                    d24=math.log(c[r + 60] / c[r + 20]), f20=math.log(c[r + 20] / ent))
        gk = 0
        for k in range(1, 21):
            if math.log(c[r + k] / ent) >= LN110:
                gk = k
                break
        hand['g'] = gk
        hand['r23'] = math.log(c[r + 60] / o[r + gk + 1]) if gk else np.nan
        ex, bars = None, None
        for k in range(1, CAP):
            d = r + k
            if c[d] < lo[d - 10:d].min():
                ex, bars = o[d + 1], k
                break
        if ex is None:
            ex, bars = c[r + CAP], CAP
        hand['r_tr'] = math.log(ex / ent)
        hand['bars'] = bars
        mine = dict(breakout=True, er20=E['er20'][q], u5=R['u5'][q], z5=R['z5'][q], u20=R['u20'][q], z20=R['z20'][q],
                    d24=R['d24'][q], f20=R['f20'][q], g=int(R['g'][q]), r23=R['r23'][q], r_tr=R['r_tr'][q],
                    bars=R['bars'][q])
        diffs = {k: (abs(float(hand[k]) - float(mine[k])) if not (isinstance(hand[k], float) and np.isnan(hand[k])
                                                                  and np.isnan(mine[k])) else 0.)
                 for k in hand}
        worst = max(diffs.values())
        desc = (f"{tick[q]} t={idx[t[q]].date()} Close {c[r]:g} > HHV20 High {hhv:g}; ER20 {er:.3f}; entry Open "
                f"{idx[t[q] + 1].date()} {ent:g}; u5 {100 * hand['u5']:.2f}% z5 {100 * hand['z5']:.2f}%; u20 "
                f"{100 * hand['u20']:.2f}% z20 {100 * hand['z20']:.2f}%; g {hand['g']} r23 {100 * hand['r23']:.2f}%; "
                f"d24 {100 * hand['d24']:.2f}%; trailing exit after {hand['bars']} bars r_tr {100 * hand['r_tr']:.2f}% "
                f"vs fixed {100 * hand['f20']:.2f}%")
        note('spot_check', 'entries', desc, worst, comment='max |hand - script| over all fields (log units)')
        rows.append((desc, worst))
    # one benchmark by hand: W2.4 EW mean of ln(C[t+60]/C[t+20]) over all tickers with a raw row on both days,
    # using the last tradable Close (Volume > 0), for the 2022 pick (no ticker may have a >= 50% move in the window)
    q, w = picks[-1]
    d20, d60 = idx[t[q] + 20], idx[t[q] + 60]
    tr = raw[(raw.Volume > 0) & (raw.Date <= d60)].sort_values('Date')
    win = tr[tr.Date >= idx[t[q] + 19 - 40]]
    jumps = win.groupby('Ticker').Close.apply(lambda s: (s.pct_change().abs() >= .5).any())
    lc20 = tr[tr.Date <= d20].groupby('Ticker').Close.last()
    lc60 = tr.groupby('Ticker').Close.last()
    both = lc20.index.intersection(lc60.index)
    bench_hand = float(np.log(lc60[both] / lc20[both]).mean())
    note('spot_check', 'W2.4', f'benchmark by hand {d20.date()}..{d60.date()} over {len(both)} tickers '
         f'(tickers with a >=50% move in window: {int(jumps.sum())})', bench_hand - R['b24_all'][q],
         comment=f"hand {100 * bench_hand:.4f}% vs script {100 * R['b24_all'][q]:.4f}%")
    return rows


# ------------------------------------------------------------------------------------------------ main
def main():
    t0 = time.time()
    P = load()
    idx = P['C'].index
    cols = list(P['C'].columns)
    cal = Calendar(idx)
    LP, LO, LH, LL = (P[k].values for k in ('lnP', 'lnO', 'lnH', 'lnL'))
    TT = P['T'].values
    U = {'all': np.arange(len(cols)), 'pre2018': np.flatnonzero(np.isin(cols, universe(P, 'pre2018')))}
    assert len(U['pre2018']) == 80

    E = build_entries(LP, LO, LH, TT)
    R = trade_path(E, LP, LO, LL, TT, U)
    tick = np.asarray(cols)[E['j']]
    print(f'entries {len(E["t"])} (MAIN {int(cal.mask("MAIN")[E["t"]].sum())}), {time.time() - t0:.1f}s')

    analyst = pd.read_csv(OUT / 'W2_tests.csv').set_index('test_id')
    ctx = pd.read_csv(OUT / 'W2_context.csv')

    def ctxv(section, tid, univ, period, start):
        x = ctx[(ctx.section == section) & (ctx.test_id == tid) & (ctx.universe == univ) & (ctx.period == period)
                & ctx.metric.str.startswith(start)]
        return float(x.value.iloc[0]) if len(x) else np.nan

    # entry counts versus the analyst's context file
    for univ in ('all', 'pre2018'):
        sel = np.isin(tick, universe(P, univ))
        for k in ('MAIN', 'P0'):
            n_me = int((sel & cal.mask(k)[E['t']]).sum())
            note('counts', 'entries', f'n entries {univ} {k}', n_me,
                 ref=ctxv('counts', 'entries', univ, k, 'n_entries (W1.1'))

    # nw cross-check
    S_all = test_series(cal, E, R, np.isin(tick, universe(P, 'all')), 'all')
    x = S_all['W2.5'][1][cal.mask('MAIN')]
    m1, se1, _ = nw(x, 20)
    m2, se2 = nw_check(x, 20)
    note('helper_check', 'W2.5', 'mpstats.nw vs independent NW (mean, se) on the W2.5 MAIN series', abs(se1 - se2),
         comment=f'nw se {se1:.6g}, independent se {se2:.6g}, means {m1:.6g}/{m2:.6g}')

    # primary results
    res = {}
    S = {'all': S_all, 'pre2018': test_series(cal, E, R, np.isin(tick, universe(P, 'pre2018')), 'pre2018')}
    for univ in ('all', 'pre2018'):
        for tid in TESTS:
            for k in PER:
                res[(tid, univ, k)] = evaluate(cal, S[univ], tid, k)
    for tid in TESTS:
        for k in PER:
            e, t, n = res[(tid, 'all', k)]
            note('primary', tid, f'all {k}', e, t, n, ref=analyst.loc[tid, f'eff_{k}'],
                 comment=f"analyst t {analyst.loc[tid, f't_{k}']:.3f}, n {analyst.loc[tid, f'n_{k}']}")
        for k in PER:
            e, t, n = res[(tid, 'pre2018', k)]
            ref = analyst.loc[tid, 'eff_pre2018'] if k == 'MAIN' else ctxv('pre2018_subperiods', tid, 'pre2018', k,
                                                                          'primary')
            note('primary', tid, f'pre2018 {k}', e, t, n, ref=ref)
        # NW lags equal to the full event window
        e, t, n = evaluate(cal, S['all'], tid, 'MAIN', lags=LAGS_WINDOW[tid])
        note('lags', tid, f'MAIN all, NW lags {LAGS_WINDOW[tid]} (primary {LAGS[tid]})', e, t, n)
        e, t, n = evaluate(cal, S['all'], tid, 'MAIN', lags=20)
        note('lags', tid, 'MAIN all, NW lags 20', e, t, n)

    # ---------------------------------------------------------------- claim checks (MAIN, all universe)
    main_ev = cal.mask('MAIN')[E['t']]
    sel_all = np.isin(tick, universe(P, 'all'))
    for tid in ('W2.1', 'W2.2'):
        _, sa, sb, up, dn = S['all'][tid]
        km = cal.mask('MAIN')
        z = R['z5' if tid == 'W2.1' else 'z20']
        uu = R['u5' if tid == 'W2.1' else 'u20']
        with np.errstate(invalid='ignore'):
            mid = sel_all & (uu > LN095) & (uu < LN105) & np.isfinite(z)
        note('claims', tid, 'day-mean z up group (%)', 100 * np.nanmean(sa[km]),
             ref=ctxv('groups', tid, 'all', 'MAIN', 'day-mean z, up'))
        note('claims', tid, 'day-mean z down group (%)', 100 * np.nanmean(sb[km]),
             ref=ctxv('groups', tid, 'all', 'MAIN', 'day-mean z, down'))
        for gname, gm in (('up', up), ('down', dn), ('middle', mid)):
            note('claims', tid, f'event-weighted z {gname} group (%)', 100 * np.nanmean(z[gm & main_ev]),
                 n=int((gm & main_ev).sum()), ref=ctxv('groups', tid, 'all', 'MAIN', f'event-weighted mean z, {gname}'))
    # W2.3 share and median trigger day
    pm = sel_all & main_ev & np.isfinite(R['f20'])
    note('claims', 'W2.3', 'share of entries reaching +10% Close gain within 20 days (%)', 100 * (R['g'][pm] > 0).mean(),
         n=int(pm.sum()), ref=ctxv('W2.3_detail', 'W2.3', 'all', 'MAIN', 'share of entries'))
    note('claims', 'W2.3', 'median trigger day g-t', float(np.median(R['g'][pm & (R['g'] > 0)])),
         ref=ctxv('W2.3_detail', 'W2.3', 'all', 'MAIN', 'median trigger'))
    v = R['r23']
    m = sel_all & np.isfinite(v)
    e, t, n = cal.mean_stat(cal.dser(E['t'][m], v[m]), 'MAIN', 60)
    note('claims', 'W2.3', 'raw lnP[t+60]-lnO[g+1] (day-mean, lags 60) (%)', 100 * e, t, n,
         ref=ctxv('alt_basis', 'W2.3', 'all', 'MAIN', 'raw'))
    for lab, km in (('fully tradable lookback', E['fullwin']), ('lookback with non-tradable day', ~E['fullwin'])):
        Sx = test_series(cal, E, R, sel_all & km, 'all')
        for tid in TESTS:
            e, t, n = evaluate(cal, Sx, tid, 'MAIN')
            note('claims', tid, f'primary statistic, {lab}', e, t, n)
    # W2.4 other windows
    for name, num, den, lag in (('abnormal drift days 1-20 (bps/day)', R['f20'] - R['b20_all'], 20., 20),):
        m = sel_all & np.isfinite(num)
        e, t, n = cal.mean_stat(cal.dser(E['t'][m], num[m] / den), 'MAIN', lag)
        note('claims', 'W2.4', name, 1e4 * e, t, n)
    p120 = take(LP, E['t'] + 120, E['j'])
    b120 = np.full(len(E['t']), np.nan)
    ok = E['t'] + 120 <= cal.N - 1
    b120[ok] = np.nanmean(LP[(E['t'] + 120)[ok]] - LP[(E['t'] + 60)[ok]], axis=1)
    num = (p120 - take(LP, E['t'] + 60, E['j'])) - b120
    m = sel_all & np.isfinite(num)
    e, t, n = cal.mean_stat(cal.dser(E['t'][m], num[m] / 60.), 'MAIN', 60)
    note('claims', 'W2.4', 'abnormal drift days 61-120 (bps/day)', 1e4 * e, t, n)
    v = R['d24'] / 40.
    m = sel_all & np.isfinite(v)
    e, t, n = cal.mean_stat(cal.dser(E['t'][m], v[m]), 'MAIN', 40)
    note('claims', 'W2.4', 'raw drift days 21-60 (bps/day)', 1e4 * e, t, n,
         ref=ctxv('alt_basis', 'W2.4', 'all', 'MAIN', 'raw'))
    # W2.5 details
    m = sel_all & main_ev & np.isfinite(R['d25'])
    b = R['bars'][m]
    note('claims', 'W2.5', 'events MAIN with full 120-bar window', int(m.sum()))
    note('claims', 'W2.5', 'trailing mean bars held', b.mean())
    note('claims', 'W2.5', 'trailing median bars held', float(np.median(b)))
    note('claims', 'W2.5', 'share exiting before bar 20 (%)', 100 * (b < 20).mean())
    note('claims', 'W2.5', 'share capped (%)', 100 * R['capped'][m].mean())
    note('claims', 'W2.5', 'share trailing beats fixed (%)', 100 * (R['d25'][m] > 0).mean())
    note('claims', 'W2.5', 'trailing raw return per bar held (bps)', 1e4 * R['r_tr'][m].sum() / b.sum())
    note('claims', 'W2.5', 'fixed raw return per bar held (bps)', 1e4 * R['r_fix'][m].sum() / (20 * m.sum()))
    note('claims', 'W2.5', 'event-weighted mean paired difference (%)', 100 * R['d25'][m].mean())
    early = m & (R['bars'] < 20)
    late = m & (R['bars'] >= 20)
    note('claims', 'W2.5', 'contribution of trades exiting before bar 20 to the mean difference (pp)',
         100 * R['d25'][early].sum() / m.sum(), n=int(early.sum()),
         comment=f"mean difference within this group {100 * R['d25'][early].mean():.2f}%")
    note('claims', 'W2.5', 'contribution of trades exiting at/after bar 20 to the mean difference (pp)',
         100 * R['d25'][late].sum() / m.sum(), n=int(late.sum()),
         comment=f"mean difference within this group {100 * R['d25'][late].mean():.2f}%")
    d = np.sort(R['d25'][m])[::-1]
    n10 = int(np.ceil(.1 * len(d)))
    note('claims', 'W2.5', 'share of the summed paired difference from the top 10% of trades (%)',
         100 * d[:n10].sum() / d.sum())
    note('claims', 'W2.5', 'trades whose exit was delayed past bar 120 by non-tradable days', int((b > CAP).sum()))
    # per-trade (event-weighted) versus day-mean: the analyst calls the day-mean a 'per trade' figure
    for c_lab, c in (('gross', 0.), ('net of cost A 0.40%', .004), ('net of cost B 0.90%', .009)):
        note('claims', 'W2.5', f'return per bar held, trailing arm, {c_lab} (bps/bar)',
             1e4 * (R['r_tr'][m].sum() - c * m.sum()) / b.sum())
        note('claims', 'W2.5', f'return per bar held, fixed 20-bar arm, {c_lab} (bps/bar)',
             1e4 * (R['r_fix'][m].sum() - c * m.sum()) / (20 * m.sum()))
    # 31-bar fixed-hold control (analyst's exploratory X-W2-1): raw, all and fully tradable lookbacks
    f31 = take(LP, E['t'] + 31, E['j']) - R['ent']
    v = R['r_tr'] - f31
    for lab, km in (('all', np.ones(len(v), bool)), ('fully tradable lookback', E['fullwin'])):
        mm = sel_all & km & np.isfinite(v)
        e, t, n = cal.mean_stat(cal.dser(E['t'][mm], v[mm]), 'MAIN', 20)
        e4, t4, _ = cal.mean_stat(cal.dser(E['t'][mm], v[mm]), 'P4', 20)
        note('claims', 'W2.5', f'trailing minus fixed 31-bar hold, raw, {lab} (%)', 100 * e, t, n,
             comment=f'P4 {100 * e4:.2f}% (t {t4:.2f}); not pre-registered')
    # right tail of fo60 (claim: top 10% of trades produce 93% of the 60-day simple P&L)
    f60 = R['f60'][sel_all & main_ev]
    s = np.sort(np.expm1(f60[np.isfinite(f60)]))[::-1]
    note('claims', 'W2.5', 'share of simple 60-day P&L of breakout entries from the top 10% of trades (%)',
         100 * s[:int(np.ceil(.1 * len(s)))].sum() / s.sum(),
         ref=ctxv('right_tail', 'fo60', 'all', 'MAIN', 'share of total simple 60-day P&L from top 10%'))
    # W2.5 by year, pre2018 universe (claim: negative every year 2021-2025)
    sp = S['pre2018']['W2.5'][1]
    for y in range(2019, 2026):
        km = np.asarray(idx.year == y)
        note('claims', 'W2.5', f'pre2018 day-mean paired difference {y} (%)', 100 * np.nanmean(sp[km]),
             n=int(np.isfinite(sp[km]).sum()))
    for k in ('P1', 'P2', 'P3', 'P4'):
        e, t, n = res[('W2.5', 'pre2018', k)]
        note('claims', 'W2.5', f'pre2018 {k}', e, t, n)

    # ---------------------------------------------------------------- tradability of entry and exit bars
    O_, H_, L_, C_ = (P[k].values for k in ('O', 'H', 'L', 'C'))
    r1 = E['t'] + 1
    flat = (O_[r1, E['j']] == H_[r1, E['j']]) & (H_[r1, E['j']] == L_[r1, E['j']]) & (L_[r1, E['j']] == C_[r1, E['j']])
    note('tradability', 'entries', 'MAIN entries whose entry bar t+1 is a one-price bar (O=H=L=C)',
         int((flat & main_ev).sum()), comment=f'of {int(main_ev.sum())} MAIN entries')
    gap = O_[r1, E['j']] / C_[E['t'], E['j']] - 1
    note('tradability', 'entries', 'MAIN entries with entry Open >= 20% above the signal Close (possible limit-up)',
         int(((gap >= .2) & main_ev).sum()))

    # ---------------------------------------------------------------- sensitivities (MAIN all / pre2018)
    run_variant(cal, P, LP, LO, LH, LL, TT, 'strict HHV20 (all 20 prior highs valid)', cols, strict=True)
    run_variant(cal, P, LP, LO, LH, LL, TT, 'W2.5 prior 10 own tradable bars', cols, own_bars=True)
    run_variant(cal, P, LP, LO, LH, LL, TT, 'W2.5 cap exit at next Open after bar 120', cols, cap_open=True)
    run_variant(cal, P, LP, LO, LH, LL, TT, 'W2.1/W2.2 z from next valid Open (not dropped)', cols, z_next_open=True)
    sym = symmetric_levels(P)
    run_variant(cal, P, sym['LP'], sym['LO'], sym['LH'], sym['LL'], TT,
                f"symmetric data-error mask |ln(1+r)|>=ln1.5 ({sym['n_bad']} masked)", cols)
    # declustered: first event per stock in 60 market days (greedy)
    keep = np.zeros(len(E['t']), bool)
    last = {}
    for q in np.lexsort((E['t'], E['j'])):
        if E['t'][q] - last.get(E['j'][q], -10 ** 9) >= 60:
            keep[q] = True
            last[E['j'][q]] = E['t'][q]
    for univ in ('all', 'pre2018'):
        Sx = test_series(cal, E, R, np.isin(tick, universe(P, univ)) & keep, univ)
        for tid in TESTS:
            e, t, n = evaluate(cal, Sx, tid, 'MAIN')
            note('sensitivity', tid, f'first event per stock in 60 days ({univ})', e, t, n,
                 ref=ctxv('first_per_60d', tid, univ, 'MAIN', 'primary'))
    # symmetric log thresholds +-0.05 for W2.1/W2.2
    for tid, u, z in (('W2.1', 'u5', 'z5'), ('W2.2', 'u20', 'z20')):
        with np.errstate(invalid='ignore'):
            up = sel_all & (R[u] >= .05) & np.isfinite(R[z])
            dn = sel_all & (R[u] <= -.05) & np.isfinite(R[z])
        e, t, n = cal.diff_stat(cal.dser(E['t'][up], R[z][up]), cal.dser(E['t'][dn], R[z][dn]), 'MAIN', 20)
        note('sensitivity', tid, 'log thresholds +-0.05', 100 * e, t, n,
             ref=ctxv('thresholds', tid, 'all', 'MAIN', 'log thresholds'))
    # W2.5 abnormal paired difference (each arm minus its same-window EW mean, universe all)
    LPa, LOa = LP, LO
    atr = np.full(len(E['t']), np.nan)
    okx = np.isfinite(R['r_tr']) & (R['exit_row'] >= 0)
    er_ = R['exit_row'][okx]
    capx = R['capped'][okx]
    endv = np.where(capx[:, None], LPa[er_], LOa[er_])
    atr[okx] = R['r_tr'][okx] - np.nanmean(endv - LOa[(E['t'] + 1)[okx]], axis=1)
    ad25 = atr - (R['f20'] - R['b20_all'])
    mm = sel_all & np.isfinite(ad25)
    e, t, n = cal.mean_stat(cal.dser(E['t'][mm], ad25[mm]), 'MAIN', 20)
    note('sensitivity', 'W2.5', 'abnormal paired difference (each arm minus same-window EW mean)', 100 * e, t, n,
         ref=ctxv('alt_basis', 'W2.5', 'all', 'MAIN', 'abnormal'))
    for k in ('P1', 'P2', 'P3', 'P4'):
        e, t, n = cal.mean_stat(cal.dser(E['t'][mm], ad25[mm]), k, 20)
        note('sensitivity', 'W2.5', f'abnormal paired difference {k}', 100 * e, t, n)

    # ---------------------------------------------------------------- extra audit checks
    m5 = sel_all & main_ev
    v = R['r23'] - R['b23_all']
    note('per_trade', 'W2.3', 'event-weighted mean abnormal return (%)', 100 * np.nanmean(v[m5]),
         n=int(np.isfinite(v[m5]).sum()), comment='primary statistic is the mean of daily means (2.30%)')
    note('per_trade', 'W2.4', 'event-weighted mean abnormal drift (bps/day)',
         1e4 * np.nanmean(((R['d24'] - R['b24_all']) / 40.)[m5]))
    note('per_trade', 'W2.5', 'event-weighted mean raw paired difference (%)', 100 * np.nanmean(R['d25'][m5]),
         n=int(np.isfinite(R['d25'][m5]).sum()), comment='primary statistic is the mean of daily means (1.74%)')
    note('per_trade', 'W2.5', 'event-weighted mean abnormal paired difference (%)', 100 * np.nanmean(ad25[m5]),
         comment='analyst alt basis 0.82% is a mean of daily means')
    # W2.5 declustered with lags 120
    v = R['d25']
    mm = sel_all & keep & np.isfinite(v)
    e, t, n = cal.mean_stat(cal.dser(E['t'][mm], v[mm]), 'MAIN', 120)
    note('sensitivity', 'W2.5', 'first event per stock in 60 days, NW lags 120', 100 * e, t, n)
    # W2.1 / W2.2: abnormal z, and a covariance-aware paired-day t (days on which both groups have events)
    U_all = np.arange(len(cols))
    for tid, u, z, k0 in (('W2.1', 'u5', 'z5', 6), ('W2.2', 'u20', 'z20', 21)):
        bz = np.full(len(E['t']), np.nan)
        okz = E['t'] + 60 <= cal.N - 1
        bz[okz] = np.nanmean(LP[(E['t'] + 60)[okz]][:, U_all] - LO[(E['t'] + k0)[okz]][:, U_all], axis=1)
        az = R[z] - bz
        with np.errstate(invalid='ignore'):
            up = sel_all & (R[u] >= LN105) & np.isfinite(az)
            dn = sel_all & (R[u] <= LN095) & np.isfinite(az)
        e, t, n = cal.diff_stat(cal.dser(E['t'][up], az[up]), cal.dser(E['t'][dn], az[dn]), 'MAIN', 20)
        note('sensitivity', tid, 'abnormal z up minus down (Diff, lags 20)', 100 * e, t, n,
             ref=ctxv('alt_basis', tid, 'all', 'MAIN', 'abnormal z'))
        _, sa, sb, _, _ = S['all'][tid]
        dd = sa - sb                                      # NaN unless both groups have events that day
        e, t, n = cal.mean_stat(dd, 'MAIN', 20)
        note('sensitivity', tid, 'paired-day difference (days with both groups; covariance kept), lags 20',
             100 * e, t, n, comment='not the pre-registered conservative Diff t')
    # entries / exits that may not have been fillable: one-price bar (O=H=L=C) with a gap in the trade direction
    up_lock = flat & (O_[r1, E['j']] > C_[E['t'], E['j']])
    xr = R['exit_row']
    okx = (xr >= 0) & ~R['capped']
    dn_lock = np.zeros(len(xr), bool)
    xi, xj = xr[okx], E['j'][okx]
    prevc = P['Cff'].values[xi - 1, xj]                  # last tradable Close before the exit bar
    dn_lock[okx] = ((O_[xi, xj] == H_[xi, xj]) & (H_[xi, xj] == L_[xi, xj]) & (L_[xi, xj] == C_[xi, xj])
                    & (O_[xi, xj] < prevc))
    note('tradability', 'entries', 'MAIN entries bought on a one-price bar that gapped up (possible locked limit-up)',
         int((up_lock & main_ev).sum()))
    note('tradability', 'W2.5', 'MAIN trailing exits sold on a one-price bar that gapped down (possible locked '
         'limit-down)', int((dn_lock & main_ev & np.isfinite(R['d25'])).sum()))
    Sx = test_series(cal, E, R, sel_all & ~up_lock & ~dn_lock, 'all')
    for tid in TESTS:
        e, t, n = evaluate(cal, Sx, tid, 'MAIN')
        note('sensitivity', tid, 'excluding possibly unfillable entries/exits (one-price gap bars)', e, t, n)
    # W2.5 fragility combinations (window-length lags on the subsamples the analyst highlights)
    v = R['d25']
    for lab, km, lg in (('fully tradable lookback, NW lags 120', E['fullwin'], 120),
                        ('fully tradable lookback, NW lags 20', E['fullwin'], 20)):
        mm = sel_all & km & np.isfinite(v)
        e, t, n = cal.mean_stat(cal.dser(E['t'][mm], v[mm]), 'MAIN', lg)
        note('sensitivity', 'W2.5', lab, 100 * e, t, n)
    mm = sel_all & np.isfinite(ad25)
    e, t, n = cal.mean_stat(cal.dser(E['t'][mm], ad25[mm]), 'MAIN', 120)
    note('sensitivity', 'W2.5', 'abnormal paired difference, NW lags 120', 100 * e, t, n)
    mm = sel_all & np.isfinite(v)
    s25 = cal.dser(E['t'][mm], v[mm])
    k08 = np.asarray((idx >= pd.Timestamp('2008-01-01')) & (idx <= pd.Timestamp(MAIN[1])))
    m08, se08, n08 = nw(s25[k08], 20)
    note('sensitivity', 'W2.5', '2008-2025 only (P2-P4), NW lags 20', 100 * m08, m08 / se08, n08)
    m08, se08, n08 = nw(s25[k08], 120)
    note('sensitivity', 'W2.5', '2008-2025 only (P2-P4), NW lags 120', 100 * m08, m08 / se08, n08)
    # counts quoted in the analyst's definition choices / caveats
    trig_drop = sel_all & main_ev & (R['g'] > 0) & ~np.isfinite(R['r23']) & np.isfinite(R['f60'])
    note('counts', 'W2.3', 'triggered MAIN events dropped for no valid Open at g+1', int(trig_drop.sum()), ref=108)
    note('counts', 'entries', 'MAIN entries kept as first per stock in 60 days', int((keep & main_ev & sel_all).sum()),
         ref=3824)
    pk = np.full(len(E['t']), np.nan)
    okp = E['t'] + CAP <= cal.N - 1
    for q in np.flatnonzero(okp & main_ev):
        pk[q] = np.argmax(LP[E['t'][q] + 1:E['t'][q] + CAP + 1, E['j'][q]]) + 1
    note('counts', 'entries', 'median bar of the 120-bar peak Close (breakout entries, MAIN)', float(np.nanmedian(pk)),
         ref=61, comment=f'share of peaks at bar 100-120 {100 * np.nanmean(pk[np.isfinite(pk)] >= 100):.1f}% '
                         '(analyst 27.6%)')
    # calendar without the two stray single-ticker CTRA bars (2008-01-11, Saturday 2009-06-06)
    stray = np.flatnonzero(np.isin(idx, pd.to_datetime(['2008-01-11', '2009-06-06'])))
    keep_rows = np.setdiff1d(np.arange(cal.N), stray)
    cal2 = Calendar(idx[keep_rows])
    run_variant(cal2, P, LP[keep_rows], LO[keep_rows], LH[keep_rows], LL[keep_rows], TT[keep_rows],
                'calendar without the 2 stray CTRA dates', cols)
    # indicative simple exposure backtest for W2.5 (PLAN criterion 4 for timing; NOT pre-registered here)
    for univ in ('all', 'pre2018'):
        selb = np.isin(tick, universe(P, univ)) & main_ev & np.isfinite(R['d25'])
        for c_lab, cin, cout in (('gross', 0., 0.), ('cost A', .0015, .0025), ('cost B', .004, .005)):
            bt = exposure_backtest(cal, E, R, LP, LO, selb, cin, cout)
            for k in ('MAIN', 'P4'):
                km = cal.mask(k) & (idx <= idx[-1])
                a, f = bt['tr'][km], bt['fix'][km]
                dlt = a - f
                md, sed, nd = nw(dlt, 5)
                sh = lambda x: x.mean() / x.std() * math.sqrt(250)
                note('exposure_bt', 'W2.5', f'{univ} {k} {c_lab}: daily EW of open trades, trailing minus fixed '
                     '(bps/day)', 1e4 * md, md / sed, nd,
                     comment=f'trailing {1e4 * a.mean():.2f} bps/day Sharpe {sh(a):.2f}; fixed {1e4 * f.mean():.2f} '
                             f'bps/day Sharpe {sh(f):.2f}; mean open trades {bt["n_tr"][km].mean():.1f} vs '
                             f'{bt["n_fix"][km].mean():.1f}')

    # ---------------------------------------------------------------- spot checks against the raw file
    spot_checks(P, E, R, cal, cols)

    # ---------------------------------------------------------------- output rows
    rows = []
    for tid in TESTS:
        e, t, n = res[(tid, 'all', 'MAIN')]
        ep, tp, _ = res[(tid, 'pre2018', 'MAIN')]
        ae, at_ = analyst.loc[tid, 'eff_MAIN'], analyst.loc[tid, 't_MAIN']
        ok_e = abs(e - ae) <= max(.1 * abs(ae), .05 if tid != 'W2.4' else .125)   # 0.05 pp over 40 days in bps/day
        ok_t = abs(t - at_) <= .5
        rows.append(dict(test_id=tid, analyst_eff=ae, analyst_t=at_, recomputed_eff=e, recomputed_t=t,
                         recomputed_eff_pre2018=ep, recomputed_t_pre2018=tp, n_days_main=n,
                         numbers_match=bool(ok_e and ok_t)))
    out = pd.DataFrame(rows)
    print(out.to_string())
    print(f'done in {time.time() - t0:.1f}s')
    return out, E, R, P, cal


# Verdicts written after reviewing this script's output (results/verify_W2_detail.csv); numbers quoted are from it.
VERDICT = {
    'W2.1': ('confirmed',
             'Recomputed exactly (2.7803%, t 1.857, 1786 days; pre2018 2.5121%; all subperiods, P0 and pre2018 '
             'subperiods identical). Method follows PLAN.md literally (raw z, thresholds ln1.05/ln0.95, decision at '
             'Close t+5 and z from Open t+6, conservative Diff t, lags 20); no look-ahead. u5/z5 hand-checked on 4 '
             'raw-file events. Claims verified: day-mean z +6.84% up / +4.06% down; event-weighted down +3.81% vs '
             'middle +3.34%; abnormal +1.75% (t 1.59), negative in P1 (-1.01) and P2 (-0.14); fully tradable '
             'lookbacks +2.54% (t 1.72). Robust to definitional choices (log +-0.05: 2.93%, t 1.95; z from next valid '
             'Open: 2.81%, t 1.89; symmetric data-error mask: 3.05%, t 2.06; without the stray CTRA dates: 2.83%, '
             't 1.88). Note: pre-registered lags 20 are short for the 55-day z window (t 1.53 with lags 60); no '
             'change to the conclusion (fails |t| >= 3). Nit: P3 t is 1.674, so "no subperiod reaches |t| > 1.67" '
             'is a rounding statement.'),
    'W2.2': ('confirmed',
             'Recomputed exactly (2.5997%, t 2.345, 2445 days; pre2018 2.6521%; P1 5.27, P2 2.40, P3 1.69, P4 0.06; '
             'pre2018 P4 0.14). Method literal (u20 at Close t+20, z from Open t+21, raw, Diff t, lags 20); no '
             'look-ahead; u20/z20 hand-checked on 4 raw-file events. Claims verified: day-mean z +4.02% up vs +1.42% '
             'down; abnormal +1.51% (t 2.21); fully tradable lookbacks +2.15% (t 1.99); first event per stock in 60 '
             'days +4.37% (t 3.40), correctly flagged as not the pre-registered statistic. Sensitivities do not '
             'change the verdict (log +-0.05 2.68% t 2.43; z from next valid Open 2.73% t 2.43; symmetric mask '
             '2.51% t 2.26; lags 60 t 1.91). Fails |t| >= 3, so "not usable" follows.'),
    'W2.3': ('confirmed',
             'Recomputed exactly (2.3022%, t 2.630, 2928 days, 5854 events; pre2018 2.0345% with the benchmark '
             'rebuilt on the 80 pre2018 stocks). Definition literal and causal: g = first Close in t+1..t+20 with '
             'lnP[g]-lnO[t+1] >= ln1.10 (PLAN day numbering: day k ends at Close t+k), entry Open g+1, identical-'
             'window EW benchmark over stocks with both ends valid; lags 60 by the general rule (lags 20: t 2.96, '
             'still < 3). g and r23 hand-checked on raw-file events (TLKM 2003 g=9, ESSA 2022 g=18). Claims '
             'verified: 35.6% trigger, median day 8, 108 dropped triggers, raw +5.48% (t 4.54), fully tradable '
             'lookbacks +1.45% (t 1.75) vs non-tradable lookbacks +8.42% (t 3.27). Note: 2.30% is the mean of daily '
             'means; event-weighted per trade it is 2.07% (still above the 0.90% B cost). The all-universe P4 '
             '(+1.76%) is carried by post-2018 listings (+7.90%), pre2018 P4 is +0.09%; the "high" survivorship '
             'label is justified.'),
    'W2.4': ('confirmed_with_caveat',
             'Recomputed exactly (1.8033 bps/day, t 2.048, 4599 days; pre2018 1.5315 with the pre2018 benchmark); a '
             'hand-computed benchmark for one 2022 window matches to 1e-16. Method literal (abnormal lnP[t+60]-'
             'lnP[t+20] minus the same-window EW mean of listed universe stocks, /40, x1e4; lags 40 by the general '
             'rule; lags 20 t 2.25, lags 60 t 2.00). Context verified: days 1-20 5.51 bps/day (t 3.70), days 61-120 '
             '1.58 (t 2.04), raw 6.46 (t 3.35), fully tradable 0.47 (t 0.55) vs 12.20 (t 4.25). Caveats: (1) '
             '"+0.72% abnormal per trade (40 x 1.80 bps)" uses the mean of daily means; event-weighted per trade it '
             'is 40 x 1.28 = 0.51%. (2) "Accrues mostly in the first 20 days" holds per day and within 60 days '
             '(1.10% vs 0.72%), but the abnormal drift continues at about 1.6 bps/day to day 120 (t 2.04), so the '
             'cumulative drift after day 20 (about 1.7% to day 120) exceeds the first-20-day amount. (3) As a timing '
             'rule PLAN criterion 4 needs an exposure backtest (not run; moot because |t| < 3). The test fails '
             '|t| >= 3 either way.'),
    'W2.5': ('confirmed_with_caveat',
             'Recomputed exactly with an explicit per-event loop (1.7427%, t 4.755, 4557 days, 16,607 trades; '
             'pre2018 1.5730%, t 4.32; P1 3.80, P2 1.56, P3 1.22, P4 -0.16; pre2018 P4 -1.27, t -3.90). Trailing rule '
             'literal and causal (first tradable Close in bars 1..119 below min lnL of the prior 10 market days, sell '
             'at the next valid Open, else Close t+120); trailing exits hand-checked on 4 raw-file events (29, 31, 96, '
             '51 bars). Criteria 1-3 pass and are robust to lags 120 (t 3.46), symmetric mask (1.71%, t 4.58), '
             '10-low over own tradable bars (1.98%, t 4.98), cap at Open t+121 (1.74%), removal of the stray dates '
             '(1.76%), excluding possibly locked one-price bars (1.66%, t 4.61) and declustering (1.61%, t 3.46 with '
             'lags 120). Caveats: (1) "+1.74% raw / +0.82% abnormal per trade" are means of daily means; per trade '
             '(event-weighted) they are +1.22% / +0.45%. (2) PLAN criterion 4 for timing requires a simple exposure '
             'backtest after costs; the analyst used per-trade/per-bar arguments instead, and reason (1) (11.8 vs '
             '12.3 bps/bar) is gross only: net of costs per bar the trailing arm is ahead (B 8.9 vs 7.8, A 10.6 vs '
             '10.3). The verifier\'s indicative exposure backtest (daily equal weight over open trades, MAIN) shows '
             'no net improvement: trailing minus fixed -1.47 bps/day gross (t -1.33), -0.70 with cost A, +0.23 with '
             'cost B (t 0.21), negative in P4 (pre2018 P4 cost B -2.57 bps/day, t -1.35). So criterion 4 is not met: '
             'best class ROBUST_NOT_USABLE_ALONE if BH q <= 0.05, not usable. (3) "Regime-dependent" is informal: '
             'W2.5 passes the stability rule (3 of 4 subperiods), so PLAN\'s REGIME_DEPENDENT class does not apply; '
             'the reversal is nevertheless real (pre2018 P4 -1.27%, t -3.90, negative every year 2021-2025), and the '
             'all-universe P4 is propped up by post-2018 listings (+4.29%, mostly PANI and WIFI). (4) "Top 10% of '
             'trades produced 93% of the 60-day P&L" describes fixed 60-day holds of all entries, not W2.5; direct '
             'evidence: the top 10% of paired differences sum to 285% of the total, trades held >= 20 bars add '
             '+1.54 pp and early exits -0.32 pp (-0.79% each). (5) Fragile: t < 3 on liquid lookbacks with lags 120 '
             '(0.97%, t 2.69), on the abnormal basis with lags 120 (0.82%, t 2.65), and in 2008-2025 (1.02%, t 2.99 '
             'at lags 20, 2.49 at lags 120); the "high" survivorship label is justified.'),
}


if __name__ == '__main__':
    out, E, R, P, cal = main()
    det = pd.DataFrame(DETAIL)
    det.to_csv(OUT / 'verify_W2_detail.csv', index=False)
    out['verdict'] = [VERDICT.get(t, ('not_checked', ''))[0] for t in out.test_id]
    out['issues'] = [VERDICT.get(t, ('', 'review pending'))[1] for t in out.test_id]
    out[['test_id', 'analyst_eff', 'analyst_t', 'recomputed_eff', 'recomputed_t', 'recomputed_eff_pre2018', 'verdict',
         'issues']].to_csv(OUT / 'verify_W2.csv', index=False)
    pd.set_option('display.width', 250)
    pd.set_option('display.max_colwidth', 140)
    print(det.to_string())
