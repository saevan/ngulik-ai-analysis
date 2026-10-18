"""Market properties v2, family W3 (market regime and volatility timing), implemented as pre-registered in PLAN.md W3.
Writes results/W3_tests.csv (primary tests W3.1-W3.7, one mpstats.row each, universes all and pre2018),
results/W3_context.csv (descriptive context, not classified: regime day counts and spells per period, mean forward
return per regime and horizon, pooled stock-day means, W3.3 Sharpe/MDD/CAGR, exposure backtests after costs, W3.7
conditional means, data-artefact sensitivity) and results/W3_exploratory.csv (X-W3-* extras, not classified).
Run: python market_properties_v2/w3_regime.py   (about a minute, includes self-checks)

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
    (paired), 2,000 resamples, fixed seed per period; z = observed difference / sd of the resampled differences.
 5. W3.4 SMA200 over t-199..t of the idx level; above = level > SMA200 (D=1), below = level <= SMA200 (D=0).
 6. W3.5 SMA50(lnP) = mean of the clean log Close over t-49..t (50 market rows, stock listed for all of them;
    lnP is flat on non-tradable days). Breadth = share of universe stocks with a defined SMA50 whose lnP exceeds it
    (tolerance 1e-12 so that a flat price never counts as 'above' through float noise). D = 1 if breadth >= 0.60,
    0 if < 0.40, NaN in between.
 7. W3.6 drawdown = level / running max since 1994-07-12 - 1 (simple); D = 1 if < -0.25 else 0.
 8. W3.7 terciles of the 60-day mean traded value (value.rolling(60, min_periods=40).mean(), Volume-0 days skipped,
    the D10 convention) among universe stocks tradable at each month-end Close (>= 15 stocks); the sort formed at
    month end m applies to rows m+1 .. next month end (so row t always uses a sort formed strictly before t).
    y[t] = EW fo[1] of bottom-tercile stocks at row t (their Open->Close log return of day t+1), x[t] = EW r_cc of
    top-tercile stocks on day t; OLS with intercept, NW lags 5.
 9. Exposure backtests (usability of timing tests, context only): EW universe (daily rebalanced, idx_ret) with
    exposure e[t] decided at the Close of t. 'open' execution: the change is made at the Open of t+1, so day t+1
    earns e[t-1] x idx_ret[t+1] + (e[t] - e[t-1]) x EW intraday simple return; 'close' execution: e[t] x
    idx_ret[t+1] (the PLAN W3.3 convention). Costs on exposure changes: buy .15% / sell .25% (A, 0.40% round
    trip) and buy .40% / sell .50% (B, 0.90% round trip, mpstats.COST_RT); cash earns 0; leverage above 1 (W3.3)
    is not charged financing. CAGR uses years = market days / ANN; MDD on the equity curve of each period.
    The rule whose direction follows the sign of the MAIN effect ('analog': cash in the regime with the lower mean
    forward return) is the usability check; its direction is therefore chosen in-sample (an upper bound).
10. Data artefacts in the panel calendar are kept in the primary statistics (pre-registered idx definition) and
    reported: 2009-06-06 is a Saturday with a single CTRA bar (idx_ret +20.06%), 2008-01-11 has a single CTRA bar,
    2006-03-31 has 8 stale duplicated bars, 1998-05-15 has 2 bars. Their effect is shown in context section
    'sensitivity' (idx_ret set to 0 on days with idx_n < 10).
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
FILTER_PP = .25
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


def terciles_by_value(c):
    """Bottom/top tercile masks (Date x Ticker) of the 60-day mean traded value, sorted at each month-end Close and
    applied from the next row through the next month end."""
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
    kr = np.searchsorted(me_pos, np.arange(len(CAL)), side='left') - 1
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
    B['n_small'] = small.sum(axis=1)
    B['n_large'] = large.sum(axis=1)
    return B


# ------------------------------------------------------------------ exposure backtests
def strat(e, B, execu='open', cost='0'):
    """Daily simple returns of the EW universe held with exposure e (decided at the Close of t), net of costs."""
    ir, idr = B['ir'], B['idr'].fillna(0.)
    e1, e2 = e.shift(1), e.shift(2)
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
    }


BT = {}      # (u, rule, exec, cost, period) -> perf dict incl. baseline and exposure stats


def run_backtests(Bs):
    for u in UNIVS:
        B = Bs[u]
        for name, e in rules(B).items():
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
                    m, se, n = nw(y.where(D == val).loc[a:b], lags)
                    ctx('regime_means', tid, u, k, f'mean_fwd{h}_{lab}', m * PCT, f'% per {h} days', n,
                        m / se if se and se > 0 else np.nan, note=f'EW mean fo[{h}] on D={int(val)} days, NW lags {lags}')
                    pm, pk = pooled(B['c'], h, D == val, a, b)
                    ctx('pooled', tid, u, k, f'pooled_fwd{h}_{lab}', pm * PCT, f'% per {h} days', pk,
                        note='stock-day pooled mean (event-weighted analogue)')
                if mid_key is not None:
                    m, se, n = nw(y.where(B[mid_key]).loc[a:b], lags)
                    ctx('regime_means', tid, u, k, f'mean_fwd{h}_middle', m * PCT, f'% per {h} days', n,
                        m / se if se and se > 0 else np.nan, note='excluded middle group')
                m, se, n = nw(y.loc[a:b], lags)
                ctx('regime_means', tid, u, k, f'mean_fwd{h}_all_days', m * PCT, f'% per {h} days', n,
                    m / se if se and se > 0 else np.nan)
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


def bt_verdict(u, rule, ex='open', cost='B'):
    x = BT[(u, rule, ex, cost, 'MAIN')]
    s_up, c_up = x['sharpe'] > x['base_sharpe'], x['cagr'] > x['base_cagr']
    sub = sum(BT[(u, rule, ex, cost, k)]['sharpe'] > BT[(u, rule, ex, cost, k)]['base_sharpe'] for k in SUBPERIODS)
    if s_up and c_up:
        v = 'net improvement after cost B (Sharpe and CAGR)'
    elif s_up:
        v = 'Sharpe/MDD improve after cost B but CAGR falls'
    elif c_up:
        v = 'CAGR improves after cost B but Sharpe falls'
    else:
        v = 'no net improvement after cost B'
    return v, sub, s_up, c_up


def surv_label(tid, eff):
    """Survivorship risk: effects favouring crash/turbulence regimes among today's survivors are high risk."""
    favours_crash = {'W3.2': eff > 0, 'W3.4': eff < 0, 'W3.5': eff < 0, 'W3.6': eff > 0, 'W3.3': eff < 0}
    if tid in ('W3.1',):
        return 'low'
    if tid == 'W3.7':
        return 'medium'
    return 'high' if favours_crash[tid] else 'low'


SURV_TXT = ('idx and forward returns are built from today\'s Kompas100 members (EW level x513 since 1994, far above '
            'the market), so stocks that crashed and delisted are missing; that bias is largest right after crashes')


def primary(Bs):
    rows = []
    for tid in DESC:
        sa, sp = stat(tid, Bs['all']), stat(tid, Bs['pre2018'])
        r = row(tid, FAM, DESC[tid], UNIT[tid], sa, sp, scale=SCALE[tid], exploit=EXPLOIT[tid])
        eff = r['eff_MAIN']
        r['survivorship_risk'] = surv_label(tid, eff)
        r['cost_note'], r['notes'] = notes(tid, r, Bs, sa, sp)
        rows.append(r)
        STATS[tid] = (sa, sp)
    return pd.DataFrame(rows)


STATS = {}


def notes(tid, r, Bs, sa, sp):
    eff = r['eff_MAIN']
    B = Bs['all']
    if tid == 'W3.1':
        a = B['ir'].abs()
        ac = {L: a.loc[MAIN[0]:MAIN[1]].autocorr(L) for L in (1, 5, 20)}
        cost = 'not a trade; volatility clustering is the premise of W3.2/W3.3'
        nt = (f'mean |idx_ret| MAIN {a.loc[MAIN[0]:MAIN[1]].mean() * BPS:.0f} bps; autocorrelation of |idx_ret| '
              f'lag1 {ac[1]:.2f}, lag5 {ac[5]:.2f}, lag20 {ac[20]:.2f}; idx rebuilt from pre2018 tickers for pre2018; '
              f'sensitivity without artefact days (idx_n < {SPUR_N}) in context; survivorship low: index-level '
              f'volatility persistence does not depend on which stocks survived')
        return cost, nt
    if tid == 'W3.3':
        bs = sa.boot.get(MAIN, {})
        x0 = BT[('all', 'always_in', 'close', '0', 'MAIN')]
        xv = BT[('all', 'W3.3:vol_target_cap1.5', 'close', '0', 'MAIN')]
        v, sub, _, _ = bt_verdict('all', 'W3.3:vol_target_cap1.5')
        cost = (f'timing (daily exposure changes): {bt_text("all", "W3.3:vol_target_cap1.5")}; '
                f'with close exec: {bt_text("all", "W3.3:vol_target_cap1.5", "close", "B")}; verdict: {v}; Sharpe '
                f'higher after B (open exec) in {sub} of 4 subperiods; leverage up to 1.5x without financing cost')
        nt = (f'MAIN gross (PLAN convention, close exec): Sharpe {xv["sharpe"]:.2f} vs {x0["sharpe"]:.2f}, MDD '
              f'{xv["mdd"] * PCT:.0f}% vs {x0["mdd"] * PCT:.0f}%, CAGR {xv["cagr"] * PCT:.1f}% vs '
              f'{x0["cagr"] * PCT:.1f}%, mean exposure {xv["expo"]:.2f}; bootstrap sd {bs.get("sd", np.nan):.3f}, '
              f'95% interval [{bs.get("lo", np.nan):+.2f}, {bs.get("hi", np.nan):+.2f}]; t column is the bootstrap z; '
              f'ANN {ANN:.1f} days; survivorship: {SURV_TXT}; vol targeting cuts exposure after crashes, when '
              f'survivors rebounded, so the bias works against vol targeting')
        return cost, nt
    if tid == 'W3.7':
        y, x = B['y7'], B['x7']
        up, dn = Diff(y.where(x > 0), y.where(x < 0), 5).at(*MAIN), None
        ns, nl = B['n_small'].loc[MAIN[0]:MAIN[1]], B['n_large'].loc[MAIN[0]:MAIN[1]]
        cost = (f'filter for small-cap entries at the next Open: next-day Open->Close of small caps after large-cap '
                f'up days minus down days {up[0] * BPS:+.1f} bps (t {up[1]:.2f}) vs filter threshold '
                f'{FILTER_PP * BPS:.0f} bps -> {"meets" if abs(up[0]) * PCT >= FILTER_PP else "below"}; as a '
                f'standalone day trade it would need > 0.90% (B) / 0.40% (A) per round trip')
        nt = (f'slope x 1% large-cap move = {eff * 100:+.1f} bps next-day small-cap Open->Close; median stocks per '
              f'tercile MAIN small {ns.median():.0f} / large {nl.median():.0f}; sort at month end applies from the next '
              f'row; controls (small-cap own lag, reverse direction) in context; survivorship medium: the small '
              f'tercile holds the least liquid current members, whose history is the most survivor-selected')
        return cost, nt
    # Dummy tests: timing
    key, lags = DUMMY[tid]
    D = B[key]
    Dk = D.loc[MAIN[0]:MAIN[1]]
    n1, n0 = int((Dk == 1).sum()), int((Dk == 0).sum())
    rule = analog_rule(tid, eff)
    v, sub, _, _ = bt_verdict('all', rule)
    other = {'W3.2': ('W3.2:cash_when_vol_top_tercile', 'W3.2:cash_when_vol_bottom_tercile'),
             'W3.4': ('W3.4:in_when_above_SMA200', 'W3.4:in_when_below_SMA200'),
             'W3.5': ('W3.5:cash_when_breadth_lt40', 'W3.5:cash_when_breadth_ge60'),
             'W3.6': ('W3.6:cash_when_dd_lt25', 'W3.6:in_only_when_dd_lt25')}[tid]
    alt = [x for x in other if x != rule][0]
    cost = (f'timing: analog rule (cash in the regime with the lower MAIN forward return) {bt_text("all", rule)}; '
            f'verdict: {v}; Sharpe higher after B in {sub} of 4 subperiods; opposite rule: {bt_text("all", alt)}')
    if tid == 'W3.4':
        cost += f'; task rule in-when-above (close exec, B): {bt_text("all", "W3.4:in_when_above_SMA200", "close", "B")}'
    m1 = nw(B['Y'][H_OF[tid]].where(D == 1).loc[MAIN[0]:MAIN[1]], lags)[0]
    m0 = nw(B['Y'][H_OF[tid]].where(D == 0).loc[MAIN[0]:MAIN[1]], lags)[0]
    names = {'W3.2': ('top tercile', 'bottom tercile'), 'W3.4': ('above', 'below'),
             'W3.5': ('breadth>=60%', 'breadth<40%'), 'W3.6': ('dd<-25%', 'other')}[tid]
    nt = (f'MAIN days {names[0]} {n1} / {names[1]} {n0} ({spells(D, *MAIN)} separate {names[0]} spells); mean '
          f'forward return {names[0]} {m1 * PCT:+.2f}% vs {names[1]} {m0 * PCT:+.2f}% (raw EW, overlapping windows); '
          f'regime spells are few and long, so the NW t may overstate the evidence; survivorship '
          f'{"high" if r["survivorship_risk"] == "high" else "low"}: {SURV_TXT}'
          + ('; this effect favours buying the turbulent regime, exactly where survivors rebounded'
             if r['survivorship_risk'] == 'high' else
             '; the effect favours the calm regime, so the missing crashed stocks would if anything strengthen it'))
    if tid == 'W3.6':
        nt += '; running max since 1994 makes the 1997-98 crisis drawdown persist into 2000-03 (context shares)'
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
        Bz = build(u, spur_zero=True)
        for tid in ('W3.1', 'W3.2', 'W3.3', 'W3.4', 'W3.5', 'W3.6'):
            st = stat(tid, Bz)
            e, t, nn = st.at(*MAIN)
            ctx('sensitivity', tid, u, 'MAIN', 'effect_with_artefact_days_zeroed', e * SCALE[tid], UNIT[tid], nn, t,
                note=f'idx_ret set to 0 on days with < {SPUR_N} stocks (2006-03-31, 2008-01-11, 2009-06-06 in MAIN)')
            e0 = res.loc[res.test_id == tid, 'eff_MAIN' if u == 'all' else 'eff_pre2018'].iloc[0]
            ctx('sensitivity', tid, u, 'MAIN', 'effect_primary', e0, UNIT[tid])
    # W3.2 threshold path and regime shares by year (all)
    B = Bs['all']
    for y_, g in B['D36'].groupby(CAL.year):
        ctx('W3.6', 'W3.6', 'all', str(y_), 'share_days_dd_lt25_pct', float(g.mean() * PCT), '%', len(g))
    for y_, g in B['D34'].groupby(CAL.year):
        ctx('W3.4', 'W3.4', 'all', str(y_), 'share_days_above_SMA200_pct', float(g.mean() * PCT), '%',
            int(g.notna().sum()))


# ------------------------------------------------------------------ exploratory (X-W3-*, filled after primary results)
def exploratory(Bs, res):
    rows = []
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
            r_ = s.rank(method='first')
            k = len(s)
            sm = set(s.index[r_ <= np.floor(k / 3) + (1 if k % 3 == 2 else 0) * 0])
            got = set(np.array(c)[B['small'].iloc[i].values])
            q = pd.qcut(r_, 3, labels=False)
            assert got == set(q.index[q == 0]), ('tercile', u, d)
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
        # vol-target gross close exec equals the W3.3 primary series
        net, _, _ = strat(B['expo'], B, 'close', '0')
        rv = B['expo'].shift(1) * B['ir']
        assert np.allclose(net.fillna(0).values, rv.fillna(0).values)
        # causality: regime variables at t are unchanged when all data after t is removed
        cut = CAL.get_loc(pd.Timestamp('2012-06-29'))
        ir_cut = B['ir'].iloc[:cut + 1]
        sig_cut = ir_cut.rolling(20, min_periods=20).std()
        assert abs(sig_cut.iloc[-1] - B['sig'].iloc[cut]) < 1e-15
        assert abs(sig_cut.expanding(min_periods=500).quantile(2 / 3).iloc[-1] - B['q2'].iloc[cut]) < 1e-15
        lv = (1 + ir_cut.fillna(0.)).cumprod()
        assert abs(lv.rolling(200).mean().iloc[-1] - B['sma200'].iloc[cut]) < 1e-9
    # SharpeDiff of a series with itself is zero
    s = Bs['all']['ir']
    assert abs(SharpeDiff(s, s).at(*MAIN)[0]) < 1e-12
    # bootstrap null: a random sign-flip timing (exposure 1 or 0.5, iid) has |z| small on average
    print('self-checks passed', flush=True)


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    pd.set_option('display.width', 250)
    Bs = {u: build(u) for u in UNIVS}
    self_checks(Bs)
    run_backtests(Bs)
    res = primary(Bs)
    res.to_csv(OUT / 'W3_tests.csv', index=False)
    show = ['test_id', 'unit', 'eff_MAIN', 't_MAIN', 'eff_P1', 'eff_P2', 'eff_P3', 'eff_P4', 'eff_P0', 'eff_pre2018',
            't_pre2018', 'signs_P1_P4', 'pass_t3', 'pass_stable', 'pass_pre2018', 'survivorship_risk']
    print(res[show].round(3).to_string(index=False), flush=True)
    context(Bs, res)
    pd.DataFrame(CTX).to_csv(OUT / 'W3_context.csv', index=False)
    ex = exploratory(Bs, res)
    if len(ex):
        ex.to_csv(OUT / 'W3_exploratory.csv', index=False)
        print(ex[[c for c in show if c in ex.columns]].round(3).to_string(index=False))
