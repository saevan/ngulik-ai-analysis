"""Adversarial critic of the interpretations drawn from the sideways study (claims 1-5). Written AFTER seeing results.csv,
descriptive.csv and s6_random_walk_baseline.csv: everything here is exploratory, not pre-registered.
Does not import battery.py (importing it would rewrite results.csv); the needed pieces are re-built here the same way.
Run: python sideways_properties/critic_sideways.py  ->  sideways_properties/critic_sideways.csv"""
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
COST = .90  # % round trip, scenario B
RNG = np.random.default_rng(20261020)
ROWS = []


def add(claim, check, subset, metric, value, t=np.nan, n=np.nan, note=''):
    ROWS.append(dict(claim=claim, check=check, subset=subset, metric=metric, value=value, t=t, n=n, note=note))


def at(s, a, b, lags):
    m, se, n = nw(np.asarray(s.loc[a:b], float), lags)
    return m, (m / se if se and se > 0 else np.nan), n


# ---------------------------------------------------------------- setup (same construction as battery.py)
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
SIDE = REG == 'sideways'
rcc, ron, rid = P['r_cc'], P['r_on'], P['r_id']
fo = P['fo']


def ab(F):
    return F.sub(F.where(E).mean(axis=1), axis=0)


def dmean(F, M):
    return F.where(M & E).mean(axis=1)


def regime_means(claim, check, s, lags, scale, metric, note='', regimes=('sideways', 'uptrend', 'downtrend'), subs=True):
    for g in regimes:
        m, t, n = at(s.where(REG == g), *MAIN, lags)
        add(claim, check, f'{g} MAIN', metric, m * scale, t, n, note)
    if subs:
        for k, (a, b) in SUB.items():
            m, t, n = at(s.where(SIDE), a, b, lags)
            add(claim, check, f'sideways {k}', metric, m * scale, t, n, note)


# ================================================================ CLAIM 1
# 1a. The gate as coded: which rows pass, and BH over directional tests only (S2a std, S6a/S6c geometric level
#     probabilities and S7b share have a non-zero null, so testing them against 0 is meaningless).
R0 = pd.read_csv(OUT / 'results.csv')
nonzero_null = ['S2a', 'S6a', 'S6c', 'S7b']
d = R0[~R0.test_id.isin(nonzero_null)].copy()
d['q_dir'] = bh_fdr(d.p.values)
for _, r in R0.iterrows():
    add('1', 'gate as coded in results.csv', r.test_id, 'robust_in_sideways', float(r.robust_in_sideways), r.primary_t,
        r.sideways_days, f'q={r.q_BH:.4f}; signs={r.side_signs_same}/4; side_minus_rest t={r.t_side_minus_rest:.2f}')
for _, r in d.iterrows():
    gate = (abs(r.primary_t) >= 3) & (r.q_dir <= .05) & (r.side_signs_same >= 3)
    add('1', 'BH over directional tests only (18)', r.test_id, 'q_dir', r.q_dir, r.primary_t, r.sideways_days,
        f'passes gate={bool(gate)}; sideways mean={r.sideways_mean:.3f} {r.unit}; side-rest t={r.t_side_minus_rest:.2f}')

# 1b. Long-only legs (what a long-only trade earns), raw and abnormal, at 5/20/60 days, sideways signal days.
H20 = lnH.shift(1).rolling(20, min_periods=15).max()
L20 = lnL.shift(1).rolling(20, min_periods=15).min()
dlnP = lnP.diff().abs()
er20 = (lnP - lnP.shift(20)).abs() / dlnP.rolling(20).sum()
mom = (lnP.shift(21) - lnP.shift(252)).where(E).rank(axis=1, pct=True)
rev = (lnP - lnP.shift(5)).where(E).rank(axis=1, pct=True)
vol20 = rcc.rolling(20, min_periods=15).std()
vmean = P['V'].shift(1).rolling(20, min_periods=15).mean()
LEGS = {
    'all eligible': E,
    'mom12-1 top quintile': (mom > .8) & E,
    'self-trending up (ER20>=.3, 20d up)': (er20 >= .3) & (lnP - lnP.shift(20) > 0) & E,
    '5-day loser bottom quintile': (rev <= .2) & E,
    'HHV20 Close breakout': (lnP > H20) & E,
    'volume spike up day': (P['V'] >= 3 * vmean) & (rcc > 0) & E,
    'touch of 20-day low': (lnL <= L20) & E,
    'vol squeeze (bottom decile)': (vol20 <= vol20.rolling(250, min_periods=200).quantile(.1)) & E,
}
for nm, M in LEGS.items():
    for h in (5, 20, 60):
        raw, abn = dmean(fo[h], M), dmean(ab(fo[h]), M)
        for kind, s in [('raw', raw), ('abnormal', abn)]:
            m, t, n = at(s.where(SIDE), *MAIN, h)
            subs = [at(s.where(SIDE), a, b, h)[0] * 100 for a, b in SUB.values()]
            m_all, t_all, _ = at(s, *MAIN, h)
            add('1', f'long-only leg fo{h} {kind}', nm, '% per trade, sideways days', m * 100, t, n,
                f'subperiods {"/".join(f"{x:+.2f}" for x in subs)}; all days {m_all * 100:+.2f} (t {t_all:.1f}); '
                f'> cost {COST}%: {bool(m * 100 > COST)}')

# ================================================================ CLAIM 2  (S6 baseline)
C, Hr, Lr = P['C'], P['H'], P['L']
ATRr = pd.DataFrame(np.nan, index=cal, columns=cols)
for t in cols:
    m = T[t].values & C[t].notna().values
    idx = cal[m]
    h, l, c = (x.loc[idx, t].values.astype(float) for x in (Hr, Lr, C))
    tr = h - l
    tr[1:] = np.maximum(tr[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    a = np.full(len(c), np.nan)
    if len(c) >= 14:
        a[13] = tr[:14].mean()
        for i in range(14, len(c)):
            a[i] = (a[i - 1] * 13 + tr[i]) / 14
    ATRr.loc[idx, t] = a / c
ATRr = ATRr.ffill()
mid = (L20 + H20) / 2
dn_lvl = L20 + np.log(1 - ATRr.clip(upper=.5))
up_lvl = H20 + np.log(1 + ATRr)
sup_ev = (lnL <= L20) & E
res_ev = (lnH >= H20) & E
Pv, Ov, Hv, Lv = lnP.values, lnO.values, lnH.values, lnL.values
Tv = T.values
NC = len(cal)
# bootstrap pools: bars relative to the previous tradable Close (r_cc, r_on are already measured that way)
prevP = lnP.shift(1)
bar_c, bar_o = rcc.values, ron.values
bar_h, bar_l = (lnH - prevP).values, (lnL - prevP).values
pool_ok = np.isfinite(bar_c) & np.isfinite(bar_o) & np.isfinite(bar_h) & np.isfinite(bar_l) & Tv
POOL = {j: np.where(pool_ok[:, j])[0] for j in range(len(cols))}
REGv = REG.values
NPATH = 1000


def simulate(j, i, c0, U, D, K, window, drift, volmatch, block=False):
    pos = POOL[j]
    p = pos[pos <= i][-window:]
    if len(p) < min(window, 100):
        return None
    c, o, h, l = bar_c[p, j], bar_o[p, j], bar_h[p, j], bar_l[p, j]
    mu = 0. if drift else c.mean()
    c, o, h, l = c - mu, o - mu, h - mu, l - mu
    if volmatch:
        trr = np.maximum(h, 0) - np.minimum(l, 0)
        s = np.log1p(ATRr.values[i, j]) / trr.mean() if trr.mean() > 0 else 1.
        c, o, h, l = c * s, o * s, h * s, l * s
    if block:  # contiguous K-bar blocks of the stock's own history: keeps its serial dependence and vol clustering
        ix = RNG.integers(0, len(p) - K + 1, size=(NPATH, 1)) + np.arange(K)[None, :]
    else:
        ix = RNG.integers(0, len(p), size=(NPATH, K))
    cc = c[ix]
    prev = c0 + np.concatenate([np.zeros((NPATH, 1)), np.cumsum(cc, 1)[:, :-1]], 1)
    Hs, Ls, Os = prev + h[ix], prev + l[ix], prev + o[ix]
    dn, up = Ls <= D, Hs >= U
    fd = np.where(dn.any(1), dn.argmax(1), K)
    fu = np.where(up.any(1), up.argmax(1), K)
    res = np.where(fd <= fu, np.where(fd < K, -1, 0), 1)
    r_ = np.arange(NPATH)
    ex = prev[:, -1] + cc[:, -1]
    ex = np.where(res == -1, np.minimum(D, Os[r_, np.minimum(fd, K - 1)]), ex)
    ex = np.where(res == 1, np.maximum(U, Os[r_, np.minimum(fu, K - 1)]), ex)
    return (res == 1).mean(), (res == -1).mean(), (ex - c0).mean()


VARIANTS = {'boot250_driftless': (250, False, False, False), 'boot250_owndrift': (250, True, False, False),
            'boot60_driftless': (60, False, False, False), 'boot250_driftless_volmatched': (250, False, True, False),
            'block250_driftless': (250, False, False, True)}
ev_rows = []
for level, ev, UPm, DNm in [('support', sup_ev, mid.values, dn_lvl.values), ('resistance', res_ev, up_lvl.values, mid.values)]:
    ii, jj = np.where(ev.values)
    for i, j in zip(ii, jj):
        if cal[i] < pd.Timestamp(MAIN[0]) or cal[i] > pd.Timestamp(MAIN[1]):
            continue
        U, D, c0 = UPm[i, j], DNm[i, j], Pv[i, j]
        if not (np.isfinite(U) and np.isfinite(D) and np.isfinite(c0)):
            continue
        res, same, ret, kk = 0., False, np.nan, None
        last = min(i + 10, NC - 1)
        for k in range(i + 1, last + 1):
            d_, u_ = Lv[k, j] <= D, Hv[k, j] >= U
            if d_:
                res, same, kk = -1., bool(u_), k
                ret = min(D, Ov[k, j]) - c0
                break
            if u_:
                res, kk = 1., k
                ret = max(U, Ov[k, j]) - c0
                break
        if kk is None:
            ret = Pv[last, j] - c0
        K = int(Tv[i + 1:last + 1, j].sum())
        row = dict(level=level, i=i, j=j, date=cal[i], regime=REGv[i], obs=res, same_bar=same, obs_ret=ret, K=K,
                   du=U - c0, dd=c0 - D)
        if K > 0:
            for vn, (w, dr, vm, bl) in VARIANTS.items():
                s = simulate(j, i, c0, U, D, K, w, dr, vm, bl)
                if s is not None:
                    row[f'{vn}_pu'], row[f'{vn}_pd'], row[f'{vn}_ret'] = s
        ev_rows.append(row)
EV = pd.DataFrame(ev_rows)


def daily_t(df, col, lags=10, a=MAIN[0], b=MAIN[1]):
    s = df.groupby('date')[col].mean().reindex(cal)
    return at(s, a, b, lags)


for level in ['support', 'resistance']:
    for g in ['sideways', 'uptrend', 'downtrend']:
        X = EV[(EV.level == level) & (EV.regime == g)].copy()
        tag = f'{level} {g}'
        add('2', 'S6 replication', tag, 'events / P(up first) / P(down first)', len(X), n=len(X),
            note=f'p_up={(X.obs == 1).mean():.4f}; p_down={(X.obs == -1).mean():.4f}; p_neither={(X.obs == 0).mean():.4f}')
        hit = X[X.obs != 0]
        add('2', 'same-bar ambiguity', tag, 'share of down-first events where the up level was also hit that bar',
            hit[hit.obs == -1].same_bar.mean(), n=int((hit.obs == -1).sum()),
            note=f'flipping them to up-first would move P(up|hit) by {hit.same_bar.mean():+.4f}')
        A = hit[(hit.du > 0) & (hit.dd > 0)].copy()
        A['ex_rw'] = (A.obs == 1).astype(float) - A.dd / (A.du + A.dd)
        m, t, n = daily_t(A, 'ex_rw')
        add('2', 'analytic RW baseline d_down/(d_up+d_down) (replication)', tag, 'excess P(up|hit)', m, t, n,
            f'observed {np.mean(A.obs == 1):.4f} vs RW {np.mean(A.dd / (A.du + A.dd)):.4f}; '
            f'median du/dd={np.median(A.du / A.dd):.2f}; share of all events with dd<=0 or du<=0: '
            f'{1 - ((X.du > 0) & (X.dd > 0)).mean():.4f}')
        A['ex_rw_same_half'] = A.ex_rw + .5 * A.same_bar
        m, t, n = daily_t(A, 'ex_rw_same_half')
        add('2', 'analytic RW baseline, same-bar both-hit counted as 0.5', tag, 'excess P(up|hit)', m, t, n)
        for vn in VARIANTS:
            Y = X.dropna(subset=[f'{vn}_pu']).copy()
            pu_, pd_ = Y[f'{vn}_pu'], Y[f'{vn}_pd']
            Y['ex_uncond'] = Y.obs - (pu_ - pd_)
            m, t, n = daily_t(Y, 'ex_uncond')
            subs = [daily_t(Y, 'ex_uncond', 10, a, b)[0] for a, b in SUB.values()]
            add('2', f'{vn}: S6 statistic P(up first)-P(down first), incl. neither', tag, 'observed minus simulated', m, t, n,
                f'observed {Y.obs.mean():+.4f} vs simulated {(pu_ - pd_).mean():+.4f}; sim P(neither) '
                f'{(1 - pu_ - pd_).mean():.3f} vs obs {(Y.obs == 0).mean():.3f}; subperiods '
                + '/'.join(f'{x:+.3f}' for x in subs))
            Z = Y[(Y.obs != 0) & (pu_ + pd_ > 0)].copy()
            Z['ex_cond'] = (Z.obs == 1).astype(float) - Z[f'{vn}_pu'] / (Z[f'{vn}_pu'] + Z[f'{vn}_pd'])
            m, t, n = daily_t(Z, 'ex_cond')
            subs = [daily_t(Z, 'ex_cond', 10, a, b)[0] for a, b in SUB.values()]
            add('2', f'{vn}: P(up first | a level is hit)', tag, 'observed minus simulated', m, t, n,
                f'observed {(Z.obs == 1).mean():.4f} vs simulated {(Z[f"{vn}_pu"] / (Z[f"{vn}_pu"] + Z[f"{vn}_pd"])).mean():.4f}; '
                'subperiods ' + '/'.join(f'{x:+.3f}' for x in subs))
            Y['ex_ret'] = (Y.obs_ret - Y[f'{vn}_ret']) * 100
            m, t, n = daily_t(Y, 'ex_ret')
            add('2', f'{vn}: long trade from touch-day Close, exit at levels or day 10 (log %)', tag,
                'observed minus simulated trade return', m, t, n,
                f'observed {Y.obs_ret.mean() * 100:+.3f}% vs simulated {Y[f"{vn}_ret"].mean() * 100:+.3f}%; cost {COST}%')
        m, t, n = daily_t(X.assign(r=X.obs_ret * 100), 'r')
        add('2', 'realized long trade from touch-day Close (levels or day 10)', tag, '% log per trade', m, t, n,
            'before cost; fills exactly at levels unless the Open gaps through')

# ================================================================ CLAIM 3  (exit from sideways)


def labels(level):
    travel = level.diff().abs().rolling(20).sum()
    er = (level.diff(20).abs() / travel.replace(0, np.nan)).mask(travel == 0, 0)
    dr = level.diff(20)
    s = pd.Series('sideways', index=level.index)
    s[(er >= .3) & (dr > 0)] = 'uptrend'
    s[(er >= .3) & (dr < 0)] = 'downtrend'
    s[er.isna()] = 'unknown'
    return s.shift(1).fillna('unknown')


def episodes(lab):
    lab = lab.loc[MAIN[0]:MAIN[1]]
    run = (lab != lab.shift()).cumsum()
    e = pd.DataFrame({'reg': lab, 'run': run, 'd': lab.index}).groupby('run').agg(
        reg=('reg', 'first'), length=('reg', 'size'), start=('d', 'first'), end=('d', 'last'))
    e['nxt'], e['nxt_len'], e['prv'] = e.reg.shift(-1), e.length.shift(-1), e.reg.shift(1)
    return e.reset_index(drop=True)


def exit_counts(lab, minlen=5, nxt_min=1):
    e = episodes(lab)
    s = e[(e.reg == 'sideways') & (e.length >= minlen) & (e.nxt_len >= nxt_min)]
    return int((s.nxt == 'uptrend').sum()), int((s.nxt == 'downtrend').sum())


assert (labels(px['proxy']).loc[MAIN[0]:MAIN[1]] == REG.loc[MAIN[0]:MAIN[1]]).all(), 'label replication failed'
EP = episodes(REG)
lr = np.log(px['proxy']).diff()
up, dn = exit_counts(REG)
add('3', 'replication', 'proxy (battery)', 'up / down exits after sideways >= 5d', up / (up + dn), (up - dn) / np.sqrt(up + dn), up + dn,
    f'{up} up vs {dn} down; z vs 50%')
tr = EP[EP.reg.isin(['uptrend', 'downtrend'])]
base = (tr.reg == 'uptrend').mean()
add('3', 'base rate', 'all trend episodes', 'share uptrend', base, n=len(tr))
for nm, sel in [('exits from all sideways episodes', EP.reg == 'sideways'), ('exits from sideways episodes < 5d', (EP.reg == 'sideways') & (EP.length < 5))]:
    x = EP[sel & EP.nxt.isin(['uptrend', 'downtrend'])]
    p = (x.nxt == 'uptrend').mean()
    add('3', 'base rate', nm, 'share up', p, n=len(x))
p0 = base
z0 = (up - (up + dn) * p0) / np.sqrt((up + dn) * p0 * (1 - p0))
add('3', 'binomial vs base rate of trend episodes', 'sideways >= 5d', 'z', z0, z0, up + dn, f'null p={p0:.3f} instead of 0.5')
for nl in (3, 5, 10):
    u2, d2 = exit_counts(REG, 5, nl)
    add('3', 'label mechanics: only exits whose next trend lasts >= N days', f'N={nl}', 'share up', u2 / (u2 + d2), (u2 - d2) / np.sqrt(u2 + d2), u2 + d2,
        f'{u2} vs {d2}')
x = EP[(EP.reg == 'sideways') & (EP.length >= 5)]
add('3', 'label mechanics', 'next trend episode after sideways >= 5d', 'share lasting 1-2 days', (x.nxt_len <= 2).mean(), n=len(x),
    note=f'up exits median len {x[x.nxt == "uptrend"].nxt_len.median()}, down exits {x[x.nxt == "downtrend"].nxt_len.median()}')
for k, (a, b) in SUB.items():
    add('3', 'drift by subperiod', k, 'battery proxy geometric annualized', float(np.expm1(lr.loc[a:b].mean() * 250)))
    y = x[(x.start >= a) & (x.start <= b)]
    u_, d_ = int((y.nxt == 'uptrend').sum()), int((y.nxt == 'downtrend').sum())
    t_ = EP[(EP.start >= a) & (EP.start <= b) & EP.reg.isin(['uptrend', 'downtrend'])]
    add('3', 'by subperiod', k, 'share up after sideways >= 5d', u_ / max(u_ + d_, 1), n=u_ + d_,
        note=f'{u_} vs {d_}; base rate of uptrend episodes {(t_.reg == "uptrend").mean():.3f}')
# prior regime as a predictor (known in real time)
for prv in ['uptrend', 'downtrend']:
    y = x[x.prv == prv]
    u_, d_ = int((y.nxt == 'uptrend').sum()), int((y.nxt == 'downtrend').sum())
    add('3', 'exit direction by regime before the sideways episode', f'preceded by {prv}', 'share up', u_ / max(u_ + d_, 1), n=u_ + d_,
        note=f'{u_} vs {d_}')

# proxy drift and alternative proxies
lr = np.log(px['proxy']).diff()
ann = lambda s: float(np.expm1(s.loc[MAIN[0]:MAIN[1]].mean() * 250))
add('3', 'drift', 'battery proxy (raw closes, all 100 tickers, data errors kept)', 'geometric annualized', ann(lr))
simple_clean = np.expm1(rcc)
alt = {
    'clean simple EW, all tradable (bad masked)': simple_clean.where(T).mean(axis=1),
    'clean simple EW, eligible only': simple_clean.where(E).mean(axis=1),
    'clean log EW (geometric), eligible only': np.expm1(rcc.where(E).mean(axis=1)),
}
for nm, r in alt.items():
    lvl = (1 + r.fillna(0)).cumprod()
    lab = labels(lvl)
    u_, d_ = exit_counts(lab)
    add('3', 'alternative proxy: drift', nm, 'geometric annualized', ann(np.log(lvl).diff()))
    add('3', 'alternative proxy: exits after sideways >= 5d', nm, 'share up', u_ / (u_ + d_), (u_ - d_) / np.sqrt(u_ + d_), u_ + d_,
        f'{u_} vs {d_}; sideways share {(lab.loc[MAIN[0]:MAIN[1]] == "sideways").mean():.3f}; '
        f'labels agree with battery on {(lab.loc[MAIN[0]:MAIN[1]] == REG.loc[MAIN[0]:MAIN[1]]).mean():.3f} of days')
# same path with the drift removed
lrm = lr.loc[MAIN[0]:MAIN[1]]
lvl0 = np.exp((lr - lrm.mean()).fillna(0).cumsum())
u_, d_ = exit_counts(labels(lvl0))
add('3', 'drift removed (demeaned log returns of the same proxy path)', 'battery proxy', 'share up', u_ / (u_ + d_),
    (u_ - d_) / np.sqrt(u_ + d_), u_ + d_, f'{u_} vs {d_}')
# block-bootstrap null (stationary bootstrap, mean block 20) keeping vs removing the drift


def er_labels_np(level):
    dl = np.abs(np.diff(level, prepend=np.nan))
    cs = np.nancumsum(dl)
    travel = cs - np.concatenate([np.full(20, np.nan), cs[:-20]])
    chg = level - np.concatenate([np.full(20, np.nan), level[:-20]])
    er = np.abs(chg) / travel
    lab = np.zeros(len(level), int)  # 0 side, 1 up, -1 down
    lab[(er >= .3) & (chg > 0)] = 1
    lab[(er >= .3) & (chg < 0)] = -1
    return np.concatenate([[9], lab[:-1]])


def exits_np(lab):
    ch = np.flatnonzero(np.diff(lab)) + 1
    starts = np.concatenate([[0], ch])
    lens = np.diff(np.concatenate([starts, [len(lab)]]))
    regs = lab[starts]
    m = (regs[:-1] == 0) & (lens[:-1] >= 5)
    nx = regs[1:][m]
    return int((nx == 1).sum()), int((nx == -1).sum())


rv = lrm.fillna(0).values
NB, L = 2000, len(rv) + 21
for nm, base_r in [('drift kept', rv), ('drift removed', rv - rv.mean())]:
    shares = np.empty(NB)
    for bidx in range(NB):
        new = RNG.random(L) < 1 / 20
        new[0] = True
        bid = np.cumsum(new) - 1
        bstart = np.flatnonzero(new)
        off = np.arange(L) - bstart[bid]
        out = base_r[(RNG.integers(len(base_r), size=len(bstart))[bid] + off) % len(base_r)]
        lab = er_labels_np(np.exp(np.cumsum(out)))[21:]
        u_, d_ = exits_np(lab)
        shares[bidx] = u_ / max(u_ + d_, 1)
    obs = up / (up + dn)
    add('3', f'stationary block bootstrap of proxy returns ({nm})', 'battery proxy', 'mean simulated share up', shares.mean(),
        n=NB, note=f'5-95%: {np.quantile(shares, .05):.3f}-{np.quantile(shares, .95):.3f}; P(sim >= observed {obs:.3f}) = {(shares >= obs).mean():.3f}')

# exit-direction predictors measured at the Close that confirms length >= 5 (4th labelled day: the 5th label comes from
# this Close), so the features never contain the Close that decides the next label
prx = px['proxy']
sma50 = lnP.rolling(50, min_periods=50).mean()
breadth = (lnP > sma50).where(E & sma50.notna()).mean(axis=1)
feat = pd.DataFrame({
    'breadth>=0.5': breadth >= .5,
    'proxy>SMA200': prx > prx.rolling(200).mean(),
    'proxy 20d change>0': prx.diff(20) > 0,
    'proxy in top half of 20d range': (prx - prx.rolling(20).min()) / (prx.rolling(20).max() - prx.rolling(20).min()) >= .5,
    'proxy>SMA50': prx > prx.rolling(50).mean(),
})
EWfo20 = dmean(fo[20], E)
x5 = x[x.nxt.isin(['uptrend', 'downtrend'])].copy()
x5['d5'] = [cal[cal.get_loc(s) + 3] for s in x5.start]
x5['up'] = (x5.nxt == 'uptrend').astype(float)
for f in feat.columns:
    v = feat[f].reindex(x5.d5).values.astype(bool)
    a1, a0 = x5.up[v], x5.up[~v]
    pp = x5.up.mean()
    se = np.sqrt(pp * (1 - pp) * (1 / max(len(a1), 1) + 1 / max(len(a0), 1)))
    add('3', 'exit direction predictor at day 5 (two-proportion z)', f, 'share up if true minus if false', a1.mean() - a0.mean(),
        (a1.mean() - a0.mean()) / se, len(x5), f'true: {a1.mean():.3f} (n {len(a1)}); false: {a0.mean():.3f} (n {len(a0)})')
m, t, n = at(EWfo20.reindex(x5.d5).reset_index(drop=True), 0, len(x5), 1)
add('3', 'tradeability', 'EW fo20 from day 5 of sideways >= 5d episodes', '% per 20d', m * 100, t, n, 'episodes non-overlapping enough; lag 1')
# sideways age
age = (REG == 'sideways').groupby((REG != REG.shift()).cumsum()).cumcount() + 1
for lo, hi in [(1, 4), (5, 9), (10, 19), (20, 999)]:
    msk = SIDE & (age >= lo) & (age <= hi)
    m, t, n = at(EWfo20.where(msk), *MAIN, 20)
    add('3', 'EW fo20 by sideways age (exploratory)', f'age {lo}-{hi}', '% per 20d', m * 100, t, n)

# ================================================================ CLAIM 4  (dispersion, daily moves, intraday)
disp = rcc.where(E).std(axis=1) * 1e4
D = SIDE.astype(float).where(REG != 'unknown')


def dummy_reg(y, extra=None, lags=5, a=MAIN[0], b=MAIN[1]):
    yy = y.loc[a:b]
    X = [np.ones(len(yy)), D.reindex(yy.index).values]
    if extra is not None:
        ex = extra.reindex(yy.index)
        ex = ex.loc[:, ex.loc[yy.notna() & D.reindex(yy.index).notna()].std() > 0] if isinstance(ex, pd.DataFrame) else ex
        X += [ex[c].values for c in ex.columns] if isinstance(ex, pd.DataFrame) else [ex.values]
    X = np.column_stack(X)
    ok = np.isfinite(yy.values) & np.isfinite(X).all(1)
    bb, tt, n = ols_nw(np.where(ok, yy.values, np.nan), np.where(ok[:, None], X, np.nan), lags)
    return bb[1], tt[1], n


yr = pd.get_dummies(pd.Series(cal.year, index=cal), prefix='y', drop_first=True).astype(float)
subfe = pd.get_dummies(pd.Series(np.select([cal < pd.Timestamp(b) + pd.Timedelta(days=1) for a, b in SUB.values()], list(SUB), 'x'),
                                 index=cal), drop_first=True).astype(float)
ewr = rcc.where(E).mean(axis=1)
ctrl = pd.DataFrame({'lag20disp': disp.shift(1).rolling(20, min_periods=15).mean(), 'absEW': ewr.abs() * 1e4})
for nm, extra in [('none', None), ('subperiod FE', subfe), ('year FE', yr), ('trailing 20d dispersion + same-day |EW return|', ctrl),
                  ('year FE + trailing dispersion + |EW|', pd.concat([yr, ctrl], axis=1))]:
    b_, t_, n_ = dummy_reg(disp, extra)
    add('4', 'dispersion: sideways minus rest', nm, 'bps/day', b_, t_, n_)
for k, (a, b) in SUB.items():
    b_, t_, n_ = dummy_reg(disp, None, 5, a, b)
    add('4', 'dispersion: sideways minus rest within subperiod', k, 'bps/day', b_, t_, n_)
absr = rcc.abs().where(E).mean(axis=1) * 100
big = (rcc.abs() >= .03).where(E).mean(axis=1)
for g in ['sideways', 'uptrend', 'downtrend']:
    msk = REG == g
    add('4', 'daily moves', g, 'mean |r_cc| of eligible stocks (%)', float(absr[msk].loc[MAIN[0]:MAIN[1]].mean()),
        note=f'share of stock-days |r|>=3%: {float(big[msk].loc[MAIN[0]:MAIN[1]].mean()):.3f}; median ATR14 %: '
             f'{float((ATRr.where(E).median(axis=1) * 100)[msk].loc[MAIN[0]:MAIN[1]].mean()):.2f}; EW |index r| '
             f'{float((ewr.abs() * 100)[msk].loc[MAIN[0]:MAIN[1]].mean()):.2f}%')
EWid, EWon, EWcc = dmean(rid, E) * 1e4, dmean(ron, E) * 1e4, dmean(rcc, E) * 1e4
post = pd.Series((cal >= pd.Timestamp('2013-01-01')).astype(float), index=cal)
for vn, y in [('intraday r_id', EWid), ('overnight r_on', EWon), ('close-close r_cc', EWcc)]:
    for nm, extra in [('none', None), ('subperiod FE', subfe), ('year FE', yr), ('post-2013 dummy', post.to_frame('post'))]:
        b_, t_, n_ = dummy_reg(y, extra)
        add('4', f'{vn}: sideways minus rest', nm, 'bps/day', b_, t_, n_)
    for nm, (a, b) in [('2000-2012', ('2000-01-01', '2012-12-31')), ('2013-2025', ('2013-01-01', MAIN[1]))] + list(SUB.items()):
        b_, t_, n_ = dummy_reg(y, None, 5, a, b)
        means = {g: float(y[REG == g].loc[a:b].mean()) for g in ['sideways', 'uptrend', 'downtrend']}
        add('4', f'{vn}: sideways minus rest within period', nm, 'bps/day', b_, t_, n_,
            'means side/up/down ' + '/'.join(f'{v:+.1f}' for v in means.values()))

# ================================================================ CLAIM 5  (daily continuation)
sg = np.sign(rcc)
comp = {'r_cc[t+1] (S3a)': rcc.shift(-1), 'r_on[t+1] (overnight, not reachable from next Open)': ron.shift(-1),
        'r_id[t+1] (Open->Close, reachable)': rid.shift(-1)}
for nm, F in comp.items():
    s = dmean(sg * F, E)
    for g in ['sideways', 'uptrend', 'downtrend']:
        m, t, n = at(s.where(REG == g), *MAIN, 5)
        add('5', f'sign(r_cc[t]) x {nm}', f'{g} MAIN', 'bps/day', m * 1e4, t, n)
    for k, (a, b) in list(SUB.items()) + [('2021-22', ('2021-01-01', '2022-12-31')), ('2023-24', ('2023-01-01', '2024-12-06')),
                                          ('2024-12-09..2025-08', ('2024-12-09', MAIN[1]))]:
        m, t, n = at(s.where(SIDE), a, b, 5)
        add('5', f'sign(r_cc[t]) x {nm}', f'sideways {k}', 'bps/day', m * 1e4, t, n)
s3a = dmean(sg * rcc.shift(-1), E)
for g in ['uptrend', 'downtrend', 'all']:
    for k in ['2016-20', '2021-25']:
        m, t, n = at(s3a if g == 'all' else s3a.where(REG == g), *SUB[k], 5)
        add('5', 'S3a outside sideways (is the 2021-25 sign flip sideways-specific?)', f'{g} {k}', 'bps/day', m * 1e4, t, n)
abr = ab(rcc)
s_ab = dmean(np.sign(abr) * abr.shift(-1), E)
s_mk = np.sign(ewr) * ewr.shift(-1)
for nm, s in [('idiosyncratic: sign(abn r) x abn r[t+1]', s_ab), ('market: sign(EW r) x EW r[t+1]', s_mk)]:
    m, t, n = at(s.where(SIDE), *MAIN, 5)
    add('5', 'decomposition', f'{nm} sideways MAIN', 'bps/day', m * 1e4, t, n)
    for k, (a, b) in SUB.items():
        m, t, n = at(s.where(SIDE), a, b, 5)
        add('5', 'decomposition', f'{nm} sideways {k}', 'bps/day', m * 1e4, t, n)
for cond, M in [('after up day', rcc > 0), ('after down day', rcc < 0)]:
    for nm, F in [('r_id[t+1]', rid.shift(-1)), ('r_cc[t+1]', rcc.shift(-1))]:
        s = dmean(F, M)
        m, t, n = at(s.where(SIDE), *MAIN, 5)
        subs = [at(s.where(SIDE), a, b, 5)[0] * 1e4 for a, b in SUB.values()]
        add('5', 'long-only legs in sideways', f'{cond}: {nm}', 'bps/day', m * 1e4, t, n,
            'subperiods ' + '/'.join(f'{v:+.1f}' for v in subs))

# ================================================================ UNTESTED (exploratory pointers)
pos20 = (prx - prx.rolling(20).min()) / (prx.rolling(20).max() - prx.rolling(20).min())
for h in (5, 10):
    EWfo = dmean(fo[h], E)
    for nm, msk in [('proxy in bottom 20% of its 20d range', pos20 <= .2), ('proxy in top 20%', pos20 >= .8)]:
        m, t, n = at(EWfo.where(SIDE & msk), *MAIN, h)
        subs = [at(EWfo.where(SIDE & msk), a, b, h)[0] * 100 for a, b in SUB.values()]
        add('U', f'index range position on sideways days -> EW fo{h} raw', nm, '% per trade', m * 100, t, n,
            'subperiods ' + '/'.join(f'{v:+.2f}' for v in subs))
shock = (rcc <= np.log(1 - 2 * ATRr.shift(1).clip(upper=.45))) & E
for nm, F, h, sc in [('next-day r_id', rid.shift(-1), 5, 1e4), ('abnormal fo5', ab(fo[5]), 5, 100), ('raw fo5', fo[5], 5, 100),
                     ('raw fo20', fo[20], 20, 100)]:
    s = dmean(F, shock)
    m, t, n = at(s.where(SIDE), *MAIN, h)
    subs = [at(s.where(SIDE), a, b, h)[0] * sc for a, b in SUB.values()]
    add('U', 'one-day drop <= -2 ATR on a sideways day', nm, 'bps' if sc == 1e4 else '% per trade', m * sc, t, n,
        'subperiods ' + '/'.join(f'{v:+.2f}' for v in subs))
on_side = dmean(ron.shift(-1), E)
for k, (a, b) in SUB.items():
    m, t, n = at(on_side.where(SIDE), a, b, 5)
    add('U', 'entry timing: overnight return after a sideways day (Close entry instead of next Open)', k, 'bps/day', m * 1e4, t, n)

R = pd.DataFrame(ROWS)
R.to_csv(OUT / 'critic_sideways.csv', index=False)
pd.set_option('display.width', 250)
pd.set_option('display.max_colwidth', 170)
pd.set_option('display.max_rows', 2000)
print(R.round(4).to_string(index=False))
