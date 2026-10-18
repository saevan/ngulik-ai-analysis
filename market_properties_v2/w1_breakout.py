"""Market properties v2, family W1 (breakout anatomy), implemented exactly as pre-registered in PLAN.md section W1.
Writes results/W1_tests.csv (primary tests W1.1-W1.10, one mpstats.row each), results/W1_context.csv (descriptive
context: event counts per period, day-averaged and event-weighted means, raw means, other horizons; not classified)
and results/W1_exploratory.csv (X-W1-* extras; not classified).
Run: python market_properties_v2/w1_breakout.py   (well under a minute, includes brute-force self-checks)

Definition choices (most literal causal reading where PLAN.md is silent):
1. Day indices t-n..t-1 are rows of the market calendar (the panel convention, as for fo[h]). max(lnH[t-n..t-1]) is
   taken over the tradable days of that window (lnH is NaN on Volume-0 bars, which carry no traded high) and needs the
   stock to be listed at t-n (a full n-day lookback exists). The breakout day t must be tradable. This follows the
   panel rule that prices of Volume-0 bars are ignored; it was fixed on event-count grounds before any return was
   computed (the strict reading, every day of the window tradable, drops 41% of HHV250 events for a single
   suspension day). The strict reading and its complement are reported in the context file; the HHV results are
   sensitive to it (see notes).
2. Abnormal fo[h] = mpstats.event_series: minus the same-day EW mean of all universe stocks with a valid fo[h].
   Every series is indexed by the day the signal is known (Close of t; W1.10: the failure day f; W1.5/W1.9: entry day).
3. W1.5/W1.9: the buy stop for day t is placed after the Close of t-1 at L+ln(1.005), L = max(lnH[t-20..t-1]) (same
   level as W1.1). Day t must be tradable with a valid clean Open (bad-print days have no clean Open and are
   skipped). Entry lnE = max(lnO[t], L+ln1.005); return lnP[t+19]-lnE (exit Close of t+19, window t..t+19);
   benchmark = same-day EW mean over all universe stocks of lnP[t+19]-lnO[t]. Fill exactly at the stop (or the Open
   when it gaps through) is assumed; daily bars cannot show slippage. Context splits the effect into the entry day
   (fill -> Close t, lags 5) and days t+1..t+19 (lags 20).
4. W1.6: mean(V[t-20..t-1]) over the 20 market days; Volume-0 days count as 0 volume, missing rows are skipped.
5. W1.7: ER20 denominator = sum of the 20 clean daily level changes |lnP[s]-lnP[s-1]|, s = t-19..t.
6. W1.8: idx level = cumulative product of (1 + EW daily simple return of the universe), recomputed for pre2018;
   SMA200 over days t-199..t (known at the Close of t); above = level > SMA200, below = level <= SMA200.
7. W1.10: for each W1.1 event (level L of day t) the failure day f is the first of t+1..t+3 with lnP[f] < L; the
   event is the pair (stock, f) with abnormal fo[20] at row f (entry Open f+1, exit Close f+20). Overlapping
   breakouts of one stock that fail on the same day f give one event (their forward window is identical).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel import load, universe, SUBPERIODS, MAIN
from mpstats import Mean, Diff, row, event_series, nw, PERIODS, COST_RT

OUT = HERE / 'results'
FAM = 'W1'
UNIVS = ('all', 'pre2018')
H, LAGS, PCT = 20, 20, 100.
UNIT = '% per 20 days'
UNIT_D = 'pp per 20-day trade (A minus B)'
K05, K2 = np.log(1.005), np.log(1.02)
CB, CA = COST_RT['B'] * PCT, COST_RT['A'] * PCT      # 0.90 / 0.40 % round trip
FILTER_PP = .25

P = load()
CAL = P['C'].index
lnP, lnO, lnH, T, V = P['lnP'], P['lnO'], P['lnH'], P['T'], P['V']
POST = set(P['post2018'])


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
BO_STRICT = {n: (lnP > hhv_level(n, strict=True)) & T for n in NS}
FULLWIN = {n: hhv_level(n, strict=True).notna() for n in NS}   # every day of t-n..t-1 tradable
BO20, L20 = BO[20], LEVEL[20]
LIQ = np.log(P['value'].rolling(60, min_periods=40).mean()).rank(axis=1, pct=True)   # liquidity pct-rank (descr.)

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
    """W1.10. Returns (failed mask at row f, non-failed mask at row t+3, first-failure masks at row t per k)."""
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
    # decomposition (context): entry day t (fill -> Close t) and days t+1..t+19 (Close t -> Close t+19)
    valid = lo.notna() & ex.notna()
    d0 = (lp - lnE).where(M).sub((lp - lo).where(valid).mean(axis=1), axis=0)
    d1 = (ex - lp).where(M).sub((ex - lp).where(valid).mean(axis=1), axis=0)
    return dict(M=M, gap=M & (lo >= L + K2), rest=M & (lo < L + K2), abn=abn.where(M), raw=raw.where(M),
                day0=d0, rest19=d1, badopen=(hi >= lev) & lo.isna() & T[c])


STOP = {u: stop_frames(u) for u in UNIVS}
REG = {u: idx_regime(u) for u in UNIVS}


# ------------------------------------------------------------------ event helpers
def evmat(mask, u, h=H, adjust=True, base='fo'):
    """Per-event matrix (NaN where no event) mirroring mpstats.event_series (checked in self_checks)."""
    c = cols(u)
    F = P[base][h][c]
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
GNAMES = {'W1.6': ('A: V >= 2x mean20', 'B: V < 2x mean20'), 'W1.7': ('A: ER20 >= 0.3', 'B: ER20 < 0.3'),
          'W1.8': ('A: idx > SMA200', 'B: idx <= SMA200'), 'W1.9': ('A: Open >= L+ln1.02', 'B: rest')}


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
    'W1.5': 'Intraday buy stop at max(lnH[t-20..t-1])+ln1.005, entry max(Open t, stop), exit Close t+19; minus '
            'same-day EW mean of lnP[t+19]-lnO[t]',
    'W1.6': 'Among W1.1 events: V[t] >= 2x mean(V[t-20..t-1]) minus < 2x; abnormal fo[20]',
    'W1.7': 'Among W1.1 events: ER20 >= 0.3 minus < 0.3; abnormal fo[20]',
    'W1.8': 'Among W1.1 events: EW idx level above its SMA200 minus below; abnormal fo[20]',
    'W1.9': 'Among W1.5 triggers: Open >= L+ln1.02 (gap >= 2% over the level) minus the rest; W1.5 returns',
    'W1.10': 'Failed W1.1 breakout: first day f in t+1..t+3 with lnP[f] < L; abnormal fo[20] from Open f+1',
}
TESTS = list(DESC)
EXPLOIT = {'W1.1': 'standalone', 'W1.2': 'standalone', 'W1.3': 'standalone', 'W1.4': 'standalone',
           'W1.5': 'standalone', 'W1.6': 'filter', 'W1.7': 'filter', 'W1.8': 'filter', 'W1.9': 'filter',
           'W1.10': 'filter'}
SURV = {'W1.1': 'high', 'W1.2': 'high', 'W1.3': 'high', 'W1.4': 'high', 'W1.5': 'medium',
        'W1.6': 'medium', 'W1.7': 'low', 'W1.8': 'low', 'W1.9': 'medium', 'W1.10': 'high'}
SURVIVOR = ('universe = today\'s Kompas100, so stocks whose breakouts failed and that were later delisted or dropped '
            'are missing; abnormal returns remove the average survivor drift but not this selection; pre2018 removes '
            'only recent listings')


def liq_rank(mask):
    """Mean cross-sectional liquidity percentile rank (60-day mean traded value) of the MAIN events of a mask."""
    return float(np.nanmean(LIQ.where(mask).loc[MAIN[0]:MAIN[1]].values))


def fmt(st, unit='%'):
    m, t, _ = st.at(*MAIN)
    return f'{m * PCT:+.2f}{unit} (t {t:.2f})'


def fail_from(bo_filter):
    """W1.10 failed-event mask (row f) restricted to breakouts (row t) that satisfy bo_filter."""
    out = frame(np.zeros(BO20.shape, bool), BO20)
    for k in (1, 2, 3):
        out = out | (FIRST_K[k] & bo_filter).shift(k, fill_value=False)
    return out


def surv_why(tid):
    if tid in ('W1.1', 'W1.2', 'W1.3', 'W1.4'):
        n = NS[int(tid[-1]) - 1]
        full, part = BO[n] & FULLWIN[n], BO[n] & ~FULLWIN[n]
        nf, npart = n_events(evmat(full, 'all'), *MAIN), n_events(evmat(part, 'all'), *MAIN)
        return (f'high because the effect leans on breakouts whose {n}-day lookback contains >= 1 non-tradable day '
                f'({npart} of {nf + npart} MAIN events, abnormal {fmt(Mean(ser(part, "all"), LAGS))}), i.e. illiquid '
                f'or suspended episodes of stocks that later became index members; fully tradable lookbacks give '
                f'{fmt(Mean(ser(full, "all"), LAGS))}; breakouts favour recent winners; {SURVIVOR}')
    if tid == 'W1.5':
        st = Mean(STOP['all']['abn'].where(FULLWIN[20]).mean(axis=1), LAGS)
        return (f'medium: triggers with a fully tradable 20-day lookback still give {fmt(st)}, so the result does not '
                f'hinge on illiquid episodes; breakouts favour recent winners; {SURVIVOR}')
    if tid == 'W1.6':
        return (f'medium: volume-spike breakouts tilt to less liquid names (liquidity pct-rank {liq_rank(VOL_HI):.2f} vs '
                f'{liq_rank(VOL_LO):.2f}); fully tradable lookbacks: '
                f'{fmt(Diff(ser(VOL_HI & FULLWIN[20], "all"), ser(VOL_LO & FULLWIN[20], "all"), LAGS), " pp")}; {SURVIVOR}')
    if tid == 'W1.7':
        return (f'low: difference of two breakout groups from the same survivor set; the low-ER group is not tilted to '
                f'illiquid names (liquidity pct-rank {liq_rank(ER_LO):.2f} vs {liq_rank(ER_HI):.2f} for ER >= 0.3); '
                f'fully tradable lookbacks: '
                f'{fmt(Diff(ser(ER_HI & FULLWIN[20], "all"), ser(ER_LO & FULLWIN[20], "all"), LAGS), " pp")}')
    if tid == 'W1.8':
        return 'low: difference of two breakout groups from the same survivor set, split by a market regime'
    if tid == 'W1.9':
        return 'medium: gap-through triggers concentrate in speculative runs; the P4 sign depends on post-2018 listings'
    return (f'high: a positive mean after a failed breakout favours stocks that recovered and delisted failures are '
            f'missing; failures of breakouts with a fully tradable lookback give '
            f'{fmt(Mean(ser(fail_from(FULLWIN[20]), "all"), LAGS))}')


def cost_note(tid, eff):
    if EXPLOIT[tid] == 'standalone':
        txt = (f'standalone long entry: MAIN abnormal {eff:+.2f}% per 20-day trade vs round trip B {CB:.2f}% / '
               f'A {CA:.2f}% -> {"above" if eff > CB else "below"} B, {"above" if eff > CA else "below"} A')
        if tid == 'W1.5':
            txt += ('; assumes the fill exactly at the stop (or Open on a gap), part of the effect is earned on the '
                    'entry day (see context day0), so stop slippage beyond scenario B 0.25%/side reduces it 1:1')
        return txt
    if tid == 'W1.10':
        return (f'exit rule inside a breakout system (sell at Open f+1 after a failure): abnormal return after the '
                f'failure {eff:+.2f}% per 20 days; selling only helps if this is negative; |effect| vs filter '
                f'threshold {FILTER_PP:.2f} pp; as a standalone buy-the-failure trade it needs > {CB:.2f}% (B)')
    return (f'filter inside a breakout entry (no extra round trip): |A-B| = {abs(eff):.2f} pp per trade vs '
            f'{FILTER_PP:.2f} pp threshold -> {"meets" if abs(eff) >= FILTER_PP else "below"}')


def n_events(mask_or_frame, a, b):
    m = mask_or_frame.loc[a:b]
    return int(np.isfinite(m.values).sum()) if m.dtypes.iloc[0] != bool else int(m.values.sum())


def ev_counts(tid, u):
    """MAIN event counts (valid forward window) per group for the notes."""
    if tid in ('W1.5', 'W1.9'):
        s = STOP[u]
        if tid == 'W1.5':
            return [n_events(s['abn'], *MAIN)]
        return [n_events(s['abn'].where(s['gap']), *MAIN), n_events(s['abn'].where(s['rest']), *MAIN)]
    a, b = GROUPS[tid]
    out = [n_events(evmat(a(u), u), *MAIN)]
    if b is not None:
        out.append(n_events(evmat(b(u), u), *MAIN))
    return out


def event_means(tid, u):
    """Event-weighted (pooled) MAIN means of the per-event abnormal returns, per group."""
    def pooled(m):
        v = m.loc[MAIN[0]:MAIN[1]].values
        return float(np.nanmean(v))
    if tid in ('W1.5', 'W1.9'):
        s = STOP[u]
        return [pooled(s['abn'])] if tid == 'W1.5' else [pooled(s['abn'].where(s['gap'])), pooled(s['abn'].where(s['rest']))]
    a, b = GROUPS[tid]
    return [pooled(evmat(a(u), u))] + ([pooled(evmat(b(u), u))] if b is not None else [])


def notes(tid, r):
    nev = ev_counts(tid, 'all')
    base = f'MAIN events (valid window): {"/".join(str(x) for x in nev)}' + (' (A/B)' if len(nev) == 2 else '')
    ew = [x * PCT for x in event_means(tid, 'all')]
    base += ('; event-weighted MAIN mean ' + (f'{ew[0]:+.2f}%' if len(ew) == 1 else
             f'A {ew[0]:+.2f}% / B {ew[1]:+.2f}% (diff {ew[0] - ew[1]:+.2f} pp)') + ' (row effect is day-averaged)')
    extra = {
        'W1.1': 'HHV over tradable days of the 20 market-day window, full lookback required (strict all-days-'
                'tradable version in context)',
        'W1.5': (f'split of the effect: entry day (fill to Close t) '
                 f'{fmt(Mean(STOP["all"]["day0"].mean(axis=1), 5))}, days t+1..t+19 '
                 f'{fmt(Mean(STOP["all"]["rest19"].mean(axis=1), LAGS))}; fill at the stop assumed'),
        'W1.6': 'volume mean includes Volume-0 days as 0',
        'W1.7': 'ER20 from clean daily level changes; A-group alone is the research Breakout20+ER>=0.3 entry '
                '(context and X-W1-ER bins)',
        'W1.8': 'idx = EW proxy of the universe (recomputed for pre2018), SMA200 incl. day t',
        'W1.9': '',
        'W1.10': 'failure day f is the first Close below the breakout level within 3 days; duplicates (stock, f) '
                 'from overlapping breakouts counted once; non-failed comparison (from Open after t+3) in context',
    }[tid] if tid in ('W1.1', 'W1.5', 'W1.6', 'W1.7', 'W1.8', 'W1.9', 'W1.10') else 'same window convention as W1.1'
    if tid == 'W1.9':
        s = STOP['all']
        a = s['abn'].where(s['gap']).loc[SUBPERIODS['P4'][0]:SUBPERIODS['P4'][1]].stack().dropna()  # pandas 3 keeps NaN
        post = a[[t in POST for t in a.index.get_level_values(1)]]
        extra = (f'P4 gap group: {len(post)} of {len(a)} events from post-2018 listings; excluding them the P4 gap-'
                 f'group event mean is {a.drop(post.index).mean() * PCT:+.2f}% vs {a.mean() * PCT:+.2f}% with them')
    return f'{base}; {extra}; survivorship {surv_why(tid)}'.replace('; ;', ';')


def primary_rows():
    rows = []
    for tid in TESTS:
        unit = UNIT_D if tid in GNAMES else UNIT
        r = row(tid, FAM, DESC[tid], unit, stat(tid, 'all'), stat(tid, 'pre2018'), scale=PCT,
                surv_risk=SURV[tid], exploit=EXPLOIT[tid])
        r['cost_note'] = cost_note(tid, r['eff_MAIN'])
        r['notes'] = notes(tid, r)
        rows.append(r)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ context (descriptive, not classified)
CTX = []


def ctx_add(tid, u, group, measure, h, mat, lags, note=''):
    """One context row per period: event count, day-averaged mean (NW t) and event-weighted mean, in %."""
    daily = mat.mean(axis=1)
    for k, (a, b) in PERIODS.items():
        v = mat.loc[a:b].values
        v = v[np.isfinite(v)]
        m, se, nd = nw(daily.loc[a:b], lags)
        CTX.append(dict(test_id=tid, universe=u, group=group, measure=measure, horizon_days=h, period=k,
                        n_events=int(v.size), n_days=int(nd), mean_daily_pct=m * PCT,
                        t_nw=(m / se if np.isfinite(se) and se > 0 else np.nan),
                        mean_event_pct=(v.mean() * PCT if v.size else np.nan), value=np.nan, note=note))


def ctx_value(tid, u, group, measure, period, value, n=np.nan, note=''):
    CTX.append(dict(test_id=tid, universe=u, group=group, measure=measure, horizon_days=np.nan, period=period,
                    n_events=n, n_days=np.nan, mean_daily_pct=np.nan, t_nw=np.nan, mean_event_pct=np.nan,
                    value=value, note=note))


def context():
    for u in UNIVS:
        for n, tid in zip(NS, ('W1.1', 'W1.2', 'W1.3', 'W1.4')):
            for h in (20, 5, 60):
                for adj, meas in ((True, 'abnormal'), (False, 'raw')):
                    ctx_add(tid, u, 'events', meas, h, evmat(BO[n], u, h, adj), max(h, 5),
                            'primary statistic' if (h == 20 and adj) else '')
            ctx_add(tid, u, 'events, strict window (all days tradable)', 'abnormal', 20, evmat(BO_STRICT[n], u), 20,
                    'sensitivity: pandas-default reading, any non-tradable day in the window voids the level')
            ctx_add(tid, u, 'events, >= 1 non-tradable day in window', 'abnormal', 20,
                    evmat(BO[n] & ~FULLWIN[n], u), 20, 'complement of the strict window: illiquid/suspended episodes')
        s = STOP[u]
        ctx_add('W1.5', u, 'triggers', 'abnormal', 20, s['abn'], 20, 'primary statistic')
        ctx_add('W1.5', u, 'triggers', 'raw', 20, s['raw'], 20, 'lnP[t+19]-lnE')
        ctx_add('W1.5', u, 'triggers', 'abnormal_day0', 1, s['day0'], 5,
                'entry day: lnP[t]-lnE minus EW mean lnP[t]-lnO[t]; in % so it adds up with the 20-day effect')
        ctx_add('W1.5', u, 'triggers', 'abnormal_t1_t19', 19, s['rest19'], 20,
                'days t+1..t+19: lnP[t+19]-lnP[t] minus EW mean of the same')
        ctx_value('W1.5', u, 'triggers', 'skipped_bad_open_days', 'ALL', int(s['badopen'].values.sum()),
                  note='trigger on a bad-print day (no clean Open): skipped')
        fw = FULLWIN[20][cols(u)]
        ctx_add('W1.5', u, 'triggers, fully tradable 20-day window', 'abnormal', 20, s['abn'].where(fw), 20)
        ctx_add('W1.5', u, 'triggers, fully tradable 20-day window', 'abnormal_day0', 1, s['day0'].where(fw), 5)
        ctx_add('W1.5', u, 'triggers, fully tradable 20-day window', 'abnormal_t1_t19', 19, s['rest19'].where(fw), 20)
        ctx_add('W1.5', u, 'triggers, >= 1 non-tradable day in window', 'abnormal', 20, s['abn'].where(~fw), 20)
        for tid in ('W1.6', 'W1.7', 'W1.8'):
            a, b = GROUPS[tid]
            for g, mk in zip(GNAMES[tid], (a, b)):
                for adj, meas in ((True, 'abnormal'), (False, 'raw')):
                    ctx_add(tid, u, g, meas, 20, evmat(mk(u), u, 20, adj), 20)
        for g, key in zip(GNAMES['W1.9'], ('gap', 'rest')):
            ctx_add('W1.9', u, g, 'abnormal', 20, s['abn'].where(s[key]), 20)
            ctx_add('W1.9', u, g, 'raw', 20, s['raw'].where(s[key]), 20)
        a = s['abn'].where(s['gap'])
        ex_post = a[[c for c in a.columns if c not in POST]]
        ctx_add('W1.9', u, 'A: Open >= L+ln1.02, excluding post-2018 listings', 'abnormal', 20, ex_post, 20,
                'descriptive check of the P4 sign')
        ctx_add('W1.10', u, 'failed (event at row f)', 'abnormal', 20, evmat(FAIL, u), 20, 'primary statistic')
        ctx_add('W1.10', u, 'failed (event at row f)', 'raw', 20, evmat(FAIL, u, 20, False), 20)
        ctx_add('W1.10', u, 'not failed within 3 days (event at row t+3)', 'abnormal', 20, evmat(NOFAIL, u), 20,
                'comparison: abnormal fo[20] from the Open after t+3')
        ctx_add('W1.10', u, 'not failed within 3 days (event at row t+3)', 'raw', 20,
                evmat(NOFAIL, u, 20, False), 20)
        for k in (1, 2, 3):
            ctx_add('W1.10', u, f'failed on day t+{k}', 'abnormal', 20,
                    evmat(FIRST_K[k].shift(k, fill_value=False), u), 20)
        c = cols(u)
        for k, (a0, b0) in PERIODS.items():
            bo = BO20[c].loc[a0:b0]
            nf = sum(int(FIRST_K[j][c].loc[a0:b0].values.sum()) for j in (1, 2, 3))
            nb = int(bo.values.sum())
            ctx_value('W1.10', u, 'W1.1 events', 'share_failed_within_3d_pct', k, 100. * nf / nb if nb else np.nan, nb,
                      'share of W1.1 events (by breakout day) whose Close falls below L within t+1..t+3')
            ctx_value('W1.10', u, 'W1.1 events', 'failing_breakouts_vs_unique_stock_f_pairs', k,
                      int(FAIL[c].loc[a0:b0].values.sum()), nf,
                      'value = unique (stock, f) events by failure day; n_events = failing breakouts by breakout day')
            up = REG[u][0].loc[a0:b0]
            ctx_value('W1.8', u, 'market days', 'share_days_idx_above_SMA200_pct', k, 100. * up.mean(), len(up))
    return pd.DataFrame(CTX)


# ------------------------------------------------------------------ exploratory (X-W1-*, not classified)
def exploratory():
    """Motivated by the primary results: W1.7 (ER filter) passes -> dose response over ER20 bins; W1.1 events cluster
    on consecutive days while a one-position-per-stock system acts on the first -> fresh-breakout version; the HHV
    effects lean on lookbacks with non-tradable days (context) -> W1.1/W1.5/W1.7 on fully tradable lookbacks only."""
    rows = []
    fw = FULLWIN[20]
    specs = [
        ('X-W1.1-fullwin', 'W1.1 events whose 20-day lookback is fully tradable; abnormal fo[20] (Mean)', UNIT,
         {u: Mean(ser(BO20 & fw, u), LAGS) for u in UNIVS}, 'high', 'standalone', 'W1.1',
         f'MAIN events {n_events(evmat(BO20 & fw, "all"), *MAIN)}; equals the strict-window reading of W1.1'),
        ('X-W1.5-fullwin', 'W1.5 triggers whose 20-day lookback is fully tradable; W1.5 abnormal return (Mean)', UNIT,
         {u: Mean(STOP[u]['abn'].where(fw[cols(u)]).mean(axis=1), LAGS) for u in UNIVS}, 'medium', 'standalone',
         'W1.5', f'MAIN events {n_events(STOP["all"]["abn"].where(fw), *MAIN)}'),
        ('X-W1.7-fullwin', 'W1.7 on W1.1 events with a fully tradable 20-day lookback: ER20 >= 0.3 minus < 0.3', UNIT_D,
         {u: Diff(ser(ER_HI & fw, u), ser(ER_LO & fw, u), LAGS) for u in UNIVS}, 'low', 'filter', 'W1.7',
         f'MAIN events A/B {n_events(evmat(ER_HI & fw, "all"), *MAIN)}/{n_events(evmat(ER_LO & fw, "all"), *MAIN)}'),
    ]
    for tid, desc, unit, st, risk, ex, like, nt in specs:
        r = row(tid, 'W1-X', desc, unit, st['all'], st['pre2018'], scale=PCT, surv_risk=risk, exploit=ex, notes=nt)
        r['cost_note'] = cost_note(like, r['eff_MAIN'])
        rows.append(r)
    bins = [('X-W1-ER<0.2', 0., .2), ('X-W1-ER0.2-0.3', .2, .3), ('X-W1-ER0.3-0.5', .3, .5), ('X-W1-ER>=0.5', .5, 1.01)]
    for tid, lo_, hi_ in bins:
        m = BO20 & (ER20 >= lo_) & (ER20 < hi_)
        st = {u: Mean(ser(m, u), LAGS) for u in UNIVS}
        r = row(tid, 'W1-X', f'W1.1 events with {lo_:.1f} <= ER20 < {min(hi_, 1):.1f}; abnormal fo[20] (Mean)', UNIT,
                st['all'], st['pre2018'], scale=PCT, surv_risk='medium', exploit='standalone',
                notes='dose response behind W1.7; ER 0.2 is the W2 entry threshold, 0.3 the research module default')
        r['cost_note'] = cost_note('W1.1', r['eff_MAIN'])
        r['notes'] += f'; MAIN events {n_events(evmat(m, "all"), *MAIN)}'
        rows.append(r)
    prev = BO20.shift(1, fill_value=False).astype(int).rolling(20, min_periods=1).sum() > 0
    fresh, repeat = BO20 & ~prev, BO20 & prev
    st = {u: Mean(ser(fresh, u), LAGS) for u in UNIVS}
    r = row('X-W1-fresh', 'W1-X', 'First W1.1 event of a stock with no W1.1 event in t-20..t-1; abnormal fo[20]',
            UNIT, st['all'], st['pre2018'], scale=PCT, surv_risk='medium', exploit='standalone')
    r['cost_note'] = cost_note('W1.1', r['eff_MAIN'])
    rep = Mean(ser(repeat, 'all'), LAGS).at(*MAIN)
    r['notes'] = (f'MAIN events fresh {n_events(evmat(fresh, "all"), *MAIN)}, repeat '
                  f'{n_events(evmat(repeat, "all"), *MAIN)}; repeat-breakout mean {rep[0] * PCT:+.2f}% (t {rep[1]:.2f})')
    rows.append(r)
    st = {u: Diff(ser(fresh & ER_HI, u), ser(fresh & ER_LO, u), LAGS) for u in UNIVS}
    r = row('X-W1-fresh-ER', 'W1-X', 'Fresh W1.1 events: ER20 >= 0.3 minus < 0.3; abnormal fo[20] (W1.7 on first '
            'signals only)', UNIT_D, st['all'], st['pre2018'], scale=PCT, surv_risk='low', exploit='filter')
    r['cost_note'] = cost_note('W1.7', r['eff_MAIN'])
    r['notes'] = (f'MAIN events A/B {n_events(evmat(fresh & ER_HI, "all"), *MAIN)}/'
                  f'{n_events(evmat(fresh & ER_LO, "all"), *MAIN)}; checks that W1.7 is not an artefact of '
                  f'overlapping repeat events')
    rows.append(r)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ self-checks (brute force on samples)
def self_checks():
    lp, lh, lo, tr = lnP.values, lnH.values, lnO.values, T.values
    N, K = lp.shape
    rng = np.random.default_rng(1)
    for n in NS:                                             # HHV level and breakout flag
        Lv, bo = LEVEL[n].values, BO[n].values
        for i, j in zip(rng.integers(n + 1, N, 3000), rng.integers(0, K, 3000)):
            w = lh[i - n:i, j]
            ref = np.nanmax(w) if (np.isfinite(lp[i - n, j]) and np.isfinite(w).any()) else np.nan
            assert (np.isnan(ref) and np.isnan(Lv[i, j])) or abs(ref - Lv[i, j]) < 1e-12, ('level', n, i, j)
            assert bool(tr[i, j] and np.isfinite(ref) and lp[i, j] > ref) == bo[i, j], ('breakout', n, i, j)
    tick = list(P['C'].columns)
    for u in UNIVS:                                          # W1.5 returns and benchmark
        s, cidx = STOP[u], [tick.index(x) for x in cols(u)]
        ev = np.argwhere(s['M'].values)
        for i, jj in ev[rng.choice(len(ev), 300, replace=False)]:
            j = cidx[jj]
            lev = np.nanmax(lh[i - 20:i, j]) + K05
            assert lh[i, j] >= lev and np.isfinite(lo[i, j])
            ref = lp[i + 19, j] - max(lo[i, j], lev) - np.nanmean(lp[i + 19, cidx] - lo[i, cidx])
            assert abs(ref - s['abn'].values[i, jj]) < 1e-12
            assert abs(s['day0'].values[i, jj] + s['rest19'].values[i, jj] - s['abn'].values[i, jj]) < 1e-12
        s1, s2 = evmat(BO20, u).mean(axis=1), event_series(P, BO20, 20, u)[0]
        assert np.allclose(s1.fillna(-9).values, s2.fillna(-9).values)
    L, bo = L20.values, BO20.values                          # W1.10 failure days, full loop
    fail, nofail = set(), set()
    for i, j in np.argwhere(bo):
        f = next((i + k for k in (1, 2, 3) if i + k < N and lp[i + k, j] < L[i, j]), None)
        if f is not None:
            fail.add((f, j))
        elif i + 3 < N and np.isfinite(lp[i + 3, j]):
            nofail.add((i + 3, j))
    assert fail == set(map(tuple, np.argwhere(FAIL.values))) and nofail == set(map(tuple, np.argwhere(NOFAIL.values)))
    assert (fail_from(frame(np.ones(BO20.shape, bool), BO20)) == FAIL).values.all()
    for n in NS:                                             # strict reading == breakout with a fully tradable window
        assert (BO_STRICT[n] == (BO[n] & FULLWIN[n])).values.all()
    ir = np.expm1(P['r_cc']).mean(axis=1)                    # idx reconstruction equals panel idx_ret
    assert np.allclose(ir.fillna(0).values, P['idx_ret'].fillna(0).values, atol=1e-15)
    # placebo through the W1.5 benchmark: random entries at the Open, window t..t+19 -> abnormal mean ~ 0
    c = cols('all')
    lo_, ex = lnO[c], lnP[c].shift(-19)
    bench = (ex - lo_).mean(axis=1)
    ts = [Mean((ex - lo_).sub(bench, axis=0).where(frame(rng.random(lo_.shape) < .02, lo_)).mean(axis=1), 20).at(*MAIN)[1]
          for _ in range(10)]
    assert max(abs(x) for x in ts) < 3.5, ts
    print('self-checks passed (HHV levels, W1.5 returns/benchmark/decomposition, W1.10 failure days, idx, placebo '
          'max|t| %.2f)' % max(abs(x) for x in ts))


if __name__ == '__main__':
    self_checks()
    OUT.mkdir(exist_ok=True)
    d = primary_rows()
    d.to_csv(OUT / 'W1_tests.csv', index=False)
    cx = context()
    cx.to_csv(OUT / 'W1_context.csv', index=False)
    x = exploratory()
    x.to_csv(OUT / 'W1_exploratory.csv', index=False)
    pd.set_option('display.width', 250)
    show = ['test_id', 'eff_MAIN', 't_MAIN', 'n_MAIN', 'eff_P1', 'eff_P2', 'eff_P3', 'eff_P4', 'eff_P0', 'eff_pre2018',
            't_pre2018', 'signs_P1_P4', 'pass_t3', 'pass_stable', 'pass_pre2018']
    print(d[show].round(3).to_string(index=False))
    print(x[show].round(3).to_string(index=False))
    print('wrote', OUT / 'W1_tests.csv', len(d), 'rows;', OUT / 'W1_context.csv', len(cx), 'rows;',
          OUT / 'W1_exploratory.csv', len(x), 'rows')
