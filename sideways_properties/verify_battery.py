"""Independent adversarial verification of sideways_properties/battery.py and s6_random_walk_baseline.py.

Does NOT import battery.py: eligibility, regimes, signals, forward returns, ATR, first passage, per-day aggregation,
Newey-West means and the dummy regression are rebuilt here from the shared helpers (panel.load, pit_universe,
pit_stale_liquidity, analyze_portfolio_regimes.regime_proxy). Compares with results.csv / descriptive.csv /
s6_random_walk_baseline.csv (tolerance: 10% relative, or difference within 0.5 t / 0.5 standard errors), then audits
look-ahead, the first-passage logic, the S6 random-walk null, the side_minus_rest dummy regression and NW lag choice.
Prints only; writes no files.  Run: python sideways_properties/verify_battery.py
"""
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from panel import load                                   # noqa: E402
import mpstats                                           # noqa: E402
import grid_search_timehunter as engine                  # noqa: E402
import pit_universe as pu                                # noqa: E402
import pit_stale_liquidity as psl                        # noqa: E402
from analyze_portfolio_regimes import regime_proxy       # noqa: E402

warnings.filterwarnings('ignore', message='Mean of empty slice')
pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 40)
MAIN = ('2000-01-01', '2025-08-15')
SUB = {'2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
       '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
REGS = ['sideways', 'uptrend', 'downtrend']
REL, TTOL = .10, .5
ISSUES, VERDICT = [], []


def say(*a):
    print(*a, flush=True)


# ------------------------------------------------------------------ statistics (own implementation)
def nw_mean(x, L, kernel='bartlett'):
    """Mean, NW standard error, n. NaN = missing; missing points keep their position (lag k = k index steps)."""
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    n = int(ok.sum())
    if n < 20:
        return np.nan, np.nan, n
    m = x[ok].mean()
    e = np.where(ok, x - m, 0.)
    v = float(e @ e)
    for k in range(1, min(L, len(e) - 1) + 1):
        w = 1 - k / (L + 1) if kernel == 'bartlett' else 1.
        v += 2 * w * float(e[k:] @ e[:-k])
    return m, math.sqrt(max(v, 0.)) / n, n


def ols_hac(y, X, L):
    y, X = np.asarray(y, float), np.asarray(X, float)
    ok = np.isfinite(y) & np.isfinite(X).all(1)
    Xo, yo = X[ok], y[ok]
    A = np.linalg.inv(Xo.T @ Xo)
    b = A @ Xo.T @ yo
    u = np.zeros(len(y))
    u[ok] = yo - Xo @ b
    g = np.where(ok[:, None], X, 0.) * u[:, None]
    S = g.T @ g
    for k in range(1, L + 1):
        G = g[k:].T @ g[:-k]
        S += (1 - k / (L + 1)) * (G + G.T)
    se = np.sqrt(np.diag(A @ S @ A))
    return b, b / se, int(ok.sum())


# ------------------------------------------------------------------ data, eligibility, regimes
P = load()
lnP, lnO, lnH, lnL, T, bad = P['lnP'], P['lnO'], P['lnH'], P['lnL'], P['T'], P['bad']
cal, cols = lnP.index, lnP.columns
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
E = pd.DataFrame({t: cal.isin(pd.DatetimeIndex(sorted(pit.get(t, set()) & stale.get(t, set())))) for t in cols},
                 index=cal)
E = E & T & ~bad & lnP.notna()
Ev = E.values

px = regime_proxy(st).reindex(cal)
REG = px['regime'].fillna('unknown')
regv = REG.values
in_main = (cal >= pd.Timestamp(MAIN[0])) & (cal <= pd.Timestamp(MAIN[1]))

# forward returns rebuilt from levels and checked against the panel's own
fo20 = lnP.shift(-20) - lnO.shift(-1)
fo5 = lnP.shift(-5) - lnO.shift(-1)
for h, F in [(20, fo20), (5, fo5)]:
    a, b = F.values, P['fo'][h].values
    same = np.array_equal(np.isnan(a), np.isnan(b)) and np.nanmax(np.abs(a - b)) < 1e-12
    say(f'fo{h} rebuilt == panel fo[{h}]: {same}')
rcc, ron, rid = P['r_cc'], P['r_on'], P['r_id']


def dmean(F, M):
    """Per-day mean of F over stocks with M & E (NaN when none)."""
    A = np.asarray(F, float)
    W = np.asarray(M, bool) & Ev & np.isfinite(A)
    with np.errstate(invalid='ignore'):
        s = np.where(W, A, 0.).sum(1) / W.sum(1)
    return pd.Series(s, index=cal)


def ab(F):
    A = np.asarray(F, float)
    W = Ev & np.isfinite(A)
    with np.errstate(invalid='ignore'):
        m = np.where(W, A, 0.).sum(1) / W.sum(1)
    return A - m[:, None]


def regime_stats(s, L, reg=None, kernel='bartlett'):
    reg = regv if reg is None else reg
    s = pd.Series(np.asarray(s, float), index=cal).where(in_main)
    r = {}
    for g in REGS:
        m, se, n = nw_mean(s.where(reg == g).values, L, kernel)
        r[f'{g}_mean'], r[f'{g}_se'], r[f'{g}_t'], r[f'{g}_days'] = m, se, m / se, n
    D = np.where(reg == 'sideways', 1., np.where(np.isin(reg, ['uptrend', 'downtrend']), 0., np.nan))
    b, tt, n = ols_hac(s.values, np.column_stack([np.ones(len(s)), D]), L)
    r['side_minus_rest'], r['t_side_minus_rest'] = b[1], tt[1]
    r['smr_se'] = b[1] / tt[1]
    y = s.values
    with np.errstate(invalid='ignore'):
        r['smr_direct'] = np.nanmean(y[D == 1]) - np.nanmean(y[D == 0])
    for k, (a, bb) in SUB.items():
        mm = (cal >= pd.Timestamp(a)) & (cal <= pd.Timestamp(bb))
        m, se, n = nw_mean(s.where((reg == 'sideways') & mm).values, L, kernel)
        r[f'side_{k}'], r[f'side_{k}_se'] = m, se
    return r


RES = pd.read_csv(HERE / 'results.csv').set_index('test_id')
DES = pd.read_csv(HERE / 'descriptive.csv').set_index('item')
RWB = pd.read_csv(HERE / 's6_random_walk_baseline.csv').set_index(['level', 'regime'])


def agree(mine, ref, se=None, is_t=False):
    if not (np.isfinite(mine) and np.isfinite(ref)):
        return (not np.isfinite(mine)) and (not np.isfinite(ref))
    if abs(mine - ref) <= REL * abs(ref) + 1e-12:
        return True
    if is_t:
        return abs(mine - ref) <= TTOL
    return se is not None and np.isfinite(se) and se > 0 and abs(mine - ref) / se <= TTOL


def compare_row(tid, s, L, scale):
    r = regime_stats(s, L)
    ref = RES.loc[tid]
    out, worst = [], []
    for f in ['sideways_mean', 'uptrend_mean', 'downtrend_mean', 'side_minus_rest'] + [f'side_{k}' for k in SUB]:
        se = r['smr_se'] if f == 'side_minus_rest' else r[f.replace('_mean', '') + '_se'] if f.endswith('_mean') else r[f + '_se']
        ok = agree(r[f] * scale, ref[f], se * scale)
        out.append(ok)
        if not ok:
            worst.append(f'{f}: mine {r[f] * scale:.4g} vs {ref[f]:.4g}')
    for f in ['sideways_t', 'uptrend_t', 'downtrend_t', 't_side_minus_rest']:
        ok = agree(r[f], ref[f], is_t=True)
        out.append(ok)
        if not ok:
            worst.append(f'{f}: mine {r[f]:.3f} vs {ref[f]:.3f}')
    dmax = max(abs(r[f] * scale - ref[f]) / max(abs(ref[f]), 1e-12) for f in ['sideways_mean', 'side_minus_rest'])
    VERDICT.append(dict(test_id=tid, ok=all(out), note=(f'side {r["sideways_mean"] * scale:.4g} (t {r["sideways_t"]:.2f}) vs '
                    f'{ref["sideways_mean"]:.4g} (t {ref["sideways_t"]:.2f}); smr {r["side_minus_rest"] * scale:.4g} '
                    f'(t {r["t_side_minus_rest"]:.2f}) vs {ref["side_minus_rest"]:.4g} (t {ref["t_side_minus_rest"]:.2f}); '
                    f'max rel dev {dmax:.2%}' + ('; MISMATCH ' + '; '.join(worst) if worst else ''))))
    assert abs(r['side_minus_rest'] - r['smr_direct']) < 1e-9 * max(1, abs(r['smr_direct'])), 'dummy coef != diff of means'
    say(f'{tid}: {"OK " if all(out) else "FAIL"} {VERDICT[-1]["note"]}')
    return r


# ------------------------------------------------------------------ audits of alignment / causality
say('\n=== Look-ahead audits ===')
closes = st.pivot(index='Date/Time', columns='Ticker', values='Close').sort_index().ffill()
ret_raw = closes.pct_change(fill_method=None)


def own_regime(ret, thr=.3):
    idx = (1 + ret.mean(axis=1).fillna(0)).cumprod() * 100
    trav = idx.diff().abs().rolling(20).sum()
    er = (idx.diff(20).abs() / trav.replace(0, np.nan)).mask(trav == 0, 0)
    d = idx.diff(20)
    s = pd.Series('sideways', index=idx.index)
    s[(er >= thr) & (d > 0)] = 'uptrend'
    s[(er >= thr) & (d < 0)] = 'downtrend'
    s[er.isna()] = 'unknown'
    return s.reindex(cal)


state_same_day = own_regime(ret_raw)
mis_lag1 = int((state_same_day.shift(1).fillna('unknown') != REG).sum())
mis_lag0 = int((state_same_day != REG).sum())
say(f'REG[t] == own ER20 state computed through Close t-1: mismatches {mis_lag1}; vs state through Close t: {mis_lag0}')
cut = pd.Timestamp('2012-06-29')
pref = regime_proxy(st[st['Date/Time'] <= cut])['regime']
say(f'regime prefix-causal at cut {cut.date()}: {bool((pref == REG.loc[:cut]).all())}')
fr_cut = {t: f[f['Date/Time'] <= cut] for t, f in fr.items() if (f['Date/Time'] <= cut).any()}
pit_c, st_c = pu.eligibility(fr_cut, .5), psl.stale_ok(fr_cut)
diff_el = sum(len({d for d in (pit[t] & stale[t]) if d <= cut} ^ (pit_c[t] & st_c[t])) for t in fr_cut)
say(f'eligibility prefix-causal at cut {cut.date()}: symmetric-difference dates = {diff_el}')
ret_clean = ret_raw.mask(ret_raw.abs() >= .5)
REG_clean = own_regime(ret_clean).shift(1).fillna('unknown')
n_badday = int((ret_raw.abs() >= .5).any(axis=1).loc[MAIN[0]:MAIN[1]].sum())
chg = float((REG_clean != REG)[in_main].mean())
say(f'proxy days in MAIN containing a >=50% single-stock jump (masked in the panel, not in the proxy): {n_badday}; '
    f'regime labels that change if those jumps are masked: {chg:.2%}')
if mis_lag1 == 0:
    say('-> regime label at t uses information through Close t-1 only (strictly lagged; no look-ahead).')
if chg > 0:
    ISSUES.append(f'Regime proxy is built from RAW closes, so the >=50% unadjusted jumps that panel.py masks still enter the '
                  f'EW proxy ({n_badday} MAIN days); masking them changes {chg:.2%} of MAIN regime labels. Minor.')

# ------------------------------------------------------------------ S1c transitions
say('\n=== S1c ===')
lab = REG[in_main].values
starts = np.r_[0, np.flatnonzero(lab[1:] != lab[:-1]) + 1]
ends = np.r_[starts[1:], len(lab)]
ep_reg, ep_len = lab[starts], ends - starts
nxt = np.append(ep_reg[1:], 'none')
sel = (ep_reg == 'sideways') & (ep_len >= 5)
up_n, dn_n = int(((nxt == 'uptrend') & sel).sum()), int(((nxt == 'downtrend') & sel).sum())
z = (up_n - dn_n) / math.sqrt(up_n + dn_n)
ref = DES.loc['S1c after sideways >= 5 days']
ok = (up_n == ref.to_uptrend) and (dn_n == ref.to_downtrend)
short = (ep_reg == 'sideways') & (ep_len < 5)
up_s, dn_s = int(((nxt == 'uptrend') & short).sum()), int(((nxt == 'downtrend') & short).sum())
n_up_ep, n_dn_ep = int((ep_reg == 'uptrend').sum()), int((ep_reg == 'downtrend').sum())
p0 = n_up_ep / (n_up_ep + n_dn_ep)
z0 = (up_n - p0 * (up_n + dn_n)) / math.sqrt((up_n + dn_n) * p0 * (1 - p0))
p1, p2 = up_n / (up_n + dn_n), up_s / (up_s + dn_s)
pp = (up_n + up_s) / (up_n + dn_n + up_s + dn_s)
z12 = (p1 - p2) / math.sqrt(pp * (1 - pp) * (1 / (up_n + dn_n) + 1 / (up_s + dn_s)))
VERDICT.append(dict(test_id='S1c', ok=ok, note=f'to_up {up_n} to_down {dn_n} z {z:.3f} vs {int(ref.to_uptrend)}/{int(ref.to_downtrend)} '
                    f'z {ref.binomial_z:.3f}'))
say(f'S1c: {"OK" if ok else "FAIL"} {VERDICT[-1]["note"]}')
say(f'  base rate: uptrend share of ALL trend episodes {n_up_ep}/{n_up_ep + n_dn_ep} = {p0:.4f}; after sideways>=5: {p1:.4f}; '
    f'after sideways<5: {up_s}/{up_s + dn_s} = {p2:.4f}')
say(f'  z vs base rate p0={p0:.3f}: {z0:.3f};  z(>=5 vs <5): {z12:.3f}')
ISSUES.append(f'S1c binomial z={z:.2f} tests against p=0.5, but the unconditional share of uptrend among all trend episodes is '
              f'{p0:.3f} (EW proxy of survivors drifts up). After sideways>=5 days the uptrend share is {p1:.3f}: z vs base '
              f'rate = {z0:.2f}; vs short sideways episodes ({p2:.3f}) z = {z12:.2f}. The "uptrend more likely after sideways" '
              f'reading carries no information beyond the base rate.')

# ------------------------------------------------------------------ S2a, S2b, S3a, S4b, S5a, S5b
say('\n=== regime rows ===')
R = {}
rcc_v = rcc.values
with np.errstate(invalid='ignore'):
    W = Ev & np.isfinite(rcc_v)
    nE = W.sum(1)
    mu = np.where(W, rcc_v, 0.).sum(1) / nE
    disp = np.sqrt(np.where(W, (rcc_v - mu[:, None]) ** 2, 0.).sum(1) / (nE - 1))
disp = np.where(nE >= 2, disp, np.nan)
R['S2a'] = compare_row('S2a', disp, 5, 1e4)

lv = lnP.values
d20 = lv - np.vstack([np.full((20, lv.shape[1]), np.nan), lv[:-20]])
absd = np.abs(np.diff(lv, axis=0, prepend=np.nan))
trav = pd.DataFrame(absd).rolling(20).sum().values
with np.errstate(invalid='ignore', divide='ignore'):
    er20 = np.abs(d20) / trav
    self_up = (er20 >= .3) & (d20 > 0)
A20 = ab(fo20.values)
R['S2b'] = compare_row('S2b', dmean(A20, self_up), 20, 100)

nxt_rcc = np.vstack([rcc_v[1:], np.full((1, rcc_v.shape[1]), np.nan)])
R['S3a'] = compare_row('S3a', dmean(np.sign(rcc_v) * nxt_rcc, np.ones_like(Ev)), 5, 1e4)

mom = lnP.shift(21) - lnP.shift(252)
rk = mom.where(E).rank(axis=1, pct=True).values
with np.errstate(invalid='ignore'):
    s4b = dmean(A20, rk > .8) - dmean(A20, rk <= .2)
R['S4b'] = compare_row('S4b', s4b, 20, 100)
R['S5a'] = compare_row('S5a', dmean(ron.values, np.ones_like(Ev)), 5, 1e4)
R['S5b'] = compare_row('S5b', dmean(rid.values, np.ones_like(Ev)), 5, 1e4)

# ------------------------------------------------------------------ ATR (Wilder, raw H/L/C on tradable bars, through bar t)
say('\n=== S6 ===')
ATR = pd.DataFrame(np.nan, index=cal, columns=cols)
for t in cols:
    m = (T[t] & P['C'][t].notna()).values
    if m.sum() < 14:
        continue
    h, l, c = (P[k][t].values[m].astype(float) for k in ('H', 'L', 'C'))
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    s = pd.Series(tr[13:].copy())
    s.iloc[0] = tr[:14].mean()
    a = np.r_[np.full(13, np.nan), s.ewm(alpha=1 / 14, adjust=False).mean().values]
    ATR.loc[cal[m], t] = a / c
ATR = ATR.ffill()
L20 = lnL.shift(1).rolling(20, min_periods=15).min()
H20 = lnH.shift(1).rolling(20, min_periods=15).max()
mid = (L20 + H20) / 2
dn_lvl = L20 + np.log(1 - ATR.clip(upper=.5))
up_lvl = H20 + np.log(1 + ATR)
with np.errstate(invalid='ignore'):
    sup_ev = (lnL.values <= L20.values) & Ev
    res_ev = (lnH.values >= H20.values) & Ev
Lv, Hv = lnL.values, lnH.values
NB = 99


def passage(ev, U, D, K=10):
    """First bar k in 1..K where Low<=D and where High>=U; result -1 (down first, same bar = -1), +1, 0 = neither."""
    U, D = np.asarray(U, float), np.asarray(D, float)
    fd = np.full(ev.shape, NB)
    fu = np.full(ev.shape, NB)
    nan_row = np.full((1, ev.shape[1]), np.nan)
    for k in range(K, 0, -1):
        Lk = np.vstack([Lv[k:], np.repeat(nan_row, k, 0)])
        Hk = np.vstack([Hv[k:], np.repeat(nan_row, k, 0)])
        with np.errstate(invalid='ignore'):
            fd = np.where(Lk <= D, k, fd)
            fu = np.where(Hk >= U, k, fu)
    r = np.where((fd < NB) & (fd <= fu), -1., np.where(fu < NB, 1., 0.))
    return np.where(ev, r, np.nan), fd, fu


fp_sup, fd_s, fu_s = passage(sup_ev, mid.values, dn_lvl.values)
fp_res, fd_r, fu_r = passage(res_ev, up_lvl.values, mid.values)
R['S6a'] = compare_row('S6a', np.nanmean(np.where(sup_ev, fp_sup, np.nan), 1), 10, 1)
R['S6c'] = compare_row('S6c', np.nanmean(np.where(res_ev, fp_res, np.nan), 1), 10, 1)

ok_all, notes = True, []
for nm, fp in [('support', fp_sup), ('resistance', fp_res)]:
    for g in REGS:
        v = fp[in_main & (regv == g)]
        v = v[np.isfinite(v)]
        ref = DES.loc[f'S6 {nm} {g}']
        mine = dict(events=len(v), p_up_first=(v == 1).mean(), p_down_first=(v == -1).mean(), p_neither=(v == 0).mean())
        ok = all(agree(mine[k], ref[k]) for k in mine)
        ok_all &= ok
        notes.append(f'{nm[:3]}/{g[:4]} n {mine["events"]}/{int(ref.events)} up {mine["p_up_first"]:.4f}/{ref.p_up_first:.4f} '
                     f'dn {mine["p_down_first"]:.4f}/{ref.p_down_first:.4f}')
VERDICT.append(dict(test_id='S6 shares', ok=ok_all, note='; '.join(notes)))
say(f'S6 first-passage shares: {"OK" if ok_all else "FAIL"}\n  ' + '\n  '.join(notes))

# first-passage logic diagnostics
lp = lnP.values
with np.errstate(invalid='ignore'):
    diag = {}
    for nm, ev, fd, fu, U, D, beyond_close, beyond_bar in [
            ('support', sup_ev, fd_s, fu_s, mid.values, dn_lvl.values, lp <= dn_lvl.values, Lv <= dn_lvl.values),
            ('resistance', res_ev, fd_r, fu_r, up_lvl.values, mid.values, lp >= up_lvl.values, Hv >= up_lvl.values)]:
        e = ev & in_main[:, None]
        n = e.sum()
        same = ((fd == fu) & (fd < NB) & e).sum()
        nanlvl = (e & ~(np.isfinite(U) & np.isfinite(D))).sum()
        tail = (e & (np.arange(len(cal)) > len(cal) - 11)[:, None]).sum()
        diag[nm] = dict(events=int(n), same_bar_both=int(same), same_bar_share=same / n,
                        touch_bar_already_beyond_break=float((beyond_bar & e).sum() / n),
                        close_t_already_beyond_break=float((beyond_close & e).sum() / n),
                        events_with_nan_level=int(nanlvl), truncated_window_at_sample_end=int(tail))
say(pd.DataFrame(diag).T.to_string())
sb = diag['support']['same_bar_share']

# outcome when touch-day close is already beyond the break level
for nm, fp, beyond in [('support', fp_sup, lp <= dn_lvl.values), ('resistance', fp_res, lp >= up_lvl.values)]:
    with np.errstate(invalid='ignore'):
        e = np.isfinite(fp) & in_main[:, None] & (regv == 'sideways')[:, None]
        say(f'  {nm} sideways: mean fp all {np.nanmean(fp[e]):.4f}; close already beyond break level '
            f'{np.nanmean(fp[e & beyond]):.4f} (n {int((e & beyond).sum())}); excluding those {np.nanmean(fp[e & ~beyond]):.4f}')

# distances in ATR units
with np.errstate(invalid='ignore', divide='ignore'):
    du_s, dd_s = mid.values - lp, lp - dn_lvl.values
    du_r, dd_r = up_lvl.values - lp, lp - mid.values
    atrl = np.log(1 + ATR.values)
    e = sup_ev & in_main[:, None]
    e2 = res_ev & in_main[:, None]
    say(f'  median distance from Close t (ATR units): support: to mid {np.nanmedian((du_s / atrl)[e]):.2f}, to break '
        f'{np.nanmedian((dd_s / atrl)[e]):.2f}; resistance: to new-high+1ATR {np.nanmedian((du_r / atrl)[e2]):.2f}, '
        f'to mid {np.nanmedian((dd_r / atrl)[e2]):.2f}')

# ------------------------------------------------------------------ S6 random-walk baseline (addendum) + window-aware null
say('\n=== S6 random-walk baseline ===')
vol20 = rcc.rolling(20, min_periods=15).std().values
ok_rw, notes = True, []
RWsave = {}
for nm, fp, du, dd in [('support', fp_sup, du_s, dd_s), ('resistance', fp_res, du_r, dd_r)]:
    with np.errstate(invalid='ignore', divide='ignore'):
        pr = dd / (du + dd)
        okm = (du > 0) & (dd > 0) & np.isfinite(fp) & (fp != 0)
        y = (fp == 1).astype(float)
        ex = np.where(okm, y - pr, np.nan)
        s = np.nanmean(ex, 1)
    RWsave[nm] = dict(okm=okm, y=y, pr=pr, du=du, dd=dd, s=s, fp=fp)
    for g in REGS:
        m, se, n = nw_mean(pd.Series(s, index=cal).where(in_main & (regv == g)).values, 10)
        sel = okm & (in_main & (regv == g))[:, None]
        ref = RWB.loc[(nm, g)]
        mine = dict(events=int(sel.sum()), observed_up_first=y[sel].mean(), random_walk_up_first=pr[sel].mean())
        ok = all(agree(mine[k], ref[k]) for k in mine) and agree(m, ref.excess, se) and agree(m / se, ref.t, is_t=True)
        sub_ok = []
        for k, (a, bb) in SUB.items():
            mm = (cal >= pd.Timestamp(a)) & (cal <= pd.Timestamp(bb)) & (regv == g)
            m2, se2, _ = nw_mean(pd.Series(s, index=cal).where(mm).values, 10)
            sub_ok.append(agree(m2, ref[k], se2))
        ok = ok and all(sub_ok)
        ok_rw &= ok
        notes.append(f'{nm[:3]}/{g[:4]} n {mine["events"]}/{int(ref.events)} excess {m:.4f}/{ref.excess:.4f} '
                     f't {m / se:.2f}/{ref.t:.2f}')
VERDICT.append(dict(test_id='S6 RW baseline', ok=ok_rw, note='; '.join(notes)))
say(f'S6 RW baseline: {"OK" if ok_rw else "FAIL"}\n  ' + '\n  '.join(notes))


def sim_null(du, dd, sig, n_paths=40, sub=16, days=10, seed=0, chunk=1500):
    """Driftless Brownian null on log price from Close t: per-day max/min, 10-day window, same-day = down first
    (battery rule), Broadie-Glasserman continuity correction (barriers moved inward) for discrete sub-steps. Returns P(up first), P(down first)."""
    rng = np.random.default_rng(seed)
    N = len(du)
    pu_, pd_ = np.empty(N), np.empty(N)
    dt = 1 / sub
    for a in range(0, N, chunk):
        b = min(a + chunk, N)
        sg = sig[a:b, None, None]
        path = np.cumsum(rng.standard_normal((b - a, n_paths, days * sub)) * sg * math.sqrt(dt), axis=2)
        path = path.reshape(b - a, n_paths, days, sub)
        hi, lo = path.max(3), path.min(3)
        cc = .5826 * sg * math.sqrt(dt)
        hd = lo <= -(dd[a:b, None, None] - cc)   # barriers moved INWARD: discrete paths miss crossings
        hu = hi >= (du[a:b, None, None] - cc)
        fdn = np.where(hd.any(2), hd.argmax(2), NB)
        fup = np.where(hu.any(2), hu.argmax(2), NB)
        res = np.where((fdn < NB) & (fdn <= fup), -1, np.where(fup < NB, 1, 0))
        pu_[a:b], pd_[a:b] = (res == 1).mean(1), (res == -1).mean(1)
    return pu_, pd_


say('\nWindow-aware null (driftless BM, 10-day window, same-bar=down rule, sigma = 20d std of r_cc or ATR/1.596):')
SIMROWS = []
for nm in ['support', 'resistance']:
    d = RWsave[nm]
    for sig_name, SIG in [('vol20', vol20), ('atr', np.log(1 + ATR.values) / 1.596)]:
        with np.errstate(invalid='ignore'):
            base = np.isfinite(d['fp']) & in_main[:, None] & (d['du'] > 0) & (d['dd'] > 0) & np.isfinite(SIG) & (SIG > 0)
        ii, jj = np.nonzero(base)
        pu_, pdn_ = sim_null(d['du'][ii, jj], d['dd'][ii, jj], SIG[ii, jj], seed=1 if nm == 'support' else 2)
        fpv = d['fp'][ii, jj]
        hit = fpv != 0
        cond = np.where(pu_ + pdn_ > 0, pu_ / np.maximum(pu_ + pdn_, 1e-12), np.nan)
        Mx = np.full(d['fp'].shape, np.nan)
        Mx[ii[hit], jj[hit]] = (fpv[hit] == 1) - cond[hit]
        Md = np.full(d['fp'].shape, np.nan)
        Md[ii, jj] = fpv - (pu_ - pdn_)
        for g in REGS:
            rg = (regv[ii] == g)
            m1, se1, _ = nw_mean(pd.Series(np.nanmean(Mx, 1), index=cal).where(regv == g).values, 10)
            m2, se2, _ = nw_mean(pd.Series(np.nanmean(Md, 1), index=cal).where(regv == g).values, 10)
            SIMROWS.append(dict(level=nm, sigma=sig_name, regime=g, events=int(rg.sum()),
                                obs_up_minus_down=float(fpv[rg].mean()), null_up_minus_down=float((pu_ - pdn_)[rg].mean()),
                                diff_excess=m2, diff_t=m2 / se2,
                                obs_up_first_given_hit=float((fpv[rg & hit] == 1).mean()),
                                naive_rw_dd_over_sum=float(np.nanmean(d['pr'][ii, jj][rg & hit])),
                                window_null_given_hit=float(np.nanmean(cond[rg & hit])), cond_excess=m1, cond_t=m1 / se1))
SIM = pd.DataFrame(SIMROWS)
say(SIM.round(4).to_string(index=False))

# ------------------------------------------------------------------ S7a, S7b
say('\n=== S7 ===')
with np.errstate(invalid='ignore'):
    brk = (lp > H20.values) & Ev
    fail = np.zeros(lp.shape, bool)
    for k in (1, 2, 3):
        fk = np.vstack([lp[k:], np.full((k, lp.shape[1]), np.nan)])
        fail |= fk < H20.values
R['S7a'] = compare_row('S7a', dmean(A20, brk), 20, 100)
R['S7b'] = compare_row('S7b', dmean(fail.astype(float), brk), 5, 1)

# ------------------------------------------------------------------ extra audits
say('\n=== NW lag sensitivity (sideways t / side_minus_rest t) ===')
SER = {'S2a': (disp, 5), 'S2b': (dmean(A20, self_up), 20), 'S3a': (dmean(np.sign(rcc_v) * nxt_rcc, np.ones_like(Ev)), 5),
       'S4b': (s4b, 20), 'S5a': (dmean(ron.values, np.ones_like(Ev)), 5), 'S5b': (dmean(rid.values, np.ones_like(Ev)), 5),
       'S7a': (dmean(A20, brk), 20), 'S7b': (dmean(fail.astype(float), brk), 5),
       'S6a': (np.nanmean(np.where(sup_ev, fp_sup, np.nan), 1), 10), 'S6c': (np.nanmean(np.where(res_ev, fp_res, np.nan), 1), 10)}
rows = []
for tid, (s, L) in SER.items():
    r = dict(test=tid, L=L)
    for lab_, LL, ker in [('L', L, 'bartlett'), ('2L', 2 * L, 'bartlett'), ('4L', 4 * L, 'bartlett'), ('L_uniform', L, 'uniform'),
                          ('60', 60, 'bartlett'), ('250', 250, 'bartlett')]:
        x = regime_stats(s, LL, kernel=ker)
        r[f'side_t_{lab_}'] = x['sideways_t']
        if ker == 'bartlett':
            r[f'smr_t_{lab_}'] = x['t_side_minus_rest']
    rows.append(r)
LAG = pd.DataFrame(rows).set_index('test')
say(LAG.round(2).to_string())

say('\n=== S3a decomposition: is the continuation reachable from the next Open? ===')
nxt_on = np.vstack([ron.values[1:], np.full((1, len(cols)), np.nan)])
nxt_id = np.vstack([rid.values[1:], np.full((1, len(cols)), np.nan)])
for nm_, Y in [('sign(r_cc[t]) x r_cc[t+1]', nxt_rcc), ('sign(r_cc[t]) x r_on[t+1]', nxt_on), ('sign(r_cc[t]) x r_id[t+1]', nxt_id)]:
    x = regime_stats(dmean(np.sign(rcc_v) * Y, np.ones_like(Ev)), 5)
    say(f'  {nm_:28s} side {x["sideways_mean"] * 1e4:7.2f} bps (t {x["sideways_t"]:.2f})  up {x["uptrend_mean"] * 1e4:6.2f}  '
        f'down {x["downtrend_mean"] * 1e4:6.2f}  smr {x["side_minus_rest"] * 1e4:6.2f} (t {x["t_side_minus_rest"]:.2f})  subs ' +
        ' '.join(f'{x[f"side_{k}"] * 1e4:.1f}' for k in SUB))

say('\n=== BH without tests whose null of zero is trivially false (S2a std>0, S6a/S6c geometry, S7b share>0) ===')
trivial = ['S2a', 'S6a', 'S6c', 'S7b']
pp_ = RES.drop(index=trivial)['p']
q2 = pd.Series(mpstats.bh_fdr(pp_.values), index=pp_.index)
say(pd.DataFrame({'p': pp_, 'q_all22': RES.loc[pp_.index, 'q_BH'], 'q_without_trivial': q2,
                  'robust_flag_in_csv': RES.loc[pp_.index, 'robust_in_sideways']}).sort_values('p').head(8).round(5).to_string())

say('\n=== regime robustness: labels from proxy with >=50% jumps masked ===')
for tid in ['S3a', 'S5b', 'S6a', 'S6c']:
    s, L = SER[tid]
    x = regime_stats(s, L, reg=REG_clean.values)
    say(f'  {tid}: side {x["sideways_mean"]:.5g} (t {x["sideways_t"]:.2f}); smr t {x["t_side_minus_rest"]:.2f}')

# ------------------------------------------------------------------ issues assembled from the numbers above
lagrow = LAG.loc['S2a']
ISSUES.append(f'S2a side_minus_rest t={RES.loc["S2a", "t_side_minus_rest"]:.2f} uses NW lags 5 on cross-sectional dispersion, a '
              f'highly persistent series; t with lags 60 = {lagrow["smr_t_60"]:.2f}, lags 250 = {lagrow["smr_t_250"]:.2f}.')
for tid in ['S2b', 'S4b', 'S7a']:
    ISSUES.append(f'{tid}: Bartlett NW with lags = horizon (20) under-weights the MA(19) overlap; sideways t {LAG.loc[tid, "side_t_L"]:.2f} '
                  f'-> {LAG.loc[tid, "side_t_2L"]:.2f} with 2L, {LAG.loc[tid, "side_t_L_uniform"]:.2f} with a uniform (Hansen-Hodrick) kernel.')
ISSUES.append('S2a, S6a, S6c and S7b are flagged robust_in_sideways=True only because their sideways mean is tested against 0, '
              'a null that is false by construction (a std is > 0; P(up)-P(down) depends on unequal level distances; a failure '
              'share is > 0). They also lower the BH thresholds for the other 18 tests (see table above).')
ISSUES.append(f'S6 first passage: same-bar ambiguity (both levels inside one bar) occurs for {sb:.2%} of support events and is '
              f'scored as "down first"; touch-day bar itself is never checked although in '
              f'{diag["support"]["touch_bar_already_beyond_break"]:.1%} of support events the touch bar already traded through '
              f'the break level and in {diag["support"]["close_t_already_beyond_break"]:.1%} the Close t is already beyond it '
              f'(near-mechanical -1). Resistance: {diag["resistance"]["close_t_already_beyond_break"]:.1%} of Closes are already '
              f'above new-high+1ATR (near-mechanical +1). The last {diag["support"]["truncated_window_at_sample_end"]} support / '
              f'{diag["resistance"]["truncated_window_at_sample_end"]} resistance events have truncated windows scored as "neither".')
sp = SIM[(SIM.level == 'support') & (SIM.sigma == 'vol20') & (SIM.regime == 'sideways')].iloc[0]
rs = SIM[(SIM.level == 'resistance') & (SIM.sigma == 'vol20') & (SIM.regime == 'uptrend')].iloc[0]
ISSUES.append(f'S6 random-walk baseline d_dn/(d_up+d_dn) is the infinite-horizon gambler\'s-ruin probability; conditioning on a hit '
              f'within 10 days (and same-bar=down) moves the null toward the NEAR level. Support/sideways: naive null '
              f'{sp.naive_rw_dd_over_sum:.3f}, window-aware BM null {sp.window_null_given_hit:.3f}, observed '
              f'{sp.obs_up_first_given_hit:.3f} -> excess {sp.cond_excess:+.4f} (t {sp.cond_t:.2f}) instead of '
              f'{RWB.loc[("support", "sideways"), "excess"]:+.4f} (t {RWB.loc[("support", "sideways"), "t"]:.2f}). Resistance/uptrend: '
              f'excess {rs.cond_excess:+.4f} (t {rs.cond_t:.2f}) instead of {RWB.loc[("resistance", "uptrend"), "excess"]:+.4f}. '
              f'Model-dependent (Gaussian, constant sigma), see the table for the ATR-based sigma.')

say('\n=== VERDICT ===')
say(pd.DataFrame(VERDICT).to_string(index=False, max_colwidth=230))
say('\n=== ISSUES ===')
for i, s in enumerate(ISSUES, 1):
    say(f'{i}. {s}')
