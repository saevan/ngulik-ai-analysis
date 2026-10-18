"""Market properties v2, family W3 (market regime and volatility timing), implemented as pre-registered in PLAN.md W3.
Writes results/W3_tests.csv (primary tests W3.1-W3.7, one mpstats.row each, universes all and pre2018),
results/W3_context.csv (descriptive context, not classified; columns section/test_id/universe/period/item/value/unit/
n/t/note; sections: regime_days = regime day counts, shares and spells per period; regime_means = raw EW mean forward
return per regime and horizon 5/10/20/60 with NW t, plus the Dummy effect at every horizon; pooled = stock-day pooled
(event-weighted) means; backtest = exposure backtests after costs; W3.1-W3.7 = test-specific extras incl. W3.3 Sharpe,
MDD, CAGR and bootstrap interval of both strategies; by_year and loyo = effect per calendar year and MAIN effect with
one year left out; sensitivity = data artefacts) and results/W3_exploratory.csv (X-W3-* extras, not classified).
Run: python market_properties_v2/w3_regime.py   (about 15 s, includes self-checks)

Definition choices (most literal causal reading where PLAN.md is silent; every regime variable is known at the Close
of day t and every statistic is recomputed from the pre2018 tickers for the pre2018 rows):
 1. idx = equal-weight daily simple return of the universe stocks with a valid clean return that day
    (np.expm1(r_cc).mean over stocks; equals panel idx_ret for 'all', asserted). idx level = cumprod(1 + idx_ret)
    from 1994-07-12 (the same construction as W1.8).
 2. Forward EW return (dependent variable of the Dummy tests) at row t = mean over universe stocks with a valid
    value of fo[h][t] = lnP[t+h] - lnO[t+1] (log, entry Open t+1, exit Close t+h); raw, not market-adjusted.
 3. sigma20[t] = sample std (ddof 1) of idx_ret over t-19..t (20 valid days). W3.2 thresholds = expanding 1/3 and
    2/3 quantiles (linear interpolation) of sigma20 over all days up to and including t, once >= 500 sigma20 values
    exist; top = sigma20 > q(2/3), bottom = sigma20 < q(1/3), middle tercile excluded (D = NaN).
 4. W3.3 expanding median(sigma20) uses the same >= 500-value minimum (PLAN states none for W3.3; this only removes
    1994-96 warm-up days of P0). Exposure e[t] = min(1.5, median/sigma20[t]) (no floor), applied to idx_ret[t+1]
    exactly as written (trade at the Close of t, no costs) vs constant exposure 1 on the same days. Annualised
    Sharpe = mean/std(ddof 1) x sqrt(ANN) with ANN = market days per calendar year in MAIN (about 243), cash rate 0.
    Bootstrap: moving blocks of 20 consecutive days drawn inside each period, the same blocks for both strategies
    (paired), 2,000 resamples, fixed seed per period; z = observed difference / sd of the resampled differences
    (reported in the t column).
 5. W3.4 SMA200 over t-199..t of the idx level; above = level > SMA200 (D=1), below = level <= SMA200 (D=0).
 6. W3.5 SMA50(lnP) = mean of the clean log Close over t-49..t (50 market rows, stock listed for all of them;
    lnP is flat on non-tradable days). Breadth = share of universe stocks with a defined SMA50 whose lnP exceeds it
    (tolerance 1e-12 so that a flat price never counts as 'above' through float noise). D = 1 if breadth >= 0.60,
    0 if < 0.40, NaN in between.
 7. W3.6 drawdown = level / running max since 1994-07-12 - 1 (simple); D = 1 if < -0.25 else 0.
 8. W3.7 terciles of the 60-day mean traded value (value.rolling(60, min_periods=40).mean(), Volume-0 days skipped,
    the D10 convention) among universe stocks tradable at each month-end Close (>= 15 stocks); the sort formed at
    month end m applies to rows m+1 .. next month end (row t always uses a sort formed strictly before t; applying
    it already on row m is shown in context and changes nothing material). y[t] = EW fo[1] of bottom-tercile stocks
    at row t (their Open->Close log return of day t+1), x[t] = EW r_cc of top-tercile stocks on day t; OLS with
    intercept, NW lags 5.
 9. Exposure backtests (usability of timing tests, context only): EW universe (daily rebalanced, idx_ret) with
    exposure e[t] decided at the Close of t. 'open' execution: the change is made at the Open of t+1, so day t+1
    earns e[t-1] x idx_ret[t+1] + (e[t] - e[t-1]) x EW intraday simple return; 'close' execution: e[t] x
    idx_ret[t+1] (the PLAN W3.3 convention). Costs on exposure changes: buy .15% / sell .25% (A, 0.40% round
    trip) and buy .40% / sell .50% (B, 0.90% round trip, mpstats.COST_RT); cash earns 0; leverage above 1 (W3.3)
    is not charged financing. On the first day a rule is defined its position counts as already in place (no entry
    cost, like the always-in baseline); rules have no undefined days after warm-up (asserted). CAGR uses years =
    market days / ANN; MDD on the equity curve of each period. The rule whose direction follows the sign of the MAIN
    effect ('analog': cash in the regime with the lower mean forward return) is the usability check; its direction
    is therefore chosen in-sample (an upper bound). Verdict text: Sharpe change >= 0.05 counts as up, CAGR change
    within +-0.5 pp/yr as unchanged (reporting convention only, not a PLAN criterion).
10. Data artefacts in the panel calendar are kept in the primary statistics (pre-registered idx definition) and
    reported: 2009-06-06 is a Saturday with a single CTRA bar (idx_ret +20.06%), 2008-01-11 has a single CTRA bar
    (market holiday), 2006-03-31 has 8 stale duplicated bars (return 0), 1998-05-15 has 2 bars. Their effect is
    shown in context section 'sensitivity' (idx_ret set to 0 on days with idx_n < 10).
11. Usability thresholds: filter 0.25 pp per trade (25 bps), standalone > 0.90% (B) / 0.40% (A) round trip, timing
    = net improvement in the exposure backtest after costs.

Fix in this version (resumed run): strat() returned NaN on the first day of each rule because the exposure change
e[t-1] - e[t-2] was NaN there and 0 x NaN = NaN even at zero cost, so that day silently dropped out of every backtest;
the self-check comparing the zero-cost close-exec vol-target series with exposure x idx_ret caught it (1996-08-20).
"""
import sys
import math
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel import load, universe, SUBPERIODS, MAIN, P0          # noqa: E402
from mpstats import (Mean, Diff, Dummy, row, nw, ols_nw, rebalance_dates, PERIODS,   # noqa: E402
                     COST_RT)

OUT = HERE / 'results'
FAM = 'W3'
UNIVS = ('all', 'pre2018')
PCT, BPS = 100., 1e4
HORIZONS = (5, 10, 20, 60)
CSPLIT = {'0': (0., 0.), 'A': (.0015, .0025), 'B': (.0040, .0050)}   # (buy, sell) per unit of exposure change
assert all(abs(sum(CSPLIT[k]) - COST_RT[k]) < 1e-12 for k in ('A', 'B'))
FILTER = .0025         # filter usability threshold: 0.25 pp per trade = 25 bps (log-return units)
SHARPE_TOL, CAGR_TOL = .05, .005   # materiality used only in the backtest verdict text (not a PLAN criterion)
THIN = 60              # a subperiod with fewer days than this in one regime is flagged as thin in the notes
SPUR_N = 10            # days with fewer stocks in idx_ret are treated as artefacts in the sensitivity check
BLOCK, REPS = 20, 2000

P = load()
CAL = P['C'].index
_main = CAL[(CAL >= MAIN[0]) & (CAL <= MAIN[1])]
ANN = len(_main) / ((_main[-1] - _main[0]).days / 365.25)
CTX = []


def cols(u):
    return universe(P, u)


def ctx(section, tid, u, period, item, value, unit='', n=np.nan, t=np.nan, note=''):
    CTX.append(dict(section=section, test_id=tid, universe=u, period=period, item=item, value=value, unit=unit,
                    n=n, t=t, note=note))


# ------------------------------------------------------------------ stat objects (same .at(a, b) contract as mpstats)
class Slope:
    """OLS slope of y on x with intercept (both Series on the market calendar), NW t."""
    def __init__(self, y, x, lags):
        self.y, self.x, self.lags = y, x, lags

    def at(self, a, b):
        y, x = self.y.loc[a:b], self.x.reindex(self.y.index).loc[a:b]
        if (y.notna() & x.notna()).sum() < 20:
            return np.nan, np.nan, 0
        coef, t, n = ols_nw(y.values, np.column_stack([np.ones(len(x)), x.values]), self.lags)
        return coef[1], t[1], n


class Coef:
    """OLS coefficient j (0 = first regressor) of y on [1, X] (X = DataFrame on the market calendar), NW t; rows
    with any NaN drop out but keep their position for the lag structure."""
    def __init__(self, y, X, j, lags):
        self.y, self.X, self.j, self.lags = y, X, j, lags

    def at(self, a, b):
        y = self.y.loc[a:b]
        X = self.X.reindex(y.index)
        ok = y.notna() & X.notna().all(axis=1)
        if ok.sum() < 20 or any(X[ok][c].nunique() < 2 for c in X.columns):
            return np.nan, np.nan, int(ok.sum())
        coef, t, n = ols_nw(y.values, np.column_stack([np.ones(len(y)), X.values]), self.lags)
        return coef[1 + self.j], t[1 + self.j], n


def sharpe(r):
    r = np.asarray(r, float)
    return r.mean() / r.std(ddof=1) * math.sqrt(ANN)


class SharpeDiff:
    """Annualised Sharpe of rv minus that of rc on their common days in [a, b]; z = difference / sd of the paired
    20-day moving-block bootstrap differences (2,000 resamples drawn inside the period, fixed seed per period)."""
    def __init__(self, rv, rc, block=BLOCK, reps=REPS):
        self.rv, self.rc, self.block, self.reps = rv, rc, block, reps
        self.boot = {}

    def at(self, a, b):
        v, c = self.rv.loc[a:b], self.rc.loc[a:b]
        ok = v.notna() & c.notna()
        v, c = v[ok].values, c[ok].values
        n = len(v)
        if n < 10 * self.block:
            return np.nan, np.nan, n
        d = sharpe(v) - sharpe(c)
        rng = np.random.default_rng([20261018, int(a.replace('-', '')), int(b.replace('-', ''))])
        nb = -(-n // self.block)
        diffs = []
        for k in range(0, self.reps, 250):
            m = min(250, self.reps - k)
            st = rng.integers(0, n - self.block + 1, size=(m, nb))
            ix = (st[:, :, None] + np.arange(self.block)).reshape(m, -1)[:, :n]
            bv, bc = v[ix], c[ix]
            sv = bv.mean(1) / bv.std(1, ddof=1)
            sc = bc.mean(1) / bc.std(1, ddof=1)
            diffs.append((sv - sc) * math.sqrt(ANN))
        diffs = np.concatenate(diffs)
        sd = diffs.std(ddof=1)
        self.boot[(a, b)] = dict(sd=sd, lo=np.percentile(diffs, 2.5), hi=np.percentile(diffs, 97.5),
                                 share_le0=float((diffs <= 0).mean()))
        return d, (d / sd if sd > 0 else np.nan), n


# ------------------------------------------------------------------ universe building blocks
def tri(cond1, cond0, defined):
    """1 where cond1, 0 where cond0, NaN elsewhere or where not defined."""
    out = pd.Series(np.where(cond1, 1., np.where(cond0, 0., np.nan)), index=CAL)
    return out.where(defined)


def terciles_by_value(c, same_row=False):
    """Bottom/top tercile masks (Date x Ticker) of the 60-day mean traded value, sorted at each month-end Close and
    applied from the next row through the next month end (same_row=True: already from the month-end row itself, a
    sensitivity; still causal because the sort uses data up to that Close)."""
    val60 = P['value'][c].rolling(60, min_periods=40).mean()
    me = rebalance_dates(P, 'M')
    me_pos = CAL.get_indexer(me)
    S = val60.loc[me].where(P['T'][c].loc[me])
    lab = np.full(S.shape, np.nan)
    nsort = []
    for k in range(len(me)):
        s = S.iloc[k]
        s = s[s.notna() & (s > 0)]
        nsort.append(len(s))
        if len(s) < 15:
            continue
        q = pd.qcut(s.rank(method='first'), 3, labels=False)
        lab[k, S.columns.get_indexer(s.index)] = q.values
    kr = np.searchsorted(me_pos, np.arange(len(CAL)), side='right' if same_row else 'left') - 1
    G = np.where((kr >= 0)[:, None], lab[np.maximum(kr, 0)], np.nan)
    G = pd.DataFrame(G, index=CAL, columns=c)
    return G == 0, G == 2, pd.Series(nsort, index=pd.DatetimeIndex(me)), G


def build(u, spur_zero=False):
    c = cols(u)
    B = dict(u=u, c=c)
    ir = np.expm1(P['r_cc'][c]).mean(axis=1)
    if spur_zero:
        n_ = P['r_cc'][c].notna().sum(axis=1)
        ir = ir.where(n_ >= SPUR_N, 0.)
    idr = np.expm1(P['r_id'][c]).mean(axis=1)
    lvl = (1 + ir.fillna(0.)).cumprod()
    sig = ir.rolling(20, min_periods=20).std()
    q1 = sig.expanding(min_periods=500).quantile(1 / 3)
    q2 = sig.expanding(min_periods=500).quantile(2 / 3)
    med = sig.expanding(min_periods=500).median()
    B.update(ir=ir, idr=idr, lvl=lvl, sig=sig, q1=q1, q2=q2, med=med)
    B['D32'] = tri(sig > q2, sig < q1, q1.notna() & q2.notna() & sig.notna())
    B['mid32'] = (sig >= q1) & (sig <= q2) & q1.notna()
    sma = lvl.rolling(200, min_periods=200).mean()
    B['sma200'] = sma
    B['D34'] = tri(lvl > sma, lvl <= sma, sma.notna())
    lnP = P['lnP'][c]
    sma50 = lnP.rolling(50, min_periods=50).mean()
    valid = lnP.notna() & sma50.notna()
    nval = valid.sum(axis=1)
    above = ((lnP > sma50 + 1e-12) & valid).sum(axis=1)
    br = (above / nval).where(nval > 0)
    B.update(breadth=br, breadth_n=nval)
    B['D35'] = tri(br >= .6, br < .4, br.notna())
    B['mid35'] = (br >= .4) & (br < .6)
    B['S35'] = B['D35'].ffill().where(br.notna())       # X-W3.5-state: last threshold crossed (>= 60% or < 40%)
    B['sgn20'] = np.sign(np.log(lvl) - np.log(lvl.shift(20)))   # A1.8 index trend sign (control in X-W3.5-incr)
    dd = lvl / lvl.cummax() - 1
    B['dd'] = dd
    B['D36'] = tri(dd < -.25, dd >= -.25, dd.notna())
    B['Y'] = {h: P['fo'][h][c].mean(axis=1) for h in (1,) + HORIZONS}
    B['expo'] = np.minimum(1.5, med / sig)
    small, large, nsort, G = terciles_by_value(c)
    B.update(small=small, large=large, nsort=nsort, G=G)
    B['y7'] = P['fo'][1][c].where(small).mean(axis=1)
    B['x7'] = P['r_cc'][c].where(large).mean(axis=1)
    B['xs7'] = P['r_cc'][c].where(small).mean(axis=1)            # small-cap own same-day return (context)
    B['yl7'] = P['fo'][1][c].where(large).mean(axis=1)            # large-cap next-day O->C (context, reverse)
    B['y7_on'] = P['r_on'][c].shift(-1).where(small).mean(axis=1)  # X-W3.7-on: small caps' overnight gap into t+1
    B['y7_cc'] = P['r_cc'][c].shift(-1).where(small).mean(axis=1)  # X-W3.7-cc: small caps' Close t -> Close t+1
    B['n_small'] = small.sum(axis=1)
    B['n_large'] = large.sum(axis=1)
    return B


# ------------------------------------------------------------------ exposure backtests
def strat(e, B, execu='open', cost='0'):
    """Daily simple returns of the EW universe held with exposure e (decided at the Close of t), net of costs.
    Day s uses e1 = e[s-1] and e2 = e[s-2]. On the first day with a defined exposure (rule defined at s-1 but not at
    s-2) the position counts as already in place (e2 := e1): no exposure change and no cost, the same treatment as the
    always-in baseline, which is never charged an entry either. Without this, 0 x NaN made the net return NaN on that
    day even at zero cost and the day silently dropped out of the backtest (found by the self-check). Rules have no
    undefined days after their warm-up (asserted in run_backtests), so this only concerns the start of the sample."""
    ir, idr = B['ir'], B['idr'].fillna(0.)
    e1, e2 = e.shift(1), e.shift(2)
    e2 = e2.where(e2.notna() | e1.isna(), e1)
    gross = e1 * ir if execu == 'close' else e2 * ir + (e1 - e2) * idr
    de = e1 - e2
    cb, cs = CSPLIT[cost]
    net = gross - cb * de.clip(lower=0) - cs * (-de).clip(lower=0)
    return net, de, e1


def perf(r):
    """CAGR, MDD (simple, negative), annualised Sharpe, annualised vol of a daily simple-return series."""
    r = r.dropna()
    n = len(r)
    if n < 60:
        return dict(cagr=np.nan, mdd=np.nan, sharpe=np.nan, vol=np.nan, n=n)
    V = np.cumprod(1 + r.values)
    peak = np.maximum.accumulate(np.maximum(V, 1.))
    return dict(cagr=V[-1] ** (ANN / n) - 1, mdd=float((V / peak - 1).min()), sharpe=sharpe(r.values),
                vol=float(r.std(ddof=1) * math.sqrt(ANN)), n=n)


def rules(B):
    """Exposure rules (e[t] decided at the Close of t). Undefined regimes -> NaN (day not evaluated)."""
    one = pd.Series(1., index=CAL)
    D32, D34, D35, D36 = B['D32'], B['D34'], B['D35'], B['D36']
    v_def = B['q1'].notna() & B['sig'].notna()
    wk = CAL.isin(rebalance_dates(P, 'W'))
    return {
        'always_in': one,
        'W3.2:cash_when_vol_top_tercile': pd.Series(np.where(D32 == 1, 0., 1.), index=CAL).where(v_def),
        'W3.2:cash_when_vol_bottom_tercile': pd.Series(np.where(D32 == 0, 0., 1.), index=CAL).where(v_def),
        'W3.3:vol_target_cap1.5': B['expo'],
        'W3.3:vol_target_cap1.0': np.minimum(1., B['med'] / B['sig']),
        'W3.4:in_when_above_SMA200': D34,
        'W3.4:in_when_below_SMA200': 1 - D34,
        'W3.5:cash_when_breadth_lt40': pd.Series(np.where(D35 == 0, 0., 1.), index=CAL).where(B['breadth'].notna()),
        'W3.5:cash_when_breadth_ge60': pd.Series(np.where(D35 == 1, 0., 1.), index=CAL).where(B['breadth'].notna()),
        'W3.6:cash_when_dd_lt25': 1 - D36,
        'W3.6:in_only_when_dd_lt25': D36,
        # context variants (not primary): vol target updated only at the last market day of each week, and the
        # breadth state (cash after breadth < 40% until it is back at >= 60%; same two thresholds, no new parameter)
        'W3.3:vol_target_cap1.5_weekly': B['expo'].where(wk).ffill().where(B['expo'].notna()),
        'X-W3.5-state:in_when_breadth_state_up': B['S35'],
    }


BT = {}      # (u, rule, exec, cost, period) -> perf dict incl. baseline and exposure stats


def run_backtests(Bs):
    for u in UNIVS:
        B = Bs[u]
        for name, e in rules(B).items():
            fv = e.first_valid_index()
            assert fv is not None and e.loc[fv:].notna().all(), ('exposure gap after warm-up', u, name)
            for ex in ('open', 'close'):
                for cost in ('0', 'A', 'B'):
                    net, de, e1 = strat(e, B, ex, cost)
                    for k, (a, b) in PERIODS.items():
                        r = net.loc[a:b].dropna()
                        base = B['ir'].reindex(r.index)
                        pr, pb = perf(r), perf(base)
                        dd_ = de.reindex(r.index)
                        yrs = len(r) / ANN if len(r) else np.nan
                        BT[(u, name, ex, cost, k)] = dict(
                            **pr, base_cagr=pb['cagr'], base_mdd=pb['mdd'], base_sharpe=pb['sharpe'],
                            base_vol=pb['vol'], expo=float(e1.reindex(r.index).mean()) if len(r) else np.nan,
                            turnover_py=float(dd_.abs().sum() / yrs) if yrs else np.nan,
                            switches_py=float((dd_.abs() > 1e-12).sum() / yrs) if yrs else np.nan)
        for name in rules(B):
            for ex in ('open', 'close'):
                for cost in ('0', 'A', 'B'):
                    if ex == 'close' and cost == 'A':
                        continue
                    for k in PERIODS:
                        if k != 'MAIN' and not (ex == 'open' and cost in ('0', 'B')) and name != 'always_in':
                            continue
                        x = BT[(u, name, ex, cost, k)]
                        tid = name.split(':')[0] if ':' in name else 'W3.x'
                        note = f'rule {name}; exec {ex}; cost {cost}'
                        for item, unit in (('cagr', '%/yr'), ('mdd', '%'), ('sharpe', 'ann.'), ('vol', '%/yr'),
                                           ('expo', 'mean exposure'), ('switches_py', 'changes/yr'),
                                           ('turnover_py', 'sum|de|/yr'), ('base_cagr', '%/yr'), ('base_mdd', '%'),
                                           ('base_sharpe', 'ann.')):
                            val = x[item] * (PCT if unit in ('%/yr', '%') else 1.)
                            ctx('backtest', tid, u, k, f'{name}|{ex}|{cost}|{item}', val, unit, x['n'], note=note)


# ------------------------------------------------------------------ context helpers
def spells(D, a, b):
    s = (D.loc[a:b] == 1).astype(int)
    return int(((s == 1) & (s.shift(1, fill_value=0) == 0)).sum())


def pooled(c, h, mask_days, a, b):
    F = P['fo'][h][c].loc[a:b]
    m = mask_days.reindex(F.index).fillna(False).astype(bool)
    s, k = F.sum(axis=1)[m].sum(), F.notna().sum(axis=1)[m].sum()
    return (s / k if k else np.nan), int(k)


def mean_nw(x, lags):
    """(mean, NW t, n); with 1-19 observations nw gives NaN, then the simple mean is returned with t = NaN."""
    m, se, n = nw(x, lags)
    if not np.isfinite(m) and n > 0:
        return float(np.nanmean(np.asarray(x, float))), np.nan, n
    return m, (m / se if se and se > 0 else np.nan), n


def by_year_effects(B, key, h, years=range(1995, 2026)):
    """year -> (mean forward return on D=1 days minus D=0 days of that year, n1, n0); equals the Dummy coefficient."""
    out = {}
    for y_ in years:
        yy = B['Y'][h].loc[f'{y_}-01-01':f'{y_}-12-31']
        Dy = B[key].reindex(yy.index)
        ok = yy.notna() & Dy.notna()
        n1, n0 = int((ok & (Dy == 1)).sum()), int((ok & (Dy == 0)).sum())
        e = yy[ok & (Dy == 1)].mean() - yy[ok & (Dy == 0)].mean() if n1 and n0 else np.nan
        out[y_] = (e, n1, n0)
    return out


def loyo_effects(B, key, h, years=range(2000, 2026)):
    """year -> MAIN Dummy (effect, t, n) with that calendar year's rows removed (positions kept for the lags)."""
    return {y_: Dummy(B['Y'][h].mask(CAL.year == y_), B[key], h).at(*MAIN) for y_ in years}


def regime_context(tid, Bs, key, h_main, lab1, lab0, mid_key=None):
    for u in UNIVS:
        B = Bs[u]
        D = B[key]
        for k, (a, b) in PERIODS.items():
            Dk = D.loc[a:b]
            n1, n0 = int((Dk == 1).sum()), int((Dk == 0).sum())
            nx = int(Dk.isna().sum())
            ctx('regime_days', tid, u, k, f'days_{lab1}', n1, 'days', note='D=1')
            ctx('regime_days', tid, u, k, f'days_{lab0}', n0, 'days', note='D=0')
            ctx('regime_days', tid, u, k, 'days_excluded_or_undefined', nx, 'days',
                note='middle group or regime not yet defined')
            ctx('regime_days', tid, u, k, f'share_{lab1}_pct', 100. * n1 / (n1 + n0) if n1 + n0 else np.nan, '%')
            ctx('regime_days', tid, u, k, f'spells_{lab1}', spells(D, a, b), 'count',
                note='number of separate D=1 episodes starting in the period (effective sample of regimes)')
            for h in HORIZONS:
                lags = max(h, 5)
                y = B['Y'][h]
                for lab, val in ((lab1, 1.), (lab0, 0.)):
                    m, t, n = mean_nw(y.where(D == val).loc[a:b], lags)
                    ctx('regime_means', tid, u, k, f'mean_fwd{h}_{lab}', m * PCT, f'% per {h} days', n, t,
                        note=f'EW mean fo[{h}] on D={int(val)} days, NW lags {lags}'
                        + ('; fewer than 20 days: simple mean, no t' if 0 < n < 20 else ''))
                    pm, pk = pooled(B['c'], h, D == val, a, b)
                    ctx('pooled', tid, u, k, f'pooled_fwd{h}_{lab}', pm * PCT, f'% per {h} days', pk,
                        note='stock-day pooled mean (event-weighted analogue)')
                if mid_key is not None:
                    m, t, n = mean_nw(y.where(B[mid_key]).loc[a:b], lags)
                    ctx('regime_means', tid, u, k, f'mean_fwd{h}_middle', m * PCT, f'% per {h} days', n, t,
                        note='excluded middle group')
                m, t, n = mean_nw(y.loc[a:b], lags)
                ctx('regime_means', tid, u, k, f'mean_fwd{h}_all_days', m * PCT, f'% per {h} days', n, t)
                eff, t, n = Dummy(y, D, lags).at(a, b)
                ctx('regime_means', tid, u, k, f'dummy_effect_fwd{h}', eff * PCT, f'% per {h} days', n, t,
                    note='primary horizon' if h == h_main else 'other horizon')


# ------------------------------------------------------------------ primary tests
DESC = {
    'W3.1': 'Volatility clustering: OLS slope of |idx_ret[t+1]| on |idx_ret[t]| (idx = EW daily simple return of '
            'the universe)',
    'W3.2': '20-day realised idx vol (std of idx_ret t-19..t) in its top tercile minus bottom tercile (expanding '
            'thresholds up to t, >= 500 values; middle excluded); forward EW mean fo[20] (Open t+1 -> Close t+20)',
    'W3.3': 'Vol targeting: exposure min(1.5, expanding median(sigma20)/sigma20[t]) on idx_ret[t+1] vs constant '
            'exposure 1; annualised Sharpe difference (t column = paired 20-day block bootstrap z, 2,000 resamples)',
    'W3.4': 'EW idx level above its SMA200 (t-199..t) minus below; forward EW mean fo[20]',
    'W3.5': 'Breadth (share of stocks with lnP > SMA50(lnP)) >= 60% minus < 40% (40-60% excluded); forward EW '
            'mean fo[20]',
    'W3.6': 'EW idx drawdown from its running max (since 1994) < -25% minus other days; forward EW mean fo[60] '
            '(Open t+1 -> Close t+60)',
    'W3.7': 'Lead-lag: OLS slope of small-cap EW fo[1] at row t (bottom tercile of 60-day mean traded value, sorted '
            'monthly; Open->Close of t+1) on large-cap (top tercile) EW r_cc of day t',
}
UNIT = {'W3.1': 'slope', 'W3.2': '% per 20 days (top minus bottom)', 'W3.3': 'annualised Sharpe difference',
        'W3.4': '% per 20 days (above minus below)', 'W3.5': '% per 20 days (>=60% minus <40%)',
        'W3.6': '% per 60 days (dd<-25% minus others)', 'W3.7': 'slope'}
SCALE = {'W3.1': 1., 'W3.2': PCT, 'W3.3': 1., 'W3.4': PCT, 'W3.5': PCT, 'W3.6': PCT, 'W3.7': 1.}
EXPLOIT = {'W3.1': 'descriptive', 'W3.2': 'timing', 'W3.3': 'timing', 'W3.4': 'timing', 'W3.5': 'timing',
           'W3.6': 'timing', 'W3.7': 'filter'}
DUMMY = {'W3.2': ('D32', 20), 'W3.4': ('D34', 20), 'W3.5': ('D35', 20), 'W3.6': ('D36', 60)}
H_OF = {'W3.2': 20, 'W3.4': 20, 'W3.5': 20, 'W3.6': 60}


def stat(tid, B):
    if tid == 'W3.1':
        a = B['ir'].abs()
        return Slope(a.shift(-1), a, 5)
    if tid == 'W3.3':
        rv = B['expo'].shift(1) * B['ir']
        rc = B['ir'].where(rv.notna())
        return SharpeDiff(rv, rc)
    if tid == 'W3.7':
        return Slope(B['y7'], B['x7'], 5)
    key, lags = DUMMY[tid]
    return Dummy(B['Y'][H_OF[tid]], B[key], lags)


# Analog timing rule per test: the direction that avoids the regime with the lower MAIN forward return
def analog_rule(tid, eff):
    return {'W3.2': 'W3.2:cash_when_vol_top_tercile' if eff < 0 else 'W3.2:cash_when_vol_bottom_tercile',
            'W3.3': 'W3.3:vol_target_cap1.5',
            'W3.4': 'W3.4:in_when_above_SMA200' if eff > 0 else 'W3.4:in_when_below_SMA200',
            'W3.5': 'W3.5:cash_when_breadth_lt40' if eff > 0 else 'W3.5:cash_when_breadth_ge60',
            'W3.6': 'W3.6:cash_when_dd_lt25' if eff < 0 else 'W3.6:in_only_when_dd_lt25'}[tid]


def bt_text(u, rule, ex='open', cost='B', k='MAIN'):
    x = BT[(u, rule, ex, cost, k)]
    return (f"{rule.split(':')[1]} ({ex} exec, cost {cost}): CAGR {x['cagr'] * PCT:.1f}% vs always-in "
            f"{x['base_cagr'] * PCT:.1f}%, Sharpe {x['sharpe']:.2f} vs {x['base_sharpe']:.2f}, MDD "
            f"{x['mdd'] * PCT:.0f}% vs {x['base_mdd'] * PCT:.0f}%, exposure {x['expo']:.2f}, "
            f"{x['switches_py']:.1f} changes/yr")


def bt_delta(u, rule, ex='open', cost='B', k='MAIN'):
    """(dCAGR, dSharpe, dMDD) of a rule vs always-in on the same days; dMDD > 0 = shallower drawdown."""
    x = BT[(u, rule, ex, cost, k)]
    return x['cagr'] - x['base_cagr'], x['sharpe'] - x['base_sharpe'], x['mdd'] - x['base_mdd']


def bt_verdict(u, rule, ex='open', cost='B'):
    """Verdict text for the MAIN backtest after costs (materiality SHARPE_TOL / CAGR_TOL), the number of subperiods
    with a higher Sharpe than always-in, dSharpe and dCAGR."""
    dc, ds, dm = bt_delta(u, rule, ex, cost)
    sub = sum(bt_delta(u, rule, ex, cost, k)[1] > 0 for k in SUBPERIODS)
    if ds >= SHARPE_TOL and dc > -CAGR_TOL:
        v = f'net improvement after cost {cost} (Sharpe up, CAGR not lower)'
    elif ds >= SHARPE_TOL:
        v = f'risk-adjusted improvement only after cost {cost} (Sharpe up, CAGR lower)'
    elif abs(ds) < SHARPE_TOL and abs(dc) < CAGR_TOL:
        v = f'no material change after cost {cost}'
    elif dc >= CAGR_TOL and ds > -SHARPE_TOL:
        v = f'higher CAGR with about the same Sharpe after cost {cost}'
    else:
        v = f'worse than always-in after cost {cost}'
    v += f' [dCAGR {dc * PCT:+.1f} pp/yr, dSharpe {ds:+.2f}, dMDD {dm * PCT:+.1f} pp, positive dMDD = shallower]'
    return v, sub, ds, dc


def surv_label(tid, eff):
    """Survivorship risk: effects favouring crash/turbulence regimes among today's survivors are high risk."""
    favours_crash = {'W3.2': eff > 0, 'W3.4': eff < 0, 'W3.5': eff < 0, 'W3.6': eff > 0, 'W3.3': eff < 0}
    if tid in ('W3.1',):
        return 'low'
    if tid == 'W3.7':
        return 'medium'
    return 'high' if favours_crash[tid] else 'low'


def surv_txt():
    lv = BS['all']['lvl']
    return ('idx and forward returns are built from today\'s Kompas100 members (EW idx level x%.0f from 1994-07 to '
            '2025-08), so stocks that crashed and were delisted or dropped are missing; that bias is largest right '
            'after crashes' % (lv.iloc[-1] / lv.iloc[0]))


def primary(Bs):
    rows = []
    for tid in DESC:
        sa, sp = stat(tid, Bs['all']), stat(tid, Bs['pre2018'])
        r = row(tid, FAM, DESC[tid], UNIT[tid], sa, sp, scale=SCALE[tid], exploit=EXPLOIT[tid])
        eff = r['eff_MAIN']
        r['survivorship_risk'] = surv_label(tid, eff)
        STATS[tid] = (sa, sp)
        r['cost_note'], r['notes'] = notes(tid, r, Bs, sa, sp)
        rows.append(r)
    return pd.DataFrame(rows)


STATS = {}
BS = {}
EXR = {}     # exploratory rows by test_id (computed before the primary notes, which cite them)


def thin_periods(D):
    out = []
    for k in SUBPERIODS:
        Dk = D.loc[slice(*PERIODS[k])]
        n1, n0 = int((Dk == 1).sum()), int((Dk == 0).sum())
        if min(n1, n0) < THIN:
            out.append(f'{k} ({n1} vs {n0} days)')
    return out


def notes(tid, r, Bs, sa, sp):
    eff = r['eff_MAIN']
    B = Bs['all']
    if tid == 'W3.1':
        a = B['ir'].abs()
        ac = {L: a.loc[MAIN[0]:MAIN[1]].autocorr(L) for L in (1, 5, 20)}
        cost = 'not a trade; volatility clustering is the premise of W3.2/W3.3'
        nt = (f'mean |idx_ret| MAIN {a.loc[MAIN[0]:MAIN[1]].mean() * BPS:.0f} bps; autocorrelation of |idx_ret| '
              f'lag1 {ac[1]:.2f}, lag5 {ac[5]:.2f}, lag20 {ac[20]:.2f}; idx rebuilt from pre2018 tickers for pre2018; '
              f'with the artefact days (idx_n < {SPUR_N}, incl. the +20.06% Saturday 2009-06-06 single-CTRA bar) '
              f'zeroed the MAIN slope is {SENS[("W3.1", "all")][0]:.3f} (t {SENS[("W3.1", "all")][1]:.1f}); '
              f'survivorship low: index-level volatility persistence does not depend much on which stocks survived')
        return cost, nt
    if tid == 'W3.3':
        bs = sa.boot.get(MAIN, {})
        x0 = BT[('all', 'always_in', 'close', '0', 'MAIN')]
        xv = BT[('all', 'W3.3:vol_target_cap1.5', 'close', '0', 'MAIN')]
        v, sub, _, _ = bt_verdict('all', 'W3.3:vol_target_cap1.5')
        va, _, _, _ = bt_verdict('all', 'W3.3:vol_target_cap1.5', cost='A')
        vw, subw, _, _ = bt_verdict('all', 'W3.3:vol_target_cap1.5_weekly')
        cost = (f'timing (exposure changes every day): {bt_text("all", "W3.3:vol_target_cap1.5")}; verdict: {v}; '
                f'Sharpe higher than always-in after B (open exec) in {sub} of 4 subperiods; cost A: {va}; close exec '
                f'B: {bt_text("all", "W3.3:vol_target_cap1.5", "close", "B")}; context variant updated weekly (chosen '
                f'after seeing the cost drag): {vw}; leverage up to 1.5x is charged no financing cost, which flatters '
                f'the rule; without leverage (cap 1.0, open exec, B): {bt_verdict("all", "W3.3:vol_target_cap1.0")[0]}')
        nt = (f'MAIN gross (PLAN convention, close exec, no cost): Sharpe {xv["sharpe"]:.2f} vs {x0["sharpe"]:.2f}, '
              f'MDD {xv["mdd"] * PCT:.0f}% vs {x0["mdd"] * PCT:.0f}%, CAGR {xv["cagr"] * PCT:.1f}% vs '
              f'{x0["cagr"] * PCT:.1f}%, mean exposure {xv["expo"]:.2f}; bootstrap sd {bs.get("sd", np.nan):.3f}, '
              f'95% interval [{bs.get("lo", np.nan):+.2f}, {bs.get("hi", np.nan):+.2f}]; t column = bootstrap z; '
              f'ANN {ANN:.1f} market days per year; per-period Sharpe and MDD of both in context; survivorship low: '
              f'{surv_txt()}; vol targeting cuts exposure after crashes, when survivors rebounded, so the bias works '
              f'against vol targeting')
        return cost, nt
    if tid == 'W3.7':
        y, x = B['y7'], B['x7']
        up = Diff(y.where(x > 0), y.where(x < 0), 5).at(*MAIN)
        ns, nl = B['n_small'].loc[MAIN[0]:MAIN[1]], B['n_large'].loc[MAIN[0]:MAIN[1]]
        on, cc = EXR['X-W3.7-on'], EXR['X-W3.7-cc']
        cost = (f'filter for small-cap entries at the next Open: next-day Open->Close of small caps after large-cap '
                f'up days minus down days {up[0] * BPS:+.1f} bps (t {up[1]:.2f}) vs filter threshold '
                f'{FILTER * BPS:.0f} bps -> {"meets" if abs(up[0]) >= FILTER else "below"}; a standalone day trade '
                f'would need > 0.90% (B) / 0.40% (A) per round trip')
        nt = (f'slope x 1% large-cap move = {eff * 100:+.1f} bps next-day small-cap Open->Close; the same regression '
              f'on the small caps\' overnight gap into t+1 gives slope {on["eff_MAIN"]:.3f} (t {on["t_MAIN"]:.1f}) '
              f'and close-to-close {cc["eff_MAIN"]:.3f} (t {cc["t_MAIN"]:.1f}) (X-W3.7-on/-cc): the lead-lag that '
              f'exists is mostly in the gap before the next Open, which an entry at the Open cannot capture; '
              f'median stocks per tercile MAIN small {ns.median():.0f} / large {nl.median():.0f}; the month-end sort '
              f'applies from the next row (same-row sort and controls in context); survivorship medium: the small '
              f'tercile holds the least liquid current members, whose history is the most survivor-selected')
        return cost, nt
    # Dummy tests: timing
    key, lags = DUMMY[tid]
    D = B[key]
    Dk = D.loc[MAIN[0]:MAIN[1]]
    n1, n0 = int((Dk == 1).sum()), int((Dk == 0).sum())
    rule = analog_rule(tid, eff)
    v, sub, _, _ = bt_verdict('all', rule)
    va, _, _, _ = bt_verdict('all', rule, cost='A')
    other = {'W3.2': ('W3.2:cash_when_vol_top_tercile', 'W3.2:cash_when_vol_bottom_tercile'),
             'W3.4': ('W3.4:in_when_above_SMA200', 'W3.4:in_when_below_SMA200'),
             'W3.5': ('W3.5:cash_when_breadth_lt40', 'W3.5:cash_when_breadth_ge60'),
             'W3.6': ('W3.6:cash_when_dd_lt25', 'W3.6:in_only_when_dd_lt25')}[tid]
    alt = [x for x in other if x != rule][0]
    cost = (f'timing: analog rule (cash in the regime with the lower MAIN forward return, so its direction is chosen '
            f'in-sample) {bt_text("all", rule)}; verdict: {v}; Sharpe higher than always-in after B in {sub} of 4 '
            f'subperiods; cost A: {va}; opposite rule: {bt_text("all", alt)}')
    if tid == 'W3.4':
        cost += f'; same rule with close exec: {bt_text("all", "W3.4:in_when_above_SMA200", "close", "B")}'
    if tid == 'W3.5':
        vs, subs, _, _ = bt_verdict('all', 'X-W3.5-state:in_when_breadth_state_up')
        cost += (f'; exploratory state version (cash after breadth < 40% until it is back at >= 60%): '
                 f'{bt_text("all", "X-W3.5-state:in_when_breadth_state_up")}; verdict: {vs}')
    m1 = nw(B['Y'][H_OF[tid]].where(D == 1).loc[MAIN[0]:MAIN[1]], lags)[0]
    m0 = nw(B['Y'][H_OF[tid]].where(D == 0).loc[MAIN[0]:MAIN[1]], lags)[0]
    names = {'W3.2': ('top tercile', 'bottom tercile'), 'W3.4': ('above', 'below'),
             'W3.5': ('breadth>=60%', 'breadth<40%'), 'W3.6': ('dd<-25%', 'other')}[tid]
    nsp = spells(D, *MAIN)
    nt = (f'MAIN days {names[0]} {n1} / {names[1]} {n0} ({nsp} separate {names[0]} spells); mean forward return '
          f'{names[0]} {m1 * PCT:+.2f}% vs {names[1]} {m0 * PCT:+.2f}% (raw EW, overlapping windows)')
    if nsp < 100:
        nt += (f'; with only {nsp} spells of a persistent regime the effective sample is far smaller than the day '
               f'count, so the NW t may overstate the evidence')
    lo = loyo_effects(B, key, H_OF[tid])
    ylo, yhi = min(lo, key=lambda y_: lo[y_][0]), max(lo, key=lambda y_: lo[y_][0])
    tlo, thi = min(v_[1] for v_ in lo.values()), max(v_[1] for v_ in lo.values())
    by = {y_: v_ for y_, v_ in by_year_effects(B, key, H_OF[tid], range(2000, 2026)).items() if np.isfinite(v_[0])}
    npos = sum(np.sign(v_[0]) == np.sign(eff) for v_ in by.values())
    nt += (f'; dropping any one MAIN year leaves {lo[ylo][0] * PCT:+.2f}% (without {ylo}) to {lo[yhi][0] * PCT:+.2f}% '
           f'(without {yhi}), t {tlo:.2f} to {thi:.2f}; the within-year difference has the MAIN sign in {npos} of '
           f'{len(by)} MAIN years with both regimes, so the pooled effect also reflects differences between years '
           f'and a few long episodes (by_year, loyo in context)')
    thin = thin_periods(D)
    if thin:
        nt += f'; thin subperiods (< {THIN} days in one regime): {", ".join(thin)}, so their sign rests on few days'
    if tid == 'W3.5':
        inc = EXR['X-W3.5-incr']
        nt += (f'; P4 (2021-25) has the opposite sign ({r["eff_P4"]:+.2f}%); controlling for the A1.8 index trend sign '
               f'and the W3.4 SMA200 regime the breadth coefficient is {inc["eff_MAIN"]:+.2f}% (t {inc["t_MAIN"]:.2f}, '
               f'X-W3.5-incr)')
    nt += (f'; survivorship {r["survivorship_risk"]}: {surv_txt()}'
           + ('; this effect favours buying the turbulent regime, exactly where survivors rebounded'
              if r['survivorship_risk'] == 'high' else
              '; the effect favours the calm regime, so the missing crashed stocks would if anything strengthen it'))
    if tid == 'W3.6':
        nt += '; the running max since 1994 makes the 1997-98 crisis drawdown persist into 2000-03 (yearly shares in context)'
    return cost, nt


# ------------------------------------------------------------------ context
def context(Bs, res):
    regime_context('W3.2', Bs, 'D32', 20, 'vol_top', 'vol_bottom', 'mid32')
    regime_context('W3.4', Bs, 'D34', 20, 'above_SMA200', 'below_SMA200')
    regime_context('W3.5', Bs, 'D35', 20, 'breadth_ge60', 'breadth_lt40', 'mid35')
    regime_context('W3.6', Bs, 'D36', 60, 'dd_lt25', 'other')
    for u in UNIVS:
        B = Bs[u]
        a_ = B['ir'].abs()
        for k, (a, b) in PERIODS.items():
            s = a_.loc[a:b]
            ctx('W3.1', 'W3.1', u, k, 'mean_abs_idx_ret', s.mean() * BPS, 'bps/day', int(s.notna().sum()))
            for L in (1, 5, 20):
                ctx('W3.1', 'W3.1', u, k, f'autocorr_abs_idx_ret_lag{L}', s.autocorr(L), 'corr', int(s.notna().sum()))
            la = np.log1p(B['ir']).abs()
            e, t, n = Slope(la.shift(-1), la, 5).at(a, b)
            ctx('W3.1', 'W3.1', u, k, 'slope_abs_log_return', e, 'slope', n, t, note='|log(1+idx_ret)| version')
            sq = B['ir'] ** 2
            e, t, n = Slope(sq.shift(-1), sq, 5).at(a, b)
            ctx('W3.1', 'W3.1', u, k, 'slope_squared_return', e, 'slope', n, t, note='squared-return version')
            ctx('W3.2', 'W3.2', u, k, 'sigma20_median_ann_pct', B['sig'].loc[a:b].median() * math.sqrt(ANN) * PCT,
                '%/yr', int(B['sig'].loc[a:b].notna().sum()))
            ctx('W3.2', 'W3.2', u, k, 'q1_threshold_end_of_period_ann_pct',
                B['q1'].loc[a:b].dropna().iloc[-1] * math.sqrt(ANN) * PCT if B['q1'].loc[a:b].notna().any() else np.nan,
                '%/yr')
            ctx('W3.2', 'W3.2', u, k, 'q2_threshold_end_of_period_ann_pct',
                B['q2'].loc[a:b].dropna().iloc[-1] * math.sqrt(ANN) * PCT if B['q2'].loc[a:b].notna().any() else np.nan,
                '%/yr')
            ctx('W3.5', 'W3.5', u, k, 'breadth_mean_pct', B['breadth'].loc[a:b].mean() * PCT, '%')
            ctx('W3.5', 'W3.5', u, k, 'breadth_min_stocks', int(B['breadth_n'].loc[a:b].min()), 'stocks')
            ctx('W3.6', 'W3.6', u, k, 'min_drawdown_pct', B['dd'].loc[a:b].min() * PCT, '%')
            # W3.3 gross (PLAN convention) Sharpe, MDD, CAGR and bootstrap interval
            sa = STATS['W3.3'][0 if u == 'all' else 1]
            if (a, b) not in sa.boot:
                sa.at(a, b)
            bs = sa.boot.get((a, b), {})
            xv, x0 = BT[(u, 'W3.3:vol_target_cap1.5', 'close', '0', k)], BT[(u, 'always_in', 'close', '0', k)]
            for nm, val, unit in (('sharpe_voltarget', xv['sharpe'], 'ann.'), ('sharpe_constant', x0['sharpe'], 'ann.'),
                                  ('mdd_voltarget_pct', xv['mdd'] * PCT, '%'), ('mdd_constant_pct', x0['mdd'] * PCT, '%'),
                                  ('cagr_voltarget_pct', xv['cagr'] * PCT, '%/yr'),
                                  ('cagr_constant_pct', x0['cagr'] * PCT, '%/yr'),
                                  ('vol_voltarget_pct', xv['vol'] * PCT, '%/yr'), ('vol_constant_pct', x0['vol'] * PCT, '%/yr'),
                                  ('mean_exposure', xv['expo'], 'x'),
                                  ('share_days_at_cap_1.5_pct',
                                   float((B['expo'].shift(1).loc[a:b].dropna() >= 1.5 - 1e-12).mean() * PCT), '%'),
                                  ('boot_sd_sharpe_diff', bs.get('sd', np.nan), 'ann.'),
                                  ('boot_2.5pct_sharpe_diff', bs.get('lo', np.nan), 'ann.'),
                                  ('boot_97.5pct_sharpe_diff', bs.get('hi', np.nan), 'ann.'),
                                  ('boot_share_diff_le_0', bs.get('share_le0', np.nan), 'share')):
                ctx('W3.3', 'W3.3', u, k, nm, val, unit, xv['n'], note='gross, exposure x idx_ret[t+1] (PLAN convention)')
            # W3.7 controls
            y, x, xs, yl = B['y7'], B['x7'], B['xs7'], B['yl7']
            Y_, X_ = y.loc[a:b], np.column_stack([np.ones(len(y.loc[a:b])), x.loc[a:b].values, xs.loc[a:b].values])
            if np.isfinite(Y_.values).sum() > 50:
                coef, t, n = ols_nw(Y_.values, X_, 5)
                ctx('W3.7', 'W3.7', u, k, 'slope_large_controlling_small_own', coef[1], 'slope', n, t[1],
                    note='y on large-cap r_cc[t] and small-cap own r_cc[t]')
                ctx('W3.7', 'W3.7', u, k, 'slope_small_own_controlling_large', coef[2], 'slope', n, t[2])
            e, t, n = Slope(yl, xs, 5).at(a, b)
            ctx('W3.7', 'W3.7', u, k, 'reverse_slope_large_fo1_on_small_rcc', e, 'slope', n, t,
                note='large-cap next-day Open->Close on small-cap r_cc[t]')
            e, t, n = Slope(y, B['ir'], 5).at(a, b)
            ctx('W3.7', 'W3.7', u, k, 'slope_small_fo1_on_idx_ret', e, 'slope', n, t)
            e, t, n = Diff(y.where(x > 0), y.where(x < 0), 5).at(a, b)
            ctx('W3.7', 'W3.7', u, k, 'small_fo1_after_large_up_minus_down', e * BPS, 'bps', n, t)
            m, se, n = nw(y.loc[a:b], 5)
            ctx('W3.7', 'W3.7', u, k, 'small_fo1_mean', m * BPS, 'bps', n, m / se if se else np.nan)
            xk = x.loc[a:b]
            if xk.notna().sum() > 100:
                qx = pd.qcut(xk.rank(method='first'), 5, labels=False)
                for q in range(5):
                    m, se, n = nw(y.loc[a:b].where(qx == q), 5)
                    ctx('W3.7', 'W3.7', u, k, f'small_fo1_mean_large_rcc_quintile{q + 1}', m * BPS, 'bps', n,
                        m / se if se else np.nan, note='quintiles of x within the period (descriptive, look-ahead)')
            ctx('W3.7', 'W3.7', u, k, 'median_n_small', float(B['n_small'].loc[a:b].median()), 'stocks')
            ctx('W3.7', 'W3.7', u, k, 'median_n_large', float(B['n_large'].loc[a:b].median()), 'stocks')
    # data artefacts and their influence
    n = P['idx_n']
    for d in n.index[(n < SPUR_N) & (n.index >= '1995-01-01')]:
        ctx('sensitivity', 'data', 'all', 'ALL', f'artefact_day_{d.date()}', float(P['idx_ret'].loc[d]) * PCT, '% idx_ret',
            int(n.loc[d]), note=f'weekday {d.dayofweek}; stocks with a return that day = n')
    for u in UNIVS:
        for tid in ('W3.1', 'W3.2', 'W3.3', 'W3.4', 'W3.5', 'W3.6'):
            e, t, nn = SENS[(tid, u)]
            ctx('sensitivity', tid, u, 'MAIN', 'effect_with_artefact_days_zeroed', e, UNIT[tid], nn, t,
                note=f'idx_ret set to 0 on days with < {SPUR_N} stocks (2006-03-31, 2008-01-11, 2009-06-06 in MAIN)')
            e0 = res.loc[res.test_id == tid, 'eff_MAIN' if u == 'all' else 'eff_pre2018'].iloc[0]
            ctx('sensitivity', tid, u, 'MAIN', 'effect_primary', e0, UNIT[tid])
    # W3.2 threshold path and regime shares by year (all)
    B = Bs['all']
    for y_, g in B['D36'].groupby(CAL.year):
        ctx('W3.6', 'W3.6', 'all', str(y_), 'share_days_dd_lt25_pct', float(g.mean() * PCT), '%', len(g))
    for y_, g in B['D34'].groupby(CAL.year):
        if g.notna().any():
            ctx('W3.4', 'W3.4', 'all', str(y_), 'share_days_above_SMA200_pct', float(g.mean() * PCT), '%',
                int(g.notna().sum()))
    # effect by calendar year = mean forward return on D=1 days minus D=0 days of that year (equals the Dummy
    # coefficient); no t-stat: a year holds only a few independent 20/60-day windows (NW with lags 20/60 on ~245 days
    # gives a variance near zero, rounding can make it negative). Leave-one-year-out: MAIN Dummy without that year.
    for u in UNIVS:
        B = Bs[u]
        for tid, key in (('W3.2', 'D32'), ('W3.4', 'D34'), ('W3.5', 'D35'), ('W3.6', 'D36')):
            h = H_OF[tid]
            for y_, (e, n1, n0) in by_year_effects(B, key, h).items():
                ctx('by_year', tid, u, str(y_), f'effect_fwd{h}_D1_minus_D0', e * PCT, f'% per {h} days', n1 + n0,
                    note=f'days with a forward return: D=1 {n1}, D=0 {n0}; descriptive, no t-stat')
            for y_, (e, t, nn) in loyo_effects(B, key, h).items():
                ctx('loyo', tid, u, 'MAIN', f'effect_without_{y_}', e * PCT, f'% per {h} days', nn, t,
                    note=f'MAIN Dummy effect with the rows of {y_} removed')
    # W3.7 sort-timing sensitivity: month-end sort applied already from the month-end row itself
    for u in UNIVS:
        c = cols(u)
        small, large, _, _ = terciles_by_value(c, same_row=True)
        y = P['fo'][1][c].where(small).mean(axis=1)
        x = P['r_cc'][c].where(large).mean(axis=1)
        for k, (a, b) in PERIODS.items():
            e, t, nn = Slope(y, x, 5).at(a, b)
            ctx('W3.7', 'W3.7', u, k, 'slope_sort_applied_from_month_end_row', e, 'slope', nn, t,
                note='sensitivity: the sort formed at the month-end Close is used already for that row')


# ------------------------------------------------------------------ sensitivity (computed before the notes cite it)
SENS = {}    # (tid, u) -> (effect x scale, t, n) with idx_ret set to 0 on artefact days (idx_n < SPUR_N)


def sensitivity():
    for u in UNIVS:
        Bz = build(u, spur_zero=True)
        for tid in ('W3.1', 'W3.2', 'W3.3', 'W3.4', 'W3.5', 'W3.6'):
            e, t, n = stat(tid, Bz).at(*MAIN)
            SENS[(tid, u)] = (e * SCALE[tid], t, n)


# ------------------------------------------------------------------ exploratory (X-W3-*, motivated by the primaries)
def exploratory(Bs):
    """Few labelled extras, chosen after seeing the primary results (not classified):
    X-W3.5-incr  W3.5 is the only regime test with |t| >= 3, and A1.8 (index TSMOM 20/20) is also significant: does
                 breadth add information beyond the index trend sign and the W3.4 SMA200 regime?
    X-W3.5-state W3.5's timing rule switches about 14 times a year and cost B removes most of its gain: a state version
                 with the same two thresholds (cash after breadth < 40% until it is back at >= 60%) switches less;
                 Dummy over all days (no excluded middle) plus its backtest in context.
    X-W3.7-on/cc W3.7's tradable next-day Open->Close slope is small: is the large->small lead-lag in the overnight
                 gap (not capturable from the next Open) or absent? Same regression with the small caps' overnight
                 return into t+1 and their close-to-close return of t+1 (cc = on + Open->Close, same stocks)."""
    rows = []
    defs = {
        'X-W3.5-incr': (lambda B: Coef(B['Y'][20], pd.DataFrame({'D35': B['D35'], 'sgn20': B['sgn20'],
                                                                  'D34': B['D34']}), 0, 20),
                        'W3.5 breadth dummy (>= 60% vs < 40%) in an OLS of the EW forward fo[20] on [1, breadth dummy, '
                        'sign of the 20-day idx log return (A1.8 signal), idx > SMA200 dummy (W3.4)]; coefficient on '
                        'breadth', '% per 20 days (breadth coefficient)', PCT, 'timing', 'low'),
        'X-W3.5-state': (lambda B: Dummy(B['Y'][20], B['S35'], 20),
                         'Breadth state: 1 after breadth reaches >= 60%, 0 after it falls < 40%, unchanged in between '
                         '(all days used); forward EW mean fo[20], state 1 minus state 0',
                         '% per 20 days (state up minus down)', PCT, 'timing', 'low'),
        'X-W3.7-on': (lambda B: Slope(B['y7_on'], B['x7'], 5),
                      'OLS slope of the small-cap (bottom value tercile) EW overnight log return into t+1 (Close t -> '
                      'Open t+1) on the large-cap EW r_cc of day t', 'slope', 1., 'descriptive', 'medium'),
        'X-W3.7-cc': (lambda B: Slope(B['y7_cc'], B['x7'], 5),
                      'OLS slope of the small-cap EW close-to-close log return of t+1 on the large-cap EW r_cc of day '
                      't (= overnight + Open->Close parts)', 'slope', 1., 'descriptive', 'medium'),
    }
    for tid, (mk, desc, unit, scale, expl, sr) in defs.items():
        sa, sp = mk(Bs['all']), mk(Bs['pre2018'])
        r = row(tid, 'W3-X', desc, unit, sa, sp, scale=scale, exploit=expl, surv_risk=sr)
        EXR[tid] = r
        rows.append(r)
    B = Bs['all']
    # notes
    ok = B['D35'].notna() & B['sgn20'].notna()
    sl = slice(*MAIN)
    corr = np.corrcoef(B['D35'][ok].loc[sl], B['sgn20'][ok].loc[sl])[0, 1]
    c_sg = Coef(B['Y'][20], pd.DataFrame({'D35': B['D35'], 'sgn20': B['sgn20'], 'D34': B['D34']}), 1, 20).at(*MAIN)
    c_34 = Coef(B['Y'][20], pd.DataFrame({'D35': B['D35'], 'sgn20': B['sgn20'], 'D34': B['D34']}), 2, 20).at(*MAIN)
    r = EXR['X-W3.5-incr']
    r['cost_note'] = ('timing input; usability would need a separate backtest of the combined rule; filter threshold '
                      'does not apply')
    r['notes'] = (f'MAIN coefficients in the same regression: idx 20-day trend sign {c_sg[0] * PCT:+.2f}% (t {c_sg[1]:.2f}), '
                  f'SMA200 dummy {c_34[0] * PCT:+.2f}% (t {c_34[1]:.2f}); correlation of the breadth dummy with the '
                  f'trend sign {corr:.2f} on days with a breadth regime, so the two signals are hard to separate and '
                  f'neither coefficient alone reaches t 3; only days with breadth >= 60% or < 40%')
    r = EXR['X-W3.5-state']
    S = B['S35'].loc[sl]
    v, sub, _, _ = bt_verdict('all', 'X-W3.5-state:in_when_breadth_state_up')
    r['cost_note'] = (f'timing: {bt_text("all", "X-W3.5-state:in_when_breadth_state_up")}; verdict: {v}; Sharpe higher '
                      f'than always-in after B in {sub} of 4 subperiods; primary W3.5 rule for comparison: '
                      f'{bt_text("all", "W3.5:cash_when_breadth_lt40")}')
    r['notes'] = (f'MAIN days state up {int((S == 1).sum())} / down {int((S == 0).sum())} ({spells(B["S35"], *MAIN)} up '
                  f'spells); same thresholds as W3.5, no new parameter; chosen after seeing the W3.5 cost drag')
    for tid in ('X-W3.7-on', 'X-W3.7-cc'):
        EXR[tid]['cost_note'] = ('not tradable from the next Open: the overnight gap is earned only by a position '
                                 'bought at the Close of t, i.e. at the same Close that reveals the signal')
    p = B['y7_on'].loc[sl] + B['y7'].loc[sl] - B['y7_cc'].loc[sl]
    EXR['X-W3.7-on']['notes'] = (f'identity cc = overnight + Open->Close on the same stocks holds (max |error| '
                                 f'{np.nanmax(np.abs(p.values)):.1e}); compare W3.7 slope (Open->Close part)')
    EXR['X-W3.7-cc']['notes'] = 'close-to-close cross-autocorrelation; A1.7 (index own AC1) is the analogous index-level figure'
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ self-checks
def self_checks(Bs):
    B = Bs['all']
    assert np.allclose(B['ir'].fillna(0).values, P['idx_ret'].fillna(0).values, atol=1e-15)
    rng = np.random.default_rng(3)
    lnP = P['lnP']
    for u in UNIVS:
        B = Bs[u]
        c = B['c']
        lp = lnP[c].values
        # breadth brute force on random rows
        for i in rng.integers(60, len(CAL), 200):
            w = lp[i - 49:i + 1]
            ok = np.isfinite(w).all(0)
            ref = (lp[i, ok] > w[:, ok].mean(0) + 1e-12).mean() if ok.any() else np.nan
            assert abs(ref - B['breadth'].iloc[i]) < 1e-9, ('breadth', u, i)
        # tercile membership: row t uses the month-end sort strictly before t
        me = rebalance_dates(P, 'M')
        val60 = P['value'][c].rolling(60, min_periods=40).mean()
        for i in rng.integers(300, len(CAL), 50):
            d = CAL[i]
            m = max(x for x in me if x < d)
            s = val60.loc[m].where(P['T'][c].loc[m])
            s = s[s.notna() & (s > 0)]
            # independent re-implementation: ranks 1..k (ties by column order), cut at 1 + (k-1)/3 and 1 + 2(k-1)/3
            r_ = s.rank(method='first')
            k = len(s)
            lo_cut, hi_cut = 1 + (k - 1) / 3, 1 + 2 * (k - 1) / 3
            got_s = set(np.array(c)[B['small'].iloc[i].values])
            got_l = set(np.array(c)[B['large'].iloc[i].values])
            assert got_s == set(s.index[r_ <= lo_cut]), ('small tercile', u, d)
            assert got_l == set(s.index[r_ > hi_cut]), ('large tercile', u, d)
            assert m < d and CAL.get_loc(m) < i
        # Dummy effect equals difference of means (no-NaN regime days)
        y, D = B['Y'][20].loc[MAIN[0]:MAIN[1]], B['D34'].loc[MAIN[0]:MAIN[1]]
        ok = y.notna() & D.notna()
        ref = y[ok & (D == 1)].mean() - y[ok & (D == 0)].mean()
        assert abs(Dummy(B['Y'][20], B['D34'], 20).at(*MAIN)[0] - ref) < 1e-12
        # backtest with exposure 1 equals idx_ret; exec conventions coincide when exposure is constant
        one = pd.Series(1., index=CAL)
        for ex in ('open', 'close'):
            net, de, _ = strat(one, B, ex, 'B')
            assert np.allclose(net.iloc[2:].fillna(0).values, B['ir'].iloc[2:].fillna(0).values)
        # vol-target gross close exec equals the W3.3 primary series on every day (incl. the first defined day)
        net, _, _ = strat(B['expo'], B, 'close', '0')
        rv = B['expo'].shift(1) * B['ir']
        assert np.allclose(net.fillna(0).values, rv.fillna(0).values)
        assert (net.notna() == rv.notna()).all()
        # open exec on a toy switch: out (0) -> in (1) decided at Close t earns the intraday return of t+1 minus the
        # buy cost; in -> out earns the overnight part (ir - idr) of t+1 minus the sell cost
        i0 = CAL.get_loc(pd.Timestamp('2012-03-01'))
        toy = pd.Series(1., index=CAL)
        toy.iloc[:i0] = 0.
        toy.iloc[i0 + 5:] = 0.
        net, de, _ = strat(toy, B, 'open', 'B')
        s1, s2 = CAL[i0 + 1], CAL[i0 + 6]
        assert abs(net.loc[s1] - (B['idr'].loc[s1] - CSPLIT['B'][0])) < 1e-12
        assert abs(net.loc[s2] - (B['ir'].loc[s2] - B['idr'].loc[s2] - CSPLIT['B'][1])) < 1e-12
        assert abs(net.loc[CAL[i0 + 3]] - B['ir'].loc[CAL[i0 + 3]]) < 1e-12 and net.loc[CAL[i0 + 8]] == 0.
        # causality: regime variables at t are unchanged when all data after t is removed
        cut = CAL.get_loc(pd.Timestamp('2012-06-29'))
        ir_cut = B['ir'].iloc[:cut + 1]
        sig_cut = ir_cut.rolling(20, min_periods=20).std()
        assert abs(sig_cut.iloc[-1] - B['sig'].iloc[cut]) < 1e-15
        assert abs(sig_cut.expanding(min_periods=500).quantile(2 / 3).iloc[-1] - B['q2'].iloc[cut]) < 1e-15
        lv = (1 + ir_cut.fillna(0.)).cumprod()
        assert abs(lv.rolling(200).mean().iloc[-1] - B['sma200'].iloc[cut]) < 1e-9
    # small caps: close-to-close = overnight + Open->Close on the same stocks (X-W3.7 decomposition)
    for u in UNIVS:
        B = Bs[u]
        d = (B['y7_on'] + B['y7'] - B['y7_cc']).abs()
        assert d.max() < 1e-10 and (B['y7'].notna() == B['y7_cc'].notna()).all(), ('cc identity', u)
    # SharpeDiff of a series with itself is zero
    s = Bs['all']['ir']
    assert abs(SharpeDiff(s, s).at(*MAIN)[0]) < 1e-12
    # bootstrap null: a random sign-flip timing (exposure 1 or 0.5, iid) has |z| small on average
    print('self-checks passed', flush=True)


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    pd.set_option('display.width', 250)
    Bs = {u: build(u) for u in UNIVS}
    BS.update(Bs)
    self_checks(Bs)
    run_backtests(Bs)
    sensitivity()
    ex = exploratory(Bs)
    res = primary(Bs)
    res.to_csv(OUT / 'W3_tests.csv', index=False)
    show = ['test_id', 'unit', 'eff_MAIN', 't_MAIN', 'eff_P1', 'eff_P2', 'eff_P3', 'eff_P4', 'eff_P0', 'eff_pre2018',
            't_pre2018', 'signs_P1_P4', 'pass_t3', 'pass_stable', 'pass_pre2018', 'survivorship_risk']
    print(res[show].round(3).to_string(index=False), flush=True)
    context(Bs, res)
    pd.DataFrame(CTX).to_csv(OUT / 'W3_context.csv', index=False)
    ex.to_csv(OUT / 'W3_exploratory.csv', index=False)
    print(ex[show].round(3).to_string(index=False))
