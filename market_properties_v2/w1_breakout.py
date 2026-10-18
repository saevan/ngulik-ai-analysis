"""Market properties v2, family W1 (breakout anatomy), implemented exactly as pre-registered in PLAN.md section W1.
Writes results/W1_tests.csv (primary tests W1.1-W1.10, one mpstats.row each), results/W1_context.csv (descriptive
context: event counts per period, day-averaged and event-weighted means, raw means, other horizons; not classified)
and results/W1_exploratory.csv (X-W1-* extras; not classified).
Run: python market_properties_v2/w1_breakout.py   (well under a minute)

Definition choices (most literal causal reading where PLAN.md is silent):
1. Day indices t-n..t-1 are rows of the market calendar (the panel convention, as for fo[h]). max(lnH[t-n..t-1]) is
   taken over the tradable days of that window (lnH is NaN on Volume-0 bars, which carry no traded high) and needs the
   stock to be listed at t-n (a full n-day lookback exists). The breakout day t must be tradable. The strict
   alternative (every day of the window tradable) is reported in the context file as a sensitivity.
2. Abnormal fo[h] = mpstats.event_series: minus the same-day EW mean of all universe stocks with a valid fo[h].
   Every series is indexed by the day the signal is known (Close of t; for W1.10 the failure day f).
3. W1.5/W1.9: the buy stop for day t is placed after the Close of t-1 at L+ln(1.005), L = max(lnH[t-20..t-1]) (same
   level as W1.1). Day t must be tradable with a valid clean Open (bad-print days have no clean Open and are
   skipped). Entry lnE = max(lnO[t], L+ln1.005); return lnP[t+19]-lnE (exit Close of t+19, window t..t+19);
   benchmark = same-day EW mean over all universe stocks of lnP[t+19]-lnO[t]; the series is indexed by entry day t.
4. W1.6: mean(V[t-20..t-1]) over the 20 market days; Volume-0 days count as 0 volume, missing rows are skipped.
5. W1.7: ER20 denominator = sum of the 20 clean daily level changes |lnP[s]-lnP[s-1]|, s = t-19..t.
6. W1.8: idx level = cumulative product of (1 + EW daily simple return of the universe), recomputed for pre2018;
   SMA200 over days t-199..t (known at the Close of t); above = level > SMA200, below = level <= SMA200.
7. W1.10: for each W1.1 event (level L of day t) the failure day f is the first of t+1..t+3 with lnP[f] < L; the
   event is the pair (stock, f) with abnormal fo[20] at row f (entry Open f+1, exit Close f+20). Overlapping
   breakouts that fail on the same day f give one event (the forward window is identical).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel import load, universe, SUBPERIODS, MAIN, P0
from mpstats import Mean, Diff, row, event_series, nw, PERIODS, COST_RT

OUT = HERE / 'results'
FAM = 'W1'
UNIVS = ('all', 'pre2018')
H, LAGS, PCT = 20, 20, 100.
UNIT = '% per 20 days'
UNIT_D = 'pp per 20-day trade (A minus B)'
K05, K2 = np.log(1.005), np.log(1.02)

P = load()
CAL = P['C'].index
lnP, lnO, lnH, T, V = P['lnP'], P['lnO'], P['lnH'], P['T'], P['V']


def cols(u):
    return universe(P, u)


def frame(values, like):
    return pd.DataFrame(values, index=like.index, columns=like.columns)


# ------------------------------------------------------------------ signals (stock level, same for both universes)
def hhv_level(n, strict=False):
    """max(lnH[t-n..t-1]) on market days, NaN-skipping; the stock must be listed at t-n. strict: all days tradable."""
    lv = lnH.rolling(n, min_periods=n if strict else 1).max().shift(1)
    return lv.where(lnP.shift(n).notna())


NS = (20, 55, 120, 250)
LEVEL = {n: hhv_level(n) for n in NS}
BO = {n: (lnP > LEVEL[n]) & T for n in NS}                  # Close breakout on day t
BO20, L20 = BO[20], LEVEL[20]

VMEAN = V.rolling(20, min_periods=1).mean().shift(1).where(lnP.shift(20).notna())
VOL_HI, VOL_LO = BO20 & (V >= 2 * VMEAN), BO20 & (V < 2 * VMEAN)

DL = lnP.diff()
ER20 = (lnP - lnP.shift(20)).abs() / DL.abs().rolling(20, min_periods=20).sum()
ER_HI, ER_LO = BO20 & (ER20 >= .3), BO20 & (ER20 < .3)


def idx_regime(u):
    """(above, below) Series: EW idx level of universe u vs its SMA200 (both False while SMA200 is undefined)."""
    ir = np.expm1(P['r_cc'][cols(u)]).mean(axis=1)
    lvl = (1 + ir.fillna(0.)).cumprod()
    sma = lvl.rolling(200, min_periods=200).mean()
    return lvl > sma, lvl <= sma


def by_day(mask, day_flag):
    return mask & frame(np.repeat(day_flag.reindex(mask.index).fillna(False).values[:, None], mask.shape[1], 1), mask)


def failed_masks():
    """W1.10. Returns (failed event mask at row f, non-failed mask at row t+3, per-k first-failure masks at row t)."""
    prior = frame(np.zeros(BO20.shape, bool), BO20)
    fmask = prior.copy()
    first = {}
    for k in (1, 2, 3):
        below = lnP.shift(-k) < L20                          # row t: lnP[t+k] < L[t]
        first[k] = BO20 & below & ~prior
        prior = prior | below
        fmask = fmask | first[k].shift(k, fill_value=False)  # move the event to its failure day f = t+k
    nofail = BO20 & ~prior & lnP.shift(-3).notna()
    return fmask, nofail.shift(3, fill_value=False), first


FAIL, NOFAIL, FIRST_K = failed_masks()


def stop_frames(u):
    """W1.5/W1.9 per-event frames on universe u: trigger mask, gap/rest masks, abnormal and raw returns."""
    c = cols(u)
    L, lo, hi, lp = L20[c], lnO[c], lnH[c], lnP[c]
    lev = L + K05
    trig = (hi >= lev) & lo.notna()
    lnE = np.maximum(lo, lev)
    ex = lp.shift(-19)
    raw = ex - lnE
    bench = (ex - lo).mean(axis=1)                           # same-day EW mean over all universe stocks
    M = trig & raw.notna()
    abn = raw.sub(bench, axis=0)
    return dict(M=M, gap=M & (lo >= L + K2), rest=M & (lo < L + K2), abn=abn.where(M), raw=raw.where(M),
                bench=bench, lnE=lnE, trig_any=trig, badopen=(hi >= lev) & lo.isna() & T[c])


STOP = {u: stop_frames(u) for u in UNIVS}
REG = {u: idx_regime(u) for u in UNIVS}


# ------------------------------------------------------------------ event helpers
def evmat(mask, u, h=H, adjust=True):
    """Per-event matrix (NaN where no event) mirroring mpstats.event_series."""
    c = cols(u)
    F = P['fo'][h][c]
    if adjust:
        F = F.sub(F.mean(axis=1), axis=0)
    M = mask.reindex(index=F.index, columns=c).fillna(False).astype(bool) & F.notna()
    return F.where(M)


def ser(mask, u, h=H, adjust=True):
    return event_series(P, mask, h, u, adjust=adjust)[0]


GROUPS = {   # test_id -> (mask builder per universe for group A, group B or None)
    'W1.1': (lambda u: BO[20], None), 'W1.2': (lambda u: BO[55], None), 'W1.3': (lambda u: BO[120], None),
    'W1.4': (lambda u: BO[250], None),
    'W1.6': (lambda u: VOL_HI, lambda u: VOL_LO), 'W1.7': (lambda u: ER_HI, lambda u: ER_LO),
    'W1.8': (lambda u: by_day(BO20, REG[u][0]), lambda u: by_day(BO20, REG[u][1])),
    'W1.10': (lambda u: FAIL, None),
}


def stat(test_id, u):
    if test_id == 'W1.5':
        return Mean(STOP[u]['abn'].mean(axis=1), LAGS)
    if test_id == 'W1.9':
        s = STOP[u]
        return Diff(s['abn'].where(s['gap']).mean(axis=1), s['abn'].where(s['rest']).mean(axis=1), LAGS)
    a, b = GROUPS[test_id]
    if b is None:
        return Mean(ser(a(u), u), LAGS)
    return Diff(ser(a(u), u), ser(b(u), u), LAGS)


DESC = {
    'W1.1': 'HHV20 Close breakout lnP[t] > max(lnH[t-20..t-1]); abnormal fo[20] (entry Open t+1, exit Close t+20)',
    'W1.2': 'HHV55 Close breakout lnP[t] > max(lnH[t-55..t-1]); abnormal fo[20]',
    'W1.3': 'HHV120 Close breakout lnP[t] > max(lnH[t-120..t-1]); abnormal fo[20]',
    'W1.4': 'HHV250 Close breakout lnP[t] > max(lnH[t-250..t-1]); abnormal fo[20]',
    'W1.5': 'Intraday buy stop at max(lnH[t-20..t-1])+ln1.005, entry max(Open, stop), exit Close t+19; minus same-day '
            'EW mean of lnP[t+19]-lnO[t]',
    'W1.6': 'Among W1.1 events: V[t] >= 2x mean(V[t-20..t-1]) minus < 2x; abnormal fo[20]',
    'W1.7': 'Among W1.1 events: ER20 >= 0.3 minus < 0.3; abnormal fo[20]',
    'W1.8': 'Among W1.1 events: EW idx level above its SMA200 minus below; abnormal fo[20]',
    'W1.9': 'Among W1.5 triggers: Open >= level+ln1.02 (gap >= 2% over the level) minus the rest; W1.5 returns',
    'W1.10': 'Failed W1.1 breakout: first day f in t+1..t+3 with lnP[f] < L; abnormal fo[20] from Open f+1',
}
TESTS = list(DESC)


def primary_rows():
    rows = []
    for tid in TESTS:
        unit = UNIT_D if tid in ('W1.6', 'W1.7', 'W1.8', 'W1.9') else UNIT
        rows.append(row(tid, FAM, DESC[tid], unit, stat(tid, 'all'), stat(tid, 'pre2018'), scale=PCT))
    return pd.DataFrame(rows)


if __name__ == '__main__':
    d = primary_rows()
    pd.set_option('display.width', 250)
    print(d[['test_id', 'eff_MAIN', 't_MAIN', 'n_MAIN', 'eff_P1', 'eff_P2', 'eff_P3', 'eff_P4', 'eff_P0', 'eff_pre2018',
             't_pre2018', 'signs_P1_P4', 'pass_t3', 'pass_stable', 'pass_pre2018']].round(3).to_string(index=False))
