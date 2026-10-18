"""W2 - trade path after breakout entries (market-properties v2, pre-registered family W2 of PLAN.md).

Entry (PLAN.md W2 header): W1.1 HHV20 Close breakout on clean levels, lnP[t] > max(lnH[t-20..t-1]), with
ER20 = |lnP[t]-lnP[t-20]| / sum(|daily lnP change|, 20) >= 0.2 (ER20 as in W1.7); buy at the next Open lnO[t+1].
Primary tests W2.1-W2.5 -> results/W2_tests.csv (mpstats.row); descriptive context -> results/W2_context.csv;
exploratory X-W2-* -> results/W2_exploratory.csv.

Definition choices (most literal causal reading of PLAN.md; repeated in the notes column of each row):
 - HHV20: max over the 20 market days t-20..t-1 of the clean High; non-tradable days have no High and are skipped
   (equivalent to a flat carried price, which cannot exceed the prior High); the window must lie after the stock's
   first bar (age >= 20 rows). The event day t must be tradable. ER20 uses lnP (flat on non-tradable days).
 - Entry needs a valid Open at t+1 (tradable, not a data-error bar). Every event is a trade; one stock can have
   several overlapping events.
 - '+5% / -5% / +10%' are simple-return levels applied to log returns: ln(1.05), ln(0.95), ln(1.10) (PLAN.md writes
   percentage thresholds this way elsewhere, e.g. W1.9 'gapped >= 2%' = ln(1.02)).
 - Per-day aggregation is by the signal day t; the series sits on the full market calendar (NaN = no event).
 - Newey-West lags: 20 where PLAN.md states it (W2.1, W2.2, W2.5). W2.3 and W2.4 state no lag, so the general rule
   'lags = h for h-day windows' applies: 60 for W2.3 (window ends at t+60), 40 for W2.4 (t+20..t+60).
 - W2.3: g = first day in t+1..t+20 with lnP[g]-lnO[t+1] >= ln(1.10); return lnP[t+60]-lnO[g+1] (needs a valid Open
   at g+1) minus the same-window EW mean over the universe (stocks with a valid Open at g+1).
 - W2.4: (lnP[t+60]-lnP[t+20]) minus the EW mean of the same window over listed universe stocks, / 40.
 - W2.5: trailing signal on tradable Closes of bars t+1..t+119: lnP[d] < min(lnL[d-10..d-1]) (non-tradable days
   skipped); exit at the next valid Open after d. No signal -> exit at the Close of bar 120 (lnP[t+120]), the same
   convention as the 20-bar hold exiting at lnP[t+20]. Only events with a full 120-bar window inside the data are
   used, so the end of the sample does not select early (stopped-out) trades.
 - Survivorship label (PLAN.md: effects favouring losers, crashed or illiquid stocks are high risk): high if the effect
   on entries whose 20-day lookback is fully tradable is below 2/3 of the overall MAIN effect (the rest comes from
   illiquid or suspended episodes of stocks that later became index members) or if W2.1/W2.2 favour losers; otherwise
   medium (the universe is today's Kompas100 in every case).
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel import load, universe, MAIN                          # noqa: E402
from mpstats import Mean, Diff, row, event_series, PERIODS, COST_RT   # noqa: E402

OUT = HERE / 'results'
FAM = 'W2'
UP5, DN5, UP10 = np.log(1.05), np.log(0.95), np.log(1.10)
ER_MIN = 0.2
LAGS = {'W2.1': 20, 'W2.2': 20, 'W2.3': 60, 'W2.4': 40, 'W2.5': 20}
CAP = 120
DECLUSTER = 60
PCT, BPS = 100., 1e4
RT_A, RT_B = f'{PCT * COST_RT["A"]:.2f}%', f'{PCT * COST_RT["B"]:.2f}%'   # round-trip cost scenarios


# ----------------------------------------------------------------------------------------------- helpers
def shifted(a, k):
    """Row i of the result = a[i+k] (NaN outside the array)."""
    out = np.full(a.shape, np.nan)
    n = a.shape[0]
    if k >= 0:
        out[:n - k] = a[k:]
    else:
        out[-k:] = a[:n + k]
    return out


def xs_mean(W):
    """Row-wise mean ignoring NaN (NaN when a row has no value), without RuntimeWarnings."""
    ok = np.isfinite(W)
    c = ok.sum(1)
    s = np.where(ok, W, 0.).sum(1)
    return np.where(c > 0, s / np.maximum(c, 1), np.nan)


def day_series(i, v, index):
    """Mean of v over the events of each signal day (row i); full market calendar, NaN = no event."""
    ok = np.isfinite(v)
    s = pd.Series(v[ok]).groupby(i[ok]).mean()
    out = np.full(len(index), np.nan)
    out[s.index.values] = s.values
    return pd.Series(out, index=index)


def in_period(dates, a, b):
    return (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b))


def first_per_window(i, j, gap):
    """Keep an event if the same stock has no kept event in the previous `gap` market days (greedy, chronological)."""
    keep = np.zeros(len(i), bool)
    last = {}
    for pos in np.lexsort((i, j)):
        jj, ii = j[pos], i[pos]
        if ii - last.get(jj, -10 ** 9) >= gap:
            keep[pos] = True
            last[jj] = ii
    return keep


# ----------------------------------------------------------------------------------------------- events
def build_events(P):
    idx = P['C'].index
    cols = list(P['C'].columns)
    N = len(idx)
    lnP, lnO, lnH, lnL, T = (P[k] for k in ('lnP', 'lnO', 'lnH', 'lnL', 'T'))
    age = lnP.notna().cumsum() - 1                  # rows since the first bar (lnP is defined from the first bar on)
    hhv20 = lnH.shift(1).rolling(20, min_periods=1).max()
    den = lnP.diff().abs().rolling(20, min_periods=20).sum()
    er20 = (lnP - lnP.shift(20)).abs() / den.where(den > 0)
    w11 = (lnP > hhv20) & T & (age >= 20)
    E = w11 & (er20 >= ER_MIN) & lnO.shift(-1).notna()
    i, j = np.nonzero(E.values)                      # row-major: sorted by date, then ticker
    LP, LO, LL, TT = lnP.values, lnO.values, lnL.values, T.values

    def g(a, off):
        r = i + off
        out = np.full(len(i), np.nan)
        ok = (r >= 0) & (r < N)
        out[ok] = a[r[ok], j[ok]]
        return out

    ent = g(LO, 1)
    ev = dict(i=i, j=j, date=idx[i], ticker=np.array(cols)[j], er20=er20.values[i, j], ent=ent)
    # W2.1 / W2.2 (+ context variants)
    for k in (5, 10, 20):
        ev[f'u{k}'] = g(LP, k) - ent
        ev[f'z{k}'] = g(LP, 60) - g(LO, k + 1)          # continuation from the Open after day t+k to Close t+60
    ev['z5_20'] = g(LP, 20) - g(LO, 6)
    ev['z5_120'] = g(LP, 120) - g(LO, 6)
    ev['z20_120'] = g(LP, 120) - g(LO, 21)
    # W2.3: first Close-based gain >= +10% within t+1..t+20
    G = np.column_stack([g(LP, k) - ent for k in range(1, 21)])
    with np.errstate(invalid='ignore'):
        hit = G >= UP10
    has = hit.any(1)
    k10 = np.where(has, hit.argmax(1) + 1, 0)
    ev['k10'] = k10
    r23 = np.full(len(i), np.nan)
    for k in range(1, 21):
        m = k10 == k
        r23[m] = (g(LP, 60) - g(LO, k + 1))[m]
    ev['r23'] = r23
    # W2.3 context: +20% threshold
    with np.errstate(invalid='ignore'):
        hit20 = G >= np.log(1.20)
    k20 = np.where(hit20.any(1), hit20.argmax(1) + 1, 0)
    r23b = np.full(len(i), np.nan)
    for k in range(1, 21):
        m = k20 == k
        r23b[m] = (g(LP, 60) - g(LO, k + 1))[m]
    ev['k20'], ev['r23_20'] = k20, r23b
    # W2.4 (+ context drifts)
    ev['d24'] = g(LP, 60) - g(LP, 20)
    ev['d_1_20'] = g(LP, 20) - ent
    ev['d_61_120'] = g(LP, 120) - g(LP, 60)
    # forward path (raw) from the entry Open; f31 = fixed-hold control for the exploratory W2.5 check
    for h in (1, 5, 10, 20, 31, 40, 60, 120):
        ev[f'f{h}'] = g(LP, h) - ent
    # W2.5: trailing exit vs fixed 20-bar hold
    LL10 = lnL.shift(1).rolling(10, min_periods=1).min().values
    full = i + CAP <= N - 1
    rows = np.minimum(i[:, None] + np.arange(1, CAP)[None, :], N - 1)          # bars t+1..t+119
    cl = LP[rows, j[:, None]]
    with np.errstate(invalid='ignore'):
        sig = TT[rows, j[:, None]] & (cl < LL10[rows, j[:, None]])
    sig &= (i[:, None] + np.arange(1, CAP)[None, :]) <= N - 1
    fired = sig.any(1)
    dsig = i + np.where(fired, sig.argmax(1) + 1, CAP)                     # signal row (or cap row)
    nxt = pd.DataFrame(np.where(np.isfinite(LO), np.arange(N)[:, None], np.nan)).bfill().values
    exit_row = np.full(len(i), -1)
    okr = fired & (dsig + 1 <= N - 1)
    er = nxt[np.minimum(dsig + 1, N - 1), j]
    okr &= np.isfinite(er)
    exit_row[okr] = er[okr].astype(int)
    r_tr = np.full(len(i), np.nan)
    r_tr[okr] = LO[exit_row[okr], j[okr]] - ent[okr]
    cap = ~fired & full
    r_tr[cap] = LP[i[cap] + CAP, j[cap]] - ent[cap]
    r_tr[~full] = np.nan
    bars = np.where(okr, exit_row - (i + 1), np.where(cap, CAP, -1)).astype(float)
    bars[~np.isfinite(r_tr)] = np.nan
    ev.update(r_tr=r_tr, r_fix=g(LP, 20) - ent, bars_tr=bars, capped=cap & np.isfinite(r_tr), exit_row=exit_row,
              full120=full)
    ev['d25'] = ev['r_tr'] - ev['r_fix']
    # right tail: peak Close within 120 bars
    rows120 = np.minimum(i[:, None] + np.arange(1, CAP + 1)[None, :], N - 1)
    path = LP[rows120, j[:, None]]
    pk = np.where(full, np.nanargmax(np.where(np.isfinite(path), path, -np.inf), 1) + 1, 0)
    ev['peak_k'] = np.where(full, pk, np.nan)
    ev['peak_gain'] = np.where(full, np.nanmax(np.where(np.isfinite(path), path, -np.inf), 1) - ent, np.nan)
    ev['keep60'] = first_per_window(i, j, DECLUSTER)
    # every day of the 20-day lookback tradable (lnH is NaN exactly on non-tradable days); context split only
    ev['fullwin'] = lnH.shift(1).rolling(20, min_periods=20).max().notna().values[i, j]
    meta = dict(E=E, N=N, idx=idx, cols=cols, LP=LP, LO=LO)
    return pd.DataFrame(ev), meta


# ----------------------------------------------------------------------------------------------- abnormal
def add_abnormal(ev, meta, univ, P):
    """Benchmarks = same-window EW mean over the universe; adds columns with suffix _<univ>."""
    cols = meta['cols']
    cm = np.isin(cols, universe(P, univ))
    LP, LO = meta['LP'][:, cm], meta['LO'][:, cm]
    i = ev['i'].values
    sfx = '_' + univ
    b = {}
    b['fo'] = {h: xs_mean(shifted(LP, h) - shifted(LO, 1)) for h in (1, 5, 10, 20, 31, 40, 60, 120)}
    b23 = {k: xs_mean(shifted(LP, 60) - shifted(LO, k + 1)) for k in range(1, 21)}
    out = {}
    for h, bb in b['fo'].items():
        out['af' + str(h) + sfx] = ev[f'f{h}'].values - bb[i]
    for k in (5, 10, 20):
        out[f'az{k}' + sfx] = ev[f'z{k}'].values - b23[k][i]
    a23 = np.full(len(ev), np.nan)
    a23b = np.full(len(ev), np.nan)
    for k in range(1, 21):
        m = ev['k10'].values == k
        a23[m] = ev['r23'].values[m] - b23[k][i[m]]
        m = ev['k20'].values == k
        a23b[m] = ev['r23_20'].values[m] - b23[k][i[m]]
    out['a23' + sfx], out['a23_20' + sfx] = a23, a23b
    b24 = xs_mean(shifted(LP, 60) - shifted(LP, 20))
    out['a24' + sfx] = ev['d24'].values - b24[i]
    b120 = xs_mean(shifted(LP, 120) - shifted(LP, 60))
    out['a_61_120' + sfx] = ev['d_61_120'].values - b120[i]
    out['a_1_20' + sfx] = ev['d_1_20'].values - b['fo'][20][i]
    # W2.5 abnormal arms (per-event benchmark windows)
    N = LP.shape[0]
    er = ev['exit_row'].values
    capped = ev['capped'].values
    btr = np.full(len(ev), np.nan)
    m = er >= 0
    btr[m] = xs_mean(LO[er[m]] - LO[i[m] + 1])
    m = capped
    btr[m] = xs_mean(LP[np.minimum(i[m] + CAP, N - 1)] - LO[i[m] + 1])
    out['atr' + sfx] = ev['r_tr'].values - btr
    out['afix' + sfx] = ev['r_fix'].values - b['fo'][20][i]
    out['ad25' + sfx] = out['atr' + sfx] - out['afix' + sfx]
    for k, v in out.items():
        ev[k] = v


# ----------------------------------------------------------------------------------------------- tests
def stats_for(ev, univ, index, P, keep=None, lags=None):
    """Per test: dict with the mpstats statistic (`stat`) and the event masks/values used; one universe.
    `keep` restricts the events (e.g. first event per stock in 60 days), `lags` overrides LAGS."""
    L = dict(LAGS, **(lags or {}))
    sel = np.isin(ev['ticker'].values, universe(P, univ))
    if keep is not None:
        sel &= keep
    i = ev['i'].values
    sfx = '_' + univ
    res = {}
    for tid, u, z in (('W2.1', 'u5', 'z5'), ('W2.2', 'u20', 'z20')):
        uu, zz = ev[u].values, ev[z].values
        with np.errstate(invalid='ignore'):
            up = sel & (uu >= UP5) & np.isfinite(zz)
            dn = sel & (uu <= DN5) & np.isfinite(zz)
        A, B = day_series(i[up], zz[up], index), day_series(i[dn], zz[dn], index)
        res[tid] = dict(stat=Diff(A, B, L[tid]), up=up, dn=dn, A=A, B=B, v=zz)
    v = ev['a23' + sfx].values
    m = sel & np.isfinite(v)
    res['W2.3'] = dict(stat=Mean(day_series(i[m], v[m], index), L['W2.3']), m=m, v=v)
    v = ev['a24' + sfx].values / 40.
    m = sel & np.isfinite(v)
    res['W2.4'] = dict(stat=Mean(day_series(i[m], v[m], index), L['W2.4']), m=m, v=v)
    v = ev['d25'].values
    m = sel & np.isfinite(v)
    res['W2.5'] = dict(stat=Mean(day_series(i[m], v[m], index), L['W2.5']), m=m, v=v)
    return res


DESC = {
    'W2.1': 'Breakout entry (HHV20 close breakout, ER20>=0.2, buy Open t+1): raw continuation z=lnP[t+60]-lnO[t+6] '
            'when u5=lnP[t+5]-lnO[t+1] >= ln1.05 minus when u5 <= ln0.95',
    'W2.2': 'Same entries: raw z=lnP[t+60]-lnO[t+21] when u20=lnP[t+20]-lnO[t+1] >= ln1.05 minus when u20 <= ln0.95',
    'W2.3': 'Same entries whose Close gain lnP[g]-lnO[t+1] first reaches >= ln1.10 at g in t+1..t+20: abnormal '
            'lnP[t+60]-lnO[g+1] (minus same-window EW universe mean)',
    'W2.4': 'Same entries: abnormal (lnP[t+60]-lnP[t+20]) / 40 (minus same-window EW universe mean), per day',
    'W2.5': 'Same entries: trailing exit (first Close < min lnL of prior 10 bars, sell next Open, cap 120 bars) minus '
            'fixed 20-bar hold (sell lnP[t+20]); raw paired per-trade difference',
}
UNIT = {'W2.1': '%', 'W2.2': '%', 'W2.3': '%', 'W2.4': 'bps/day', 'W2.5': '%'}
SCALE = {'W2.1': PCT, 'W2.2': PCT, 'W2.3': PCT, 'W2.4': BPS, 'W2.5': PCT}
SCALE_CTX = SCALE                                   # context values are stored in the reporting unit
EXPLOIT = {'W2.1': 'filter', 'W2.2': 'filter', 'W2.3': 'standalone', 'W2.4': 'timing', 'W2.5': 'timing'}
COST = {
    'W2.1': ('Early-path rule inside the breakout signal: usable if |difference| >= 0.25 pp per trade. Cutting a loser '
             'at day 5 adds no round trip (the position is sold once either way); redeploying the cash costs a new '
             f'round trip ({RT_A} A / {RT_B} B).'),
    'W2.2': ('Early-path rule at day 20: usable if |difference| >= 0.25 pp per trade; cutting or keeping adds no round '
             f'trip, redeploying costs {RT_A} A / {RT_B} B.'),
    'W2.3': ('As an add-on (pyramid) entry at Open g+1 held to t+60 the abnormal effect must exceed the round trip '
             f'{RT_B} (B; {RT_A} A). As a hold-instead-of-take-profit rule for an open position no extra round trip.'),
    'W2.4': ('Holding-period extension from day 20 to day 60: per-trade incremental abnormal = 40 x drift, no extra '
             f'round trip for an open position (versus a fresh entry at t+20: {RT_B} B / {RT_A} A round trip).'),
    'W2.5': ('One round trip in both arms, so costs cancel per trade (net difference = gross difference); the trailing '
             'arm ties capital up longer (holding days and per-day returns in W2_context.csv).'),
}


LIQ_RATIO = 2 / 3


def survivorship(tid, eff, ctx):
    """PLAN.md: effects favouring losers, crashed or illiquid stocks are high risk (delisted stocks are missing).
    Rule used here: high if the effect on entries whose 20-day lookback is fully tradable is below 2/3 of the overall
    MAIN effect (the rest comes from illiquid or suspended episodes of stocks that later became index members), or if
    W2.1/W2.2 favour losers (difference <= 0); otherwise medium (current-constituent universe)."""
    x = ctx[(ctx.section == 'lookback_liquidity') & (ctx.test_id == tid) & (ctx.universe == 'all')
            & (ctx.period == 'MAIN') & ctx.metric.str.contains('fully tradable')]
    liq = x['value'].iloc[0] / SCALE_CTX[tid]
    if (tid in ('W2.1', 'W2.2') and eff <= 0) or not (np.sign(liq) == np.sign(eff) and abs(liq) >= LIQ_RATIO * abs(eff)):
        return 'high'
    return 'medium'


def main():
    t0 = time.time()
    P = load()
    OUT.mkdir(exist_ok=True)
    index = P['C'].index
    ev, meta = build_events(P)
    for u in ('all', 'pre2018'):
        add_abnormal(ev, meta, u, P)
    print(f'events built: {len(ev)} entries, {time.time() - t0:.1f}s')

    # sanity: own abnormal fo[20] day series equals mpstats.event_series on the same events
    for u in ('all', 'pre2018'):
        sel = np.isin(ev['ticker'].values, universe(P, u))
        mine = day_series(ev['i'].values[sel], ev['af20_' + u].values[sel], index)
        ref, nref = event_series(P, meta['E'], 20, u)
        d = (mine - ref).abs().max()
        assert d < 1e-12 and nref == int(np.isfinite(ev['af20_' + u].values[sel]).sum()), (u, d, nref)
    print('check vs event_series OK')

    R = {u: stats_for(ev, u, index, P) for u in ('all', 'pre2018')}
    ctx = context(ev, meta, P, R, index)
    ctx.to_csv(OUT / 'W2_context.csv', index=False)
    xp = exploratory(ev, meta, P, index)
    xp.to_csv(OUT / 'W2_exploratory.csv', index=False)

    rows = []
    for tid in ('W2.1', 'W2.2', 'W2.3', 'W2.4', 'W2.5'):
        ra, rp = R['all'][tid], R['pre2018'][tid]
        eff = ra['stat'].at(*MAIN)[0]
        mm = in_period(ev['date'], *MAIN).values
        if tid in ('W2.1', 'W2.2'):
            cnt = f'events MAIN up {int((ra["up"] & mm).sum())} / down {int((ra["dn"] & mm).sum())}'
        else:
            cnt = f'events MAIN {int((ra["m"] & mm).sum())}'
        notes = (f'{cnt}; NW lags {LAGS[tid]}; daily means over events of signal day t; entries overlap '
                 f'(each event = trade). ' + NOTE_EXTRA[tid] + ' ' + robustness_note(ctx, xp, tid))
        rows.append(row(tid, FAM, DESC[tid], UNIT[tid], ra['stat'], rp['stat'], scale=SCALE[tid],
                        cost_note=COST[tid], surv_risk=survivorship(tid, eff, ctx), exploit=EXPLOIT[tid], notes=notes))
    tests = pd.DataFrame(rows)
    tests.to_csv(OUT / 'W2_tests.csv', index=False)
    print(tests[['test_id', 'unit', 'eff_MAIN', 't_MAIN', 'n_MAIN', 'eff_P1', 'eff_P2', 'eff_P3', 'eff_P4', 'eff_P0',
                 'eff_pre2018', 't_pre2018', 'signs_P1_P4', 'pass_t3', 'pass_stable', 'pass_pre2018']]
          .to_string(float_format=lambda x: f'{x:.3f}'))
    print(f'wrote {len(tests)} tests, {len(ctx)} context rows, {len(xp)} exploratory rows in {time.time() - t0:.1f}s')
    return tests, ctx, xp, ev


def robustness_note(ctx, xp, tid):
    """One-line summary of the context robustness checks (MAIN, universe all) for the notes column."""
    def get(section, metric_start, univ='all', period='MAIN'):
        x = ctx[(ctx.section == section) & (ctx.test_id == tid) & (ctx.universe == univ) & (ctx.period == period)
                & ctx.metric.str.startswith(metric_start)]
        return (x['value'].iloc[0], x['t'].iloc[0]) if len(x) else (np.nan, np.nan)
    u = UNIT[tid]
    alt = {'W2.1': 'abnormal z', 'W2.2': 'abnormal z', 'W2.3': 'raw', 'W2.4': 'raw', 'W2.5': 'abnormal'}[tid]
    a = get('alt_basis', alt)
    f = get('first_per_60d', 'primary')
    lg = ctx[(ctx.section == 'lag_sensitivity') & (ctx.test_id == tid) & (ctx.universe == 'all')]
    s = (f'Robustness (MAIN, all): {alt} basis {a[0]:.2f}{u} (t {a[1]:.2f}); first event per stock in 60 days '
         f'{f[0]:.2f}{u} (t {f[1]:.2f}); {lg.metric.iloc[0].split(" (")[0].replace("t with ", "")} t {lg.t.iloc[0]:.2f}.')
    p4 = get('pre2018_subperiods', 'primary', univ='pre2018', period='P4')
    s += f' pre2018 universe in P4: {p4[0]:.2f}{u} (t {p4[1]:.2f}).'
    lq = ctx[(ctx.section == 'lookback_liquidity') & (ctx.test_id == tid) & (ctx.universe == 'all') & (ctx.period == 'MAIN')]
    full, gap = lq[lq.metric.str.contains('fully')].iloc[0], lq[~lq.metric.str.contains('fully')].iloc[0]
    s += (f' Lookback liquidity: entries with a fully tradable 20-day lookback {full.value:.2f}{u} (t {full.t:.2f}, '
          f'{full.note}), with >= 1 non-tradable day {gap.value:.2f}{u} (t {gap.t:.2f}, {gap.note}); survivorship label '
          f'high if the first is below 2/3 of the overall effect.')
    if tid == 'W2.5':
        d = ctx[(ctx.section == 'W2.5_detail') & (ctx.universe == 'all')].set_index('metric')['value']
        x1 = xp.set_index('test_id')
        s += (f' Trailing arm: mean {d["trailing arm mean bars held"]:.1f} bars (median '
              f'{d["trailing arm median bars held"]:.0f}), {d["trailing arm share exiting before bar 20"]:.0f}% exit before '
              f'bar 20, wins in {d["share of trades where trailing beats fixed"]:.0f}% of trades; raw return per bar held '
              f'{d["trailing arm return per bar held (sum r / sum bars)"]:.1f} vs fixed '
              f'{d["fixed arm return per bar held (sum r / (20 n))"]:.1f} bps. Versus a fixed 31-bar hold (exploratory '
              f'X-W2-1/2): raw {x1.loc["X-W2-1", "eff_MAIN"]:.2f}% (t {x1.loc["X-W2-1", "t_MAIN"]:.2f}), abnormal '
              f'{x1.loc["X-W2-2", "eff_MAIN"]:.2f}% (t {x1.loc["X-W2-2", "t_MAIN"]:.2f}).')
    return s


NOTE_EXTRA = {
    'W2.1': 'Thresholds +-5% as ln(1.05)/ln(0.95); z needs a valid Open at t+6. Raw (not abnormal) returns as PLAN.md.',
    'W2.2': 'Thresholds +-5% as ln(1.05)/ln(0.95); z needs a valid Open at t+21. Raw returns as PLAN.md.',
    'W2.3': '+10% as ln(1.10); g = first Close in t+1..t+20 at or above it; needs a valid Open at g+1; lags 60 by the '
            'general rule (no lag stated for W2.3).',
    'W2.4': 'Abnormal 40-day window return / 40, x1e4; lags 40 by the general rule (no lag stated for W2.4).',
    'W2.5': 'Trailing signal checked on tradable Closes of bars 1..119, exit next valid Open; no signal -> Close of '
            'bar 120. Only events with a full 120-bar window. Raw returns as PLAN.md.',
}


# ----------------------------------------------------------------------------------------------- context
def context(ev, meta, P, R, index):
    C = []

    def add(section, tid, univ, period, metric, value, unit='', n=np.nan, t=np.nan, note=''):
        C.append(dict(section=section, test_id=tid, universe=univ, period=period, metric=metric,
                      value=value, unit=unit, n=n, t=t, note=note))

    dates = ev['date']
    per = {k: in_period(dates, a, b).values for k, (a, b) in PERIODS.items()}
    # 1. entry counts
    for u in ('all', 'pre2018'):
        sel = np.isin(ev['ticker'].values, universe(P, u))
        for k in PERIODS:
            add('counts', 'entries', u, k, 'n_entries (W1.1 & ER20>=0.2 & valid Open t+1)', int((sel & per[k]).sum()))
            add('counts', 'entries', u, k, 'n_entries first per stock in 60 days', int((sel & per[k] & ev['keep60'].values).sum()))
            add('counts', 'entries', u, k, 'n_signal_days', int(ev.loc[sel & per[k], 'i'].nunique()))
    # 2. per-test counts and event-weighted means; group means
    for u in ('all', 'pre2018'):
        r = R[u]
        for tid in ('W2.1', 'W2.2'):
            up, dn, v = r[tid]['up'], r[tid]['dn'], r[tid]['v']
            uu = ev['u5' if tid == 'W2.1' else 'u20'].values
            with np.errstate(invalid='ignore'):
                mid = np.isin(ev['ticker'].values, universe(P, u)) & (uu > DN5) & (uu < UP5) & np.isfinite(v)
            for k in PERIODS:
                pm = per[k]
                add('counts', tid, u, k, 'n_up', int((up & pm).sum()))
                add('counts', tid, u, k, 'n_down', int((dn & pm).sum()))
                add('counts', tid, u, k, 'n_middle', int((mid & pm).sum()))
                if (up & pm).sum() and (dn & pm).sum():
                    add('event_weighted', tid, u, k, 'mean z up minus down', PCT * (v[up & pm].mean() - v[dn & pm].mean()), '%',
                        n=int((up & pm).sum() + (dn & pm).sum()))
            pm = per['MAIN']
            for gname, gm in (('up', up), ('down', dn), ('middle', mid)):
                add('groups', tid, u, 'MAIN', f'event-weighted mean z, {gname} group', PCT * v[gm & pm].mean(), '%', n=int((gm & pm).sum()))
            add('groups', tid, u, 'MAIN', 'day-mean z, up group', PCT * r[tid]['A'].loc[MAIN[0]:MAIN[1]].mean(), '%')
            add('groups', tid, u, 'MAIN', 'day-mean z, down group', PCT * r[tid]['B'].loc[MAIN[0]:MAIN[1]].mean(), '%')
        for tid, sc, un in (('W2.3', PCT, '%'), ('W2.4', BPS, 'bps/day'), ('W2.5', PCT, '%')):
            m, v = r[tid]['m'], r[tid]['v']
            for k in PERIODS:
                add('counts', tid, u, k, 'n_events', int((m & per[k]).sum()))
                if (m & per[k]).sum():
                    add('event_weighted', tid, u, k, 'event-weighted mean (primary definition)', sc * v[m & per[k]].mean(), un,
                        n=int((m & per[k]).sum()))
    # 3. alternative return bases: raw for W2.3/W2.4, abnormal for W2.1/W2.2/W2.5 (day-mean, NW)
    i = ev['i'].values
    for u in ('all', 'pre2018'):
        sel = np.isin(ev['ticker'].values, universe(P, u))
        sfx = '_' + u
        for tid, ucol, zcol in (('W2.1', 'u5', 'az5'), ('W2.2', 'u20', 'az20')):
            uu, zz = ev[ucol].values, ev[zcol + sfx].values
            with np.errstate(invalid='ignore'):
                up, dn = sel & (uu >= UP5) & np.isfinite(zz), sel & (uu <= DN5) & np.isfinite(zz)
            st = Diff(day_series(i[up], zz[up], index), day_series(i[dn], zz[dn], index), LAGS[tid])
            for k in ('MAIN', 'P1', 'P2', 'P3', 'P4'):
                e, t, n = st.at(*PERIODS[k])
                add('alt_basis', tid, u, k, 'abnormal z up minus down (day-mean)', PCT * e, '%', n, t)
        for tid, col, sc, un, lag, div in (('W2.3', 'r23', PCT, '%', 60, 1.), ('W2.4', 'd24', BPS, 'bps/day', 40, 40.)):
            v = ev[col].values / div
            m = sel & np.isfinite(v)
            st = Mean(day_series(i[m], v[m], index), lag)
            for k in ('MAIN', 'P1', 'P2', 'P3', 'P4'):
                e, t, n = st.at(*PERIODS[k])
                add('alt_basis', tid, u, k, 'raw (not abnormal) mean (day-mean)', sc * e, un, n, t)
        v = ev['ad25' + sfx].values
        m = sel & np.isfinite(v)
        st = Mean(day_series(i[m], v[m], index), 20)
        for k in ('MAIN', 'P1', 'P2', 'P3', 'P4'):
            e, t, n = st.at(*PERIODS[k])
            add('alt_basis', 'W2.5', u, k, 'abnormal paired difference (day-mean)', PCT * e, '%', n, t)
    # 3b. primary statistics of the pre2018 universe by subperiod (mpstats.row reports pre2018 for MAIN only)
    for tid in ('W2.1', 'W2.2', 'W2.3', 'W2.4', 'W2.5'):
        for k in PERIODS:
            e, t, n = R['pre2018'][tid]['stat'].at(*PERIODS[k])
            add('pre2018_subperiods', tid, 'pre2018', k, 'primary statistic (day-mean)', SCALE[tid] * e, UNIT[tid], n, t)
    # 4. lag sensitivity of the primary statistics (MAIN, all)
    alt_lags = {'W2.1': 60, 'W2.2': 60, 'W2.3': 20, 'W2.4': 20, 'W2.5': 120}
    for u in ('all', 'pre2018'):
        r2 = stats_for(ev, u, index, P, lags=alt_lags)
        for tid, lag in alt_lags.items():
            e, t, n = r2[tid]['stat'].at(*MAIN)
            add('lag_sensitivity', tid, u, 'MAIN', f't with NW lags {lag} (primary uses {LAGS[tid]})', SCALE[tid] * e,
                UNIT[tid], n, t)
    # 5. first event per stock in any 60-day window (W2.1, W2.2, W2.5; plus W2.3/W2.4 for completeness)
    keep = ev['keep60'].values
    for u in ('all', 'pre2018'):
        r1 = stats_for(ev, u, index, P, keep=keep)
        for tid in ('W2.1', 'W2.2', 'W2.3', 'W2.4', 'W2.5'):
            for k in ('MAIN', 'P1', 'P2', 'P3', 'P4', 'P0'):
                e, t, n = r1[tid]['stat'].at(*PERIODS[k])
                if tid in ('W2.1', 'W2.2'):
                    ne = int(((r1[tid]['up'] | r1[tid]['dn']) & per[k]).sum())
                else:
                    ne = int((r1[tid]['m'] & per[k]).sum())
                add('first_per_60d', tid, u, k, 'primary statistic, first event per stock in 60 days (day-mean)',
                    SCALE[tid] * e, UNIT[tid], n, t, note=f'n_events={ne}')
    # 5b. lookback liquidity split: every day of t-20..t-1 tradable vs >= 1 non-tradable day (illiquid/suspended
    # episodes lean on stocks that later became index members, so they carry more survivorship risk)
    fw = ev['fullwin'].values
    for u in ('all', 'pre2018'):
        for label, km in (('20-day lookback fully tradable', fw), ('20-day lookback with >= 1 non-tradable day', ~fw)):
            rs = stats_for(ev, u, index, P, keep=km)
            for tid in ('W2.1', 'W2.2', 'W2.3', 'W2.4', 'W2.5'):
                for k in ('MAIN', 'P1', 'P2', 'P3', 'P4'):
                    e, t, n = rs[tid]['stat'].at(*PERIODS[k])
                    if tid in ('W2.1', 'W2.2'):
                        ne = int(((rs[tid]['up'] | rs[tid]['dn']) & per[k]).sum())
                    else:
                        ne = int((rs[tid]['m'] & per[k]).sum())
                    add('lookback_liquidity', tid, u, k, f'primary statistic, {label} (day-mean)', SCALE[tid] * e,
                        UNIT[tid], n, t, note=f'n_events={ne}' + ('' if np.isfinite(e) else
                                                                  '; fewer than 20 event days, no estimate'))
    # 6. other horizons: forward path after entry (raw and abnormal), drifts per day in windows, early-path variants
    for u in ('all', 'pre2018'):
        sel = np.isin(ev['ticker'].values, universe(P, u))
        sfx = '_' + u
        for h in (1, 5, 10, 20, 40, 60, 120):
            for basis, col in (('raw', f'f{h}'), ('abnormal', f'af{h}' + sfx)):
                v = ev[col].values
                m = sel & np.isfinite(v)
                st = Mean(day_series(i[m], v[m], index), max(h, 5))
                for k in ('MAIN', 'P1', 'P2', 'P3', 'P4'):
                    e, t, n = st.at(*PERIODS[k])
                    add('path', 'entries', u, k, f'{basis} lnP[t+{h}]-lnO[t+1] (day-mean)', PCT * e, '%', n, t)
                add('path', 'entries', u, 'MAIN', f'{basis} lnP[t+{h}]-lnO[t+1] (event-weighted)',
                    PCT * v[m & per['MAIN']].mean(), '%', int((m & per['MAIN']).sum()))
        for name, col, div, lag in (('abnormal drift days 1-20 per day (Open t+1 to Close t+20)', 'a_1_20', 20., 20),
                                    ('abnormal drift days 21-60 per day (= W2.4)', 'a24', 40., 40),
                                    ('abnormal drift days 61-120 per day', 'a_61_120', 60., 60)):
            v = ev[col + sfx].values / div
            m = sel & np.isfinite(v)
            st = Mean(day_series(i[m], v[m], index), lag)
            for k in ('MAIN', 'P1', 'P2', 'P3', 'P4'):
                e, t, n = st.at(*PERIODS[k])
                add('horizons', 'W2.4', u, k, name, BPS * e, 'bps/day', n, t)
        # early-path variants: decision day 10; continuation windows to t+20 and t+120
        for tid, ucol, zcol, lab in (('W2.1', 'u10', 'z10', 'u10>=ln1.05 minus u10<=ln0.95, z=lnP[t+60]-lnO[t+11]'),
                                     ('W2.1', 'u5', 'z5_20', 'u5 split, short continuation z=lnP[t+20]-lnO[t+6]'),
                                     ('W2.1', 'u5', 'z5_120', 'u5 split, long continuation z=lnP[t+120]-lnO[t+6]'),
                                     ('W2.2', 'u20', 'z20_120', 'u20 split, long continuation z=lnP[t+120]-lnO[t+21]')):
            uu, zz = ev[ucol].values, ev[zcol].values
            with np.errstate(invalid='ignore'):
                up, dn = sel & (uu >= UP5) & np.isfinite(zz), sel & (uu <= DN5) & np.isfinite(zz)
            st = Diff(day_series(i[up], zz[up], index), day_series(i[dn], zz[dn], index), 20)
            for k in ('MAIN', 'P1', 'P2', 'P3', 'P4'):
                e, t, n = st.at(*PERIODS[k])
                add('horizons', tid, u, k, 'raw ' + lab, PCT * e, '%', n, t)
        # symmetric log thresholds +-0.05 instead of ln(1.05)/ln(0.95)
        for tid, ucol, zcol in (('W2.1', 'u5', 'z5'), ('W2.2', 'u20', 'z20')):
            uu, zz = ev[ucol].values, ev[zcol].values
            with np.errstate(invalid='ignore'):
                up, dn = sel & (uu >= .05) & np.isfinite(zz), sel & (uu <= -.05) & np.isfinite(zz)
            st = Diff(day_series(i[up], zz[up], index), day_series(i[dn], zz[dn], index), 20)
            e, t, n = st.at(*MAIN)
            add('thresholds', tid, u, 'MAIN', 'log thresholds +-0.05 instead of ln1.05/ln0.95', PCT * e, '%', n, t)
        # W2.3 with a +20% trigger
        v = ev['a23_20' + sfx].values
        m = sel & np.isfinite(v)
        st = Mean(day_series(i[m], v[m], index), 60)
        for k in ('MAIN', 'P1', 'P2', 'P3', 'P4'):
            e, t, n = st.at(*PERIODS[k])
            add('thresholds', 'W2.3', u, k, 'trigger +20% (ln1.20) instead of +10%: abnormal lnP[t+60]-lnO[g+1]',
                PCT * e, '%', n, t, note=f'n_events={int((m & per[k]).sum())}')
    # W2.3 descriptives: share reaching +10%, day g distribution
    sel = np.isin(ev['ticker'].values, universe(P, 'all'))
    pm = per['MAIN'] & sel & np.isfinite(ev['f20'].values)
    k10 = ev['k10'].values
    add('W2.3_detail', 'W2.3', 'all', 'MAIN', 'share of entries reaching +10% Close gain within 20 days', PCT * (k10[pm] > 0).mean(), '%', int(pm.sum()))
    add('W2.3_detail', 'W2.3', 'all', 'MAIN', 'median trigger day g-t', float(np.median(k10[pm & (k10 > 0)])), 'days', int((pm & (k10 > 0)).sum()))
    nv = per['MAIN'] & sel & (k10 > 0) & ~np.isfinite(ev['r23'].values) & np.isfinite(ev['f60'].values)
    add('W2.3_detail', 'W2.3', 'all', 'MAIN', 'triggered events dropped: no valid Open at g+1', int(nv.sum()), 'events')
    # 7. W2.5 detail
    for u in ('all', 'pre2018'):
        sel = np.isin(ev['ticker'].values, universe(P, u))
        m = sel & per['MAIN'] & np.isfinite(ev['d25'].values)
        b = ev['bars_tr'].values[m]
        add('W2.5_detail', 'W2.5', u, 'MAIN', 'trailing arm mean raw return per trade', PCT * ev['r_tr'].values[m].mean(), '%', int(m.sum()))
        add('W2.5_detail', 'W2.5', u, 'MAIN', 'fixed 20-bar arm mean raw return per trade', PCT * ev['r_fix'].values[m].mean(), '%', int(m.sum()))
        add('W2.5_detail', 'W2.5', u, 'MAIN', 'trailing arm mean bars held', b.mean(), 'bars', int(m.sum()))
        add('W2.5_detail', 'W2.5', u, 'MAIN', 'trailing arm median bars held', float(np.median(b)), 'bars', int(m.sum()))
        add('W2.5_detail', 'W2.5', u, 'MAIN', 'trailing arm share capped at 120 bars', PCT * ev['capped'].values[m].mean(), '%', int(m.sum()))
        add('W2.5_detail', 'W2.5', u, 'MAIN', 'trailing arm share exiting before bar 20', PCT * (b < 20).mean(), '%', int(m.sum()))
        add('W2.5_detail', 'W2.5', u, 'MAIN', 'trailing arm return per bar held (sum r / sum bars)',
            BPS * ev['r_tr'].values[m].sum() / b.sum(), 'bps/bar', int(m.sum()))
        add('W2.5_detail', 'W2.5', u, 'MAIN', 'fixed arm return per bar held (sum r / (20 n))',
            BPS * ev['r_fix'].values[m].sum() / (20 * m.sum()), 'bps/bar', int(m.sum()))
        add('W2.5_detail', 'W2.5', u, 'MAIN', 'abnormal trailing arm mean per trade', PCT * ev['atr_' + u].values[m].mean(), '%', int(m.sum()))
        add('W2.5_detail', 'W2.5', u, 'MAIN', 'abnormal fixed arm mean per trade', PCT * ev['afix_' + u].values[m].mean(), '%', int(m.sum()))
        add('W2.5_detail', 'W2.5', u, 'MAIN', 'share of trades where trailing beats fixed', PCT * (ev['d25'].values[m] > 0).mean(), '%', int(m.sum()))
    # 8. right tail (descriptive; informs exits). Benchmark = every stock-day entry (buy any Open) in the same period:
    # under a driftless random walk the bar of the 120-bar maximum is arcsine distributed (median ~60 bars, ~27% of
    # peaks in bars 100-120), so the timing numbers only mean something next to the benchmark.
    def tail_rows(u, k, label, f60, pkk, pkg):
        x = np.sort(f60[np.isfinite(f60)])[::-1]
        s = np.expm1(x)
        n = len(x)
        n10, n1 = int(np.ceil(.1 * n)), int(np.ceil(.01 * n))
        add('right_tail', 'fo60', u, k, 'mean simple 60-day P&L per trade (Open t+1 to Close t+60)', PCT * s.mean(), '%', n, note=label)
        add('right_tail', 'fo60', u, k, 'share of total simple 60-day P&L from top 10% of trades', PCT * s[:n10].sum() / s.sum(), '% of total', n, note=label)
        add('right_tail', 'fo60', u, k, 'share of total simple 60-day P&L from top 1% of trades', PCT * s[:n1].sum() / s.sum(), '% of total', n, note=label)
        add('right_tail', 'fo60', u, k, 'mean simple 60-day P&L excluding top 10% of trades', PCT * s[n10:].mean(), '%', n - n10, note=label)
        add('right_tail', 'fo60', u, k, 'share of trades with positive 60-day P&L', PCT * (x > 0).mean(), '%', n, note=label)
        add('right_tail', 'peak120', u, k, 'median bars to peak Close within 120 bars', float(np.median(pkk)), 'bars', len(pkk), note=label)
        add('right_tail', 'peak120', u, k, '25th percentile bars to peak Close', float(np.percentile(pkk, 25)), 'bars', len(pkk), note=label)
        add('right_tail', 'peak120', u, k, '75th percentile bars to peak Close', float(np.percentile(pkk, 75)), 'bars', len(pkk), note=label)
        add('right_tail', 'peak120', u, k, 'share of trades whose 120-bar peak is at bar 100-120', PCT * (pkk >= 100).mean(), '%', len(pkk), note=label)
        add('right_tail', 'peak120', u, k, 'median peak Close gain within 120 bars (log)', PCT * float(np.median(pkg)), '%', len(pkg), note=label)

    for u in ('all', 'pre2018'):
        sel = np.isin(ev['ticker'].values, universe(P, u))
        for label, km in (('breakout entries, all', np.ones(len(ev), bool)), ('breakout entries, first per stock in 60 days', keep)):
            for k in ('MAIN', 'P1', 'P2', 'P3', 'P4'):
                m = sel & km & per[k]
                m2 = m & np.isfinite(ev['peak_k'].values)
                tail_rows(u, k, label, ev['f60'].values[m], ev['peak_k'].values[m2], ev['peak_gain'].values[m2])
        bench = random_entries(meta, P, u)
        for k in ('MAIN', 'P1', 'P2', 'P3', 'P4'):
            m = in_period(bench['date'], *PERIODS[k])
            m2 = m & np.isfinite(bench['peak_k'])
            tail_rows(u, k, 'benchmark: every stock-day entry (buy next Open)', bench['f60'][m], bench['peak_k'][m2],
                      bench['peak_gain'][m2])
    note = 'theoretical reference (arcsine law, continuous approximation): peak timing looks like this without any edge'
    add('right_tail', 'peak120', 'reference', 'any', 'driftless random walk: median bar of the 120-bar maximum',
        CAP / 2., 'bars', note=note)
    add('right_tail', 'peak120', 'reference', 'any', 'driftless random walk: share of 120-bar maxima at bar 100-120',
        PCT * (1 - 2 / np.pi * np.arcsin(np.sqrt(99.5 / CAP))), '%', note=note)
    # 9. index-day sensitivity: aggregate by the decision day (t+5, t+20) or trigger day g instead of the signal day t
    for u in ('all', 'pre2018'):
        r = R[u]
        for tid, off in (('W2.1', 5), ('W2.2', 20)):
            up, dn, v = r[tid]['up'], r[tid]['dn'], r[tid]['v']
            st = Diff(day_series(i[up] + off, v[up], index), day_series(i[dn] + off, v[dn], index), LAGS[tid])
            e, t, n = st.at(*MAIN)
            add('index_sensitivity', tid, u, 'MAIN', f'primary statistic aggregated by decision day t+{off}', PCT * e, '%', n, t)
        m, v = r['W2.3']['m'], r['W2.3']['v']
        st = Mean(day_series(i[m] + ev['k10'].values[m], v[m], index), LAGS['W2.3'])
        e, t, n = st.at(*MAIN)
        add('index_sensitivity', 'W2.3', u, 'MAIN', 'primary statistic aggregated by trigger day g', PCT * e, '%', n, t)
    # 10. W2.5 by calendar year (day-mean of the paired difference; raw and abnormal)
    yr = dates.dt.year.values
    for u in ('all', 'pre2018'):
        sel = np.isin(ev['ticker'].values, universe(P, u))
        for basis, col in (('raw', 'd25'), ('abnormal', 'ad25_' + u)):
            v = ev[col].values
            m = sel & np.isfinite(v)
            s = day_series(i[m], v[m], index)
            for y in range(2000, 2026):
                sy = s[s.index.year == y]
                ny = int((m & (yr == y)).sum())
                if ny:
                    add('W2.5_by_year', 'W2.5', u, str(y), f'{basis} paired difference trailing minus fixed-20 (day-mean)',
                        PCT * sy.mean(), '%', ny)
    return pd.DataFrame(C)


def random_entries(meta, P, univ):
    """Every stock-day t with a valid Open at t+1 and a full 120-bar window: 60-day P&L and the bar of the 120-bar
    peak Close (benchmark for the right-tail table)."""
    from numpy.lib.stride_tricks import sliding_window_view
    LP, LO, N, idx = meta['LP'], meta['LO'], meta['N'], meta['idx']
    t_all = np.arange(N - 60)                                         # t + 60 <= N - 1 (60-day P&L)
    out = dict(date=[], f60=[], peak_k=[], peak_gain=[])
    for j in np.nonzero(np.isin(meta['cols'], universe(P, univ)))[0]:
        x = LP[:, j]
        ent = LO[t_all + 1, j]
        f60 = x[t_all + 60] - ent
        ok = np.isfinite(f60)
        t = t_all[ok]
        pk, pg = np.full(len(t), np.nan), np.full(len(t), np.nan)
        win = sliding_window_view(x, CAP)                               # win[r] = x[r : r + CAP]
        full = t + CAP <= N - 1                                         # peak needs the full 120-bar window
        w = win[t[full] + 1]
        okw = np.isfinite(w).all(1)
        pk[np.nonzero(full)[0][okw]] = w[okw].argmax(1) + 1.
        pg[np.nonzero(full)[0][okw]] = w[okw].max(1) - ent[ok][full][okw]
        out['date'].append(idx[t].values)
        out['f60'].append(f60[ok])
        out['peak_k'].append(pk)
        out['peak_gain'].append(pg)
    out = {k: np.concatenate(v) for k, v in out.items()}
    out['date'] = pd.DatetimeIndex(out['date'])
    return out


# ----------------------------------------------------------------------------------------------- exploratory
def exploratory(ev, meta, P, index):
    """Motivated by W2.5: the trailing arm holds 31 bars on average versus 20, so part of its per-trade edge can be
    plain extra time in a rising (survivor) market. Control: the same trades held a fixed 31 bars (the MAIN mean
    holding of the trailing arm, rounded). Not classified."""
    i = ev['i'].values
    full = ev['full120'].values
    m_all = np.isin(ev['ticker'].values, universe(P, 'all')) & in_period(ev['date'], *MAIN).values
    mean_bars = np.nanmean(ev['bars_tr'].values[m_all & np.isfinite(ev['d25'].values)])
    stats = {}
    fw = ev['fullwin'].values
    for u in ('all', 'pre2018'):
        sel = np.isin(ev['ticker'].values, universe(P, u)) & full
        raw = ev['r_tr'].values - ev['f31'].values
        ab = ev['atr_' + u].values - ev['af31_' + u].values
        for key, v in (('raw', raw), ('ab', ab)):
            for sub, km in (('', np.ones(len(ev), bool)), ('_liq', fw)):
                m = sel & km & np.isfinite(v)
                stats[(key + sub, u)] = Mean(day_series(i[m], v[m], index), LAGS['W2.5'])
        stats[('n', u)] = int((sel & np.isfinite(raw) & in_period(ev['date'], *MAIN).values).sum())
    note = (f'Control for time in market: trailing-arm mean holding in MAIN = {mean_bars:.1f} bars -> fixed 31-bar '
            f'hold (lnP[t+31]-lnO[t+1]) on the same W2.5 trades (full 120-bar window); events MAIN {stats[("n", "all")]}; '
            'NW lags 20 as W2.5; exploratory, not classified (31 bars is taken from the data).')
    rows = []
    for xid, key, desc in (('X-W2-1', 'raw', 'raw paired per-trade difference'),
                           ('X-W2-2', 'ab', 'abnormal paired per-trade difference (each arm minus its same-window EW '
                                            'universe mean)')):
        e, t, n = stats[(key + '_liq', 'all')].at(*MAIN)
        e4, t4, _ = stats[(key + '_liq', 'all')].at(*PERIODS['P4'])
        e_all = stats[(key, 'all')].at(*MAIN)[0]
        risk = 'medium' if (np.sign(e) == np.sign(e_all) and abs(e) >= LIQ_RATIO * abs(e_all)) else 'high'
        liq = (f' Entries with a fully tradable 20-day lookback: {PCT * e:.2f}% (t {t:.2f}), P4 {PCT * e4:.2f}% '
               f'(t {t4:.2f}); survivorship label by the same 2/3 rule as the primary rows.')
        rows.append(row(xid, FAM, 'W2.5 entries: trailing exit (10-bar low, next Open, cap 120) minus fixed 31-bar hold '
                        f'(lnP[t+31]); {desc}', '%', stats[(key, 'all')], stats[(key, 'pre2018')], scale=PCT,
                        cost_note='One round trip in both arms (costs cancel per trade).', surv_risk=risk,
                        exploit='timing', notes=note + liq))
    return pd.DataFrame(rows)


if __name__ == '__main__':
    main()
