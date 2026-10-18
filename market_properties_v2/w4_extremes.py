"""Market properties v2, family W4 (extreme events and liquidity shocks), implemented as pre-registered in PLAN.md W4.
Writes results/W4_tests.csv (primary tests W4.1-W4.6, one mpstats.row each), results/W4_context.csv (descriptive
context: event counts per period, day-averaged and event-weighted means, raw means, other horizons, execution and
survivorship splits; not classified) and results/W4_exploratory.csv (X-W4-* extras; not classified).
Run: python market_properties_v2/w4_extremes.py   (about a minute, includes brute-force self-checks)

Definition choices (most literal causal reading where PLAN.md is silent; fixed before any return was computed):
1. Close = High: raw C[t] >= H[t]*(1-1e-9); Close = Low: raw C[t] <= L[t]*(1+1e-9) (raw adjusted prices: the ratio is
   unaffected by the adjustment factor). Day t must be tradable (implied by a valid r_cc).
2. Thresholds on the clean panel return: r_cc[t] >= ln 1.15 (W4.1), r_cc[t] <= ln 0.85 (W4.2). After Volume-0 days the
   panel measures r_cc from the last tradable Close, so a few events are multi-day moves (counted in context). Bad
   prints (|simple return| >= 50%) have r_cc = NaN and cannot be events.
3. W4.3/W4.4: mean(V[t-20..t-1]) over the 20 market days before t; Volume-0 days count as 0, missing rows (164 cells in
   the panel) are skipped, the stock must be listed at t-20 (same implementation as W1.6). Event: V[t] >= 3*mean and
   r_cc[t] > 0 (W4.3) or < 0 (W4.4). A zero mean (no trade in t-20..t-1) satisfies V >= 3*0 literally; these resumption
   days are kept and reported in context together with the effect without them.
4. W4.5/W4.6: lnP[t]-lnP[t-20] on the clean levels (20 market days, stock listed at t-20). No tradability requirement
   on day t (lnP carries the last traded Close, known at t); the entry still needs a tradable t+1. The variant that
   requires day t tradable is in context.
5. Every day on which the condition holds is an event; one stock can contribute overlapping events (day-averaging and
   NW lags = h absorb the overlap). Entry = next Open (t+1 tradable with a clean Open, as in fo[h]); events whose next
   day is not tradable (e.g. a suspension after a limit move) drop out and are counted in context.
6. Abnormal = mpstats.event_series: event fo[h] minus the same-day EW mean fo[h] of all universe stocks with a valid
   window (recomputed on the pre2018 columns for the pre2018 statistic). Mean over the events of signal day t, NW lags
   h = 5 (W4.1/W4.2) or 20 (W4.3-W4.6) as PLAN.md states. Unit % per h days (x100).
7. exploit_type (rule fixed before results): each test is a long event trade at the next Open. A positive MAIN effect is
   judged as a standalone entry (needs > 0.90% round trip B, 0.40% A reported); a negative MAIN effect can only be an
   avoid/exit filter in a long-only system (|effect| >= 0.25 pp, with the abnormal effect vs the average stock as the
   difference, an approximation of the difference inside a specific signal).
8. survivorship_risk (rule fixed before results): W4.6 high (crashed stocks that later delisted are missing). W4.2/W4.4
   (down events): high if the MAIN effect is positive (favours losers that survived), else medium. W4.1/W4.3/W4.5 (up
   events): medium if the effect is negative (selection would shrink a reversal, not create it); if positive, medium
   when events of stocks above the bottom tercile of pre-event liquidity (mean traded value t-60..t-1, rank within the
   universe) keep the sign and >= 2/3 of the overall MAIN effect, else high (the effect then leans on small, illiquid
   names where today's-constituent selection is strongest). Low is never assigned: every event set comes from today's
   Kompas100 members.
Context returns are all in % per window (also the 1-day ones, so that they add up with the multi-day effects).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel import load, universe, SUBPERIODS, MAIN                       # noqa: E402
from mpstats import Mean, Diff, row, event_series, nw, PERIODS, COST_RT  # noqa: E402

OUT = HERE / 'results'
FAM = 'W4'
UNIVS = ('all', 'pre2018')
PCT = 100.
EPS = 1e-9
UP15, DN15 = np.log(1.15), np.log(0.85)
RUN, CRASH = np.log(1.5), np.log(1 / 1.5)
CB, CA = COST_RT['B'] * PCT, COST_RT['A'] * PCT      # 0.90 / 0.40 % round trip
FILTER_PP = .25
HORIZONS = (1, 5, 10, 20, 60)

P = load()
CAL = P['C'].index
O, H, L, C, V, T = (P[k] for k in ('O', 'H', 'L', 'C', 'V', 'T'))
lnP, r_cc, r_on = P['lnP'], P['r_cc'], P['r_on']
POST = set(P['post2018'])


def cols(u):
    return universe(P, u)


def frame(values, like):
    return pd.DataFrame(values, index=like.index, columns=like.columns)


def nextday(df):
    """Row t = value of day t+1 (bool frames: False after the last day)."""
    return df.shift(-1, fill_value=False) if df.dtypes.iloc[0] == bool else df.shift(-1)


# ------------------------------------------------------------------ event masks (stock level, both universes)
AT_HIGH = T & (C >= H * (1 - EPS))
AT_LOW = T & (C <= L * (1 + EPS))
E41 = (r_cc >= UP15) & AT_HIGH
E42 = (r_cc <= DN15) & AT_LOW
VMEAN = V.rolling(20, min_periods=1).mean().shift(1).where(lnP.shift(20).notna())   # mean V[t-20..t-1]
SPIKE = V >= 3 * VMEAN
E43 = SPIKE & (r_cc > 0)
E44 = SPIKE & (r_cc < 0)
R20 = lnP - lnP.shift(20)
E45 = R20 >= RUN
E46 = R20 <= CRASH
RESUME = VMEAN == 0                                    # no trade at all in t-20..t-1
VRATIO = V / VMEAN.where(VMEAN > 0)

# next-day execution flags (row t describes day t+1)
T1 = nextday(T)
O1, H1, L1, C1, R1 = nextday(O), nextday(H), nextday(L), nextday(C), nextday(r_cc)
LOCK_UP = T1 & (O1 >= H1 * (1 - EPS)) & (C1 >= H1 * (1 - EPS)) & (R1 >= UP15)   # locked auto-reject-up queue proxy
OPEN_HIGH = T1 & (O1 >= H1 * (1 - EPS))                                         # looser: opens at its High
LOCK_DN = T1 & (O1 <= L1 * (1 + EPS)) & (C1 <= L1 * (1 + EPS)) & (R1 <= DN15)
PREV_NT = ~T.shift(1, fill_value=True)                 # previous market day not tradable (multi-day r_cc)

# pre-event liquidity: mean traded value over t-60..t-1 (>= 40 tradable days), ranked within the universe
LIQV = P['value'].rolling(60, min_periods=40).mean().shift(1)


def liq_groups(u):
    rk = LIQV[cols(u)].rank(axis=1, pct=True)
    return {'bottom tercile': rk <= 1 / 3, 'middle tercile': (rk > 1 / 3) & (rk <= 2 / 3), 'top tercile': rk > 2 / 3,
            'above bottom tercile': rk > 1 / 3, 'unranked (< 40 days history)': rk.isna()}


def fresh(mask, gap=20):
    """Events of a stock with no event (condition day) of the same mask in t-gap..t-1."""
    prev = mask.shift(1, fill_value=False).astype(int).rolling(gap, min_periods=1).sum() > 0
    return mask & ~prev


TESTS = {
    'W4.1': dict(mask=E41, h=5, kind='up', desc='Strong close at high: r_cc[t] >= ln 1.15 and Close = High (raw C >= '
                 'H*(1-1e-9)); abnormal fo[5] (entry Open t+1, exit Close t+5)'),
    'W4.2': dict(mask=E42, h=5, kind='down', desc='Weak close at low: r_cc[t] <= ln 0.85 and Close = Low (raw C <= '
                 'L*(1+1e-9)); abnormal fo[5] (entry Open t+1, exit Close t+5)'),
    'W4.3': dict(mask=E43, h=20, kind='up', desc='Volume spike up: V[t] >= 3 x mean(V[t-20..t-1]) and r_cc[t] > 0; '
                 'abnormal fo[20] (entry Open t+1, exit Close t+20)'),
    'W4.4': dict(mask=E44, h=20, kind='down', desc='Volume spike down: V[t] >= 3 x mean(V[t-20..t-1]) and r_cc[t] < 0; '
                 'abnormal fo[20]'),
    'W4.5': dict(mask=E45, h=20, kind='up', desc='Run-up: lnP[t]-lnP[t-20] >= ln 1.5 (clean levels); abnormal fo[20]'),
    'W4.6': dict(mask=E46, h=20, kind='down', desc='Crash: lnP[t]-lnP[t-20] <= ln(1/1.5) (clean levels); abnormal '
                 'fo[20]'),
}


# ------------------------------------------------------------------ event helpers
def evmat(mask, u, h, adjust=True, base='fo'):
    """Per-event matrix (NaN where no event) mirroring mpstats.event_series (checked in self_checks)."""
    c = cols(u)
    F = P[base][h][c]
    if adjust:
        F = F.sub(F.mean(axis=1), axis=0)
    M = mask.reindex(index=F.index, columns=c).fillna(False).astype(bool) & F.notna()
    return F.where(M)


def gapmat(mask, u, h):
    """Abnormal overnight move into t+1 (r_on[t+1] minus its same-day EW mean) for events with a valid fo[h]."""
    c = cols(u)
    G = nextday(r_on[c])
    G = G.sub(G.mean(axis=1), axis=0)
    return G.where(evmat(mask, u, h).notna())


def ser(mask, u, h, adjust=True):
    return event_series(P, mask, h, u, adjust=adjust)[0]


def stat(tid, u, mask=None):
    s = TESTS[tid]
    m = s['mask'] if mask is None else mask
    return Mean(ser(m[cols(u)], u, s['h']), s['h'])


def nev(mat, a=MAIN[0], b=MAIN[1]):
    return int(np.isfinite(mat.loc[a:b].values).sum())


def ncond(mask, u, a=MAIN[0], b=MAIN[1]):
    return int(mask[cols(u)].loc[a:b].values.sum())


def pooled(mat, a=MAIN[0], b=MAIN[1]):
    v = mat.loc[a:b].values
    v = v[np.isfinite(v)]
    return float(v.mean()) if v.size else np.nan


def fmt(st, unit='%'):
    m, t, n = st.at(*MAIN)
    return f'{m * PCT:+.2f}{unit} (t {t:.2f}, {n} days)'


# ------------------------------------------------------------------ primary rows
def exploit_of(eff):
    return 'standalone' if eff > 0 else 'filter'


def surv_of(tid, eff, liq_eff):
    s = TESTS[tid]
    if tid == 'W4.6':
        return 'high'
    if s['kind'] == 'down':
        return 'high' if eff > 0 else 'medium'
    if eff <= 0:
        return 'medium'
    ok = np.isfinite(liq_eff) and np.sign(liq_eff) == np.sign(eff) and abs(liq_eff) >= 2 / 3 * abs(eff)
    return 'medium' if ok else 'high'


def cost_note(tid, eff, h):
    if exploit_of(eff) == 'standalone':
        txt = (f'standalone long entry at the next Open: MAIN abnormal {eff:+.2f}% per {h}-day trade vs round trip B '
               f'{CB:.2f}% / A {CA:.2f}% -> {"above" if eff > CB else "below"} B, {"above" if eff > CA else "below"} A'
               f'; as a filter/ranking input inside an existing signal |effect| {abs(eff):.2f} pp vs {FILTER_PP:.2f} '
               f'pp -> {"meets" if abs(eff) >= FILTER_PP else "below"}')
    else:
        txt = (f'long-only: a negative abnormal return cannot be traded standalone; as an avoid/exit filter |effect| '
               f'{abs(eff):.2f} pp per trade vs {FILTER_PP:.2f} pp threshold -> '
               f'{"meets" if abs(eff) >= FILTER_PP else "below"} (difference vs the average stock, not vs the trades '
               f'of a specific signal)')
    if tid == 'W4.1':
        txt += ('; next-Open fills after a limit-up close are often not achievable (locked queue at t+1, see notes and '
                'context), so the realised entry would be later and different')
    if tid == 'W4.2':
        txt += '; buying at a locked limit-down Open is feasible (sellers queue at the limit)'
    return txt


def survivorship_text(tid, risk, liq_eff, eff):
    if tid == 'W4.6':
        why = ('high by construction: crashed stocks that later delisted or fell out of the index are missing, so a '
               'rebound after a crash is measured only on stocks that recovered enough to be in today\'s Kompas100')
    elif TESTS[tid]['kind'] == 'down':
        why = (f'{risk}: down events favour losers; {"a positive (rebound) effect is the direction that missing "
               "delisted losers inflate" if eff > 0 else "a negative effect is not created by the missing delisted "
               "losers (they would make it more negative), but its size is uncertain"}')
    else:
        why = (f'{risk}: events of stocks above the bottom pre-event liquidity tercile give {liq_eff:+.2f}% vs '
               f'{eff:+.2f}% overall (rule: medium if same sign and >= 2/3 of the overall effect); extreme up-moves '
               f'concentrate in small speculative names whose survivors became today\'s members')
    return why + '; universe = today\'s Kompas100, pre2018 removes only recent listings'


def test_notes(tid, r, liq_eff):
    s = TESTS[tid]
    m, h = s['mask'], s['h']
    mat = evmat(m, 'all', h)
    n_ok, n_c = nev(mat), ncond(m, 'all')
    n_nt = ncond(m & ~T1, 'all')
    out = [f'MAIN events with a valid window {n_ok} (condition days {n_c}; next day not tradable {n_nt}, others lost '
           f'to the sample end or a bad print at t+1); event-weighted MAIN mean {pooled(mat) * PCT:+.2f}% (row effect '
           f'is day-averaged)']
    if not np.isfinite(r['eff_P4']):
        out.append(f'P4 has {r["n_P4"]} event days (< 20) so mpstats.nw returns NaN for P4 and signs_P1_P4 counts it '
                   f'as not same-sign')
    if tid == 'W4.1':
        lk = evmat(m & LOCK_UP, 'all', h)
        oh = evmat(m & OPEN_HIGH, 'all', h)
        out.append(f'next day locked limit-up proxy (Open = High = Close at t+1 with r_cc >= ln1.15): {nev(lk)} of '
                   f'{n_ok} MAIN events cannot be bought at the next Open in practice; excluding them '
                   f'{fmt(stat(tid, "all", m & ~LOCK_UP))}; looser proxy (t+1 opens at its High) {nev(oh)} events, '
                   f'excluding them {fmt(stat(tid, "all", m & ~OPEN_HIGH))}')
        out.append(f'events after a non-tradable day (multi-day r_cc) {nev(evmat(m & PREV_NT, "all", h))}')
    if tid == 'W4.2':
        out.append(f'next day locked limit-down proxy {nev(evmat(m & LOCK_DN, "all", h))} MAIN events (buyable, kept)'
                   f'; few events after 2015 (2016-2025: {ncond(m, "all", "2016-01-01", "2025-12-31")} condition '
                   f'days; per-year counts in context)')
    if tid in ('W4.3', 'W4.4'):
        rs = evmat(m & RESUME, 'all', h)
        out.append(f'resumption days (zero volume in t-20..t-1) {nev(rs)} MAIN events; excluding them '
                   f'{fmt(stat(tid, "all", m & ~RESUME))}')
    if tid in ('W4.5', 'W4.6'):
        out.append(f'events on a non-tradable day t (stale level, entry at the resumption Open) '
                   f'{nev(evmat(m & ~T, "all", h))}; day t tradable only {fmt(stat(tid, "all", m & T))}; first event '
                   f'per stock in 20 days {fmt(stat(tid, "all", fresh(m)))}')
    out.append(f'survivorship {survivorship_text(tid, r["survivorship_risk"], liq_eff, r["eff_MAIN"])}')
    return '; '.join(out)


def primary_rows():
    rows = []
    for tid, s in TESTS.items():
        unit = f'% per {s["h"]} days'
        r = row(tid, FAM, s['desc'], unit, stat(tid, 'all'), stat(tid, 'pre2018'), scale=PCT)
        liq = liq_groups('all')['above bottom tercile']
        liq_eff = stat(tid, 'all', s['mask'][cols('all')] & liq).at(*MAIN)[0] * PCT
        r['exploit_type'] = exploit_of(r['eff_MAIN'])
        r['survivorship_risk'] = surv_of(tid, r['eff_MAIN'], liq_eff)
        r['cost_note'] = cost_note(tid, r['eff_MAIN'], s['h'])
        r['notes'] = test_notes(tid, r, liq_eff)
        rows.append(r)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ context (descriptive, not classified)
CTX = []


def ctx_add(tid, u, group, measure, h, mat, lags, note=''):
    """One row per period: event count, day-averaged mean (NW t) and event-weighted mean, in % per window."""
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


def bins_up(r):
    return [('0 < r_cc < ln1.02', (r > 0) & (r < np.log(1.02))), ('ln1.02 <= r_cc < ln1.05', (r >= np.log(1.02)) &
            (r < np.log(1.05))), ('ln1.05 <= r_cc < ln1.10', (r >= np.log(1.05)) & (r < np.log(1.10))),
            ('r_cc >= ln1.10', r >= np.log(1.10))]


def bins_dn(r):
    return [('ln0.98 < r_cc < 0', (r < 0) & (r > np.log(.98))), ('ln0.95 < r_cc <= ln0.98', (r <= np.log(.98)) &
            (r > np.log(.95))), ('ln0.90 < r_cc <= ln0.95', (r <= np.log(.95)) & (r > np.log(.90))),
            ('r_cc <= ln0.90', r <= np.log(.90))]


def context():
    for u in UNIVS:
        c = cols(u)
        lg = liq_groups(u)
        for tid, s in TESTS.items():
            m, h0 = s['mask'][c], s['h']
            for h in HORIZONS:
                for adj, meas in ((True, 'abnormal fo'), (False, 'raw fo')):
                    ctx_add(tid, u, 'events', meas, h, evmat(m, u, h, adj), max(h, 5),
                            'primary statistic' if (h == h0 and adj) else '')
            ctx_add(tid, u, 'events', 'abnormal fc (Close t -> Close t+h)', h0, evmat(m, u, h0, True, 'fc'), h0,
                    'includes the overnight move into t+1 that a next-Open entry cannot capture; fc needs day t '
                    'tradable')
            ctx_add(tid, u, 'events (valid fo window)', 'abnormal overnight r_on[t+1]', 1, gapmat(m, u, h0), 5,
                    'Close t -> Open t+1 minus the same-day EW mean; the part of fc that fo misses')
            for g, lm in lg.items():
                ctx_add(tid, u, f'events, pre-event liquidity {g}', 'abnormal fo', h0, evmat(m & lm, u, h0), h0,
                        'liquidity = mean traded value t-60..t-1 ranked within the universe (survivorship check)')
            for k, (a, b) in PERIODS.items():
                mm = m.loc[a:b]
                n_c = int(mm.values.sum())
                ctx_value(tid, u, 'events', 'n_condition_days', k, n_c, note='condition true, regardless of window')
                ctx_value(tid, u, 'events', 'n_valid_window', k, nev(evmat(m, u, h0), a, b))
                ctx_value(tid, u, 'events', 'n_lost_next_day_not_tradable', k, int((mm & T1[c].loc[a:b].eq(False))
                                                                                    .values.sum()),
                          note='next market day Volume 0 or missing (e.g. suspension): no next-Open entry')
                if u == 'all':
                    npost = int(mm[[x for x in c if x in POST]].values.sum())
                    ctx_value(tid, u, 'events', 'share_condition_days_post2018_tickers_pct', k,
                              100. * npost / n_c if n_c else np.nan, n_c)
            # test-specific context
            if tid == 'W4.1':
                ctx_add(tid, u, 'events excluding next-day locked proxy', 'abnormal fo', 5, evmat(m & ~LOCK_UP[c], u, 5),
                        5, 'locked proxy: t+1 Open = High and Close = High with r_cc[t+1] >= ln1.15 (not buyable at the '
                        'Open in practice)')
                ctx_add(tid, u, 'events with next-day locked proxy', 'abnormal fo', 5, evmat(m & LOCK_UP[c], u, 5), 5,
                        'return as if filled at the locked Open (not achievable)')
                ctx_add(tid, u, 'events excluding next day opening at its High', 'abnormal fo', 5,
                        evmat(m & ~OPEN_HIGH[c], u, 5), 5, 'looser proxy for an unfillable next Open')
                ctx_add(tid, u, 'events after a non-tradable day', 'abnormal fo', 5, evmat(m & PREV_NT[c], u, 5), 5,
                        'r_cc spans more than one market day')
                for k, (a, b) in PERIODS.items():
                    ctx_value(tid, u, 'events (valid window)', 'n_next_day_locked_proxy', k,
                              nev(evmat(m & LOCK_UP[c], u, 5), a, b), nev(evmat(m, u, 5), a, b),
                              'value = events with the locked proxy at t+1; n_events = all valid events')
                    ctx_value(tid, u, 'events (valid window)', 'n_next_day_opens_at_high', k,
                              nev(evmat(m & OPEN_HIGH[c], u, 5), a, b), nev(evmat(m, u, 5), a, b))
            if tid == 'W4.2':
                ctx_add(tid, u, 'events excluding next-day locked-down proxy', 'abnormal fo', 5,
                        evmat(m & ~LOCK_DN[c], u, 5), 5, 'locked-down proxy: t+1 Open = Low = Close, r_cc[t+1] <= '
                        'ln0.85; buying there is feasible, so the primary keeps them')
                ctx_add(tid, u, 'events after a non-tradable day', 'abnormal fo', 5, evmat(m & PREV_NT[c], u, 5), 5,
                        'r_cc spans more than one market day')
            if tid in ('W4.1', 'W4.2'):
                yr = m.groupby(m.index.year).sum().sum(axis=1)
                for y, n in yr.items():
                    ctx_value(tid, u, 'events', 'n_condition_days_by_year', str(y), int(n))
            if tid in ('W4.3', 'W4.4'):
                ctx_add(tid, u, 'events excluding resumption days', 'abnormal fo', 20, evmat(m & ~RESUME[c], u, 20), 20,
                        'resumption = zero volume in t-20..t-1 (V >= 3*0 holds literally)')
                ctx_add(tid, u, 'resumption days only', 'abnormal fo', 20, evmat(m & RESUME[c], u, 20), 20)
                vr = VRATIO[c]
                for g, b in (('3x <= V/mean < 5x', (vr >= 3) & (vr < 5)), ('5x <= V/mean < 10x', (vr >= 5) & (vr < 10)),
                             ('V/mean >= 10x', vr >= 10)):
                    ctx_add(tid, u, f'events, spike size {g}', 'abnormal fo', 20, evmat(m & b, u, 20), 20)
                for g, b in (bins_up(r_cc[c]) if tid == 'W4.3' else bins_dn(r_cc[c])):
                    ctx_add(tid, u, f'events, same-day move {g}', 'abnormal fo', 20, evmat(m & b, u, 20), 20)
                ctx_add(tid, u, 'first event per stock in 20 days', 'abnormal fo', 20, evmat(fresh(m), u, 20), 20,
                        'no event of the same stock in t-20..t-1')
            if tid in ('W4.5', 'W4.6'):
                ctx_add(tid, u, 'events on a tradable day t only', 'abnormal fo', 20, evmat(m & T[c], u, 20), 20)
                ctx_add(tid, u, 'events on a non-tradable day t', 'abnormal fo', 20, evmat(m & ~T[c], u, 20), 20,
                        'stale level; entry at the Open of the resumption day')
                ctx_add(tid, u, 'first event per stock in 20 days', 'abnormal fo', 20, evmat(fresh(m), u, 20), 20,
                        'no event of the same stock in t-20..t-1')
    return pd.DataFrame(CTX)


# ------------------------------------------------------------------ exploratory (X-W4-*, not classified)
def exploratory():
    """Motivated by the primary results: only W4.3 (volume spike on an up day) reaches |t| >= 3. Three checks of that
    result: (a) survivorship: events of stocks above the bottom pre-event liquidity tercile; (b) overlap: the first
    event per stock in 20 days, which is what a one-position-per-stock system would act on; (c) information content of
    the volume itself: among up days (r_cc > 0) with a defined 20-day volume mean, V >= 3x minus V < 3x."""
    rows = []
    up = (r_cc > 0) & VMEAN.notna()
    specs = [
        ('X-W4.3-liquid', 'W4.3 events of stocks above the bottom tercile of pre-event liquidity (mean traded value '
         't-60..t-1, rank within the universe); abnormal fo[20] (Mean)', '% per 20 days',
         {u: stat('W4.3', u, E43[cols(u)] & liq_groups(u)['above bottom tercile']) for u in UNIVS}, 'medium',
         'standalone'),
        ('X-W4.3-fresh', 'First W4.3 event of a stock with no W4.3 event in t-20..t-1; abnormal fo[20] (Mean)',
         '% per 20 days', {u: stat('W4.3', u, fresh(E43)) for u in UNIVS}, 'high', 'standalone'),
        ('X-W4.3-volinfo', 'Among up days r_cc[t] > 0: V[t] >= 3x mean(V[t-20..t-1]) minus V[t] < 3x; abnormal fo[20] '
         '(Diff)', 'pp per 20-day trade (A minus B)',
         {u: Diff(ser(E43[cols(u)], u, 20), ser((up & ~SPIKE)[cols(u)], u, 20), 20) for u in UNIVS}, 'medium',
         'filter'),
    ]
    for tid, desc, unit, st, risk, ex in specs:
        r = row(tid, 'W4-X', desc, unit, st['all'], st['pre2018'], scale=PCT, surv_risk=risk, exploit=ex)
        eff = r['eff_MAIN']
        if ex == 'standalone':
            r['cost_note'] = cost_note('W4.3', eff, 20)
        else:
            r['cost_note'] = (f'filter/ranking inside an existing long signal (no extra round trip): |A-B| = '
                              f'{abs(eff):.2f} pp per trade vs {FILTER_PP:.2f} pp -> '
                              f'{"meets" if abs(eff) >= FILTER_PP else "below"}')
        rows.append(r)
    d = pd.DataFrame(rows)
    liq = liq_groups('all')['above bottom tercile']
    m_liq = evmat(E43[cols('all')] & liq, 'all', 20)
    m_fr = evmat(fresh(E43), 'all', 20)
    m_a, m_b = evmat(E43, 'all', 20), evmat(up & ~SPIKE, 'all', 20)
    d.loc[0, 'notes'] = (f'MAIN events {nev(m_liq)} of {nev(evmat(E43, "all", 20))}; event-weighted {pooled(m_liq) * PCT:+.2f}%; '
                         f'bottom tercile alone {fmt(stat("W4.3", "all", E43[cols("all")] & liq_groups("all")["bottom tercile"]))}; '
                         f'survivorship medium: stocks were already liquid before the event, but they are still today\'s members')
    d.loc[1, 'notes'] = (f'MAIN events {nev(m_fr)}; event-weighted {pooled(m_fr) * PCT:+.2f}%; repeat events (an event in '
                         f't-20..t-1) {fmt(stat("W4.3", "all", E43 & ~fresh(E43)))}; survivorship as W4.3')
    d.loc[2, 'notes'] = (f'MAIN events A/B {nev(m_a)}/{nev(m_b)}; event-weighted A {pooled(m_a) * PCT:+.2f}% / B '
                         f'{pooled(m_b) * PCT:+.2f}%; B = all other up days of stocks with a defined 20-day volume mean; '
                         f'difference within the same survivor set (medium)')
    return d


# ------------------------------------------------------------------ self-checks (brute force on samples)
def self_checks():
    rng = np.random.default_rng(4)
    Cv, Hv, Lv, Ov, Vv, Tv = C.values, H.values, L.values, O.values, V.values, T.values
    rv, lp = r_cc.values, lnP.values
    N, K = Cv.shape
    listed = lp == lp                                         # lnP defined from the first bar on
    for i, j in zip(rng.integers(21, N - 1, 20000), rng.integers(0, K, 20000)):
        ok_r = np.isfinite(rv[i, j])
        e1 = ok_r and rv[i, j] >= UP15 and Tv[i, j] and Cv[i, j] >= Hv[i, j] * (1 - EPS)
        e2 = ok_r and rv[i, j] <= DN15 and Tv[i, j] and Cv[i, j] <= Lv[i, j] * (1 + EPS)
        assert e1 == E41.values[i, j] and e2 == E42.values[i, j], ('E41/E42', i, j)
        w = Vv[i - 20:i, j]
        vm = np.nanmean(w) if (listed[i - 20, j] and np.isfinite(w).any()) else np.nan
        assert (np.isnan(vm) and np.isnan(VMEAN.values[i, j])) or abs(vm - VMEAN.values[i, j]) <= 1e-9 * max(vm, 1)
        sp = bool(np.isfinite(vm) and np.isfinite(Vv[i, j]) and Vv[i, j] >= 3 * vm)
        assert (sp and ok_r and rv[i, j] > 0) == E43.values[i, j] and (sp and ok_r and rv[i, j] < 0) == E44.values[i, j]
        d20 = lp[i, j] - lp[i - 20, j]
        assert (np.isfinite(d20) and d20 >= RUN) == E45.values[i, j] and (np.isfinite(d20) and d20 <= CRASH) == E46.values[i, j]
        lk = bool(Tv[i + 1, j] and Ov[i + 1, j] >= Hv[i + 1, j] * (1 - EPS) and Cv[i + 1, j] >= Hv[i + 1, j] * (1 - EPS)
                  and np.isfinite(rv[i + 1, j]) and rv[i + 1, j] >= UP15)
        assert lk == LOCK_UP.values[i, j], ('LOCK_UP', i, j)
    for u in UNIVS:                                           # evmat mirrors event_series; fo window as documented
        for tid, s in TESTS.items():
            s1 = evmat(s['mask'], u, s['h']).mean(axis=1)
            s2, n2 = event_series(P, s['mask'], s['h'], u)
            assert np.allclose(s1.fillna(-9).values, s2.fillna(-9).values), (tid, u)
            assert n2 == int(np.isfinite(evmat(s['mask'], u, s['h']).values).sum())
    tick = list(C.columns)
    c = cols('all')
    lo = P['lnO'].values
    for tid in ('W4.1', 'W4.3', 'W4.6'):
        h = TESTS[tid]['h']
        M = evmat(TESTS[tid]['mask'], 'all', h)
        ev = np.argwhere(np.isfinite(M.values))
        F = P['fo'][h][c].values
        for i, j in ev[rng.choice(len(ev), min(300, len(ev)), replace=False)]:
            ref = lp[i + h, tick.index(c[j])] - lo[i + 1, tick.index(c[j])]
            assert abs(ref - F[i, j]) < 1e-12
            assert abs(M.values[i, j] - (F[i, j] - np.nanmean(F[i]))) < 1e-12
    # placebo: events drawn at random with the W4.3 per-stock frequency -> |t| small
    dens = E43.loc[MAIN[0]:MAIN[1]].values.mean()
    ts = [Mean(ser(frame(rng.random(C.shape) < dens, C), 'all', 20), 20).at(*MAIN)[1] for _ in range(10)]
    assert max(abs(x) for x in ts) < 3.5, ts
    print('self-checks passed (event masks, volume mean, lock proxy, evmat == event_series, fo windows, placebo '
          'max|t| %.2f)' % max(abs(x) for x in ts))


if __name__ == '__main__':
    self_checks()
    OUT.mkdir(exist_ok=True)
    d = primary_rows()
    d.to_csv(OUT / 'W4_tests.csv', index=False)
    cx = context()
    cx.to_csv(OUT / 'W4_context.csv', index=False)
    x = exploratory()
    x.to_csv(OUT / 'W4_exploratory.csv', index=False)
    pd.set_option('display.width', 250)
    show = ['test_id', 'eff_MAIN', 't_MAIN', 'n_MAIN', 'eff_P1', 'eff_P2', 'eff_P3', 'eff_P4', 'eff_P0', 'eff_pre2018',
            't_pre2018', 'signs_P1_P4', 'pass_t3', 'pass_stable', 'pass_pre2018', 'survivorship_risk', 'exploit_type']
    print(d[show].round(3).to_string(index=False))
    print(x[show].round(3).to_string(index=False))
    print('wrote', OUT / 'W4_tests.csv', len(d), 'rows;', OUT / 'W4_context.csv', len(cx), 'rows;',
          OUT / 'W4_exploratory.csv', len(x), 'rows')
