"""Adversarial, independent re-computation of family W1 (breakout anatomy) of market-properties v2 (PLAN.md).

Nothing is imported from w1_breakout.py, and mpstats.event_series / sort_series / row are NOT used. From panel.py only
the raw/clean matrices lnP, lnO, lnH, V, T, C, O, H, L, idx_ret and the period constants are taken; signals (HHV levels
via a NaN-skipping sparse-table max, volume means, ER20, the EW index and its SMA200, failure days), forward returns,
abnormal adjustments, daily aggregation and differences are rebuilt here with numpy. mpstats.nw is used for the HAC
t-stats and is cross-checked against an own Newey-West implementation. The clean levels are rebuilt from the raw
C/O/H/L/T matrices and must equal the panel's; six events are re-derived by hand from Data/Data kompas 100.csv.

Readings (same as PLAN.md's most literal causal reading, chosen before comparing with the analyst):
- t-n..t-1 are market-calendar rows; max(lnH[...]) skips non-tradable days (lnH is NaN there, panel rule "prices of
  Volume-0 bars are ignored"); the stock must be listed at t-n; day t tradable. Sensitivities: strict (all days
  tradable), carry (a non-tradable day contributes its carried clean close), rawbar (Volume-0 bars' recorded High
  included, as in backtest_breakout_er.py's per-ticker rolling(20) on the stock's own bars).
- abnormal = minus the same-day EW mean over all universe stocks with a valid value over the identical window;
  pre2018 recomputes every cross-sectional mean and the EW index on the 80 tickers.
- W1.5: L = max(lnH[t-20..t-1]) (same as W1.1), trigger lnH[t] >= L+ln1.005 and a clean Open on day t, entry
  max(lnO[t], L+ln1.005), exit lnP[t+19]; benchmark EW mean of lnP[t+19]-lnO[t].
- W1.6 volume mean over the 20 market rows, Volume-0 days count as 0, missing rows skipped.
- W1.8 idx level = cumulative product of (1 + idx_ret); SMA200 over t-199..t; above: level > SMA, below: <=.
- W1.10 event = unique (stock, failure day f) pair; abnormal fo[20] at row f (entry Open f+1).

Writes results/verify_W1.csv. Run: python market_properties_v2/verify_w1.py   (about 1-2 minutes)
"""
import math
import sys
import time
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from panel import load, SUBPERIODS, MAIN, P0  # noqa: E402  (data + period constants only)
from mpstats import nw  # noqa: E402  (HAC helper only, cross-checked below)

warnings.filterwarnings('ignore', category=RuntimeWarning)
RAW = ROOT / 'Data' / 'Data kompas 100.csv'
OUT = HERE / 'results' / 'verify_W1.csv'
T0 = time.time()
PER = {'MAIN': MAIN, **SUBPERIODS, 'P0': P0}
SUBS = list(SUBPERIODS)
K05, K2 = math.log(1.005), math.log(1.02)
COST_B, COST_A = 0.90, 0.40   # % round trip (PLAN)
TESTS = ['W1.1', 'W1.2', 'W1.3', 'W1.4', 'W1.5', 'W1.6', 'W1.7', 'W1.8', 'W1.9', 'W1.10']
DIFF_TESTS = {'W1.6', 'W1.7', 'W1.8', 'W1.9'}


def say(*a):
    print(' '.join(str(x) for x in a), flush=True)


# ============================================================================ data
P = load()
DATES = P['C'].index
TICK = list(P['C'].columns)
_f = lambda k: P[k].values.astype(float)  # noqa: E731
lnP, lnO, lnH, V, C, O, H, L = (_f(k) for k in ['lnP', 'lnO', 'lnH', 'V', 'C', 'O', 'H', 'L'])
TM = P['T'].values.astype(bool)
N, K = lnP.shape
FIRST = np.array([int(np.argmax(np.isfinite(C[:, j]))) for j in range(K)])
POST = sorted(TICK[j] for j in range(K) if DATES[FIRST[j]] >= pd.Timestamp('2018-01-01'))
assert POST == sorted(P['post2018']) and len(POST) == 20
UNIV = {'all': np.arange(K), 'pre2018': np.array([j for j in range(K) if TICK[j] not in set(POST)])}


def rows_of(a, b):
    return (DATES >= pd.Timestamp(a)) & (DATES <= pd.Timestamp(b))


RM = rows_of(*MAIN)


# ============================================================================ helpers (own)
def shift(A, k):
    """result[t] = A[t-k] on the market calendar (k > 0 looks back, k < 0 looks forward)."""
    out = np.full(A.shape, np.nan) if A.dtype.kind == 'f' else np.zeros(A.shape, A.dtype)
    if k > 0:
        out[k:] = A[:-k]
    elif k < 0:
        out[:k] = A[-k:]
    else:
        out[:] = A
    return out


def roll_fmax_incl(X, n):
    """NaN-skipping max over rows t-n+1..t by sparse-table doubling (NaN if the window has no finite value)."""
    tab, span = {1: X}, 1
    while span * 2 <= n:
        tab[span * 2] = np.fmax(tab[span], shift(tab[span], span))
        span *= 2
    return np.fmax(tab[span], shift(tab[span], n - span)) if n > span else tab[span]


def roll_sum_incl(Z, n):
    """sum over rows t-n+1..t of a NaN-free matrix; first n-1 rows NaN."""
    c = np.vstack([np.zeros((1, Z.shape[1])), np.cumsum(Z, axis=0)])
    out = np.full(Z.shape, np.nan)
    out[n - 1:] = c[n:] - c[:-n]
    return out


def dmean(E, M):
    """daily mean over the day's events (M & finite)."""
    M = M & np.isfinite(E)
    s, n = np.where(M, E, 0.).sum(1), M.sum(1)
    out = np.full(len(s), np.nan)
    out[n > 0] = s[n > 0] / n[n > 0]
    return out


def own_nw(x, lags):
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    n = ok.sum()
    m = x[ok].mean()
    e = np.where(ok, x - m, 0.)
    s = e @ e
    for k in range(1, lags + 1):
        s += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k])
    return m, math.sqrt(s) / n, int(n)


def mstat(s, lags=20, per='MAIN'):
    r = rows_of(*PER[per])
    m, se, n = nw(s[r], lags)
    return m * 100, (m / se if se and se > 0 else np.nan), n


def dstat(sa, sb, lags=20, per='MAIN'):
    r = rows_of(*PER[per])
    ma, sea, na = nw(sa[r], lags)
    mb, seb, nb = nw(sb[r], lags)
    return (ma - mb) * 100, (ma - mb) / math.sqrt(sea ** 2 + seb ** 2), min(na, nb)


def build_levels(extra_bad=None, sym=False):
    """Clean log levels rebuilt from raw C/O/H and tradability (panel rule |simple| >= 50% masked)."""
    Ct = np.where(TM, C, np.nan)
    prevC = shift(pd.DataFrame(Ct).ffill().values, 1)
    lr, simple = np.log(Ct / prevC), Ct / prevC - 1
    bad = (np.abs(lr) >= math.log(1.5) - 1e-12) if sym else (np.abs(simple) >= .5)
    if extra_bad is not None:
        bad = bad | extra_bad
    rcc = np.where(bad, np.nan, lr)
    ron = np.where(bad, np.nan, np.log(np.where(TM, O, np.nan) / prevC))
    listed = np.cumsum(np.isfinite(C), axis=0) > 0
    lp = np.where(listed, np.cumsum(np.nan_to_num(rcc), axis=0), np.nan)
    lo = np.where(TM, shift(lp, 1) + ron, np.nan)
    lh = np.where(TM, lp + np.log(H / C), np.nan)
    return dict(lnP=lp, lnO=lo, lnH=lh, bad=bad, simple=np.where(bad, np.nan, simple), lr=lr)


# ============================================================================ all ten tests
def compute(lv=None, window='skip', lags=20, drop_entry=None, stop_drop=None, w10dup=False, w8cumsum=False,
            w6trad=False, stopfill=None):
    """Returns (stats, series, aux). stats[(tid, univ)][period] = (eff %, t, n); also 'evw' (event-weighted MAIN) and
    'nev'. drop_entry: signal-row mask of next-Open events to drop; stop_drop: W1.5 trigger days to drop; stopfill:
    optional clean-level fill matrix for W1.5 non-gap triggers (else exact stop)."""
    lp = lnP if lv is None else lv['lnP']
    lo = lnO if lv is None else lv['lnO']
    lh = lnH if lv is None else lv['lnH']
    fo20 = shift(lp, -20) - shift(lo, -1)                                  # lnP[t+20] - lnO[t+1]

    def level(n):
        if window == 'carry':
            X = np.where(TM, lh, lp)
        elif window == 'rawbar':
            X = np.where(np.isfinite(C), lp + np.log(H / C), np.nan)
        else:
            X = lh
        out = shift(roll_fmax_incl(X, n), 1)                              # rows t-n..t-1
        if window == 'strict':
            cnt = shift(roll_sum_incl(np.isfinite(lh).astype(float), n), 1)
            out[~(cnt == n)] = np.nan
        out[~np.isfinite(shift(lp, n))] = np.nan                          # listed at t-n
        return out

    LV = {n: level(n) for n in (20, 55, 120, 250)}
    BO = {n: TM & np.isfinite(LV[n]) & (lp > LV[n]) for n in LV}
    BOd = {n: (BO[n] & ~drop_entry) if drop_entry is not None else BO[n] for n in BO}
    L20, BO20 = LV[20], BO[20]
    # W1.6 volume mean over t-20..t-1
    vok = (TM & np.isfinite(V)) if w6trad else np.isfinite(V)
    vs = shift(roll_sum_incl(np.where(vok, V, 0.), 20), 1)
    vc = shift(roll_sum_incl(vok.astype(float), 20), 1)
    vmean = np.where(vc > 0, vs / np.where(vc > 0, vc, 1), np.nan)
    vmean[~np.isfinite(shift(lp, 20))] = np.nan
    A6 = BOd[20] & np.isfinite(vmean) & (V >= 2 * vmean)
    B6 = BOd[20] & np.isfinite(vmean) & (V < 2 * vmean)
    # W1.7 ER20
    dl = np.abs(np.diff(lp, axis=0, prepend=np.nan))
    den = roll_sum_incl(np.where(np.isfinite(dl), dl, 0.), 20)
    den[roll_sum_incl(np.isfinite(dl).astype(float), 20) < 20] = np.nan
    er = np.abs(lp - shift(lp, 20)) / den
    A7 = BOd[20] & np.isfinite(er) & (er >= .3)
    B7 = BOd[20] & np.isfinite(er) & (er < .3)
    # W1.8 regime
    simple_c = build_levels()['simple'] if lv is None else lv['simple']

    def regime(ret):
        x = np.nan_to_num(ret)
        lvl = 1 + np.cumsum(x) if w8cumsum else np.cumprod(1 + x)
        sma = pd.Series(lvl).rolling(200, min_periods=200).mean().values
        return (lvl > sma) & np.isfinite(sma), (lvl <= sma) & np.isfinite(sma)
    # W1.10 failure days
    fail = np.zeros(BO20.shape, bool)
    prior = np.zeros(BO20.shape, bool)
    wdup = np.zeros(BO20.shape)
    for k in (1, 2, 3):
        nxt = shift(lp, -k)
        below = np.isfinite(nxt) & np.isfinite(L20) & (nxt < L20)
        fk = BO20 & below & ~prior
        prior |= below
        fail[k:] |= fk[:-k]
        wdup[k:] += fk[:-k]
    if drop_entry is not None:
        fail &= ~drop_entry
        wdup = np.where(drop_entry, 0., wdup)
    ser, stats = {}, {}
    for u in ('all', 'pre2018'):
        c = UNIV[u]
        F = fo20[:, c]
        Fa = F - np.nanmean(F, axis=1, keepdims=True)
        evm = lambda M: np.where(M & np.isfinite(Fa), Fa, np.nan)  # noqa: E731
        for n, tid in zip((20, 55, 120, 250), ('W1.1', 'W1.2', 'W1.3', 'W1.4')):
            ser[(tid, u)] = ('m', dmean(Fa, BOd[n][:, c]), evm(BOd[n][:, c]))
        # W1.5 / W1.9
        Lc, loc, hic, lpc = L20[:, c], lo[:, c], lh[:, c], lp[:, c]
        lev = Lc + K05
        trig = np.isfinite(lev) & np.isfinite(hic) & (hic >= lev) & np.isfinite(loc)
        if stop_drop is not None:
            trig &= ~stop_drop[:, c]
        fill = lev if stopfill is None else np.where(np.isfinite(stopfill[:, c]), stopfill[:, c], lev)
        lnE = np.maximum(loc, fill)
        ex = shift(lpc, -19)
        bench = np.nanmean(ex - loc, axis=1, keepdims=True)
        M = trig & np.isfinite(ex - lnE)
        a = np.where(M, ex - lnE - bench, np.nan)
        gap = M & (loc >= Lc + K2)
        rest = M & ~(loc >= Lc + K2)
        ser[('W1.5', u)] = ('m', dmean(a, M), a)
        ser[('W1.9', u)] = ('d', (dmean(a, gap), dmean(a, rest)), (np.where(gap, a, np.nan), np.where(rest, a, np.nan)))
        for tid, A_, B_ in (('W1.6', A6, B6), ('W1.7', A7, B7)):
            ser[(tid, u)] = ('d', (dmean(Fa, A_[:, c]), dmean(Fa, B_[:, c])), (evm(A_[:, c]), evm(B_[:, c])))
        idx_src = P['idx_ret'].values if (u == 'all' and lv is None) else np.nanmean(simple_c[:, c], axis=1)
        up, dn = regime(idx_src)
        mA, mB = BOd[20][:, c] & up[:, None], BOd[20][:, c] & dn[:, None]
        ser[('W1.8', u)] = ('d', (dmean(Fa, mA), dmean(Fa, mB)), (evm(mA), evm(mB)))
        if w10dup:
            w = wdup[:, c]
            mm = (w > 0) & np.isfinite(Fa)
            sd, nd = np.where(mm, Fa * w, 0.).sum(1), np.where(mm, w, 0.).sum(1)
            s10 = np.full(N, np.nan)
            s10[nd > 0] = sd[nd > 0] / nd[nd > 0]
        else:
            s10 = dmean(Fa, fail[:, c])
        ser[('W1.10', u)] = ('m', s10, evm(fail[:, c]))
    for key, (kind, s, ev) in ser.items():
        pers = PER if key[1] == 'all' else {'MAIN': MAIN}
        if kind == 'm':
            stats[key] = {p: mstat(s, lags, p) for p in pers}
            stats[key]['evw'] = np.nanmean(ev[RM]) * 100
            stats[key]['nev'] = int(np.isfinite(ev[RM]).sum())
        else:
            stats[key] = {p: dstat(s[0], s[1], lags, p) for p in pers}
            stats[key]['evw'] = (np.nanmean(ev[0][RM]) - np.nanmean(ev[1][RM])) * 100
            stats[key]['nev'] = (int(np.isfinite(ev[0][RM]).sum()), int(np.isfinite(ev[1][RM]).sum()))
    aux = dict(LV=LV, BO=BO, A6=A6, B6=B6, A7=A7, B7=B7, er=er, vmean=vmean, fail=fail, fo20=fo20, lp=lp, lo=lo,
               lh=lh, prior=prior)
    return stats, ser, aux


def brief(st, tag):
    say(f'  {tag:44s}', ' '.join(f'{t} {st[(t, "all")]["MAIN"][0]:+.3f}({st[(t, "all")]["MAIN"][1]:.2f})' for t in TESTS))


# ============================================================================ 1. integrity checks
say('== 1. integrity: panel levels rebuilt from raw matrices, own NW vs mpstats.nw, brute-force HHV')
LV0 = build_levels()
for nm, a, b in (('lnP', LV0['lnP'], lnP), ('lnO', LV0['lnO'], lnO), ('lnH', LV0['lnH'], lnH)):
    ok = np.allclose(np.nan_to_num(a, nan=-99.), np.nan_to_num(b, nan=-99.), atol=1e-9)
    assert ok, nm
say('  clean lnP/lnO/lnH rebuilt from C/O/H/T equal the panel; bad prints', int(LV0['bad'].sum()), '(panel', P['bad_count'], ')')
ew = np.nanmean(LV0['simple'], axis=1)
assert np.allclose(np.nan_to_num(ew), np.nan_to_num(P['idx_ret'].values), atol=1e-15)
say('  idx_ret equals own EW mean of clean simple returns')
BASE, SER, AUX = compute()
s11 = SER[('W1.1', 'all')][1][RM]
m1, se1, _ = nw(s11, 20)
m2, se2, _ = own_nw(s11, 20)
assert abs(m1 - m2) < 1e-14 and abs(se1 - se2) < 1e-14
say(f'  own NW == mpstats.nw on the W1.1 series (se {se1:.3e})')
rng = np.random.default_rng(20261018)
for n in (20, 55, 120, 250):
    lvn, bon = AUX['LV'][n], AUX['BO'][n]
    for i, j in zip(rng.integers(n, N, 4000), rng.integers(0, K, 4000)):
        w = lnH[i - n:i, j]
        ref = np.nanmax(w) if (np.isfinite(lnP[i - n, j]) and np.isfinite(w).any()) else np.nan
        assert (np.isnan(ref) and np.isnan(lvn[i, j])) or abs(ref - lvn[i, j]) < 1e-12, (n, i, j)
        assert bool(TM[i, j] and np.isfinite(ref) and lnP[i, j] > ref) == bool(bon[i, j])
say('  brute-force HHV levels / breakout flags agree on 16,000 random cells')

# ============================================================================ 2. hand checks against the raw CSV
say('== 2. spot checks against', RAW.name)
raw = pd.read_csv(RAW)
raw['Date'] = pd.to_datetime(raw['Date/Time'], format='mixed', dayfirst=True)
raw = raw[raw['Date'] == raw['Date'].dt.normalize()].copy()            # drop intraday-stamped bar (engine rule)
px = raw[['Open', 'High', 'Low', 'Close']].to_numpy(float)
raw['High'], raw['Low'] = px.max(1), px.min(1)                          # engine repairs High/Low (31 raw anomalies)
CAL = pd.DatetimeIndex(sorted(raw['Date'].unique()))
assert CAL.equals(DATES), 'raw market calendar differs from panel calendar'
RAWG = {tk: g.set_index('Date').sort_index() for tk, g in raw.groupby('Ticker')}


def rget(tk, i):
    g = RAWG[tk]
    d = CAL[i]
    return g.loc[d] if d in g.index else None


def raw_level(tk, i, n=20):
    hs = [r['High'] for r in (rget(tk, k) for k in range(i - n, i)) if r is not None and r['Volume'] > 0]
    return max(hs), n - len(hs)


def raw_close_carry(tk, i):
    for k in range(i, -1, -1):
        r = rget(tk, k)
        if r is not None and r['Volume'] > 0:
            return r['Close']


def pick(mask, tk=None, start='2000-01-01', extra=None):
    cand = np.argwhere(mask & rows_of(start, '2025-12-31')[:, None])
    for i, j in cand:
        if tk is not None and TICK[j] != tk:
            continue
        if extra is not None and not extra(i, j):
            continue
        return int(i), int(j)
    raise RuntimeError('no event')


SPOT = []
fo20, BO20, L20 = AUX['fo20'], AUX['BO'][20], AUX['LV'][20]
clean_window = lambda i, j, a, b: not LV0['bad'][i + a:i + b + 1, j].any()  # noqa: E731
fwin = lambda i, j: np.isfinite(fo20[i, j]) and clean_window(i, j, -21, 21)  # noqa: E731
TRADCNT20 = shift(roll_sum_incl(np.isfinite(lnH).astype(float), 20), 1)   # tradable days in t-20..t-1
events = [('W1.1 liquid P4', pick(BO20, 'BBRI', '2023-01-01', fwin)),
          ('W1.1 with Volume-0 day in lookback', pick(BO20 & (TRADCNT20 < 20), None, '2009-01-01', fwin)),
          ('W1.1 top contributor (ULTJ Apr 2001)', pick(BO20, 'ULTJ', '2001-04-23', fwin))]
for tag, (i, j) in events:
    tk = TICK[j]
    lev, n0 = raw_level(tk, i)
    r_t, r_e = rget(tk, i), rget(tk, i + 1)
    cx = raw_close_carry(tk, i + 20)
    rr = math.log(cx / r_e['Open'])
    assert r_t['Close'] > lev and r_t['Volume'] > 0 and r_e['Volume'] > 0
    assert abs(rr - fo20[i, j]) < 1e-9, (tag, rr, fo20[i, j])
    # benchmark from raw: EW mean over all tickers with entry Open at i+1 (Volume>0) and carried exit close at i+20
    vals = []
    for tk2 in TICK:
        e2 = rget(tk2, i + 1)
        if e2 is None or e2['Volume'] <= 0 or not np.isfinite(fo20[i, TICK.index(tk2)]):
            continue
        vals.append(math.log(raw_close_carry(tk2, i + 20) / e2['Open']))
    bm = float(np.mean(vals))
    pan_bm = float(np.nanmean(fo20[i, :]))
    SPOT.append(dict(check=tag, ticker=tk, date=str(CAL[i].date()), raw_level=lev, nontradable_in_window=n0,
                     close_t=r_t['Close'], entry_open=r_e['Open'], exit_close=cx, raw_ret=rr, panel_fo20=fo20[i, j],
                     raw_bench=bm, panel_bench=pan_bm, raw_abn_pct=(rr - bm) * 100))
    assert abs(bm - pan_bm) < 1e-6, (tag, bm, pan_bm)
# W1.5 non-gap and gap triggers
lev5 = L20 + K05
trig5 = np.isfinite(lev5) & np.isfinite(lnH) & (lnH >= lev5) & np.isfinite(lnO) & np.isfinite(shift(lnP, -19))
for tag, cond, tk0, st in (('W1.5 non-gap trigger', lambda i, j: lnO[i, j] < lev5[i, j], 'TLKM', '2018-01-01'),
                           ('W1.5 gap trigger (Open >= L+2%)', lambda i, j: lnO[i, j] >= L20[i, j] + K2, None, '2019-01-01')):
    i, j = pick(trig5, tk0, st, lambda i, j, cond=cond: cond(i, j) and clean_window(i, j, -21, 20))
    tk = TICK[j]
    lev, n0 = raw_level(tk, i)
    stop = lev * 1.005
    r_t = rget(tk, i)
    assert r_t['High'] >= stop and r_t['Volume'] > 0
    entry = max(r_t['Open'], stop)
    cx = raw_close_carry(tk, i + 19)
    rr = math.log(cx / entry)
    pan = shift(lnP, -19)[i, j] - max(lnO[i, j], lev5[i, j])
    assert abs(rr - pan) < 1e-9, (tag, rr, pan)
    SPOT.append(dict(check=tag, ticker=tk, date=str(CAL[i].date()), raw_level=lev, nontradable_in_window=n0,
                     close_t=r_t['Close'], entry_open=entry, exit_close=cx, raw_ret=rr, panel_fo20=pan,
                     raw_bench=np.nan, panel_bench=np.nan, raw_abn_pct=np.nan))
# W1.10 failure
FAIL = AUX['fail']
i, j = pick(FAIL, 'ASII', '2015-01-01', lambda i, j: np.isfinite(fo20[i, j]) and clean_window(i, j, -25, 21))
tk = TICK[j]
found = None
for k in (1, 2, 3):                                                     # find the breakout day t that failed on f=i
    t = i - k
    if BO20[t, j]:
        lev_t, _ = raw_level(tk, t)
        closes = [raw_close_carry(tk, t + q) for q in (1, 2, 3)]
        f_first = next((q for q, cq in zip((1, 2, 3), closes) if cq < lev_t), None)
        if f_first == k:
            found = (t, lev_t)
            break
assert found is not None
t, lev_t = found
r_e = rget(tk, i + 1)
cx = raw_close_carry(tk, i + 20)
rr = math.log(cx / r_e['Open'])
assert abs(rr - fo20[i, j]) < 1e-9
SPOT.append(dict(check='W1.10 failure day f (breakout ' + str(CAL[t].date()) + ')', ticker=tk, date=str(CAL[i].date()),
                 raw_level=lev_t, nontradable_in_window=np.nan, close_t=raw_close_carry(tk, i), entry_open=r_e['Open'],
                 exit_close=cx, raw_ret=rr, panel_fo20=fo20[i, j], raw_bench=np.nan, panel_bench=np.nan,
                 raw_abn_pct=np.nan))
# W1.6 / W1.7 inputs on the first spot event
i, j = events[0][1]
tk = TICK[j]
vols = [r['Volume'] for r in (rget(tk, k) for k in range(i - 20, i)) if r is not None]
cl = [raw_close_carry(tk, k) for k in range(i - 20, i + 1)]
er_raw = abs(math.log(cl[-1] / cl[0])) / sum(abs(math.log(cl[q] / cl[q - 1])) for q in range(1, 21))
assert abs(np.mean(vols) - AUX['vmean'][i, j]) < 1e-6 and abs(er_raw - AUX['er'][i, j]) < 1e-9
say(f'  {tk} {CAL[i].date()}: raw mean V[t-20..t-1] {np.mean(vols):,.0f} (V[t] {rget(tk, i)["Volume"]:,.0f}), raw ER20 '
    f'{er_raw:.4f} == own matrices')
spot = pd.DataFrame(SPOT)
with pd.option_context('display.width', 250, 'display.max_columns', 20):
    say(spot.round(5).to_string(index=False))

# ============================================================================ 3. primary statistics vs analyst
say('== 3. primary statistics (MAIN all / pre2018) vs analyst W1_tests.csv')
AN = pd.read_csv(HERE / 'results' / 'W1_tests.csv').set_index('test_id')
dev = 0.
for t in TESTS:
    for p in PER:
        e, tt, n = BASE[(t, 'all')][p]
        dev = max(dev, abs(e - AN.loc[t, f'eff_{p}']), abs(tt - AN.loc[t, f't_{p}']), abs(n - AN.loc[t, f'n_{p}']))
    e, tt, n = BASE[(t, 'pre2018')]['MAIN']
    dev = max(dev, abs(e - AN.loc[t, 'eff_pre2018']), abs(tt - AN.loc[t, 't_pre2018']), abs(n - AN.loc[t, 'n_pre2018']))
    say(f'  {t:5s} analyst {AN.loc[t, "eff_MAIN"]:+.4f} t {AN.loc[t, "t_MAIN"]:.3f} | own {BASE[(t, "all")]["MAIN"][0]:+.4f} t '
        f'{BASE[(t, "all")]["MAIN"][1]:.3f} n {BASE[(t, "all")]["MAIN"][2]} | pre2018 {BASE[(t, "pre2018")]["MAIN"][0]:+.4f} '
        f't {BASE[(t, "pre2018")]["MAIN"][1]:.3f} | subs ' + ' '.join(f'{BASE[(t, "all")][p][0]:+.2f}' for p in SUBS)
        + f' | P0 {BASE[(t, "all")]["P0"][0]:+.2f} | evw {BASE[(t, "all")]["evw"]:+.3f}')
say(f'  max |deviation| over every period, effect, t and n: {dev:.2e}')

# ============================================================================ 4. sensitivities
say('== 4. sensitivities (MAIN, all universe; eff % (t))')
SENS = {}
brief(BASE, 'base (PLAN reading = analyst reading)')
for tag, kw in (('NW lags 40 (2h)', dict(lags=40)), ('window strict (all days tradable)', dict(window='strict')),
                ('window carry (non-tradable = carried close)', dict(window='carry')),
                ('window rawbar (V=0 bars incl., research code)', dict(window='rawbar')),
                ('W1.10 per failing breakout, W1.8 cumsum, W1.6 trad', dict(w10dup=True, w8cumsum=True, w6trad=True))):
    SENS[tag] = compute(**kw)[0]
    brief(SENS[tag], tag)
# bad-print masking: targeted reverting legs vs symmetric ln1.5 threshold
Ct = np.where(TM, C, np.nan)
lr = LV0['lr']
rev = np.zeros(TM.shape, bool)
for j in range(K):
    tr = np.where(TM[:, j])[0]
    for p in range(1, len(tr)):
        a_, b_ = tr[p - 1], tr[p]
        if (LV0['bad'][a_, j] or rev[a_, j]) and not LV0['bad'][b_, j] and np.sign(lr[b_, j]) != np.sign(lr[a_, j]) \
                and abs(lr[b_, j]) >= math.log(1.2):
            rev[b_, j] = True
SENS['targeted'] = compute(lv=build_levels(extra_bad=rev))[0]
brief(SENS['targeted'], f'mask reverting legs after masked day ({int(rev.sum())})')
LVS = build_levels(sym=True)
SENS['sym'] = compute(lv=LVS)[0]
extra_sym = LVS['bad'] & ~LV0['bad']
brief(SENS['sym'], f'symmetric |ln| >= ln1.5 mask (+{int(extra_sym.sum())} days)')
doid = TICK.index('DOID')
e2 = extra_sym.copy()
e2[:, doid] = False
SENS['sym_noDOID'] = compute(lv=build_levels(extra_bad=e2 | rev))[0]
brief(SENS['sym_noDOID'], 'symmetric mask except DOID crash days')
# untradable / suspicious entries
prevC = shift(pd.DataFrame(Ct).ffill().values, 1)
locked = TM & (O == H) & (H == L) & (L == C) & (C > prevC * 1.05)
openhigh = TM & (O == H) & (O / prevC - 1 >= .10)
ron_, rid_ = np.log(O / prevC), np.log(C / O)
badopen = TM & (np.abs(ron_) >= .25) & (np.abs(rid_) >= .2) & (np.sign(ron_) != np.sign(rid_))
nxt = lambda m: shift(m.astype(float), -1) > 0  # noqa: E731
SENS['drop_locked'] = compute(drop_entry=nxt(locked | openhigh | badopen), stop_drop=locked | openhigh)[0]
brief(SENS['drop_locked'], 'drop limit-locked/open-at-high/odd-open entries')
say(f'    (W1.1 MAIN events with such an entry day: {int((BO20 & nxt(locked | openhigh | badopen))[RM].sum())}; '
    f'W1.5 MAIN triggers on locked/open-at-high days: {int((trig5 & (locked | openhigh))[RM].sum())})')
# unmasked sub-50% close spikes that revert next row (possible data errors below the panel threshold)
rcc_ = np.where(LV0['bad'], np.nan, lr)
nx_ = shift(rcc_, -1)
spike = np.isfinite(rcc_) & np.isfinite(nx_) & (np.abs(rcc_) >= math.log(1.25)) & (np.sign(nx_) != np.sign(rcc_)) \
    & (np.abs(nx_) >= math.log(1.2))
inwin = np.zeros(TM.shape, bool)
for k in range(1, 21):
    inwin |= shift(spike.astype(float), -k) > 0
SENS['drop_spike'] = compute(drop_entry=spike | inwin)[0]
brief(SENS['drop_spike'], f'drop events at/near {int(spike[RM].sum())} spike-revert prints')
# W1.5 next-tick fills: effective tick = min positive gap between distinct OHLC prices of the stock in rows i-60..i
TKM = np.full(TM.shape, np.nan)
for j in range(K):
    pxj = np.stack([O[:, j], H[:, j], L[:, j], C[:, j]], 1)
    okr = np.isfinite(pxj).all(1)
    for i in np.where(okr)[0]:
        lo_ = max(0, i - 60)
        v = np.unique(np.round(pxj[lo_:i + 1][okr[lo_:i + 1]].ravel(), 6))
        d = np.diff(v)
        d = d[d > 1e-6]
        if len(d):
            TKM[i, j] = d.min()
prevC_raw = shift(C, 1)


def tick_fill(stop_clean):
    stop_raw = np.exp(stop_clean - lnP) * C                                # same-day clean -> raw price map
    anchor = np.where(np.isfinite(prevC_raw), prevC_raw, O)
    fr = anchor + np.ceil((stop_raw - anchor) / TKM - 1e-9) * TKM
    fr = np.minimum(np.where(np.isfinite(fr), np.maximum(fr, stop_raw), stop_raw), H)
    return stop_clean + np.log(fr / stop_raw)


FILL5 = tick_fill(L20 + K05)
SENS['tick'], SER_TICK, _ = compute(stopfill=FILL5)
brief(SENS['tick'], 'W1.5/W1.9 fills at next price-grid tick')
# lenient alternative: finest common grid (gcd-like) of the window's prices on trigger cells
TKM_MIN = TKM.copy()
for i, j in np.argwhere(np.isfinite(L20) & np.isfinite(lnH) & (lnH >= L20 + K05) & np.isfinite(lnO)):
    lo_ = max(0, i - 60)
    v = np.unique(np.round(np.concatenate([O[lo_:i + 1, j], H[lo_:i + 1, j], L[lo_:i + 1, j], C[lo_:i + 1, j]]), 6))
    v = v[np.isfinite(v)]
    if len(v) < 2 or not np.isfinite(TKM_MIN[i, j]):
        continue
    for q in range(1, 11):
        rem = (v - v[0]) / (TKM_MIN[i, j] / q)
        if np.all(np.abs(rem - np.round(rem)) < 1e-3):
            TKM[i, j] = TKM_MIN[i, j] / q
            break
    else:
        TKM[i, j] = np.nan                                                # no common grid: exact stop (lenient)
SENS['tick_gcd'] = compute(stopfill=tick_fill(L20 + K05))[0]
TKM = TKM_MIN
brief(SENS['tick_gcd'], 'W1.5/W1.9 lenient grid (finest common grid)')
r4 = rows_of(*SUBPERIODS['P4'])


def rule_tick(p):   # IDX fraksi harga since 2016
    return np.select([p < 200, p < 500, p < 2000, p < 5000], [1, 2, 5, 10], 25)


m4 = trig5 & r4[:, None] & np.isfinite(TKM) & np.isfinite(prevC_raw)
tk_est, tk_rule = TKM[m4], rule_tick(prevC_raw[m4])
TICK_VALID = (np.mean(np.isclose(tk_est, tk_rule)), np.mean(tk_est < tk_rule - 1e-9), np.mean(tk_est > tk_rule + 1e-9))
extra_slip = np.where(trig5 & (lnO < L20 + K05), FILL5 - (L20 + K05), 0.)
say(f'    tick check P4: estimated == IDX table {TICK_VALID[0]:.1%}, smaller {TICK_VALID[1]:.1%}, larger {TICK_VALID[2]:.1%}; mean '
    f'extra fill vs exact stop over triggers {np.nanmean(extra_slip[trig5 & RM[:, None]]) * 100:.3f}% (P1 '
    f'{np.nanmean(extra_slip[trig5 & rows_of(*SUBPERIODS["P1"])[:, None]]) * 100:.2f}%, P4 '
    f'{np.nanmean(extra_slip[trig5 & r4[:, None]]) * 100:.2f}%)')
bench_oc = np.nanmean(lnP - lnO, axis=1, keepdims=True)
D0 = {}
for nm, fl in (('exact', L20 + K05), ('tick', FILL5)):
    fill = np.maximum(lnO, fl)
    D0[nm] = mstat(dmean(np.where(trig5, lnP - fill - bench_oc, np.nan), trig5), 5)
PLACEBO = {}
for x in (.005, .01, .02):
    stp = lnO + math.log(1 + x)
    trp = np.isfinite(lnO) & np.isfinite(lnH) & (lnH >= stp)
    PLACEBO[x] = (mstat(dmean(np.where(trp, lnP - stp - bench_oc, np.nan), trp), 5)[0],
                  mstat(dmean(np.where(trp, lnP - tick_fill(stp) - bench_oc, np.nan), trp), 5)[0])
say(f'    W1.5 entry-day part: exact fill {D0["exact"][0]:+.3f}% (t {D0["exact"][1]:.1f}) -> tick fill {D0["tick"][0]:+.3f}% '
    f'(t {D0["tick"][1]:.1f}); placebo buy stops at Open+0.5/1/2% on all stock-days: exact '
    + '/'.join(f'{v[0]:+.2f}' for v in PLACEBO.values()) + ', tick ' + '/'.join(f'{v[1]:+.2f}' for v in PLACEBO.values()))
W15T = SENS['tick'][('W1.5', 'all')]
ENTRY_GAP = {k: SENS[k][('W1.5', 'all')]['MAIN'][0] - BASE[('W1.1', 'all')]['MAIN'][0] for k in ('tick', 'tick_gcd')}
ENTRY_GAP['exact'] = BASE[('W1.5', 'all')]['MAIN'][0] - BASE[('W1.1', 'all')]['MAIN'][0]
say(f'    stop entry vs Close-confirmed entry (W1.5 minus W1.1, MAIN day-averaged, descriptive): exact {ENTRY_GAP["exact"]:+.2f} pp, '
    f'next-tick {ENTRY_GAP["tick"]:+.2f} pp, lenient grid {ENTRY_GAP["tick_gcd"]:+.2f} pp')
say(f'    W1.5 tick fill: MAIN {W15T["MAIN"][0]:+.3f} t {W15T["MAIN"][1]:.2f}; subs ' + ' '.join(f'{W15T[p][0]:+.2f}' for p in SUBS)
    + f'; pre2018 {SENS["tick"][("W1.5", "pre2018")]["MAIN"][0]:+.3f} t {SENS["tick"][("W1.5", "pre2018")]["MAIN"][1]:.2f}; '
    f'event-weighted {W15T["evw"]:+.3f}')


# robustness of passers: leave one ticker out, winsorised abnormal returns, pre2018 P4
def from_ev(kind, ev, cols=None, clip=None, per='MAIN'):
    if kind == 'm':
        e = ev if cols is None else ev[:, cols]
        e = e if clip is None else np.clip(e, -clip, clip)
        return mstat(np.nanmean(e, axis=1), 20, per)
    a, b = ev
    if cols is not None:
        a, b = a[:, cols], b[:, cols]
    if clip is not None:
        a, b = np.clip(a, -clip, clip), np.clip(b, -clip, clip)
    return dstat(np.nanmean(a, axis=1), np.nanmean(b, axis=1), 20, per)


ROB = {}
for t in TESTS:
    kind, _, ev = SER[(t, 'all')]
    loo = sorted((from_ev(kind, ev, cols=np.array([c for c in range(K) if c != j]))[1], TICK[j]) for j in range(K))
    ROB[t] = dict(loo_min=loo[0], loo_2nd=loo[1], clip50=from_ev(kind, ev, clip=.5), clip30=from_ev(kind, ev, clip=.3),
                  pre_P4=from_ev(*SER[(t, 'pre2018')][::2], per='P4'))
    if t in DIFF_TESTS:
        (sa, sb) = SER[(t, 'all')][1]
        both = np.isfinite(sa) & np.isfinite(sb)
        ROB[t]['paired'] = mstat(np.where(both, sa - sb, np.nan)) if t != 'W1.8' else (np.nan, np.nan, 0)
    say(f'  {t:5s} leave-one-ticker-out min t {loo[0][0]:.2f} (w/o {loo[0][1]}), 2nd {loo[1][0]:.2f} (w/o {loo[1][1]}); '
        f'clip +-50%: {ROB[t]["clip50"][0]:+.3f} t {ROB[t]["clip50"][1]:.2f}; clip +-30%: {ROB[t]["clip30"][0]:+.3f} t '
        f'{ROB[t]["clip30"][1]:.2f}; pre2018 P4 {ROB[t]["pre_P4"][0]:+.3f} t {ROB[t]["pre_P4"][1]:.2f}'
        + (f'; paired same-day diff {ROB[t]["paired"][0]:+.3f} t {ROB[t]["paired"][1]:.2f}' if t in DIFF_TESTS - {'W1.8'} else ''))
# contributions to W1.1
ev11 = SER[('W1.1', 'all')][2]
nday = np.isfinite(ev11).sum(1)
contrib = np.where(np.isfinite(ev11) & RM[:, None], ev11 / np.maximum(nday, 1)[:, None], 0.) / int(np.isfinite(SER[('W1.1', 'all')][1][RM]).sum()) * 100
bytk = pd.Series(contrib.sum(0), index=TICK).sort_values(ascending=False)
ultj01 = contrib[rows_of('2001-04-01', '2001-05-31'), TICK.index('ULTJ')].sum()
nd4 = int(np.isfinite(SER[('W1.1', 'all')][1][r4]).sum())
con4 = pd.Series(np.where(np.isfinite(ev11) & r4[:, None], ev11 / np.maximum(nday, 1)[:, None], 0.).sum(0) / nd4 * 100, index=TICK)
P4_POST = float(con4[POST].sum())
P4_TOP = con4[POST].sort_values(ascending=False).head(4).to_dict()
say(f'  W1.1 P4 mean {con4.sum():.3f}: post-2018 listings contribute {P4_POST:.3f} pp (' +
    ', '.join(f'{k} {v:.3f}' for k, v in P4_TOP.items()) + ')')
say(f'  W1.1 contribution by ticker (pp of {np.nansum(contrib):.3f}): ' + ', '.join(f'{k} {v:.3f}' for k, v in bytk.head(6).items())
    + f'; ULTJ Apr-May 2001 single-event days alone {ultj01:.3f} pp')
# fresh vs repeat, fullwin, failure shares, P4 composition (claims)
prev = shift(roll_sum_incl(BO20.astype(float), 20), 1)
prev[:21] = np.vstack([np.zeros((1, K)), np.cumsum(BO20.astype(float), axis=0)[:-1]])[:21]
FRESH, REP = BO20 & (prev == 0), BO20 & (prev > 0)
FW20 = (shift(roll_sum_incl(np.isfinite(lnH).astype(float), 20), 1) == 20) & np.isfinite(shift(lnP, 20))
Fa_all = fo20 - np.nanmean(fo20, axis=1, keepdims=True)
cm = lambda M: mstat(dmean(Fa_all, M))  # noqa: E731
CL = dict(fresh=cm(FRESH), repeat=cm(REP), rep_share=np.isfinite(np.where(REP, Fa_all, np.nan)[RM]).sum() /
          np.isfinite(np.where(BO20, Fa_all, np.nan)[RM]).sum(), full=cm(BO20 & FW20), part=cm(BO20 & ~FW20),
          er_bins=[cm(BO20 & (AUX['er'] >= a) & (AUX['er'] < b)) for a, b in ((0, .2), (.2, .3), (.3, .5), (.5, 2))],
          w17_full=dstat(dmean(Fa_all, AUX['A7'] & FW20), dmean(Fa_all, AUX['B7'] & FW20)),
          w17_fresh=dstat(dmean(Fa_all, AUX['A7'] & FRESH), dmean(Fa_all, AUX['B7'] & FRESH)))
nofail = np.zeros(TM.shape, bool)
nofail[3:] = (BO20 & ~AUX['prior'] & np.isfinite(shift(lnP, -3)))[:-3]
CL['nofail'] = cm(nofail)
g9 = SER[('W1.9', 'all')][2][0][r4]
jj9 = np.where(np.isfinite(g9))[1]
isp = np.array([TICK[j] in set(POST) for j in jj9])
v9 = g9[np.isfinite(g9)]
CL['w19_p4'] = (len(v9), int(isp.sum()), v9.mean() * 100, v9[~isp].mean() * 100, Counter(TICK[j] for j in jj9[isp]).most_common(3))
say(f'  claims: fresh {CL["fresh"][0]:+.2f} (t {CL["fresh"][1]:.2f}), repeat {CL["repeat"][0]:+.2f} (t {CL["repeat"][1]:.2f}), '
    f'repeat share {CL["rep_share"]:.1%}; full lookback {CL["full"][0]:+.2f} (t {CL["full"][1]:.2f}), non-tradable day in '
    f'lookback {CL["part"][0]:+.2f} (t {CL["part"][1]:.2f}); ER bins ' + ' '.join(f'{b[0]:+.2f}' for b in CL['er_bins'])
    + f'; W1.7 full lookback {CL["w17_full"][0]:+.2f} (t {CL["w17_full"][1]:.2f}), fresh {CL["w17_fresh"][0]:+.2f} '
    f'(t {CL["w17_fresh"][1]:.2f}); non-failed {CL["nofail"][0]:+.2f} (t {CL["nofail"][1]:.2f}); W1.9 P4 gap events '
    f'{CL["w19_p4"][0]}, post-2018 {CL["w19_p4"][1]} {CL["w19_p4"][4]}, mean {CL["w19_p4"][2]:+.2f}% / ex post-2018 '
    f'{CL["w19_p4"][3]:+.2f}%')

# ============================================================================ 5. verdicts and output
g = lambda key, t, u='all', p='MAIN': SENS[key][(t, u)][p]  # noqa: E731
fmt = lambda x: f'{x[0]:+.2f} (t {x[1]:.2f})'  # noqa: E731
def sym_note(t):
    return (f'the symmetric |ln(1+r)|>=ln1.5 re-mask (as in cache/panel_sym.pkl) would give {fmt(g("sym", t))} but only '
            'because it also masks real crash days (DOID 22-23 Dec 2005 after 430->195 on volume, and 3 Mar 2006): '
            f"without DOID's extra masks {fmt(g('sym_noDOID', t))}; the targeted reverting-leg fix gives "
            f'{fmt(g("targeted", t))}')


def common(t):
    b = BASE[(t, 'all')]
    return (f'reproduced exactly (own code; all periods, t and n match to 1e-15); NW lags 40: t {g("NW lags 40 (2h)", t)[1]:.2f}; '
            f'event-weighted {b["evw"]:+.2f}')


ISS = {
    'W1.1': [common('W1.1'),
             f'window reading: strict (any non-tradable day voids the level) {fmt(g("window strict (all days tradable)", "W1.1"))} '
             f'fails t>=3, but the carried-close reading {fmt(g("window carry (non-tradable = carried close)", "W1.1"))} and the '
             f'research-code reading (Volume-0 bars included) {fmt(g("window rawbar (V=0 bars incl., research code)", "W1.1"))} '
             'agree with the analyst; PLAN (lnH NaN on non-tradable days, prices of Volume-0 bars ignored) supports the '
             "analyst's NaN-skipping reading, so the strict figure is a sensitivity, not the PLAN statistic",
             f'the t>=3 pass is knife-edge: without one ticker t falls to {ROB["W1.1"]["loo_min"][0]:.2f} '
             f'(w/o {ROB["W1.1"]["loo_min"][1]}) or {ROB["W1.1"]["loo_2nd"][0]:.2f} (w/o {ROB["W1.1"]["loo_2nd"][1]}); clipping '
             f'20-day abnormal returns at +-50% gives {fmt(ROB["W1.1"]["clip50"])}; ULTJ Apr-May 2001 single-event days '
             f'(+100..127%) contribute {ultj01:.2f} pp of the 0.79%',
             f'pre2018 P4 is {fmt(ROB["W1.1"]["pre_P4"])}: post-2018 listings supply {P4_POST:.2f} pp of the P4 mean '
             f'{BASE[("W1.1", "all")]["P4"][0]:.2f}% (' + ', '.join(f'{k} {v:.2f}' for k, v in P4_TOP.items()) + ')',
             'usability statement correct (0.79 < B 0.90); interpretation and high survivorship label supported'],
    'W1.2': [common('W1.2'),
             f'fails t>=3 by 0.02 under the PLAN reading; carried-close reading '
             f'{fmt(g("window carry (non-tradable = carried close)", "W1.2"))} would pass, strict '
             f'{fmt(g("window strict (all days tradable)", "W1.2"))}; classification is knife-edge',
             sym_note('W1.2'), 'interpretation supported (full-lookback events +0.69%, t 1.94)'],
    'W1.3': [common('W1.3'), f'strict reading {fmt(g("window strict (all days tradable)", "W1.3"))}', sym_note('W1.3'),
             'interpretation (effect carried by illiquid/suspended lookbacks) supported'],
    'W1.4': [common('W1.4'), f'strict reading {fmt(g("window strict (all days tradable)", "W1.4"))}', sym_note('W1.4'),
             f'leave-one-ticker-out min t {ROB["W1.4"]["loo_min"][0]:.2f} (w/o {ROB["W1.4"]["loo_min"][1]})'],
    'W1.5': [common('W1.5'),
             f'the entry-day +{D0["exact"][0]:.2f}% (t {D0["exact"][1]:.1f}) is an artefact of exact fills at the off-grid stop '
             f'price: with fills at the next price-grid tick (tick from the stock\'s own prices; equals the IDX table in '
             f'{TICK_VALID[0]:.0%} of P4 triggers, smaller in {TICK_VALID[1]:.0%}) it is {D0["tick"][0]:+.2f}% (t {D0["tick"][1]:.1f}), '
             f'and placebo buy stops at Open+0.5/1/2% on every stock-day earn '
             + '/'.join(f'{v[0]:+.2f}' for v in PLACEBO.values()) + '% with exact fills ('
             + '/'.join(f'{v[1]:+.2f}' for v in PLACEBO.values())
             + '% with tick fills); so "close above the fill" is not a breakout property and its P1->P4 shrinkage tracks '
             'the shrinking relative tick size',
             f'with next-tick fills W1.5 = {fmt(W15T["MAIN"])} (subperiods ' + '/'.join(f'{W15T[p][0]:+.2f}' for p in SUBS)
             + f', pre2018 {fmt(SENS["tick"][("W1.5", "pre2018")]["MAIN"])}, event-weighted {W15T["evw"]:+.2f}%); lenient '
             f'bound (finest common price grid, exact stop where no grid is found) {fmt(g("tick_gcd", "W1.5"))} (pre2018 '
             f'{fmt(SENS["tick_gcd"][("W1.5", "pre2018")]["MAIN"])}); '
             'criteria 1-3 still pass, but the effect sits at the cost-B threshold (0.90%) instead of 0.26 pp above it '
             '(in P4 the official IDX tick table implies a larger fill bias than the estimate), so standalone usability '
             'under B is not established (it clears A 0.40%); the analyst\'s "marginal" is right, but W1.5 should not be '
             'classified ROBUST_USABLE on the exact-stop 1.16%; the classify.py rationale "entry-type choice (buy stop instead '
             f'of Close confirmation)" also rests on the artefact: W1.5 minus W1.1 is {ENTRY_GAP["exact"]:+.2f} pp with exact '
             f'fills but {ENTRY_GAP["tick"]:+.2f} to {ENTRY_GAP["tick_gcd"]:+.2f} pp with grid fills (< 0.25 pp filter '
             'threshold; descriptive, different windows and event sets)',
             f'right-tail dependence: clip +-30% gives {fmt(ROB["W1.5"]["clip30"])}; pre2018 P4 {fmt(ROB["W1.5"]["pre_P4"])}',
             'removing locked limit-up / open-at-high trigger days raises the effect '
             f'({fmt(g("drop_locked", "W1.5"))}), so untradable fills do not inflate it'],
    'W1.6': [common('W1.6'), f'paired same-day difference {fmt(ROB["W1.6"]["paired"])}; tradable-days-only volume mean '
             f'{fmt(g("W1.10 per failing breakout, W1.8 cumsum, W1.6 trad", "W1.6"))}; interpretation supported'],
    'W1.7': [common('W1.7'),
             f'robust: leave-one-ticker-out min t {ROB["W1.7"]["loo_min"][0]:.2f}, clip +-30% {fmt(ROB["W1.7"]["clip30"])}, '
             f'strict window {fmt(g("window strict (all days tradable)", "W1.7"))}, paired same-day '
             f'{fmt(ROB["W1.7"]["paired"])}, tick/mask variants unchanged; P1/P2 individually weak and fresh-only '
             f'{fmt(CL["w17_fresh"])} as the analyst reports; pre2018 P4 {fmt(ROB["W1.7"]["pre_P4"])}'],
    'W1.8': [common('W1.8'), f'cumsum idx level {fmt(g("W1.10 per failing breakout, W1.8 cumsum, W1.6 trad", "W1.8"))}; '
             'P3 sign (-0.02) is essentially zero, signs_P1_P4=3 is fragile but the test fails t anyway'],
    'W1.9': [common('W1.9'), f'with tick fills (rest group pays the grid) {fmt(g("tick", "W1.9"))}; paired '
             f'{fmt(ROB["W1.9"]["paired"])}; P4 composition claim verified ({CL["w19_p4"][1]} of {CL["w19_p4"][0]} gap events '
             f'post-2018, ex post-2018 {CL["w19_p4"][3]:+.2f}%)'],
    'W1.10': [common('W1.10'), f'counting each failing breakout (duplicates weighted) {fmt(g("W1.10 per failing breakout, W1.8 cumsum, W1.6 trad", "W1.10"))}; '
              f'non-failed comparison {fmt(CL["nofail"])}; interpretation and exit-rule reading supported'],
}
VERDICT = {'W1.1': 'confirmed_with_caveat', 'W1.2': 'confirmed', 'W1.3': 'confirmed', 'W1.4': 'confirmed',
           'W1.5': 'confirmed_with_caveat', 'W1.6': 'confirmed', 'W1.7': 'confirmed', 'W1.8': 'confirmed',
           'W1.9': 'confirmed', 'W1.10': 'confirmed'}
rows = []
for t in TESTS:
    b, bp = BASE[(t, 'all')], BASE[(t, 'pre2018')]['MAIN']
    sgn = np.sign(b['MAIN'][0])
    rows.append(dict(
        test_id=t, analyst_eff=AN.loc[t, 'eff_MAIN'], analyst_t=AN.loc[t, 't_MAIN'], recomputed_eff=b['MAIN'][0],
        recomputed_t=b['MAIN'][1], recomputed_eff_pre2018=bp[0], verdict=VERDICT[t], issues='; '.join(ISS[t]),
        unit=AN.loc[t, 'unit'], recomputed_n_MAIN=b['MAIN'][2], recomputed_t_pre2018=bp[1],
        recomputed_signs_P1_P4=int(sum(np.sign(b[p][0]) == sgn for p in SUBS)),
        **{f'recomputed_eff_{p}': b[p][0] for p in SUBS + ['P0']},
        recomputed_eff_event_weighted=b['evw'],
        eff_strict_window=g('window strict (all days tradable)', t)[0], t_strict_window=g('window strict (all days tradable)', t)[1],
        t_lags40=g('NW lags 40 (2h)', t)[1], eff_symmetric_mask=g('sym', t)[0], t_symmetric_mask=g('sym', t)[1],
        eff_targeted_mask=g('targeted', t)[0], t_targeted_mask=g('targeted', t)[1],
        eff_tick_fill=g('tick', t)[0], t_tick_fill=g('tick', t)[1],
        loo_min_t=ROB[t]['loo_min'][0], loo_min_ticker=ROB[t]['loo_min'][1],
        eff_clip50=ROB[t]['clip50'][0], t_clip50=ROB[t]['clip50'][1]))
out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)
say(f'wrote {OUT} ({len(out)} rows) in {time.time() - T0:.0f} s')
with pd.option_context('display.width', 250, 'display.max_colwidth', 40):
    say(out[['test_id', 'analyst_eff', 'analyst_t', 'recomputed_eff', 'recomputed_t', 'recomputed_eff_pre2018',
             'verdict']].round(4).to_string(index=False))
