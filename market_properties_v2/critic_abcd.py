"""Adversarial critic of the exploratory claims the main session drew from families A-D (claims C-a .. C-g).
NOT pre-registered: written after seeing results/{A,B,C,D}_tests.csv, ABCD_exploratory.csv and D_topex_exploratory.csv.
Every test tries to refute a claim with an artifact of the data source (back-adjusted prices, opening/closing print
conventions, stale prints, zero-volume days, 2025 Kompas100 membership) or with an alternative explanation.
Writes results/critic_ABCD.csv in long format: claim, test, subset, period, stat, value, t, n, note.
Conventions as in PLAN.md: event tests average per day first, NW t (lags 5 daily, h for h-day windows, 2 for monthly
sorts); abnormal = minus the same-day equal-weight mean of the universe. External facts used (from press reports found
by web search, not verified against IDX primary rules): IDX pre-opening and pre-closing call auctions were limited to
LQ45 constituents until they were extended to Main/New-Economy/Development board stocks on 9 Dec 2024; the lower
auto-rejection limit was 7% from Mar 2020 to about mid 2023. LQ45 membership is not in the data: the proxy is the top 40
panel stocks by 250-day mean traded value known before the day.
Resumed run (extensions at the end of the file, tests a10-a11, b4-b7, c5-c7, d5-d7, e5, f4-f6, g5): a data-driven tick
(smallest price step in the previous 20 days, valid on back-adjusted prices) replaces the modern tick table where the
tick matters; the auction timeline was refined (pre-opening LQ45-only since 18 May 2009 with suspensions 13 Oct 2008 -
15 May 2009 and 13 Mar - 4 Sep 2020; pre-closing call auction from 2 Jan 2013), see the comment above ext_a.
Run: python market_properties_v2/critic_abcd.py (about 1.5 minutes)"""
import math
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel import load, universe, SUBPERIODS, MAIN, P0
from mpstats import nw, ols_nw, Dummy, Mean, Diff, event_series, rebalance_dates

T0 = time.time()
P = load()
OUT = HERE / 'results' / 'critic_ABCD.csv'
PERS = {'MAIN': MAIN, **SUBPERIODS}
ROWS = []

O, H, L, C, V, T = (P[k] for k in ['O', 'H', 'L', 'C', 'V', 'T'])
ron, rid, rcc = P['r_on'], P['r_id'], P['r_cc']
lnP, lnH, lnL, lnOn = P['lnP'], P['lnH'], P['lnL'], P['lnO'].shift(-1)
CAL = C.index
ALL = list(C.columns)
PRE = universe(P, 'pre2018')
prevC = C.where(T).ffill().shift(1)
AB_ID = rid.sub(rid.mean(axis=1), axis=0)                       # abnormal intraday (Open->Close)
GD = (ron < np.log(.98)) & rid.notna()
GU = (ron > np.log(1.02)) & rid.notna()
LIQ60 = P['value'].rolling(60, min_periods=40).mean()
LR = LIQ60.shift(1).rank(axis=1, pct=True)                       # liquidity percentile known before day t
LIQ250 = P['value'].rolling(250, min_periods=120).mean().shift(1)
LQ_PROXY = LIQ250.rank(axis=1, ascending=False) <= 40           # LQ45 proxy (approximate, see docstring)
REST = ~LQ_PROXY & LIQ250.notna()
AUCTION_EXT = '2024-12-09'                                       # auctions extended beyond LQ45 (press reports)


def frame(x):
    return pd.DataFrame(x, index=CAL, columns=C.columns)


def tick(price):
    """Current IDX price fractions applied to (back-adjusted) prices: counterfactual before ~2017."""
    p = np.asarray(price, float)
    return np.select([p < 200, p < 500, p < 2000, p < 5000], [1, 2, 5, 10], 25).astype(float)


def isclose(a, b):
    return frame(np.isclose(a.values, b.values, rtol=1e-9, atol=0))


REL_TICK = frame(tick(prevC.values)) / prevC                     # relative tick of the previous Close (known at Open)
OPEN_LOW, OPEN_HIGH = isclose(O, L), isclose(O, H)
CLOSE_HIGH, CLOSE_LOW = isclose(C, H), isclose(C, L)
OPEN_PREV = frame(np.isclose(O.values, prevC.values, rtol=0, atol=1e-9))


def add(claim, test, subset, period, stat, value, t=np.nan, n=np.nan, note=''):
    f = lambda x: float(x) if x is not None and np.isfinite(x) else np.nan
    ROWS.append(dict(claim=claim, test=test, subset=subset, period=period, stat=stat, value=f(value), t=f(t),
                     n=n, note=note))


def dw(mask, ser=AB_ID, a=MAIN[0], b=MAIN[1], lags=5, scale=1e4):
    """Day-weighted mean of ser over the events in mask (average per day first), NW t, number of events."""
    s = ser.loc[a:b]
    m_ = mask.reindex_like(s).fillna(False).astype(bool) & s.notna()
    d = s.where(m_).mean(axis=1)
    m, se, _ = nw(d.values, lags)
    return m * scale, (m / se if se and se > 0 else np.nan), int(m_.values.sum())


def daily(mask, ser=AB_ID):
    m_ = mask.reindex_like(ser).fillna(False).astype(bool) & ser.notna()
    return ser.where(m_).mean(axis=1)


def evw(mask, ser, a, b, scale=1e4):
    """Event-weighted values (finite) of ser on mask in [a, b]."""
    x = ser.loc[a:b].where(mask.reindex_like(ser.loc[a:b]).fillna(False).astype(bool)).values
    x = x[np.isfinite(x)]
    return x * scale


def ew_day(fr):
    return fr.mean(axis=1)


def vw_day(fr, w):
    ww = w.reindex_like(fr).where(fr.notna())
    return (fr * ww).sum(axis=1, min_count=1) / ww.sum(axis=1, min_count=1)


def mean_t(series, a, b, lags, scale):
    m, se, n = nw(series.loc[a:b].values, lags)
    return m * scale, (m / se if se and se > 0 else np.nan), n


def diff_t(m1, se1, m2, se2):
    return (m1 - m2) / math.sqrt(se1 ** 2 + se2 ** 2)


# ------------------------------------------------------------------------------------------------- C-a gap reversal
def claim_a():
    cl = 'C-a'
    # a1: replicate B3/B4 by period and universe (abnormal day-weighted; raw event-weighted)
    for u, cols in [('all', ALL), ('pre2018', PRE)]:
        ab_u = rid[cols].sub(rid[cols].mean(axis=1), axis=0)
        for lab, ev in [('gap_up', GU[cols]), ('gap_down', GD[cols])]:
            for k, (a, b) in {**PERS, 'P0': P0}.items():
                m, t, n = dw(ev, ab_u, a, b)
                add(cl, 'a1_replicate_B3_B4', f'{lab}_{u}', k, 'abnormal_intraday_bps', m, t, n)
                if u == 'all':
                    x = evw(ev, rid, a, b)
                    add(cl, 'a1_replicate_B3_B4', f'{lab}_{u}', k, 'raw_intraday_bps_event_weighted', x.mean(), n=len(x))
    # a2: monotonicity in the overnight return, per period (log r_on buckets as in X-B4-f)
    edges = [-9, -.04, -.02, -.005, .005, .02, .04, 9]
    for k, (a, b) in PERS.items():
        means = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m, t, n = dw((ron >= lo) & (ron < hi), AB_ID, a, b)
            means.append(m)
            add(cl, 'a2_monotonic', f'r_on_{lo}_{hi}', k, 'abnormal_intraday_bps', m, t, n)
        add(cl, 'a2_monotonic', 'all_buckets', k, 'monotonic_decreasing_1yes', float(all(np.diff(means) < 0)))
    # a3: year by year
    for y in range(2000, 2026):
        for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
            m, t, n = dw(ev, AB_ID, f'{y}-01-01', f'{y}-12-31')
            add(cl, 'a3_by_year', lab, str(y), 'abnormal_intraday_bps', m, t, n)
    # a4: the Open==Low / Open==High split conditions on the day's own Low/High (look-ahead): mechanical benchmark
    ng = (ron.abs() < np.log(1.005)) & rid.notna()
    for k, (a, b) in [('MAIN', MAIN), ('P4', SUBPERIODS['P4'])]:
        for lab, ev, ext, nm in [('nongap', ng, OPEN_LOW, 'open==low'), ('gap_down', GD, OPEN_LOW, 'open==low'),
                                 ('nongap', ng, OPEN_HIGH, 'open==high'), ('gap_up', GU, OPEN_HIGH, 'open==high')]:
            for side, msk in [(nm, ev & ext), ('not_' + nm, ev & ~ext)]:
                m, t, n = dw(msk, AB_ID, a, b)
                add(cl, 'a4_open_extreme_mechanical', f'{lab}_{side}', k, 'abnormal_intraday_bps', m, t, n,
                    'conditions on the same day Low/High: not tradable; compare with the nongap baseline')
            sh = (ev & ext).loc[a:b].values.sum() / ev.loc[a:b].values.sum()
            add(cl, 'a4_open_extreme_mechanical', f'{lab}_{nm}', k, 'share_of_days', sh)
        for lab, ev, ext, base_ev in [('gap_down', GD, OPEN_LOW, ng), ('gap_up', GU, OPEN_HIGH, ng)]:
            for side, f in [('extreme', lambda e: e), ('not_extreme', lambda e: ~e)]:
                m, t, n = Diff(daily(ev & f(ext)), daily(base_ev & f(ext)), 5).at(a, b)
                add(cl, 'a4_open_extreme_mechanical', f'{lab}_{side}_minus_nongap_{side}', k, 'excess_bps', m * 1e4, t, n,
                    'gap effect net of the mechanical Open==Low/High selection')
    # a5: liquidity tercile x relative tick (modern ticks on adjusted prices: only P4 close to real ticks)
    liq_b = {'liqL': (0, 1 / 3), 'liqM': (1 / 3, 2 / 3), 'liqH': (2 / 3, 1.01)}
    tick_b = {'tick<0.4%': (0, .004), 'tick0.4-1%': (.004, .01), 'tick>=1%': (.01, 9)}
    for k in ['MAIN', 'P2', 'P3', 'P4']:
        a, b = PERS[k]
        for ln, (l0, l1) in liq_b.items():
            for tn, (t0, t1) in tick_b.items():
                cell = (LR > l0) & (LR <= l1) & (REL_TICK >= t0) & (REL_TICK < t1)
                for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
                    m, t, n = dw(ev & cell, AB_ID, a, b)
                    add(cl, 'a5_liquidity_x_tick', f'{lab}_{ln}_{tn}', k, 'abnormal_intraday_bps', m, t, n)
                    m, t, n = dw(ev & cell, rid, a, b)
                    add(cl, 'a5_liquidity_x_tick', f'{lab}_{ln}_{tn}', k, 'raw_intraday_bps', m, t, n)
    a, b = SUBPERIODS['P4']
    for ln, (l0, l1) in liq_b.items():
        for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
            m, t, n = dw(ev & (LR > l0) & (LR <= l1), AB_ID / REL_TICK, a, b, scale=1)
            add(cl, 'a5_liquidity_x_tick', f'{lab}_{ln}', 'P4', 'abnormal_intraday_in_ticks', m, t, n,
                'reversal measured in units of the (real, P4) tick of the previous Close')
    # a6: stale / odd print conditions
    prev_tr = T.shift(1).fillna(False).astype(bool)
    vmed = V.where(T).rolling(60, min_periods=20).median().shift(1)
    vr = V / vmed
    vr_prev = vr.shift(1)
    pch, pcl = CLOSE_HIGH.shift(1).fillna(False).astype(bool), CLOSE_LOW.shift(1).fillna(False).astype(bool)
    single = isclose(O, H) & isclose(L, C) & isclose(O, C)
    splits = {'prev_market_day_not_tradable': ~prev_tr, 'prev_market_day_tradable': prev_tr,
              'gapday_vol<0.2xmedian60': vr < .2, 'gapday_vol0.2-1x': (vr >= .2) & (vr < 1), 'gapday_vol>=1x': vr >= 1,
              'prevday_vol<0.2xmedian60': vr_prev < .2, 'prevday_vol>=0.2x': vr_prev >= .2,
              'prev_close==prev_high': pch, 'prev_close==prev_low': pcl, 'prev_close_inside_range': ~pch & ~pcl}
    for k in ['MAIN', 'P4']:
        a, b = PERS[k]
        for nm, msk in splits.items():
            for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
                m, t, n = dw(ev & msk, AB_ID, a, b)
                add(cl, 'a6_stale_print_splits', f'{lab}_{nm}', k, 'abnormal_intraday_bps', m, t, n)
        for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
            add(cl, 'a6_stale_print_splits', f'{lab}_single_price_day', k, 'events',
                int((ev & single).loc[a:b].values.sum()), note='O=H=L=C gives r_id=0, cannot create a reversal')
    # a7: lower auto-rejection limit (7%, ~Mar 2020 - mid 2023): gap-down opens at the limit
    w0, w1 = '2020-04-01', '2023-05-31'
    arb = (ron < np.log(.935)) & (ron >= np.log(.925))
    gd_w = GD.loc[w0:w1]
    add(cl, 'a7_ARB_7pct', 'gap_down_open_in_[-7.5%,-6.5%)', f'{w0}..{w1}', 'share_of_gap_downs',
        (gd_w & arb.loc[w0:w1]).values.sum() / gd_w.values.sum(), n=int(gd_w.values.sum()))
    x = np.expm1(ron.loc[w0:w1].where(GD.loc[w0:w1]).values)
    x = x[np.isfinite(x)]
    for lo, hi in [(-.075, -.07), (-.07, -.065), (-.065, -.06)]:
        add(cl, 'a7_ARB_7pct', f'gap_down_simple_r_on_[{lo},{hi})', f'{w0}..{w1}', 'events', int(((x >= lo) & (x < hi)).sum()))
    for nm, msk in [('at_limit', GD & arb), ('other_gap_down', GD & ~arb)]:
        m, t, n = dw(msk, AB_ID, w0, w1)
        add(cl, 'a7_ARB_7pct', nm, f'{w0}..{w1}', 'abnormal_intraday_bps', m, t, n)
    # a8: the eight largest names
    big = ['BBCA', 'BBRI', 'BMRI', 'TLKM', 'ASII', 'BBNI', 'UNVR', 'ICBP']
    mb = frame(np.zeros(C.shape, bool))
    mb[big] = True
    for k, (a, b) in PERS.items():
        for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
            m, t, n = dw(ev & mb, AB_ID, a, b)
            add(cl, 'a8_big8_names', lab, k, 'abnormal_intraday_bps', m, t, n, ','.join(big))
    # a9: natural experiment: opening/closing auctions extended from LQ45 to all main-board stocks on 9 Dec 2024
    pre_w, post_w = ('2023-01-01', '2024-12-06'), (AUCTION_EXT, MAIN[1])
    res = {}
    for grp_name, grp in [('LQ45proxy_top40', LQ_PROXY), ('rest', REST)]:
        for wl, (a, b) in [('2023-01..2024-12-06', pre_w), ('2024-12-09..2025-08-15', post_w)]:
            for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
                for sn, ser in [('abnormal', AB_ID), ('raw', rid)]:
                    s = daily(ev & grp, ser).loc[a:b]
                    m, se, n = nw(s.values, 5)
                    res[(grp_name, wl, lab, sn)] = (m, se)
                    add(cl, 'a9_auction_extension_Dec2024', f'{lab}_{grp_name}', wl, f'{sn}_intraday_bps', m * 1e4,
                        m / se if se else np.nan, int((ev & grp).loc[a:b].values.sum()))
        for lab in ['gap_up', 'gap_down']:
            (m0, s0), (m1, s1) = res[(grp_name, '2023-01..2024-12-06', lab, 'abnormal')], res[(grp_name, '2024-12-09..2025-08-15', lab, 'abnormal')]
            add(cl, 'a9_auction_extension_Dec2024', f'{lab}_{grp_name}', 'post_minus_pre', 'abnormal_intraday_bps',
                (m1 - m0) * 1e4, diff_t(m1, s1, m0, s0))
    # placebo split dates: 8 months before vs 8 months after, non-LQ45 proxy
    for split in ['2023-06-01', '2023-12-01', '2024-06-03', AUCTION_EXT]:
        sd = pd.Timestamp(split)
        a0, b0 = str((sd - pd.DateOffset(months=8)).date()), str((sd - pd.Timedelta(days=1)).date())
        a1, b1 = split, str((sd + pd.DateOffset(months=8)).date())
        for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
            s = daily(ev & REST)
            m0, se0, _ = nw(s.loc[a0:b0].values, 5)
            m1, se1, _ = nw(s.loc[a1:b1].values, 5)
            add(cl, 'a9_placebo_split_dates', f'{lab}_rest', split, 'after_minus_before_abnormal_bps', (m1 - m0) * 1e4,
                diff_t(m1, se1, m0, se0), note=f'before {m0 * 1e4:.0f} bps, after {m1 * 1e4:.0f} bps (8-month windows)')
    # post window without the Mar-Apr 2025 turmoil
    for grp_name, grp in [('LQ45proxy_top40', LQ_PROXY), ('rest', REST)]:
        for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
            s = daily(ev & grp).loc[post_w[0]:post_w[1]]
            s = s.drop(s.loc['2025-03-01':'2025-04-30'].index)
            m, se, n = nw(s.values, 5)
            add(cl, 'a9_auction_extension_Dec2024', f'{lab}_{grp_name}', 'post_excl_2025-03..04', 'abnormal_intraday_bps',
                m * 1e4, m / se if se else np.nan)
    # year by year for the two groups
    for y in range(2016, 2025):
        b = f'{y}-12-06' if y == 2024 else f'{y}-12-31'
        for grp_name, grp in [('LQ45proxy_top40', LQ_PROXY), ('rest', REST)]:
            for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
                m, t, n = dw(ev & grp, AB_ID, f'{y}-01-01', b)
                add(cl, 'a9_groups_by_year', f'{lab}_{grp_name}', str(y), 'abnormal_intraday_bps', m, t, n)


# ------------------------------------------------------------------------------------------------- C-b cost model and rules
def claim_b():
    cl = 'C-b'
    tkO, tkC = frame(tick(O.values)), frame(tick(C.values))
    ev = GD
    rel = tkO / O
    for k, (a, b) in PERS.items():
        x = evw(ev, rel, a, b, scale=100)
        add(cl, 'b1_relative_tick_gap_down', 'buy_side_tick_over_open', k, 'mean_pct', x.mean(), n=len(x))
        add(cl, 'b1_relative_tick_gap_down', 'buy_side_tick_over_open', k, 'median_pct', np.median(x), n=len(x))
        add(cl, 'b1_relative_tick_gap_down', 'buy_side_tick_over_open', k, 'p90_pct', np.quantile(x, .9), n=len(x))
        add(cl, 'b1_relative_tick_gap_down', 'buy_side_tick_over_open', k, 'share_above_2pct', (x > 2).mean(), n=len(x))
        add(cl, 'b1_relative_tick_gap_down', 'adjusted_open<50', k, 'events', int((ev & (O < 50)).loc[a:b].values.sum()))
        off = evw(ev, frame((np.abs(O.values - np.round(O.values)) > 1e-6).astype(float)), a, b, scale=1)
        add(cl, 'b1_relative_tick_gap_down', 'open_not_integer(back-adjusted)', k, 'share', off.mean(), n=len(off))
    sellC = (C - tkC).where(C - tkC > 0)
    models = {
        'M0_gross': np.log(C / O),
        'M1_fee_only(.15%+.25%)': np.log(C * .9975 / (O * 1.0015)),
        'M2_fee+0.25%slip_per_side': np.log(C * .9975 * .9975 / (O * 1.0025 * 1.0015)),
        'M3_fee+1tick_per_side': np.log(sellC * .9975 / ((O + tkO) * 1.0015)),
        'M5_fee+0.5tick_per_side': np.log((C - .5 * tkC) * .9975 / ((O + .5 * tkO) * 1.0015)),
        'M4_main_session(fee+1tick+0.25%/side)': np.log(sellC * .9975 * .9975 / ((O + tkO) * 1.0025 * 1.0015)),
    }
    for k, (a, b) in PERS.items():
        for nm, net in models.items():
            x = evw(ev, net, a, b)
            add(cl, 'b2_net_per_trade_gap_down', nm, k, 'event_weighted_mean_bps', x.mean(), n=len(x))
            add(cl, 'b2_net_per_trade_gap_down', nm, k, 'event_weighted_median_bps', np.median(x), n=len(x))
            m, t, n = dw(ev, net, a, b)
            add(cl, 'b2_net_per_trade_gap_down', nm, k, 'day_weighted_mean_bps', m, t, n)
        x = evw(ev & (rel <= .01), models['M4_main_session(fee+1tick+0.25%/side)'], a, b)
        add(cl, 'b2_net_per_trade_gap_down', 'M4_main_session_only_reltick<=1%', k, 'event_weighted_mean_bps', x.mean(), n=len(x))
        g = evw(ev, models['M0_gross'], a, b).mean()
        rt = evw(ev, rel, a, b, scale=1e4).mean()
        be = (g - 40) / 2
        add(cl, 'b2_net_per_trade_gap_down', 'break_even', k, 'spread_impact_allowance_per_side_bps', be,
            note=f'= (gross {g:.0f} - fees 40) / 2; mean tick {rt:.0f} bps -> {be / rt:.2f} ticks per side')
    a, b = SUBPERIODS['P4']
    cell = (LR > 2 / 3) & (REL_TICK < .004)
    for nm in ['M0_gross', 'M1_fee_only(.15%+.25%)', 'M3_fee+1tick_per_side']:
        m, t, n = dw(ev & cell, models[nm], a, b)
        add(cl, 'b2_net_per_trade_gap_down', f'{nm}_liqH_tick<0.4%', 'P4', 'day_weighted_mean_bps', m, t, n)
    # b3: execution rules evaluated in system-like contexts (raw intraday return on the event day)
    brk = (lnP > lnH.shift(1).rolling(20, min_periods=20).max()) & T          # W1.1 breakout at Close t
    er20 = (lnP - lnP.shift(20)).abs() / lnP.diff().abs().rolling(20).sum()
    Pc = np.exp(lnP)
    sma30 = Pc.rolling(30, min_periods=30).mean()
    cross_dn = (Pc < sma30) & (Pc.shift(1) >= sma30.shift(1)) & T              # first Close below SMA30
    llv10 = (lnP < lnL.shift(1).rolling(10, min_periods=10).min()) & T          # Close below prior 10-day low
    sh = lambda m: m.shift(1).fillna(False).astype(bool)                        # signal at t-1, action on day t
    ctx_buy = {'all_gap_up': GU, 'after_breakout_HHV20': GU & sh(brk), 'after_breakout_HHV20_ER20>=0.3': GU & sh(brk & (er20 >= .3)),
               'non_gap_after_breakout(ref)': sh(brk) & ~GU & ~GD & rid.notna()}
    ctx_sell = {'all_gap_down': GD, 'after_close_cross_below_SMA30': GD & sh(cross_dn), 'after_close_below_LLV10': GD & sh(llv10),
                'non_gap_after_SMA30_cross(ref)': sh(cross_dn) & ~GU & ~GD & rid.notna()}
    pers_b = {**PERS, 'pre_auction_ext_2023-01..2024-12-06': ('2023-01-01', '2024-12-06'),
              'post_auction_ext_2024-12-09..': (AUCTION_EXT, MAIN[1])}
    for rule, ctxs, sgn, note in [('rule_buy_gapup_at_Close_not_Open', ctx_buy, -1, 'benefit = -raw r_id (buy at Close instead of Open)'),
                                  ('rule_sell_gapdown_at_Close_not_Open', ctx_sell, 1, 'benefit = +raw r_id (sell at Close instead of Open)')]:
        for cn, msk in ctxs.items():
            for k, (a, b) in pers_b.items():
                m, t, n = dw(msk, rid, a, b)
                add(cl, 'b3_' + rule, cn, k, 'benefit_bps_day_weighted', sgn * m, sgn * t, n, note)
            x = evw(msk, rid, *MAIN)
            if len(x):
                add(cl, 'b3_' + rule, cn, 'MAIN', 'raw_r_id_p05_bps', np.quantile(x, .05), n=len(x))
                add(cl, 'b3_' + rule, cn, 'MAIN', 'raw_r_id_p95_bps', np.quantile(x, .95), n=len(x))
                add(cl, 'b3_' + rule, cn, 'MAIN', 'share_raw_r_id_below_-5pct', (x < -500).mean(), n=len(x))
        for cn, msk in [('liqH_tick<0.4%', (GU if sgn < 0 else GD) & (LR > 2 / 3) & (REL_TICK < .004))]:
            m, t, n = dw(msk, rid, *SUBPERIODS['P4'])
            add(cl, 'b3_' + rule, cn, 'P4', 'benefit_bps_day_weighted', sgn * m, sgn * t, n, note)
    # does a gap-up entry after a breakout have a worse follow-through? abnormal from the entry Open / from the Close
    F20 = P['fo'][20]
    ab_open = F20.sub(F20.mean(axis=1), axis=0).shift(1)                       # row t: lnP[t+19]-lnO[t], abnormal
    fromC = (lnP.shift(-19) - lnP)
    ab_close = fromC.sub(fromC.mean(axis=1), axis=0)                           # row t: lnP[t+19]-lnP[t], abnormal
    for cn, msk in [('breakout_entry_gap_up', GU & sh(brk)), ('breakout_entry_no_gap', sh(brk) & ~GU & ~GD & rid.notna())]:
        for sn, ser in [('abnormal_20d_from_entry_Open_pct', ab_open), ('abnormal_19d_from_entry_day_Close_pct', ab_close)]:
            m, t, n = dw(msk, ser, *MAIN, lags=20, scale=100)
            add(cl, 'b3_breakout_followthrough', cn, 'MAIN', sn, m, t, n)


# ------------------------------------------------------------------------------------------------- C-c overnight vs intraday
def claim_c():
    cl = 'C-c'
    first = P['first']
    cohort = [c for c in ALL if first[c] < pd.Timestamp('2005-01-01')]
    on0 = ron.ne(0) & ron.notna()
    for y in range(2000, 2026):
        a, b = f'{y}-01-01', f'{y}-12-31'
        for leg, fr in [('overnight', ron), ('intraday', rid)]:
            m, t, n = mean_t(ew_day(fr), a, b, 5, 1e4)
            add(cl, 'c1_by_year', f'{leg}_EW_all', str(y), 'bps_per_day', m, t, n)
            for ln, (l0, l1) in {'liqL': (0, 1 / 3), 'liqM': (1 / 3, 2 / 3), 'liqH': (2 / 3, 1.01)}.items():
                m, t, n = mean_t(ew_day(fr.where((LR > l0) & (LR <= l1))), a, b, 5, 1e4)
                add(cl, 'c1_by_year', f'{leg}_EW_{ln}', str(y), 'bps_per_day', m, t, n)
            m, t, n = mean_t(ew_day(fr[cohort]), a, b, 5, 1e4)
            add(cl, 'c1_by_year', f'{leg}_EW_cohort_first_bar<2005', str(y), 'bps_per_day', m, t, n, f'{len(cohort)} stocks')
            m, t, n = mean_t(fr.median(axis=1), a, b, 5, 1e4)
            add(cl, 'c1_by_year', f'{leg}_cross_sectional_median', str(y), 'bps_per_day', m, t, n)
        m, t, n = mean_t(ew_day(rid.where(on0)), a, b, 5, 1e4)
        add(cl, 'c1_by_year', 'intraday_EW_excluding_Open==prevClose_days', str(y), 'bps_per_day', m, t, n)
        Tt = (T & prevC.notna()).loc[a:b]
        for nm, msk in [('Open==prevClose', OPEN_PREV), ('Open==High', OPEN_HIGH), ('Open==Low', OPEN_LOW),
                        ('Close==High', CLOSE_HIGH), ('Close==Low', CLOSE_LOW)]:
            add(cl, 'c2_print_shares_by_year', nm, str(y), 'share_of_tradable_days', (msk.loc[a:b] & Tt).values.sum() / Tt.values.sum())
        for ln, (l0, l1) in {'liqL': (0, 1 / 3), 'liqH': (2 / 3, 1.01)}.items():
            g = Tt & ((LR > l0) & (LR <= l1)).loc[a:b]
            d1 = ((CLOSE_HIGH.loc[a:b] & g).values.sum() - (CLOSE_LOW.loc[a:b] & g).values.sum()) / g.values.sum()
            d2 = ((OPEN_HIGH.loc[a:b] & g).values.sum() - (OPEN_LOW.loc[a:b] & g).values.sum()) / g.values.sum()
            add(cl, 'c2_print_shares_by_year', f'Close==High_minus_Close==Low_{ln}', str(y), 'share_difference', d1)
            add(cl, 'c2_print_shares_by_year', f'Open==High_minus_Open==Low_{ln}', str(y), 'share_difference', d2)
    for k, (a, b) in {**PERS, '2016-2025': ('2016-01-01', MAIN[1])}.items():
        for leg, fr in [('overnight', ron), ('intraday', rid)]:
            m, t, n = mean_t(vw_day(fr, LIQ60.shift(1)), a, b, 5, 1e4)
            add(cl, 'c3_value_weighted', leg, k, 'bps_per_day', m, t, n, 'weights: 60-day mean traded value at t-1')
    # auction regime: the split in LQ45 proxy (auctions throughout) and the rest, before/after 9 Dec 2024
    for grp_name, grp in [('LQ45proxy_top40', LQ_PROXY), ('rest', REST)]:
        for wl, (a, b) in [('2023-01..2024-12-06', ('2023-01-01', '2024-12-06')), ('2024-12-09..2025-08-15', (AUCTION_EXT, MAIN[1]))]:
            for leg, fr in [('overnight', ron), ('intraday', rid)]:
                m, t, n = mean_t(ew_day(fr.where(grp)), a, b, 5, 1e4)
                add(cl, 'c4_auction_regime', f'{leg}_{grp_name}', wl, 'bps_per_day', m, t, n)
            g = (T & prevC.notna() & grp).loc[a:b]
            add(cl, 'c4_auction_regime', f'Open==prevClose_{grp_name}', wl, 'share', (OPEN_PREV.loc[a:b] & g).values.sum() / g.values.sum())


# ------------------------------------------------------------------------------------------------- C-d trend persistence
def tsmom_series(k, h, cols=ALL, fwd='fo', demean=False, vw=False, nonzero=False):
    past = rcc if k == 1 else lnP - lnP.shift(k)
    s = np.sign(past[cols]).where(T[cols])
    y = P[fwd][h][cols] if isinstance(fwd, str) else fwd[cols]
    if demean:
        y = y.sub(y.mean(axis=1), axis=0)
    ok = s.notna() & y.notna()
    if nonzero:
        ok &= s != 0
    prod = (s * y).where(ok)
    return vw_day(prod, LIQ60[cols]) if vw else prod.mean(axis=1)


def claim_d():
    cl = 'C-d'
    # d1: the 1-day signal split into the legs of day t+1
    legs = {'next_overnight_r_on[t+1]': ron.shift(-1), 'next_intraday_fo[1](=A1.1)': P['fo'][1], 'next_close_close_fc[1]': P['fc'][1]}
    for ln, y in legs.items():
        for var, kw in [('raw', {}), ('xs_demeaned', {'demean': True})]:
            ser = tsmom_series(1, 1, fwd=y, **kw)
            for k, (a, b) in PERS.items():
                m, t, n = mean_t(ser, a, b, 5, 1e4)
                add(cl, 'd1_tsmom1_legs', f'{ln}_{var}', k, 'bps_per_day', m, t, n)
    # d2: horizons x variants
    for (k_, h) in [(1, 1), (5, 5), (10, 10), (20, 20), (60, 20)]:
        lags = max(5, h)
        scale, unit = (1e4, 'bps') if h == 1 else (100, 'pct_per_window')
        variants = {'raw_EW': {}, 'close_based_fc': {'fwd': 'fc'}, 'xs_demeaned': {'demean': True},
                    'value_weighted': {'vw': True}, 'pre2018': {'cols': PRE}, 'nonzero_signal_only': {'nonzero': True}}
        for vn, kw in variants.items():
            ser = tsmom_series(k_, h, **kw)
            for k, (a, b) in {**PERS, '2016-2019': ('2016-01-01', '2019-12-31')}.items():
                m, t, n = mean_t(ser, a, b, lags, scale)
                add(cl, 'd2_tsmom_horizons', f'TSMOM({k_},{h})_{vn}', k, unit, m, t, n)
    # d3: gradual decay or 2021 break? windows and differences
    s20, s1 = tsmom_series(20, 20), tsmom_series(1, 1)
    wins = {'2000-2010': ('2000', '2010'), '2011-2015': ('2011', '2015'), '2016-2019': ('2016', '2019'),
            '2020': ('2020', '2020'), '2021-2025': ('2021', '2025')}
    st = {}
    for wn, (a, b) in wins.items():
        for nm, ser, lags, sc in [('TSMOM(20,20)_pct', s20, 20, 100), ('TSMOM(1,1)_bps', s1, 5, 1e4)]:
            m, se, n = nw(ser.loc[a:b].values, lags)
            st[(nm, wn)] = (m, se)
            add(cl, 'd3_decay_windows', nm, wn, 'mean', m * sc, m / se, n)
    for nm, sc in [('TSMOM(20,20)_pct', 100), ('TSMOM(1,1)_bps', 1e4)]:
        for w0 in ['2016-2019', '2011-2015']:
            (m0, s0), (m1, s1_) = st[(nm, w0)], st[(nm, '2021-2025')]
            add(cl, 'd3_decay_windows', nm, f'{w0}_minus_2021-2025', 'difference', (m0 - m1) * sc, diff_t(m0, s0, m1, s1_))
    # d4: index AC1, EW (as A1.7) and value weighted
    simple = np.expm1(rcc)
    vwi = vw_day(simple, LIQ60.shift(1))
    for nm, x in [('EW_idx_ret', P['idx_ret']), ('VW_by_traded_value', vwi)]:
        for k, (a, b) in {**PERS, '2016-2019': ('2016-01-01', '2019-12-31')}.items():
            y, xx = x.shift(-1).loc[a:b], x.loc[a:b]
            bb, tt, n = ols_nw(y.values, np.column_stack([np.ones(len(xx)), xx.values]), 5)
            add(cl, 'd4_index_AC1', nm, k, 'slope', bb[1], tt[1], n)


# ------------------------------------------------------------------------------------------------- C-e Monday
def claim_e():
    cl = 'C-e'
    mon = pd.Series(CAL.dayofweek == 0, index=CAL)
    wk = CAL.isocalendar().week.values
    first_wd = pd.Series(np.r_[True, wk[1:] != wk[:-1]], index=CAL)
    gapd = pd.Series(np.r_[np.nan, (CAL[1:] - CAL[:-1]).days], index=CAL)
    w = LIQ60.shift(1)
    for leg, fr in [('close_close', rcc), ('overnight', ron), ('intraday', rid)]:
        for vn, y in [('EW', ew_day(fr)), ('VW', vw_day(fr, w)), ('pre2018_EW', ew_day(fr[PRE]))]:
            for k, (a, b) in {**PERS, '2016-2020': ('2016-01-01', '2020-12-31')}.items():
                m, t, n = Dummy(y, mon, 5).at(a, b)
                add(cl, 'e1_monday_minus_other', f'{leg}_{vn}', k, 'bps_per_day', m * 1e4, t, n)
    y = ew_day(rcc)
    for nm, D, yy in [('first_trading_day_of_week', first_wd, y), ('monday_excl_long_weekends', mon, y.where(~(mon & (gapd > 3))))]:
        for k, (a, b) in PERS.items():
            m, t, n = Dummy(yy, D, 5).at(a, b)
            add(cl, 'e2_definition_variants', nm, k, 'bps_per_day', m * 1e4, t, n)
    for yr in range(2000, 2026):
        m, t, n = Dummy(y, mon, 5).at(f'{yr}-01-01', f'{yr}-12-31')
        add(cl, 'e3_by_year', 'close_close_EW', str(yr), 'bps_per_day', m * 1e4, t, n)
    for w0, (a0, b0) in [('2000-2020', ('2000-01-01', '2020-12-31')), ('2016-2020', ('2016-01-01', '2020-12-31'))]:
        m0, t0, _ = Dummy(y, mon, 5).at(a0, b0)
        m1, t1, _ = Dummy(y, mon, 5).at('2021-01-01', MAIN[1])
        se0, se1 = abs(m0 / t0), abs(m1 / t1)
        add(cl, 'e4_change_test', 'close_close_EW', f'{w0}_minus_2021-2025', 'bps_per_day', (m0 - m1) * 1e4, diff_t(m0, se0, m1, se1))
        add(cl, 'e4_change_test', 'close_close_EW', '2021-2025', 'ci95_low_bps', (m1 - 1.96 * se1) * 1e4)
        add(cl, 'e4_change_test', 'close_close_EW', '2021-2025', 'ci95_high_bps', (m1 + 1.96 * se1) * 1e4)


# ------------------------------------------------------------------------------------------------- sorts for C-f, C-g
DATES = rebalance_dates(P, 'M')


def xs_sort(signal, cols=ALL, n=5, min_stocks=25, a=None, b=None, elig=None, weight=None):
    """Same construction as mpstats.sort_series (signal at the month-end Close where tradable, hold next Open -> next
    month-end Close) with an arbitrary column set, an optional eligibility mask known at the formation date, an
    optional window (formation date in (a, b]) and an optional value-weighted top-group excess."""
    a = pd.Timestamp(a) if a is not None else None
    b = pd.Timestamp(b) if b is not None else None
    rows = []
    for d0, d1 in zip(DATES[:-1], DATES[1:]):
        if (a is not None and d0 <= a) or (b is not None and d0 > b):
            continue
        s = signal.loc[d0, cols].where(T.loc[d0, cols])
        if elig is not None:
            s = s.where(elig.loc[d0, cols].astype(bool))
        f = lnP.loc[d1, cols] - lnOn.loc[d0, cols]
        ok = s.notna() & f.notna()
        if ok.sum() < min_stocks:
            continue
        q = pd.qcut(s[ok].rank(method='first'), n, labels=False)
        g = f[ok].groupby(q).mean()
        allm = f[ok].mean()
        r = dict(date=d0, hl=g.iloc[-1] - g.iloc[0], top_ex=g.iloc[-1] - allm, bot_ex=g.iloc[0] - allm, n=int(ok.sum()))
        if weight is not None:
            ww = weight.loc[d0, cols][ok]
            top = (q == n - 1).values
            fv = f[ok]
            r['top_ex_vw'] = (fv[top] * ww[top]).sum() / ww[top].sum() - (fv * ww).sum() / ww.sum()
        rows.append(r)
    return pd.DataFrame(rows).set_index('date')


def mt_sort(x, a=None, b=None, lags=2):
    x = x.loc[a:b] if (a or b) else x
    m, se, n = nw(x.values, lags)
    return m * 100, (m / se if se and se > 0 else np.nan), n


SIG = {'D10_log_traded_value': np.log(LIQ60),
       'D9_amihud': (np.expm1(rcc).abs() / P['value']).rolling(60, min_periods=40).mean(),
       'D1_mom12_1': lnP.shift(21) - lnP.shift(252)}


def members_at(Y, frac):
    """Pseudo-index at date Y: top `frac` of panel stocks with >= 250 tradable days, by 250-day mean traded value."""
    Yd = CAL[CAL <= pd.Timestamp(Y)][-1]
    hist = T.loc[:Yd].sum()
    avail = [c for c in ALL if hist[c] >= 250]
    lv = P['value'].loc[:Yd].tail(250).mean()[avail].sort_values(ascending=False)
    return Yd, list(lv.index[:int(round(len(avail) * frac))]), len(avail)


# ------------------------------------------------------------------------------------------------- C-f illiquidity
def claim_f():
    cl = 'C-f'
    # f1: time profile of the full-panel sorts (quintiles as in D9/D10), both universes
    wins = {'2000-2007': ('2000-01-01', '2007-12-31'), '2008-2015': ('2008-01-01', '2015-12-31'),
            '2016-2020': ('2016-01-01', '2020-12-31'), '2021-2022': ('2021-01-01', '2022-12-31'),
            'last24m_2023-08..2025-08': ('2023-08-01', MAIN[1]), '2000-2022': ('2000-01-01', '2022-12-31'), 'MAIN': MAIN}
    for sn in ['D10_log_traded_value', 'D9_amihud']:
        for u, cols in [('all', ALL), ('pre2018', PRE)]:
            ss = xs_sort(SIG[sn], cols)
            for wn, (a, b) in wins.items():
                for col in ['hl', 'bot_ex', 'top_ex']:
                    m, t, n = mt_sort(ss[col], a, b)
                    add(cl, 'f1_time_profile', f'{sn}_{u}_{col}', wn, 'pct_per_month', m, t, n,
                        'D10: hl<0 = illiquid earns more; D9: hl>0 = illiquid earns more')
    # f2: pseudo-membership experiment in non-overlapping 5-year windows
    for sn in ['D10_log_traded_value', 'D9_amihud']:
        for frac in [.5, 1 / 3]:
            pre_all, pre_mem, post_all, post_mem = [], [], [], []
            for Y in ['2005-12-31', '2010-12-31', '2015-12-31', '2020-12-31']:
                Yd, mem, navail = members_at(Y, frac)
                a = Yd - pd.DateOffset(years=5)
                bpost = min(Yd + pd.DateOffset(years=5), pd.Timestamp(MAIN[1]))
                A = xs_sort(SIG[sn], ALL, 3, 12, a, Yd)
                B = xs_sort(SIG[sn], mem, 3, 12, a, Yd)
                Cm = xs_sort(SIG[sn], mem, 3, 12, Yd, bpost)
                D = xs_sort(SIG[sn], ALL, 3, 12, Yd, bpost)
                pre_all.append(A)
                pre_mem.append(B)
                post_mem.append(Cm)
                post_all.append(D)
                j = A.join(B, lsuffix='_all', rsuffix='_mem', how='inner')
                for lab, x in [('pre_all_hl', A.hl), ('pre_members_hl', B.hl), ('pre_members_minus_all_hl', j.hl_mem - j.hl_all),
                               ('pre_all_bot_ex', A.bot_ex), ('pre_members_bot_ex', B.bot_ex),
                               ('post_members_hl', Cm.hl), ('post_all_hl', D.hl)]:
                    m, t, n = mt_sort(x)
                    add(cl, 'f2_pseudo_membership', f'{sn}_top{frac:.2f}_{lab}', f'Y={Yd.date()}', 'pct_per_month', m, t, n,
                        f'{len(mem)} members of {navail} available; terciles, >=12 stocks')
            PA, PM, QA, QM = (pd.concat(x).sort_index() for x in (pre_all, pre_mem, post_all, post_mem))
            j = PA.join(PM, lsuffix='_all', rsuffix='_mem', how='inner')
            for lab, x in [('pre_all_hl', PA.hl), ('pre_members_hl', PM.hl), ('pre_members_minus_all_hl', j.hl_mem - j.hl_all),
                           ('pre_members_minus_all_bot_ex', j.bot_ex_mem - j.bot_ex_all),
                           ('post_members_hl', QM.hl), ('post_all_hl', QA.hl)]:
                m, t, n = mt_sort(x)
                add(cl, 'f2_pseudo_membership', f'{sn}_top{frac:.2f}_{lab}', 'pooled_4_windows', 'pct_per_month', m, t, n,
                    'pre = 5y before Y with look-ahead membership at Y; post = 5y after Y, membership known at Y')
    # f3: contemporaneous liquidity halves (known at formation, no look-ahead) - is the premium only in the bottom half?
    med = LIQ60.rank(axis=1, pct=True)
    for sn in ['D10_log_traded_value', 'D9_amihud']:
        for half, elig in [('top_half_liquidity', med > .5), ('bottom_half_liquidity', med <= .5)]:
            ss = xs_sort(SIG[sn], ALL, 3, 12, elig=elig)
            for wn, (a, b) in PERS.items():
                m, t, n = mt_sort(ss.hl, a, b)
                add(cl, 'f3_liquidity_halves', f'{sn}_{half}_hl', wn, 'pct_per_month', m, t, n, 'terciles within the half')


# ------------------------------------------------------------------------------------------------- C-g momentum ranking
def claim_g():
    cl = 'C-g'
    sig = SIG['D1_mom12_1']
    w = LIQ60
    for u, cols in [('all', ALL), ('pre2018', PRE)]:
        ss = xs_sort(sig, cols, weight=w)
        for k, (a, b) in {**PERS, '2000-2022': ('2000-01-01', '2022-12-31')}.items():
            for col in ['top_ex', 'hl', 'top_ex_vw']:
                m, t, n = mt_sort(ss[col], a, b)
                add(cl, 'g1_top_quintile_excess', f'D1_{u}_{col}', k, 'pct_per_month', m, t, n)
            m, t, n = mt_sort(ss['top_ex'], a, b, lags=6)
            add(cl, 'g1_top_quintile_excess', f'D1_{u}_top_ex_NWlags6', k, 'pct_per_month', m, t, n)
    # g2: within contemporaneous liquidity halves; g5: excluding the bottom liquidity tercile
    rk = LIQ60.rank(axis=1, pct=True)
    for nm, elig, nq, ms in [('top_half_liquidity', rk > .5, 5, 15), ('bottom_half_liquidity', rk <= .5, 5, 15),
                             ('excluding_bottom_liquidity_tercile', rk > 1 / 3, 5, 20)]:
        ss = xs_sort(sig, ALL, nq, ms, elig=elig)
        for k, (a, b) in PERS.items():
            m, t, n = mt_sort(ss.top_ex, a, b)
            add(cl, 'g2_within_liquidity_groups', f'D1_{nm}_top_ex', k, 'pct_per_month', m, t, n)
    # share of top-quintile momentum stocks that sit in the bottom liquidity tercile
    shares = []
    for d0 in DATES[:-1]:
        if d0 < pd.Timestamp(MAIN[0]):
            continue
        s = sig.loc[d0].where(T.loc[d0])
        ok = s.notna() & rk.loc[d0].notna()
        if ok.sum() < 25:
            continue
        top = s[ok] >= s[ok].quantile(.8)
        shares.append((rk.loc[d0][ok][top] <= 1 / 3).mean())
    add(cl, 'g2_within_liquidity_groups', 'share_of_D1_top_quintile_in_bottom_liquidity_tercile', 'MAIN', 'share', np.mean(shares),
        n=len(shares), note='1/3 if unrelated')
    # g3: pseudo-membership for momentum: top_ex among stocks already liquid at Y, after Y
    post_mem, post_all = [], []
    for Y in ['2005-12-31', '2010-12-31', '2015-12-31', '2020-12-31']:
        Yd, mem, navail = members_at(Y, .5)
        bpost = min(Yd + pd.DateOffset(years=5), pd.Timestamp(MAIN[1]))
        post_mem.append(xs_sort(sig, mem, 5, 15, Yd, bpost))
        post_all.append(xs_sort(sig, ALL, 5, 25, Yd, bpost))
    for lab, x in [('post_members_top_ex', pd.concat(post_mem).top_ex), ('post_all_top_ex', pd.concat(post_all).top_ex)]:
        m, t, n = mt_sort(x.sort_index())
        add(cl, 'g3_pseudo_membership', f'D1_{lab}', 'pooled_4_windows', 'pct_per_month', m, t, n,
            'members = top half by liquidity at Y; quintiles, >=15 stocks')
    # g4: ranking breakout candidates by 12-1 momentum: W1.1 events, abnormal fo[20] from the next Open
    mrk = sig.where(T).rank(axis=1, pct=True)
    brk = (lnP > lnH.shift(1).rolling(20, min_periods=20).max()) & T
    er20 = (lnP - lnP.shift(20)).abs() / lnP.diff().abs().rolling(20).sum()
    for bn, b_ in [('W1.1_HHV20', brk), ('W1.1_HHV20_ER20>=0.3', brk & (er20 >= .3)),
                   ('W1.1_HHV20_liquid_half', brk & (rk > .5))]:
        valid = b_ & mrk.notna()
        groups = {'top_mom_quintile': valid & (mrk > .8), 'rest': valid & (mrk <= .8), 'bottom_mom_quintile': valid & (mrk <= .2)}
        for u in ['all', 'pre2018']:
            ser = {g: event_series(P, m_, 20, u) for g, m_ in groups.items()}
            for k, (a, b) in PERS.items():
                for g in groups:
                    m, t, n = Mean(ser[g][0], 20).at(a, b)
                    add(cl, 'g4_breakout_ranking', f'{bn}_{g}_{u}', k, 'abnormal_fo20_pct', m * 100, t, n)
                m, t, n = Diff(ser['top_mom_quintile'][0], ser['rest'][0], 20).at(a, b)
                add(cl, 'g4_breakout_ranking', f'{bn}_top_minus_rest_{u}', k, 'abnormal_fo20_diff_pct', m * 100, t, n,
                    'usability threshold (PLAN): |difference| >= 0.25 pp per trade')
                m, t, n = Diff(ser['top_mom_quintile'][0], ser['bottom_mom_quintile'][0], 20).at(a, b)
                add(cl, 'g4_breakout_ranking', f'{bn}_top_minus_bottom_{u}', k, 'abnormal_fo20_diff_pct', m * 100, t, n)
            if u == 'all':
                add(cl, 'g4_breakout_ranking', f'{bn}_events', 'MAIN', 'events_top/rest',
                    int(groups['top_mom_quintile'].loc[MAIN[0]:MAIN[1]].values.sum()),
                    n=int(groups['rest'].loc[MAIN[0]:MAIN[1]].values.sum()))


def replication_checks():
    """Recompute a few main-session numbers to make sure the critic uses the same objects."""
    b = pd.read_csv(HERE / 'results' / 'B_tests.csv').set_index('test_id')
    a = pd.read_csv(HERE / 'results' / 'A_tests.csv').set_index('test_id')
    m, t, n = dw(GD, AB_ID, *MAIN)
    add('check', 'replication', 'B4', 'MAIN', 'abs_diff_vs_B_tests', abs(m - b.loc['B4', 'eff_MAIN']))
    m, t, n = dw(GU, AB_ID, *MAIN)
    add('check', 'replication', 'B3', 'MAIN', 'abs_diff_vs_B_tests', abs(m - b.loc['B3', 'eff_MAIN']))
    m, t, n = mean_t(tsmom_series(1, 1), *MAIN, 5, 1e4)
    add('check', 'replication', 'A1.1', 'MAIN', 'abs_diff_vs_A_tests', abs(m - a.loc['A1.1', 'eff_MAIN']))
    ss = xs_sort(SIG['D1_mom12_1'])
    m, t, n = mt_sort(ss.top_ex, *MAIN)
    add('check', 'replication', 'X-D-topex D1', 'MAIN', 'value_should_be_0.858', m, t, n)


# ================================================================================================= extensions (resumed run)
# Added in the resumed critic run after reading the first run's evidence (rows of the tests a10-a11, b4-b7, c5-c7,
# d5-d7, e5, f4-f6, g5). External facts (press reports found by web search; not checked against IDX primary rules):
# pre-opening call auction for the top ~60-65 stocks until 8 Oct 2008, none 13 Oct 2008 - 15 May 2009, LQ45 only from
# 18 May 2009, none 13 Mar - 4 Sep 2020, LQ45 only from 7 Sep 2020, extended together with pre-closing to the
# Main/Development/New-Economy boards on 9 Dec 2024 (Kep-00196/BEI/12-2024). Pre-closing (closing call auction)
# introduced 2 Jan 2013 (Kep-00399/BEI/11-2012); lot 500 -> 100 shares and new price fractions 6 Jan 2014; random
# closing and IEP/IEV display 6 Dec 2021.
def empirical_tick(win=20):
    """Smallest positive price step seen over the previous `win` market days (O/H/L/C within the day and C/O versus the
    previous tradable Close), in adjusted units. Back-adjustment multiplies all prices of a period by one factor, so
    step / price estimates the real relative tick of that time without the historical tick table or the traded price
    level. Adjusted prices are rounded to 0.01 and the O/H/L/C fields of one traded price can differ by one cent, so
    steps <= max(0.0151, 0.02% of price) are ignored (below any real IDX relative tick). Known before day t (shifted)."""
    Ot, Ht, Lt, Ct = (x.where(T) for x in (O, H, L, C))
    floor = np.maximum(.0151, .0002 * prevC)        # one-cent field inconsistencies (e.g. 1481.70 vs 1481.69) are noise
    m = None
    for d in [Ht - Lt, (Ht - Ot).abs(), (Ot - Lt).abs(), (Ht - Ct).abs(), (Ct - Lt).abs(), (Ot - Ct).abs(),
              (Ct - prevC).abs(), (Ot - prevC).abs()]:
        d = d.where(d > floor)
        m = d if m is None else np.fmin(m, d)
    return m.rolling(win, min_periods=5).min().shift(1)


TK_EMP = empirical_tick()
RT_EMP = TK_EMP / prevC
SHIFT1 = lambda m: m.shift(1).fillna(False).astype(bool)                    # signal at t-1, action on day t
BRK20 = (lnP > lnH.shift(1).rolling(20, min_periods=20).max()) & T          # W1.1 Close breakout
EXT_PERS = {**PERS, 'P0': P0}


def win_mean(mask, ser, a, b, lags=5):
    s = daily(mask, ser).loc[a:b]
    m, se, n = nw(s.values, lags)
    return m, se, int((mask.reindex_like(ser).fillna(False).astype(bool) & ser.notna()).loc[a:b].values.sum())


# ------------------------------------------------------------------------------------------------- C-a extensions
def ext_a():
    cl = 'C-a'
    # a10: empirical tick. Validation against the modern table where adjusted ~ traded prices (2021-25)
    for wn, (a, b) in {'2000-2007': ('2000', '2007'), '2008-2013': ('2008', '2013'), '2014-2016': ('2014', '2016'),
                       '2017-2020': ('2017', '2020'), '2021-2025': ('2021', '2025')}.items():
        e = RT_EMP.loc[a:b].values
        r = e / REL_TICK.loc[a:b].values
        ok = np.isfinite(r)
        add(cl, 'a10_empirical_tick', 'validation_vs_modern_table', wn, 'median_empirical_rel_tick_pct',
            np.nanmedian(e) * 100, n=int(np.isfinite(e).sum()))
        add(cl, 'a10_empirical_tick', 'validation_vs_modern_table', wn, 'median_ratio_empirical_to_modern', np.median(r[ok]))
        add(cl, 'a10_empirical_tick', 'validation_vs_modern_table', wn, 'share_ratio_within_10pct',
            np.mean(np.abs(r[ok] - 1) < .1), note='near 1 in 2021-25 validates the estimator; older years had other tick tables')
    for k, (a, b) in EXT_PERS.items():
        for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
            m, t, n = dw(ev, AB_ID / RT_EMP, a, b, scale=1)
            add(cl, 'a10_empirical_tick', lab, k, 'abnormal_intraday_in_empirical_ticks', m, t, n)
            m, t, n = dw(ev, rid / RT_EMP, a, b, scale=1)
            add(cl, 'a10_empirical_tick', lab, k, 'raw_intraday_in_empirical_ticks', m, t, n)
            x = evw(ev, rid / RT_EMP, a, b, scale=1)
            add(cl, 'a10_empirical_tick', lab, k, 'raw_intraday_in_empirical_ticks_event_median', np.median(x) if len(x) else np.nan,
                n=len(x))
            x = evw(ev, RT_EMP, a, b, scale=100)
            add(cl, 'a10_empirical_tick', lab, k, 'median_empirical_rel_tick_pct', np.median(x) if len(x) else np.nan, n=len(x))
    buckets = {'emptick<0.4%': (0, .004), 'emptick0.4-1%': (.004, .01), 'emptick1-2%': (.01, .02), 'emptick>=2%': (.02, 9)}
    for k, (a, b) in PERS.items():
        for bn, (t0, t1) in buckets.items():
            cell = (RT_EMP >= t0) & (RT_EMP < t1)
            for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
                m, t, n = dw(ev & cell, AB_ID, a, b)
                add(cl, 'a10_empirical_tick', f'{lab}_{bn}', k, 'abnormal_intraday_bps', m, t, n)
        cell = (LR > 2 / 3) & (RT_EMP < .004)
        for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
            m, t, n = dw(ev & cell, AB_ID, a, b)
            add(cl, 'a10_empirical_tick', f'{lab}_liqH_emptick<0.4%', k, 'abnormal_intraday_bps', m, t, n)
            m, t, n = dw(ev & cell, rid, a, b)
            add(cl, 'a10_empirical_tick', f'{lab}_liqH_emptick<0.4%', k, 'raw_intraday_bps', m, t, n)
    gap_ticks = (O - prevC).abs() / TK_EMP
    for k, (a, b) in PERS.items():
        for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
            tot = int((ev & gap_ticks.notna()).loc[a:b].values.sum())
            for gn, (g0, g1) in {'gap<=2ticks': (0, 2.5), 'gap3-5ticks': (2.5, 5.5), 'gap>=6ticks': (5.5, 1e12)}.items():
                cell = (gap_ticks >= g0) & (gap_ticks < g1)
                add(cl, 'a10_empirical_tick', f'{lab}_{gn}', k, 'share_of_events',
                    (ev & cell).loc[a:b].values.sum() / tot if tot else np.nan, n=tot)
                m, t, n = dw(ev & cell, AB_ID, a, b)
                add(cl, 'a10_empirical_tick', f'{lab}_{gn}', k, 'abnormal_intraday_bps', m, t, n)
                m, t, n = dw(ev & cell, AB_ID / RT_EMP, a, b, scale=1)
                add(cl, 'a10_empirical_tick', f'{lab}_{gn}', k, 'abnormal_intraday_in_empirical_ticks', m, t, n)
    # a11: pre-opening suspensions as natural experiments (difference in differences, LQ45 proxy vs rest)
    exps = {'2020_suspension': {'pre': ('2019-09-13', '2020-03-12'), 'treat': ('2020-03-13', '2020-09-04'),
                                'post': ('2020-09-07', '2021-03-05')},
            '2008_09_suspension': {'pre': ('2008-03-13', '2008-10-08'), 'treat': ('2008-10-13', '2009-05-15'),
                                   'post': ('2009-05-18', '2009-11-30')}}
    notes = {'2020_suspension': 'LQ45 lost its opening auction 13 Mar - 4 Sep 2020; rest had none throughout; '
                                'confounded by COVID and the 7% lower limit from Mar 2020 (affects gap-downs most)',
             '2008_09_suspension': 'top ~60-65 lost the opening auction 13 Oct 2008 - 15 May 2009, LQ45 only afterwards; '
                                   'panel top-40 proxy is crude in 2008 and the crisis confounds'}
    for exp, wins in exps.items():
        for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
            st = {}
            for gname, g in [('LQ45proxy_top40', LQ_PROXY), ('rest', REST)]:
                for wn, (a, b) in wins.items():
                    m, se, n = win_mean(ev & g, AB_ID, a, b)
                    st[(gname, wn)] = (m, se)
                    add(cl, 'a11_preopening_suspension_DiD', f'{lab}_{gname}', f'{exp}:{wn}_{a}..{b}',
                        'abnormal_intraday_bps', m * 1e4, m / se if se else np.nan, n)

            def contrast(g):
                (mt, s_t), (m0, s0), (m1, s1) = st[(g, 'treat')], st[(g, 'pre')], st[(g, 'post')]
                return mt - (m0 + m1) / 2, s_t ** 2 + (s0 ** 2 + s1 ** 2) / 4
            ca_, va = contrast('LQ45proxy_top40')
            cb_, vb = contrast('rest')
            add(cl, 'a11_preopening_suspension_DiD', f'{lab}_LQ45proxy_top40', exp, 'treat_minus_mean_adjacent_bps',
                ca_ * 1e4, ca_ / math.sqrt(va))
            add(cl, 'a11_preopening_suspension_DiD', f'{lab}_rest', exp, 'treat_minus_mean_adjacent_bps',
                cb_ * 1e4, cb_ / math.sqrt(vb))
            add(cl, 'a11_preopening_suspension_DiD', lab, exp, 'DiD_LQ45proxy_minus_rest_bps', (ca_ - cb_) * 1e4,
                (ca_ - cb_) / math.sqrt(va + vb),
                note='auction-matters prediction: gap_up < 0, gap_down > 0. ' + notes[exp])
    # a12: the 9 Dec 2024 extension as a difference in differences (rest gained auctions, LQ45 proxy had them before)
    pre_w, post_w = ('2023-01-01', '2024-12-06'), (AUCTION_EXT, MAIN[1])
    for excl in [False, True]:
        for lab, ev in [('gap_up', GU), ('gap_down', GD)]:
            chg = {}
            for gname, g in [('LQ45proxy_top40', LQ_PROXY), ('rest', REST)]:
                s = daily(ev & g, AB_ID)
                s0, s1 = s.loc[pre_w[0]:pre_w[1]], s.loc[post_w[0]:post_w[1]]
                if excl:
                    s1 = s1.drop(s1.loc['2025-03-01':'2025-04-30'].index)
                m0, se0, _ = nw(s0.values, 5)
                m1, se1, _ = nw(s1.values, 5)
                chg[gname] = (m1 - m0, se0 ** 2 + se1 ** 2)
            d_ = chg['rest'][0] - chg['LQ45proxy_top40'][0]
            add(cl, 'a12_auction_extension_DiD', lab, 'post_excl_2025-03..04' if excl else 'post_2024-12-09..2025-08-15',
                'DiD_rest_minus_LQ45proxy_change_bps', d_ * 1e4, d_ / math.sqrt(chg['rest'][1] + chg['LQ45proxy_top40'][1]),
                note='change post minus pre (2023-01..2024-12-06); auction-matters prediction: gap_up > 0, gap_down < 0')


# ------------------------------------------------------------------------------------------------- C-b extensions
def ext_b():
    cl = 'C-b'
    tk = TK_EMP
    sellC = (C - tk).where(C - tk > 0)
    models = {'M3e_fee+1emptick_per_side': np.log(sellC * .9975 / ((O + tk) * 1.0015)),
              'M5e_fee+0.5emptick_per_side': np.log((C - .5 * tk) * .9975 / ((O + .5 * tk) * 1.0015)),
              'M4e_main_session_model_with_empirical_tick': np.log(sellC * .9975 * .9975 / ((O + tk) * 1.0025 * 1.0015))}
    ev = GD & tk.notna()
    modern_rel = frame(tick(O.values)) / O
    for k, (a, b) in PERS.items():
        for nm, net in models.items():
            x = evw(ev, net, a, b)
            add(cl, 'b4_cost_with_empirical_tick', nm, k, 'event_weighted_mean_bps', x.mean(), n=len(x))
            add(cl, 'b4_cost_with_empirical_tick', nm, k, 'event_weighted_median_bps', np.median(x), n=len(x))
            m, t, n = dw(ev, net, a, b)
            add(cl, 'b4_cost_with_empirical_tick', nm, k, 'day_weighted_mean_bps', m, t, n)
        x = evw(ev, RT_EMP, a, b, scale=1e4)
        add(cl, 'b4_cost_with_empirical_tick', 'gap_down_empirical_rel_tick', k, 'mean_bps', x.mean(), n=len(x))
        add(cl, 'b4_cost_with_empirical_tick', 'gap_down_empirical_rel_tick', k, 'median_bps', np.median(x), n=len(x))
        x = evw(ev, modern_rel, a, b, scale=1e4)
        add(cl, 'b4_cost_with_empirical_tick', 'gap_down_modern_table_rel_tick_on_adjusted_open', k, 'mean_bps', x.mean(),
            n=len(x), note='the tick the main session charged (modern table on back-adjusted prices)')
    # b5: gross / fee-only / PLAN cost B by auction group and recent window
    nets = {'M0_gross': np.log(C / O), 'M1_fee_only(0.40%rt)': np.log(C * .9975 / (O * 1.0015)),
            'M2_PLAN_cost_B(0.90%rt)': np.log(C * .9975 * .9975 / (O * 1.0025 * 1.0015)),
            'M3e_fee+1emptick_per_side': models['M3e_fee+1emptick_per_side'],
            'M5e_fee+0.5emptick_per_side': models['M5e_fee+0.5emptick_per_side']}
    wins = {'2016-2020': ('2016-01-01', '2020-12-31'), '2021-01..2024-12-06': ('2021-01-01', '2024-12-06'),
            '2024-12-09..2025-08-15': (AUCTION_EXT, MAIN[1])}
    for gname, g in [('LQ45proxy_top40', LQ_PROXY), ('rest', REST), ('all', frame(np.ones(C.shape, bool)))]:
        for wn, (a, b) in wins.items():
            for nm, net in nets.items():
                m, t, n = dw(GD & g, net, a, b)
                add(cl, 'b5_gap_down_trade_by_group_recent', f'{nm}_{gname}', wn, 'day_weighted_mean_bps', m, t, n)
                x = evw(GD & g, net, a, b)
                add(cl, 'b5_gap_down_trade_by_group_recent', f'{nm}_{gname}', wn, 'event_weighted_mean_bps',
                    x.mean() if len(x) else np.nan, n=len(x))
    # b6: the two execution rules when a Close fill can fail at a price limit (then trade at the next Open)
    lnO_t, lnO_next = P['lnO'], P['lnO'].shift(-1)
    Pc = np.exp(lnP)
    sma30 = Pc.rolling(30, min_periods=30).mean()
    cross_dn = (Pc < sma30) & (Pc.shift(1) >= sma30.shift(1)) & T
    llv10 = (lnP < lnL.shift(1).rolling(10, min_periods=10).min()) & T
    pers_b = {**PERS, 'post_auction_ext_2024-12-09..': (AUCTION_EXT, MAIN[1])}
    specs = [('rule2_sell_gapdown_at_Close',
              {'all_gap_down': GD, 'after_close_cross_below_SMA30': GD & SHIFT1(cross_dn),
               'after_close_below_LLV10': GD & SHIFT1(llv10)},
              rid, lnO_next - lnO_t,
              {'nonfill_if_Close==Low': CLOSE_LOW, 'nonfill_if_Close==Low&r_cc<=-6.5%': CLOSE_LOW & (rcc <= np.log(.935))}),
             ('rule1_buy_gapup_at_Close',
              {'all_gap_up': GU, 'after_breakout_HHV20': GU & SHIFT1(BRK20)},
              -rid, lnO_t - lnO_next,
              {'nonfill_if_Close==High': CLOSE_HIGH, 'nonfill_if_Close==High&r_cc>=+18%': CLOSE_HIGH & (rcc >= np.log(1.18))})]
    for rule, ctxs, ben0, alt, lims in specs:
        for cn, msk in ctxs.items():
            for vn, lim in [('assume_fill', None), *lims.items()]:
                ben = ben0 if lim is None else ben0.where(~lim.fillna(False).astype(bool), alt)
                for k, (a, b) in pers_b.items():
                    m, t, n = dw(msk & ben.notna(), ben, a, b)
                    add(cl, 'b6_rules_with_limit_nonfill', f'{rule}_{cn}_{vn}', k, 'benefit_bps_day_weighted', m, t, n,
                        'non-fill days traded at the next Open instead of the Close')
                if lim is not None:
                    a, b = MAIN
                    add(cl, 'b6_rules_with_limit_nonfill', f'{rule}_{cn}_{vn}', 'MAIN', 'share_of_events_flagged',
                        (msk & lim).loc[a:b].values.sum() / msk.loc[a:b].values.sum())
    # b7: rule 1 read as "skip gap-up entries": follow-through of breakout entries with and without a gap-up Open
    F20 = P['fo'][20]
    ab_open = F20.sub(F20.mean(axis=1), axis=0).shift(1)                       # row t: lnP[t+19]-lnO[t], abnormal
    s_gu = daily(GU & SHIFT1(BRK20), ab_open)
    s_ng = daily(SHIFT1(BRK20) & ~GU & ~GD & rid.notna(), ab_open)
    for k, (a, b) in PERS.items():
        m, t, n = Diff(s_gu, s_ng, 20).at(a, b)
        add(cl, 'b7_rule1_as_skip', 'breakout_entry_gap_up_minus_no_gap', k, 'abnormal_20d_from_entry_Open_diff_pct',
            m * 100, t, n, '> 0: skipping gap-up breakout entries gives up better-than-average trades')


# ------------------------------------------------------------------------------------------------- C-c extensions
def monthly(series):
    return series.groupby(series.index.to_period('M')).mean()


def break_search(y, lo, hi):
    """Least-squares single mean break in a monthly series; candidate break months in [lo, hi]."""
    y = y.dropna()
    v = y.values
    best = None
    for i, p in enumerate(y.index):
        if p < pd.Period(lo, 'M') or p > pd.Period(hi, 'M'):
            continue
        a, b = v[:i], v[i:]
        ssr = ((a - a.mean()) ** 2).sum() + ((b - b.mean()) ** 2).sum()
        if best is None or ssr < best[0]:
            best = (ssr, p, a.mean(), b.mean())
    ssr0 = ((v - v.mean()) ** 2).sum()
    return best[1], best[2], best[3], (ssr0 - best[0]) / (best[0] / (len(v) - 2))


def ext_c():
    cl = 'C-c'
    Tt = T & prevC.notna()
    nT = Tt.sum(axis=1).astype(float)
    close_loc = ((CLOSE_HIGH & Tt).sum(axis=1) - (CLOSE_LOW & Tt).sum(axis=1)) / nT.replace(0, np.nan)
    open_loc = ((OPEN_HIGH & Tt).sum(axis=1) - (OPEN_LOW & Tt).sum(axis=1)) / nT.replace(0, np.nan)
    daily_series = {'overnight_EW_bps': ew_day(ron) * 1e4, 'intraday_EW_bps': ew_day(rid) * 1e4,
                    'close_location_share(C==H minus C==L)': close_loc, 'open_location_share(O==H minus O==L)': open_loc}
    # c5: least-squares break month (descriptive; monthly means, serial correlation ignored in the F)
    for nm, s in daily_series.items():
        ym = monthly(s.loc[MAIN[0]:MAIN[1]])
        for wn, (w0, w1, lo, hi) in {'2000-2025_breaks_2003..2022': ('2000-01', '2025-08', '2003-01', '2022-12'),
                                     '2008-2019_breaks_2009..2018': ('2008-01', '2019-12', '2009-01', '2018-12')}.items():
            yy = ym.loc[pd.Period(w0, 'M'):pd.Period(w1, 'M')]
            p, m0, m1, F = break_search(yy, lo, hi)
            add(cl, 'c5_break_month', nm, wn, 'break_month_yyyymm', p.year * 100 + p.month,
                note=f'mean before {m0:.3f}, after {m1:.3f}, F {F:.1f}')
    # c6: 12-month windows around microstructure dates and placebo New-Year dates
    dates = {'2010-01-04': 'placebo', '2011-01-03': 'placebo', '2012-01-02': 'placebo',
             '2013-01-02': 'pre-closing call auction introduced', '2014-01-06': 'lot 500->100 and new price fractions',
             '2015-01-02': 'placebo', '2016-01-04': 'placebo', '2017-01-02': 'placebo (post-closing session 2017)',
             '2021-12-06': 'random closing + IEP/IEV display', '2024-12-09': 'auctions extended beyond LQ45'}
    grp_series = {}
    for gname, g in [('LQ45proxy_top40', LQ_PROXY), ('rest', REST)]:
        Tg = Tt & g
        nG = Tg.sum(axis=1).astype(float).replace(0, np.nan)
        grp_series[f'intraday_EW_bps_{gname}'] = ew_day(rid.where(g)) * 1e4
        grp_series[f'overnight_EW_bps_{gname}'] = ew_day(ron.where(g)) * 1e4
        grp_series[f'close_location_share_{gname}'] = ((CLOSE_HIGH & Tg).sum(axis=1) - (CLOSE_LOW & Tg).sum(axis=1)) / nG
    for d, lab in dates.items():
        dd = pd.Timestamp(d)
        a0, b0 = str((dd - pd.DateOffset(months=12)).date()), str((dd - pd.Timedelta(days=1)).date())
        a1, b1 = d, str(min(dd + pd.DateOffset(months=12) - pd.Timedelta(days=1), pd.Timestamp(MAIN[1])).date())
        for nm, s in {**daily_series, **grp_series}.items():
            m0, se0, _ = nw(s.loc[a0:b0].values, 5)
            m1, se1, n1 = nw(s.loc[a1:b1].values, 5)
            add(cl, 'c6_event_windows_12m', nm, f'{d} {lab}', 'after_minus_before', m1 - m0, diff_t(m1, se1, m0, se0), n1,
                f'before {m0:.3f}, after {m1:.3f}')
    # c7: what makes up the EW overnight mean: small moves vs >2% gaps; and the balance of up/down opens
    nrow = ron.notna().sum(axis=1).replace(0, np.nan)
    parts = {'|r_on|<=2%': ron.abs() <= np.log(1.02), 'r_on>+2%': ron > np.log(1.02), 'r_on<-2%': ron < np.log(.98)}
    up_dn = ((ron > 0).sum(axis=1) - (ron < 0).sum(axis=1)) / nrow
    for k, (a, b) in {**PERS, '2016-2025': ('2016-01-01', MAIN[1])}.items():
        for pn, msk in parts.items():
            contrib = ron.where(msk, 0.).where(ron.notna()).sum(axis=1) / nrow
            m, t, n = mean_t(contrib, a, b, 5, 1e4)
            add(cl, 'c7_overnight_composition', pn, k, 'contribution_bps_per_day', m, t, n, 'the three parts sum to B1')
        m, t, n = mean_t(up_dn, a, b, 5, 1)
        add(cl, 'c7_overnight_composition', 'share(r_on>0)-share(r_on<0)', k, 'share_difference', m, t, n)
        m, t, n = mean_t(close_loc, a, b, 5, 1)
        add(cl, 'c7_overnight_composition', 'close_location_share(C==H minus C==L)', k, 'share_difference', m, t, n)


# ------------------------------------------------------------------------------------------------- C-d extensions
def ext_d():
    cl = 'C-d'
    legs = {'overnight_r_on[t+1]': tsmom_series(1, 1, fwd=ron.shift(-1)), 'A1.1_open_to_close_fo[1]': tsmom_series(1, 1),
            'close_to_close_fc[1]': tsmom_series(1, 1, fwd='fc')}
    for y in range(2000, 2026):
        for ln, s in legs.items():
            m, t, n = mean_t(s, f'{y}-01-01', f'{y}-12-31', 5, 1e4)
            add(cl, 'd5_tsmom1_legs_by_year', ln, str(y), 'bps_per_day', m, t, n)
    # d6: stale-price measures by year (nonsynchronous trading inflates EW index autocorrelation)
    listed = C.notna().cumsum() > 0
    zero = T & (rcc == 0)
    for y in range(1995, 2026):
        a, b = f'{y}-01-01', f'{y}-12-31'
        add(cl, 'd6_stale_prices_by_year', 'non_tradable_share_of_listed_days', str(y), 'share',
            (listed & ~T).loc[a:b].values.sum() / listed.loc[a:b].values.sum())
        add(cl, 'd6_stale_prices_by_year', 'zero_close_to_close_return_share', str(y), 'share',
            zero.loc[a:b].values.sum() / (T & rcc.notna()).loc[a:b].values.sum())
        x = P['idx_ret'].loc[a:b]
        add(cl, 'd6_stale_prices_by_year', 'EW_idx_AC1', str(y), 'autocorrelation', x.autocorr(1))
    # d7: the liquid subset (LQ45 proxy): index AC1 and TSMOM legs
    simple = np.expm1(rcc)
    idx_lq = simple.where(LQ_PROXY).mean(axis=1)
    idx_rest = simple.where(REST).mean(axis=1)
    for k, (a, b) in {**PERS, '2016-2019': ('2016-01-01', '2019-12-31')}.items():
        for nm, x in [('EW_idx_LQ45proxy_top40', idx_lq), ('EW_idx_rest', idx_rest)]:
            yy, xx = x.shift(-1).loc[a:b], x.loc[a:b]
            bb, tt, n = ols_nw(yy.values, np.column_stack([np.ones(len(xx)), xx.values]), 5)
            add(cl, 'd7_liquid_subset', nm, k, 'AC1_slope', bb[1], tt[1], n)
    for (k_, h, fwd, nm) in [(1, 1, 'fo', 'TSMOM(1,1)_open_to_close'), (1, 1, 'fc', 'TSMOM(1,1)_close_to_close'),
                             (20, 20, 'fo', 'TSMOM(20,20)')]:
        past = rcc if k_ == 1 else lnP - lnP.shift(k_)
        sgn = np.sign(past).where(T & LQ_PROXY)
        yv = P[fwd][h]
        ser = (sgn * yv).where(sgn.notna() & yv.notna()).mean(axis=1)
        lags, sc = (5, 1e4) if h == 1 else (20, 100)
        for k, (a, b) in PERS.items():
            m, t, n = mean_t(ser, a, b, lags, sc)
            add(cl, 'd7_liquid_subset', f'{nm}_LQ45proxy_top40', k, 'bps' if h == 1 else 'pct_per_window', m, t, n)


# ------------------------------------------------------------------------------------------------- C-e extension
def ext_e():
    cl = 'C-e'
    mon = pd.Series(CAL.dayofweek == 0, index=CAL)
    for ln, (l0, l1) in {'liqL': (0, 1 / 3), 'liqM': (1 / 3, 2 / 3), 'liqH': (2 / 3, 1.01)}.items():
        g = (LR > l0) & (LR <= l1)
        for leg, fr in [('close_close', rcc), ('overnight', ron), ('intraday', rid)]:
            y = ew_day(fr.where(g))
            for k, (a, b) in PERS.items():
                m, t, n = Dummy(y, mon, 5).at(a, b)
                add(cl, 'e5_monday_by_liquidity', f'{leg}_{ln}', k, 'bps_per_day', m * 1e4, t, n)


# ------------------------------------------------------------------------------------------------- C-f extensions
def ext_f():
    cl = 'C-f'
    # f4: formal pre-minus-post contrasts of the pseudo-membership experiment
    for sn in ['D10_log_traded_value', 'D9_amihud']:
        for frac in [.5, 1 / 3]:
            pre_mem, post_mem, post_all = [], [], []
            for Y in ['2005-12-31', '2010-12-31', '2015-12-31', '2020-12-31']:
                Yd, mem, _ = members_at(Y, frac)
                a = Yd - pd.DateOffset(years=5)
                bpost = min(Yd + pd.DateOffset(years=5), pd.Timestamp(MAIN[1]))
                pre_mem.append(xs_sort(SIG[sn], mem, 3, 12, a, Yd))
                post_mem.append(xs_sort(SIG[sn], mem, 3, 12, Yd, bpost))
                post_all.append(xs_sort(SIG[sn], ALL, 3, 12, Yd, bpost))
            PM, QM, QA = (pd.concat(x).sort_index() for x in (pre_mem, post_mem, post_all))
            m1, se1, n1 = nw(PM.hl.values, 2)
            m2, se2, n2 = nw(QM.hl.values, 2)
            add(cl, 'f4_pseudo_membership_contrasts', f'{sn}_top{frac:.2f}', 'pooled_4_windows',
                'pre_members_hl_minus_post_members_hl_pct', (m1 - m2) * 100, diff_t(m1, se1, m2, se2), min(n1, n2),
                'same stocks: look-ahead membership (pre) vs membership known (post)')
            j = QM.join(QA, lsuffix='_mem', rsuffix='_all', how='inner')
            m, t, n = mt_sort(j.hl_mem - j.hl_all)
            add(cl, 'f4_pseudo_membership_contrasts', f'{sn}_top{frac:.2f}', 'pooled_4_windows',
                'post_members_hl_minus_post_all_hl_paired_pct', m, t, n, 'same months, members-at-Y vs whole panel')
    # f5: does the low-liquidity excess return come from stocks whose liquidity rank rose afterwards?
    rk = LIQ60.rank(axis=1, pct=True)
    recs = []
    for i, (d0, d1) in enumerate(zip(DATES[:-1], DATES[1:])):
        if d0 < pd.Timestamp(MAIN[0]) or i + 24 >= len(DATES):
            continue
        s = rk.loc[d0].where(T.loc[d0])
        f = lnP.loc[d1] - lnOn.loc[d0]
        fut = rk.loc[DATES[i + 24]]
        ok = s.notna() & f.notna()
        if ok.sum() < 25:
            continue
        allm = f[ok].mean()
        terc = pd.qcut(s[ok].rank(method='first'), 3, labels=False)
        for tq, tn in [(0, 'bottom'), (1, 'middle'), (2, 'top')]:
            idx = terc.index[terc == tq]
            dr = (fut[idx] - s[idx])
            med = dr.median()
            up = idx[(dr > med).values]
            dn = idx[(dr <= med).values | dr.isna().values]
            recs.append(dict(date=d0, tercile=tn, ex=f[idx].mean() - allm,
                             up=f[up].mean() - allm if len(up) else np.nan,
                             dn=f[dn].mean() - allm if len(dn) else np.nan,
                             up_minus_dn=(f[up].mean() - f[dn].mean()) if len(up) and len(dn) else np.nan))
    R = pd.DataFrame(recs)
    for tn in ['bottom', 'middle', 'top']:
        x = R[R.tercile == tn].set_index('date')
        for col in ['ex', 'up', 'dn', 'up_minus_dn']:
            for wn, (a, b) in {'2000-2023': (MAIN[0], '2023-07-31'), '2000-2010': (MAIN[0], '2010-12-31'),
                               '2011-2023': ('2011-01-01', '2023-07-31')}.items():
                m, t, n = mt_sort(x[col], a, b)
                add(cl, 'f5_future_liquidity_risers', f'liquidity_{tn}_tercile_{col}', wn, 'pct_per_month', m, t, n,
                    'up/dn = top/bottom half of the change in liquidity percentile over the next 24 months; '
                    'next-month return minus universe mean (look-ahead split, diagnostic only)')
    # f6: is the premium larger long before 2025? slope of the monthly D10/D9 spreads on years to 2025-08
    for sn in ['D10_log_traded_value', 'D9_amihud']:
        ss = xs_sort(SIG[sn], ALL)
        ss = ss.loc[MAIN[0]:MAIN[1]]
        yrs = (pd.Timestamp(MAIN[1]) - ss.index).days / 365.25
        bb, tt, n = ols_nw(ss.hl.values * 100, np.column_stack([np.ones(len(ss)), yrs]), 2)
        add(cl, 'f6_distance_to_2025', f'{sn}_hl', 'MAIN', 'slope_pct_per_month_per_year_to_2025', bb[1], tt[1], n,
            f'intercept (at 2025-08) {bb[0]:.2f}; D10: negative slope = premium larger long before 2025; D9: positive')


# ------------------------------------------------------------------------------------------------- C-g extension
def ext_g():
    cl = 'C-g'
    sig = SIG['D1_mom12_1']
    post_mem, post_all = [], []
    for Y in ['2005-12-31', '2010-12-31', '2015-12-31', '2020-12-31']:
        Yd, mem, _ = members_at(Y, .5)
        bpost = min(Yd + pd.DateOffset(years=5), pd.Timestamp(MAIN[1]))
        post_mem.append(xs_sort(sig, mem, 5, 15, Yd, bpost))
        post_all.append(xs_sort(sig, ALL, 5, 25, Yd, bpost))
    QM, QA = pd.concat(post_mem).sort_index(), pd.concat(post_all).sort_index()
    j = QM.join(QA, lsuffix='_mem', rsuffix='_all', how='inner')
    m, t, n = mt_sort(j.top_ex_mem - j.top_ex_all)
    add(cl, 'g5_pseudo_membership_contrast', 'D1_post_members_top_ex_minus_post_all_top_ex_paired', 'pooled_4_windows',
        'pct_per_month', m, t, n, 'members = top half by liquidity at Y; same months')
    # pre2018 universe, D1 top_ex by subperiod with value weights (complements g1)
    ss = xs_sort(sig, PRE, weight=LIQ60)
    for k, (a, b) in PERS.items():
        m, t, n = mt_sort(ss.top_ex_vw, a, b)
        add(cl, 'g5_pseudo_membership_contrast', 'D1_pre2018_top_ex_vw', k, 'pct_per_month', m, t, n)


if __name__ == '__main__':
    for fn in [replication_checks, claim_a, claim_b, claim_c, claim_d, claim_e, claim_f, claim_g,
               ext_a, ext_b, ext_c, ext_d, ext_e, ext_f, ext_g]:
        t1 = time.time()
        fn()
        print(f'{fn.__name__}: {time.time() - t1:.1f}s, rows {len(ROWS)}', flush=True)
    res = pd.DataFrame(ROWS)
    res.to_csv(OUT, index=False)
    print(f'wrote {OUT} ({len(res)} rows) in {time.time() - T0:.0f}s')
