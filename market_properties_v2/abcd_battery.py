"""Market properties v2, families A-D exactly as pre-registered in PLAN.md: time-series structure (A), overnight and
gaps (B), calendar (C), cross-sectional sorts (D). Writes results/{A,B,C,D}_tests.csv and results/ABCD_context.csv.
Run: python market_properties_v2/abcd_battery.py"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel import load, universe, MAIN
from mpstats import Mean, Dummy, row, event_series, sort_series, ols_nw

OUT = HERE / 'results'
UNIVS = ('all', 'pre2018')
P = load()
CAL = P['C'].index
CONTEXT = []


def ctx(test_id, item, value):
    CONTEXT.append(dict(test_id=test_id, item=item, value=value))


class Slope:
    """OLS slope of y on x (both Series on the market calendar), NW t."""
    def __init__(self, y, x, lags):
        self.y, self.x, self.lags = y, x, lags

    def at(self, a, b):
        y, x = self.y.loc[a:b], self.x.reindex(self.y.index).loc[a:b]
        if (y.notna() & x.notna()).sum() < 20:
            return np.nan, np.nan, 0
        coef, t, n = ols_nw(y.values, np.column_stack([np.ones(len(x)), x.values]), self.lags)
        return coef[1], t[1], n


def cols(u):
    return universe(P, u)


def ew_ret(u):
    """Equal-weight daily simple return of a universe (same construction as panel idx_ret)."""
    return np.expm1(P['r_cc'][cols(u)]).mean(axis=1)


def daily_mean(frame):
    return frame.mean(axis=1)


def emit(rows, test_id, family, desc, unit, make, scale, **kw):
    """make(u) -> stat object for universe u."""
    rows.append(row(test_id, family, desc, unit, make('all'), make('pre2018'), scale=scale, **kw))


# ---------------------------------------------------------------- A. time-series structure (raw returns)
def family_a():
    rows = []
    lnP, T = P['lnP'], P['T']

    def tsmom(u, past, h):
        c = cols(u)
        s = np.sign(past[c]).where(T[c])
        y = P['fo'][h][c]
        return daily_mean((s * y).where(s.notna() & y.notna()))

    specs = [('A1.2', 'TSMOM(5,5): sign(5-day return) x fo[5]', lnP - lnP.shift(5), 5, 5),
             ('A1.3', 'TSMOM(20,20): sign(20-day return) x fo[20]', lnP - lnP.shift(20), 20, 20),
             ('A1.4', 'TSMOM(60,20): sign(60-day return) x fo[20]', lnP - lnP.shift(60), 20, 20),
             ('A1.5', 'TSMOM(120 skip 20,20): sign(lnP[t-21]-lnP[t-141]) x fo[20]', lnP.shift(21) - lnP.shift(141), 20, 20),
             ('A1.6', 'TSMOM(250 skip 20,20): sign(lnP[t-21]-lnP[t-252]) x fo[20]', lnP.shift(21) - lnP.shift(252), 20, 20)]
    emit(rows, 'A1.1', 'A', 'TSMOM(1,1): sign(r_cc[t]) x fo[1] (next-day Open->Close)', 'bps/day',
         lambda u: Mean(tsmom(u, P['r_cc'], 1), 5), 1e4, surv_risk='low', exploit='standalone',
         cost_note='daily turnover; compare with 0.40%/0.90% round trip per trade')
    for tid, desc, past, h, lags in specs:
        emit(rows, tid, 'A', desc, '% per window', lambda u, past=past, h=h, lags=lags: Mean(tsmom(u, past, h), lags), 100,
             surv_risk='medium', exploit='standalone', cost_note='one round trip per window')
    emit(rows, 'A1.7', 'A', 'Index AC1: slope of idx_ret[t+1] on idx_ret[t]', 'slope',
         lambda u: Slope(ew_ret(u).shift(-1), ew_ret(u), 5), 1., surv_risk='low', exploit='descriptive',
         notes='equal-weight survivor proxy, not IHSG; close-to-close (not tradable as such)')

    def idx_tsmom(u):
        c = cols(u)
        lvl = np.log1p(ew_ret(u).fillna(0)).cumsum()
        s = np.sign(lvl - lvl.shift(20))
        y = P['fo'][20][c].mean(axis=1)
        return (s * y).where(s.notna() & y.notna())
    emit(rows, 'A1.8', 'A', 'Index TSMOM(20,20): sign(20-day idx log return) x EW mean fo[20]', '% per window',
         lambda u: Mean(idx_tsmom(u), 20), 100, surv_risk='medium', exploit='timing',
         notes='long/short the EW universe; long-only use = in when sign>0')
    for u in UNIVS:
        for tid, past, h in [('A1.1', P['r_cc'], 1)] + [(s[0], s[2], s[3]) for s in specs]:
            ser = tsmom(u, past, h)
            ctx(tid, f'{u}_days', int(ser.loc[MAIN[0]:MAIN[1]].notna().sum()))
    return rows


# ---------------------------------------------------------------- B. overnight, intraday, gaps
def family_b():
    rows = []
    T = P['T']
    emit(rows, 'B1', 'B', 'Mean overnight log return r_on (EW over stocks)', 'bps/day',
         lambda u: Mean(daily_mean(P['r_on'][cols(u)]), 5), 1e4, surv_risk='low', exploit='descriptive')
    emit(rows, 'B2', 'B', 'Mean intraday log return r_id (EW over stocks)', 'bps/day',
         lambda u: Mean(daily_mean(P['r_id'][cols(u)]), 5), 1e4, surv_risk='low', exploit='descriptive')

    def same_day(u, up):
        c = cols(u)
        ron, rid = P['r_on'][c], P['r_id'][c]
        ab = rid.sub(rid.mean(axis=1), axis=0)
        ev = (ron > np.log(1.02)) if up else (ron < np.log(.98))
        ev = ev & rid.notna()
        ctx('B3' if up else 'B4', f'{u}_events_MAIN', int(ev.loc[MAIN[0]:MAIN[1]].values.sum()))
        ctx('B3' if up else 'B4', f'{u}_raw_intraday_bps_event_weighted',
            float(rid.where(ev).loc[MAIN[0]:MAIN[1]].stack().mean() * 1e4))
        return ab.where(ev).mean(axis=1)
    emit(rows, 'B3', 'B', 'Gap up >2%: same-day abnormal intraday return (Open->Close)', 'bps',
         lambda u: Mean(same_day(u, True), 5), 1e4, surv_risk='low', exploit='filter',
         cost_note='as a standalone short it is not available (long only); as a filter: do not buy gap-ups at the Open')
    emit(rows, 'B4', 'B', 'Gap down >2%: same-day abnormal intraday return (Open->Close)', 'bps',
         lambda u: Mean(same_day(u, False), 5), 1e4, surv_risk='medium', exploit='standalone',
         cost_note='buy at Open, sell at Close: needs > 0.90% (B) / 0.40% (A) round trip')

    def gap_fwd(u, up):
        c = cols(u)
        ron = P['r_on'][c]
        ev = ((ron > np.log(1.02)) if up else (ron < np.log(.98))) & T[c]
        s, n = event_series(P, ev, 5, u)
        ctx('B5' if up else 'B6', f'{u}_events', n)
        return s
    emit(rows, 'B5', 'B', 'Gap up >2% on day t: abnormal fo[5] (entry Open t+1)', '% per 5 days',
         lambda u: Mean(gap_fwd(u, True), 5), 100, surv_risk='low', exploit='filter')
    emit(rows, 'B6', 'B', 'Gap down >2% on day t: abnormal fo[5] (entry Open t+1)', '% per 5 days',
         lambda u: Mean(gap_fwd(u, False), 5), 100, surv_risk='medium', exploit='standalone')
    return rows


# ---------------------------------------------------------------- C. calendar
def closures():
    """Consecutive trading dates with weekdays missing between them."""
    d = CAL
    gaps = pd.DataFrame({'d0': d[:-1], 'd1': d[1:]})
    gaps['closed_weekdays'] = [np.busday_count((a + pd.Timedelta(days=1)).date(), b.date()) for a, b in zip(gaps.d0, gaps.d1)]
    return gaps[gaps.closed_weekdays >= 1].reset_index(drop=True)


EID = ['1995-03-02', '1996-02-20', '1997-02-09', '1998-01-30', '1999-01-19', '2000-01-08', '2000-12-27', '2001-12-16',
       '2002-12-06', '2003-11-25', '2004-11-14', '2005-11-03', '2006-10-24', '2007-10-13', '2008-10-01', '2009-09-20',
       '2010-09-10', '2011-08-30', '2012-08-19', '2013-08-08', '2014-07-28', '2015-07-17', '2016-07-06', '2017-06-25',
       '2018-06-15', '2019-06-05', '2020-05-24', '2021-05-13', '2022-05-02', '2023-04-22', '2024-04-10', '2025-03-31']


def lebaran_closures(cl):
    def xmas(a, b):
        span = pd.date_range(a + pd.Timedelta(days=1), b - pd.Timedelta(days=1))
        return any((x.month == 12 and x.day >= 24) or (x.month == 1 and x.day <= 2) for x in span)
    c = cl[[not xmas(a, b) for a, b in zip(cl.d0, cl.d1)]].copy()
    c['year'] = c.d0.dt.year
    return c.sort_values(['year', 'closed_weekdays', 'd0'], ascending=[True, False, True]).groupby('year').head(1)


def family_c():
    rows = []
    d = pd.Series(CAL, index=CAL)
    mon = CAL.to_period('M')
    fwd = d.groupby(mon).cumcount()
    back = d.groupby(mon).cumcount(ascending=False)
    tom = pd.Series((fwd < 3) | (back == 0), index=CAL)
    dow = pd.Series(CAL.dayofweek, index=CAL)
    month = pd.Series(CAL.month, index=CAL)
    cl = closures()
    leb = lebaran_closures(cl)
    pos = {x: i for i, x in enumerate(CAL)}
    pre = pd.Series(False, index=CAL)
    post = pd.Series(False, index=CAL)
    for a, b in zip(leb.d0, leb.d1):
        pre.iloc[max(0, pos[a] - 4):pos[a] + 1] = True
        post.iloc[pos[b]:pos[b] + 5] = True
    preh = pd.Series(CAL.isin(cl.d0), index=CAL)
    eid = pd.to_datetime(EID)
    for a, b, w in zip(leb.d0, leb.d1, leb.closed_weekdays):
        near = eid[(eid > a - pd.Timedelta(days=3)) & (eid < b + pd.Timedelta(days=3))]
        ctx('C6', f'closure_{a.date()}_{b.date()}', f'{w} weekdays; Eid inside: {",".join(str(x.date()) for x in near) or "NO"}')
    for e in eid:
        if not any((e > a - pd.Timedelta(days=3)) & (e < b + pd.Timedelta(days=3)) for a, b in zip(leb.d0, leb.d1)):
            ctx('C6', f'eid_not_matched_{e.date()}', 'pre-registered rule picked another closure that year')
    specs = [('C1', 'Turn of month (last + first 3 trading days) minus other days', tom),
             ('C2', 'Monday minus other days', dow == 0), ('C3', 'Friday minus other days', dow == 4),
             ('C4', 'December minus other months', month == 12), ('C5', 'January minus other months', month == 1),
             ('C6', 'Pre-Lebaran: 5 trading days before the year\'s longest non-Christmas closure minus other days', pre),
             ('C7', 'Post-Lebaran: first 5 trading days after that closure minus other days', post),
             ('C8', 'Pre-holiday: last trading day before a closure of >=1 weekday minus other days', preh)]
    for tid, desc, D in specs:
        emit(rows, tid, 'C', desc, 'bps/day', lambda u, D=D: Dummy(ew_ret(u), D, 5), 1e4, surv_risk='low', exploit='timing',
             cost_note='needs entering/exiting around the dates: round trip 0.40%/0.90% vs a few bps/day')
        ctx(tid, 'days_flagged_MAIN', int(D.loc[MAIN[0]:MAIN[1]].sum()))
    return rows


# ---------------------------------------------------------------- D. cross-sectional sorts
def family_d():
    rows = []
    lnP, lnH, r = P['lnP'], P['lnH'], P['r_cc']
    simple = np.expm1(r)
    value = P['value']
    dlnP = lnP.diff().abs()

    def beta(u):
        c = cols(u)
        x = np.log1p(ew_ret(u))
        Y = r[c]
        X = pd.DataFrame(np.repeat(x.values[:, None], len(c), 1), index=Y.index, columns=c).where(Y.notna())
        Yv = Y.where(X.notna())
        roll = lambda f: f.rolling(60, min_periods=40)
        n = roll(Yv.notna().astype(float)).sum()
        mx, my = roll(X).mean(), roll(Yv).mean()
        cov = roll(X * Yv).mean() - mx * my
        var = roll(X * X).mean() - mx * mx
        return (cov / var).where(n >= 40)

    sigs = {
        'D1': ('MOM12-1: lnP[t-21]-lnP[t-252]', lambda u: lnP.shift(21) - lnP.shift(252), 'M', 'medium'),
        'D2': ('MOM6-1: lnP[t-21]-lnP[t-141]', lambda u: lnP.shift(21) - lnP.shift(141), 'M', 'medium'),
        'D3': ('MOM3-1: lnP[t-21]-lnP[t-84]', lambda u: lnP.shift(21) - lnP.shift(84), 'M', 'medium'),
        'D4': ('REV1M: lnP[t]-lnP[t-21]', lambda u: lnP - lnP.shift(21), 'M', 'medium'),
        'D5': ('REV1W: lnP[t]-lnP[t-5] (weekly)', lambda u: lnP - lnP.shift(5), 'W', 'medium'),
        'D6': ('52-week-high proximity: lnP - max(lnH[t-251..t])', lambda u: lnP - lnH.rolling(252, min_periods=200).max(), 'M', 'medium'),
        'D7': ('Volatility: std r_cc 60d', lambda u: r.rolling(60, min_periods=40).std(), 'M', 'high'),
        'D8': ('MAX: max r_cc 21d', lambda u: r.rolling(21, min_periods=15).max(), 'M', 'high'),
        'D9': ('Amihud: mean |simple r|/value 60d', lambda u: (simple.abs() / value).rolling(60, min_periods=40).mean(), 'M', 'high'),
        'D10': ('Liquidity: log mean traded value 60d', lambda u: np.log(value.rolling(60, min_periods=40).mean()), 'M', 'high'),
        'D11': ('Signed ER60: (lnP[t]-lnP[t-60])/sum|dlnP|,60', lambda u: (lnP - lnP.shift(60)) / dlnP.rolling(60).sum(), 'M', 'medium'),
        'D12': ('Beta 60d vs log(1+idx_ret)', beta, 'M', 'medium'),
    }
    for tid, (desc, make_sig, freq, risk) in sigs.items():
        stats = {}
        for u in UNIVS:
            ss = sort_series(P, make_sig(u), u, n=5, freq=freq, min_stocks=25)
            stats[u] = Mean(ss.hl, 2)
            m = ss.loc[MAIN[0]:MAIN[1]]
            for k in ['q0', 'q1', 'q2', 'q3', 'q4', 'top_ex', 'bot_ex']:
                ctx(tid, f'{u}_{k}_mean_pct', float(m[k].mean() * 100))
            ctx(tid, f'{u}_periods_MAIN', len(m))
            ctx(tid, f'{u}_median_stocks', float(m.n_stocks.median()))
        unit = '%/week' if freq == 'W' else '%/month'
        rows.append(row(tid, 'D', f'{desc}; Q5 (high) minus Q1 (low)', unit, stats['all'], stats['pre2018'], scale=100,
                        surv_risk=risk, exploit='filter',
                        cost_note='as ranking inside existing entries no extra cost; standalone monthly rebalance turnover not modelled'))
    return rows


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    for name, fn in [('A', family_a), ('B', family_b), ('C', family_c), ('D', family_d)]:
        res = pd.DataFrame(fn())
        res.to_csv(OUT / f'{name}_tests.csv', index=False)
        show = ['test_id', 'unit', 'eff_MAIN', 't_MAIN', 'eff_P1', 'eff_P2', 'eff_P3', 'eff_P4', 'eff_P0', 'eff_pre2018',
                'signs_P1_P4', 'pass_t3', 'pass_stable', 'pass_pre2018']
        pd.set_option('display.width', 250)
        print(res[show].round(3).to_string(index=False), flush=True)
    pd.DataFrame(CONTEXT).to_csv(OUT / 'ABCD_context.csv', index=False)
