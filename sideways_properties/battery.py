"""Market properties during sideways markets (plan: sideways_properties/PLAN.md, committed before results).
Run: python sideways_properties/battery.py  ->  sideways_properties/results.csv, descriptive.csv"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from panel import load
from mpstats import nw, ols_nw, bh_fdr, pval
import grid_search_timehunter as engine
import pit_universe as pu
import pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy

OUT = Path(__file__).resolve().parent
SUB = {'2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
       '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
MAIN = ('2000-01-01', '2025-08-15')

P = load()
lnP, lnO, lnH, lnL, T = P['lnP'], P['lnO'], P['lnH'], P['lnL'], P['T']
cal, cols = lnP.index, lnP.columns
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
E = pd.DataFrame(False, index=cal, columns=cols)
for t in cols:
    E.loc[E.index.isin(list(pit[t] & stale[t])), t] = True
E = E & T & ~P['bad'] & lnP.notna()
px = regime_proxy(st).reindex(cal)
REG = px['regime'].fillna('unknown')
r60 = px['proxy'] / px['proxy'].shift(60) - 1
REG60 = pd.Series('sideways', index=cal)
REG60[r60 > .05] = 'uptrend'
REG60[r60 < -.05] = 'downtrend'
REG60 = REG60.where(r60.notna(), 'unknown').shift(1).fillna('unknown')


def ab(F):
    return F.sub(F.where(E).mean(axis=1), axis=0)


def dmean(F, M):
    return F.where(M & E).mean(axis=1)


fo = {h: P['fo'][h] for h in (5, 20)}
fc5 = lnP.shift(-5) - lnP
fc10 = lnP.shift(-10) - lnP
rcc = P['r_cc']
ROWS, DESC = [], []


def at(s, a, b, lags):
    m, se, n = nw(s.loc[a:b].values, lags)
    return m, (m / se if se and se > 0 else np.nan), n


def regime_row(tid, desc, unit, s, lags, scale, primary='side'):
    s = s.loc[:MAIN[1]]
    r = dict(test_id=tid, description=desc, unit=unit)
    for g in ['sideways', 'uptrend', 'downtrend']:
        m, t, n = at(s.where(REG.reindex(s.index) == g), *MAIN, lags)
        r[f'{g}_mean'], r[f'{g}_t'], r[f'{g}_days'] = m * scale, t, n
    D = (REG.reindex(s.index) == 'sideways').astype(float).where(REG.reindex(s.index) != 'unknown')
    y = s.loc[MAIN[0]:]
    X = np.column_stack([np.ones(len(y)), D.loc[MAIN[0]:].values])
    ok = np.isfinite(y.values) & np.isfinite(X).all(1)
    b, tt, n = ols_nw(np.where(ok, y.values, np.nan), np.where(ok[:, None], X, np.nan), lags)
    r['side_minus_rest'], r['t_side_minus_rest'] = b[1] * scale, tt[1]
    for k, (a, bb) in SUB.items():
        m, t, n = at(s.where(REG.reindex(s.index) == 'sideways'), a, bb, lags)
        r[f'side_{k}'] = m * scale
    m, t, n = at(s.where(REG60.reindex(s.index) == 'sideways'), *MAIN, lags)
    r['side_ret60_mean'], r['side_ret60_t'] = m * scale, t
    r['primary_stat'] = 'sideways_mean'
    r['primary_t'] = r['sideways_t']
    ROWS.append(r)
    return r


def within_side_row(tid, desc, unit, y, D, lags, scale):
    """Effect of dummy D on y using sideways days only."""
    side = REG.reindex(y.index) == 'sideways'
    r = dict(test_id=tid, description=desc, unit=unit, primary_stat='within_sideways_diff')
    for k, (a, b) in [('MAIN', MAIN)] + list(SUB.items()):
        yy = y.where(side).loc[a:b]
        DD = D.astype(float).where(D.notna()).reindex(yy.index)
        X = np.column_stack([np.ones(len(yy)), DD.values])
        ok = np.isfinite(yy.values) & np.isfinite(X).all(1)
        if ok.sum() < 30 or len(np.unique(DD.values[ok])) < 2:
            r[f'side_{k}'] = np.nan
            continue
        bb, tt, n = ols_nw(np.where(ok, yy.values, np.nan), np.where(ok[:, None], X, np.nan), lags)
        if k == 'MAIN':
            r['sideways_mean'], r['sideways_t'], r['sideways_days'] = bb[1] * scale, tt[1], n
        else:
            r[f'side_{k}'] = bb[1] * scale
    r['primary_t'] = r.get('sideways_t', np.nan)
    ROWS.append(r)


def atr_matrix():
    C, H, L = P['C'], P['H'], P['L']
    A = pd.DataFrame(np.nan, index=cal, columns=cols)
    for t in cols:
        m = T[t].values & C[t].notna().values
        idx = cal[m]
        h, l, c = (x.loc[idx, t].values.astype(float) for x in (H, L, C))
        tr = h - l
        tr[1:] = np.maximum(tr[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
        a = np.full(len(c), np.nan)
        if len(c) >= 14:
            a[13] = tr[:14].mean()
            for i in range(14, len(c)):
                a[i] = (a[i - 1] * 13 + tr[i]) / 14
        A.loc[idx, t] = a / c  # relative ATR through bar t
    return A.ffill()


# ---- S1 market dynamics
lab = REG.loc[MAIN[0]:MAIN[1]]
runs = (lab != lab.shift()).cumsum()
ep = pd.DataFrame({'reg': lab, 'run': runs}).groupby('run').agg(reg=('reg', 'first'), length=('reg', 'size'),
                                                                   start=('reg', lambda s: s.index[0]))
for g in ['sideways', 'uptrend', 'downtrend']:
    e = ep[ep.reg == g]
    DESC.append(dict(item=f'S1a {g}', share_days=float((lab == g).mean()), episodes=len(e),
                     median_len=float(e.length.median()), p75_len=float(e.length.quantile(.75)), p90_len=float(e.length.quantile(.9))))
for k, (a, b) in SUB.items():
    DESC.append(dict(item=f'S1a sideways share {k}', share_days=float((REG.loc[a:b] == 'sideways').mean())))
nxt = ep.reg.shift(-1)
long_side = ep[(ep.reg == 'sideways') & (ep.length >= 5)]
to = nxt.loc[long_side.index].value_counts()
up_n, dn_n = int(to.get('uptrend', 0)), int(to.get('downtrend', 0))
z = (up_n - dn_n) / np.sqrt(up_n + dn_n) if up_n + dn_n else np.nan
DESC.append(dict(item='S1c after sideways >= 5 days', to_uptrend=up_n, to_downtrend=dn_n, binomial_z=z))
EWfo20 = dmean(fo[20], E)
regime_row('S1b', 'EW forward 20-day return (Open t+1 -> Close t+20), raw', '% per 20d', EWfo20, 20, 100)

# ---- S2 dispersion and own trend
regime_row('S2a', 'cross-sectional std of daily returns (eligible)', 'bps/day', rcc.where(E).std(axis=1), 5, 1e4)
dlnP = lnP.diff().abs()
er20 = (lnP - lnP.shift(20)).abs() / dlnP.rolling(20).sum()
self_up = (er20 >= .3) & (lnP - lnP.shift(20) > 0)
regime_row('S2b', 'stocks trending on their own (ER20>=0.3, 20d up): abnormal fo20', '% per 20d', dmean(ab(fo[20]), self_up), 20, 100)
DESC.append(dict(item='S2b share of eligible stocks self-trending up, by regime',
                 **{g: float(self_up.where(E).mean(axis=1)[REG == g].mean()) for g in ['sideways', 'uptrend', 'downtrend']}))

# ---- S3 time-series predictability (raw)
regime_row('S3a', 'sign(r_cc[t]) x r_cc[t+1] (close to close)', 'bps/day', dmean(np.sign(rcc) * rcc.shift(-1), E), 5, 1e4)
regime_row('S3b', 'sign(5-day return) x next 5-day close-to-close', '% per 5d', dmean(np.sign(lnP - lnP.shift(5)) * fc5, E), 5, 100)
regime_row('S3c', 'sign(20-day return) x fo20', '% per 20d', dmean(np.sign(lnP - lnP.shift(20)) * fo[20], E), 20, 100)


# ---- S4 cross-section (daily quintiles among eligible)
def q_spread(sig, F, top_minus_bottom=True):
    S = sig.where(E)
    rk = S.rank(axis=1, pct=True)
    A = ab(F)
    top, bot = dmean(A, rk > .8), dmean(A, rk <= .2)
    return top - bot if top_minus_bottom else bot - top


regime_row('S4a', 'short-term reversal: 5-day return bottom minus top quintile -> abnormal fo5', '% per 5d',
           q_spread(lnP - lnP.shift(5), fo[5], False), 5, 100)
regime_row('S4b', '12-1 momentum top minus bottom quintile -> abnormal fo20', '% per 20d',
           q_spread(lnP.shift(21) - lnP.shift(252), fo[20]), 20, 100)

# ---- S5 overnight / intraday
regime_row('S5a', 'EW overnight return r_on', 'bps/day', dmean(P['r_on'], E), 5, 1e4)
regime_row('S5b', 'EW intraday return r_id', 'bps/day', dmean(P['r_id'], E), 5, 1e4)

# ---- S6 range reliability (first passage within 10 days)
ATRr = atr_matrix()
L20 = lnL.shift(1).rolling(20, min_periods=15).min()
H20 = lnH.shift(1).rolling(20, min_periods=15).max()
mid = (L20 + H20) / 2
dn_lvl = L20 + np.log(1 - ATRr.clip(upper=.5))
up_lvl = H20 + np.log(1 + ATRr)
sup_ev = (lnL <= L20) & E
res_ev = (lnH >= H20) & E
Hv, Lv = lnH.values, lnL.values


def first_passage(ev, hit_up, hit_dn):
    """+1 if the up level is reached first, -1 if the down level first (same-bar = -1), 0 if neither in 10 days."""
    out = np.full(ev.shape, np.nan)
    ii, jj = np.where(ev.values)
    U, Dn = hit_up.values, hit_dn.values
    for i, j in zip(ii, jj):
        res = 0.
        for k in range(i + 1, min(i + 11, len(cal))):
            d_ = Lv[k, j] <= Dn[i, j]
            u_ = Hv[k, j] >= U[i, j]
            if d_:
                res = -1.; break
            if u_:
                res = 1.; break
        out[i, j] = res
    return pd.DataFrame(out, index=cal, columns=cols)


fp_sup = first_passage(sup_ev, mid, dn_lvl)
fp_res = first_passage(res_ev, up_lvl, mid)
regime_row('S6a', 'touch of 20-day low: P(mid first) - P(1 ATR below old low first), 10 days', 'prob diff', fp_sup.mean(axis=1), 10, 1)
regime_row('S6b', 'touch of 20-day low: close-to-close return over 10 days, abnormal', '% per 10d', dmean(ab(fc10), sup_ev), 10, 100)
regime_row('S6c', 'touch of 20-day high: P(new high + 1 ATR first) - P(back to mid first), 10 days', 'prob diff', fp_res.mean(axis=1), 10, 1)
for nm, fp in [('support', fp_sup), ('resistance', fp_res)]:
    for g in ['sideways', 'uptrend', 'downtrend']:
        v = fp.loc[MAIN[0]:MAIN[1]][REG.loc[MAIN[0]:MAIN[1]] == g].values
        v = v[np.isfinite(v)]
        DESC.append(dict(item=f'S6 {nm} {g}', events=len(v), p_up_first=float((v == 1).mean()), p_down_first=float((v == -1).mean()),
                         p_neither=float((v == 0).mean())))

# ---- S7 breakouts
brk = (lnP > H20) & E
regime_row('S7a', 'HHV20 Close breakout -> abnormal fo20', '% per 20d', dmean(ab(fo[20]), brk), 20, 100)
fail = pd.concat([lnP.shift(-k) < H20 for k in (1, 2, 3)]).groupby(level=0).max().reindex(cal).astype(float)
regime_row('S7b', 'breakout failure rate (Close back below the level within 3 days)', 'share', fail.where(brk).mean(axis=1), 5, 1)

# ---- S8 volatility squeeze
vol20 = rcc.rolling(20, min_periods=15).std()
sq = (vol20 <= vol20.rolling(250, min_periods=200).quantile(.1)) & E
nsq = (~sq) & E & vol20.notna()
absfo = fo[20].abs()
regime_row('S8a', 'squeeze: |fo20| squeeze minus non-squeeze stocks', '% per 20d', dmean(absfo, sq) - dmean(absfo, nsq), 20, 100)
regime_row('S8b', 'squeeze: abnormal fo20', '% per 20d', dmean(ab(fo[20]), sq), 20, 100)

# ---- S9 volume spike up
vmean = P['V'].shift(1).rolling(20, min_periods=15).mean()
spike = (P['V'] >= 3 * vmean) & (rcc > 0) & E
regime_row('S9a', 'volume spike on an up day -> abnormal fo20', '% per 20d', dmean(ab(fo[20]), spike), 20, 100)

# ---- S10 characteristics
x = np.log1p(P['r_cc'].where(E).pipe(np.expm1).mean(axis=1))
X = pd.DataFrame(np.repeat(x.values[:, None], len(cols), 1), index=cal, columns=cols).where(rcc.notna())
Y = rcc.where(X.notna())
roll = lambda f: f.rolling(60, min_periods=40)
beta = (roll(X * Y).mean() - roll(X).mean() * roll(Y).mean()) / (roll(X * X).mean() - roll(X).mean() ** 2)


def tercile_spread(sig, F):
    rk = sig.where(E).rank(axis=1, pct=True)
    A = ab(F)
    return dmean(A, rk > 2 / 3) - dmean(A, rk <= 1 / 3)


regime_row('S10a', 'beta (60d) top minus bottom tercile -> abnormal fo20', '% per 20d', tercile_spread(beta, fo[20]), 20, 100)
regime_row('S10b', 'liquidity (log 60d traded value) top minus bottom tercile -> abnormal fo20', '% per 20d',
           tercile_spread(np.log(P['value'].rolling(60, min_periods=40).mean()), fo[20]), 20, 100)

# ---- S11 what predicts the exit from sideways
sma50 = lnP.rolling(50, min_periods=50).mean()
breadth = (lnP > sma50).where(E & sma50.notna()).mean(axis=1)
Db = pd.Series(np.where(breadth >= .6, 1., np.where(breadth < .4, 0., np.nan)), index=cal)
within_side_row('S11a', 'within sideways: breadth >= 60% minus < 40% -> EW fo20 (raw)', '% per 20d', EWfo20, Db, 20, 100)
prx = px['proxy']
Dt = (prx > prx.rolling(200).mean()).astype(float).where(prx.rolling(200).mean().notna())
within_side_row('S11b', 'within sideways: EW proxy above minus below SMA200 -> EW fo20 (raw)', '% per 20d', EWfo20, Dt, 20, 100)

R = pd.DataFrame(ROWS)
R['p'] = [pval(t) for t in R.primary_t]
R['q_BH'] = bh_fdr(R.p.values)
side_cols = [f'side_{k}' for k in SUB]
R['side_signs_same'] = [int(sum(np.sign(r[c]) == np.sign(r['sideways_mean']) for c in side_cols)) for _, r in R.iterrows()]
R['robust_in_sideways'] = (R.primary_t.abs() >= 3) & (R.q_BH <= .05) & (R.side_signs_same >= 3)
R.to_csv(OUT / 'results.csv', index=False)
pd.DataFrame(DESC).to_csv(OUT / 'descriptive.csv', index=False)
pd.set_option('display.width', 260)
pd.set_option('display.max_columns', 40)
show = ['test_id', 'unit', 'sideways_mean', 'sideways_t', 'uptrend_mean', 'downtrend_mean', 'side_minus_rest', 't_side_minus_rest',
        'side_2000-07', 'side_2008-15', 'side_2016-20', 'side_2021-25', 'side_ret60_mean', 'q_BH', 'robust_in_sideways']
print(R[show].round(3).to_string(index=False))
print(pd.DataFrame(DESC).round(3).to_string(index=False))
