"""Market structure battery v3 (plan: market_structure_results/PLAN.md). Kompas100 panel 2000-2025.08.
Writes market_structure_results/s*.csv and events.csv"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from panel import load
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy

OUT = ROOT / 'market_structure_results'
PER = {'2000-25': ('2000-01-01', '2025-08-15'), '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
       '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
SUB = ['2000-07', '2008-15', '2016-20', '2021-25']
P = load()
C, O, H, L, T, Cff = P['C'], P['O'], P['H'], P['L'], P['T'], P['Cff']
lnP, lnO, lnH, lnL, fo = P['lnP'], P['lnO'], P['lnH'], P['lnL'], P['fo']
dates, tick = C.index, C.columns
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
E = pd.DataFrame(False, index=dates, columns=tick)
for t in tick:
    E.loc[dates.isin(pd.DatetimeIndex(sorted(pit[t] & stale[t]))), t] = True
ALL = pd.DataFrame(True, index=dates, columns=tick)
prev = Cff.shift(1)
EV = []


def ev(mask, h, U):
    F = fo[h].where(U)
    F = F.sub(F.mean(axis=1), axis=0)
    M = mask.reindex_like(F).fillna(False).astype(bool) & U & F.notna()
    return F.where(M).mean(axis=1), int(M.values.sum())


def record(structure, variant, mask, hs=(1, 5, 20)):
    for h in hs:
        for un, U in (('all', ALL), ('eligible', E)):
            s, n = ev(mask, h, U)
            for pn, (a, b) in PER.items():
                m, se, k = nw(s.loc[a:b].to_numpy(), max(1, h))
                EV.append(dict(structure=structure, variant=variant, h=h, universe=un, period=pn, effect_pct=m * 100,
                               t=m / se if se and se > 0 else np.nan, days=k, events=n if pn == '2000-25' else np.nan))


def per_ticker(fn):
    out = {}
    for t in tick:
        ok = T[t].to_numpy(bool)
        out[t] = fn(t, ok)
    return out


# S0 data grid
def tick_of(p):
    return np.select([p < 200, p < 500, p < 2000, p < 5000], [1, 2, 5, 10], 25)
c = C.where(T).stack().dropna()
yr = c.index.get_level_values(0).year
s0 = pd.DataFrame({'integer': (c == c.round()).to_numpy(), 'on_today_grid': (np.abs(c / tick_of(c.to_numpy()) - np.round(c / tick_of(c.to_numpy()))) < 1e-9)},
                  index=c.index).groupby(pd.cut(yr, [1993, 1999, 2007, 2015, 2020, 2025], labels=['1994-99'] + SUB)).mean()
s0.to_csv(OUT / 's0_grid.csv')

# S1 ARA / ARB (approximate bands)
simple = C.where(T) / prev - 1
band = pd.DataFrame(np.select([prev < 200, prev < 5000], [.35, .25], .20), index=dates, columns=tick)
band_dn = band.copy()
band_dn.loc['2020-03-10':'2023-06-04'] = .07
ara = (simple >= band - .02) & (C >= H) & T
arb = (simple <= -(band_dn - .02)) & (C <= L) & T
s1 = []
for name, m in (('ARA', ara), ('ARB', arb)):
    nxt_on = P['r_on'].shift(-1).where(m)
    nxt_id = P['r_id'].shift(-1).where(m)
    for pn, (a, b) in PER.items():
        mm = m.loc[a:b]
        g_, i_ = nxt_on.loc[a:b].stack().dropna(), nxt_id.loc[a:b].stack().dropna()
        s1.append(dict(event=name, period=pn, per_year=mm.values.sum() / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25),
                       next_gap_pct=g_.mean() * 100, next_open_to_close_pct=i_.mean() * 100, next_gap_up_share=(g_ > 0).mean(),
                       next_gap_down_share=(g_ < 0).mean()))
    record('S1 limit', name, m)
pd.DataFrame(s1).to_csv(OUT / 's1_limits.csv', index=False)

# S2 / S3 swing structure
M_ = 3
up_state = pd.DataFrame(False, index=dates, columns=tick)
dn_state = up_state.copy()
pers, legs = [], []
for t in tick:
    ok = T[t].to_numpy(bool)
    if ok.sum() < 300:
        continue
    d = dates[ok]
    h, l = lnH[t].to_numpy()[ok], lnL[t].to_numpy()[ok]
    n = len(h)
    hw = pd.Series(h).rolling(2 * M_ + 1, center=True).max().to_numpy()
    lw = pd.Series(l).rolling(2 * M_ + 1, center=True).min().to_numpy()
    ph = np.flatnonzero(np.isfinite(hw) & (h == hw))
    pl = np.flatnonzero(np.isfinite(lw) & (l == lw))
    # states known at each bar (pivot k confirmed at k+M_)
    st_up, st_dn = np.zeros(n, bool), np.zeros(n, bool)
    hs_, ls_ = [], []
    events = sorted([(k + M_, 'H', k) for k in ph] + [(k + M_, 'L', k) for k in pl])
    j = 0
    for i in range(n):
        while j < len(events) and events[j][0] <= i:
            _, typ, k = events[j]
            (hs_ if typ == 'H' else ls_).append(h[k] if typ == 'H' else l[k])
            j += 1
        if len(hs_) >= 2 and len(ls_) >= 2:
            st_up[i] = hs_[-1] > hs_[-2] and ls_[-1] > ls_[-2]
            st_dn[i] = hs_[-1] < hs_[-2] and ls_[-1] < ls_[-2]
    up_state.loc[d, t] = st_up
    dn_state.loc[d, t] = st_dn
    # persistence: at confirmation of pivot high j (state then), is pivot high j+1 higher than j?
    for a_, b_ in zip(ph[:-1], ph[1:]):
        i = a_ + M_
        if i < n:
            pers.append(dict(year=d[min(i, n - 1)].year, state='up' if st_up[i] else ('down' if st_dn[i] else 'mixed'), next_higher=h[b_] > h[a_]))
    # legs: alternate pivots
    piv = sorted([(k, 'H', h[k]) for k in ph] + [(k, 'L', l[k]) for k in pl])
    alt = []
    for p_ in piv:
        if alt and alt[-1][1] == p_[1]:
            if (p_[1] == 'H' and p_[2] > alt[-1][2]) or (p_[1] == 'L' and p_[2] < alt[-1][2]):
                alt[-1] = p_
        else:
            alt.append(p_)
    for q in range(len(alt) - 3):
        a0, a1, a2, a3 = alt[q:q + 4]
        if a0[1] == 'L':   # up-leg a0->a1, down-leg a1->a2, next up-leg a2->a3
            up = a1[2] - a0[2]
            if up <= 0:
                continue
            legs.append(dict(year=d[a0[0]].year, up_len=a1[0] - a0[0], up_size=np.expm1(up), down_len=a2[0] - a1[0], down_size=np.expm1(a2[2] - a1[2]),
                             retrace=(a1[2] - a2[2]) / up, next_new_high=a3[2] > a1[2], next_up=a3[2] - a2[2],
                             needed=a1[2] - a2[2]))
Pers = pd.DataFrame(pers)
Pers['period'] = pd.cut(Pers.year, [1993, 1999, 2007, 2015, 2020, 2025], labels=['1994-99'] + SUB)
s2 = Pers[Pers.year >= 2000].groupby(['state']).next_higher.agg(['mean', 'size']).reset_index().assign(period='2000-25')
s2 = pd.concat([s2, Pers[Pers.year >= 2000].groupby(['period', 'state'], observed=True).next_higher.agg(['mean', 'size']).reset_index()])
s2.to_csv(OUT / 's2_swing_persistence.csv', index=False)
record('S2 swing', 'up (HH+HL)', up_state, (5, 20))
record('S2 swing', 'down (LH+LL)', dn_state, (5, 20))
Lg = pd.DataFrame(legs)
Lg = Lg[Lg.year >= 2000]
Lg['bucket'] = pd.cut(Lg.retrace, [-1e9, .382, .618, 1.0, 1e9], labels=['<38.2%', '38.2-61.8%', '61.8-100%', '>100%'])
s3a = Lg.groupby('bucket', observed=True).agg(n=('next_new_high', 'size'), p_next_new_high=('next_new_high', 'mean'),
                                              median_next_up_leg=('next_up', 'median'), median_needed=('needed', 'median')).reset_index()
# mechanical control: next up-leg sizes drawn from ALL legs (no link to the retracement), same needed distance
pool = Lg.next_up.to_numpy()
s3a['p_if_next_leg_independent'] = [float((np.random.default_rng(7).choice(pool, 20000) > Lg[Lg.bucket == b_].needed.to_numpy()[np.random.default_rng(8).integers(0, (Lg.bucket == b_).sum(), 20000)]).mean())
                                    for b_ in s3a.bucket]
s3b = pd.Series(dict(up_len_median=Lg.up_len.median(), up_len_mean=Lg.up_len.mean(), up_size_median=Lg.up_size.median(),
                     down_len_median=Lg.down_len.median(), down_size_median=Lg.down_size.median(), retrace_median=Lg.retrace.median(),
                     p_next_new_high_all=Lg.next_new_high.mean(), legs=len(Lg)))
ages = Lg.up_len.to_numpy()
haz = []
for a_, b_ in ((1, 5), (6, 10), (11, 20), (21, 40), (41, 999)):
    alive = (ages >= a_).sum()
    end = ((ages >= a_) & (ages <= b_)).sum()
    haz.append(dict(age=f'{a_}-{b_ if b_ < 999 else "+"}', legs_alive=int(alive), share_ending_in_bucket=end / alive if alive else np.nan,
                    per_bar_hazard=1 - (1 - end / alive) ** (1 / (min(b_, 60) - a_ + 1)) if alive else np.nan))
s3a.to_csv(OUT / 's3_retracement.csv', index=False)
s3b.to_csv(OUT / 's3_legs.csv')
pd.DataFrame(haz).to_csv(OUT / 's3_hazard.csv', index=False)

# S4 squeeze
tr = pd.concat([lnH - lnL, (lnH - lnP.shift(1)).abs(), (lnL - lnP.shift(1)).abs()]).groupby(level=0).max().reindex(dates).where(T)
sq = pd.DataFrame(False, index=dates, columns=tick)
rng_n = pd.DataFrame(np.nan, index=dates, columns=tick)
for t in tick:
    ok = T[t].to_numpy(bool)
    if ok.sum() < 400:
        continue
    x = tr[t][ok]
    a10, a100 = x.rolling(10).mean(), x.rolling(100).mean()
    ratio = a10 / a100
    q = ratio.rolling(250, min_periods=200).quantile(.1)
    sq.loc[x.index, t] = (ratio <= q).to_numpy()
    hh = lnH[t][ok][::-1].rolling(10, min_periods=10).max()[::-1].shift(-1)
    ll = lnL[t][ok][::-1].rolling(10, min_periods=10).min()[::-1].shift(-1)
    rng_n.loc[x.index, t] = ((hh - ll) / a100).to_numpy()
s4 = []
for pn, (a, b) in PER.items():
    r_all = rng_n.loc[a:b].where(E.loc[a:b]).stack()
    r_sq = rng_n.loc[a:b].where(sq.loc[a:b] & E.loc[a:b]).stack()
    s4.append(dict(period=pn, next10_range_over_atr100_all=r_all.mean(), next10_range_over_atr100_squeeze=r_sq.mean(),
                   ratio=r_sq.mean() / r_all.mean(), squeeze_share=float(sq.loc[a:b].where(E.loc[a:b]).stack().mean())))
pd.DataFrame(s4).to_csv(OUT / 's4_squeeze.csv', index=False)
record('S4 squeeze', 'ATR10/ATR100 bottom 10% own history', sq, (10,) if 10 in fo else (5, 20))

# S5 round numbers (raw prices)
s5 = []
pc = prev.where(T)
for kind, off in (('00', 0), ('50', 50)):
    lev = np.ceil((pc - off) / 100) * 100 + off
    lev = lev.where(lev > pc, lev + 100)
    d = lev / pc - 1
    cond = (pc >= 1000) & (pc <= 10000) & T
    cond.loc[:'2020-12-31'] = False   # prices before 2021 are mostly back-adjusted (off the tick grid, see S0)
    touch = cond & (H >= lev)
    above = touch & (C >= lev)
    for lo, hi in ((0, .01), (.01, .02), (.02, .04)):
        m = touch & (d > lo) & (d <= hi)
        s5.append(dict(level=kind, dist=f'{lo*100:.0f}-{hi*100:.0f}%', touches=int(m.values.sum()), p_close_above=float((above & m).values.sum() / max(1, m.values.sum()))))
    record('S5 round', f'closed above level ending {kind}', above, (5,))
pd.DataFrame(s5).to_csv(OUT / 's5_round.csv', index=False)

# S6 prior 60-day extremes vs arbitrary levels at the same distance
hh60 = H.where(T).rolling(60, min_periods=40).max().shift(1)
ll60 = L.where(T).rolling(60, min_periods=40).min().shift(1)
s6 = []
buckets = ((0, .01, .005), (.01, .02, .015), (.02, .03, .025), (.03, .05, .04))
for lo, hi, mid in buckets:
    dH = hh60 / pc - 1
    ev_h = T & (pc < hh60) & (H >= hh60) & (dH > lo) & (dH <= hi)
    rate_h = float(((C >= hh60) & ev_h).values.sum() / max(1, ev_h.values.sum()))
    ctl_touch = T & (H / pc - 1 >= mid)
    rate_ch = float((ctl_touch & (C / pc - 1 >= mid)).values.sum() / max(1, ctl_touch.values.sum()))
    dL = 1 - ll60 / pc
    ev_l = T & (pc > ll60) & (L <= ll60) & (dL > lo) & (dL <= hi)
    rate_l = float(((C <= ll60) & ev_l).values.sum() / max(1, ev_l.values.sum()))
    ctl_l = T & (L / pc - 1 <= -mid)
    rate_cl = float((ctl_l & (C / pc - 1 <= -mid)).values.sum() / max(1, ctl_l.values.sum()))
    s6.append(dict(distance=f'{lo*100:.0f}-{hi*100:.0f}%', high_touches=int(ev_h.values.sum()), p_close_above_60d_high=rate_h,
                   p_close_above_arbitrary=rate_ch, low_touches=int(ev_l.values.sum()), p_close_below_60d_low=rate_l, p_close_below_arbitrary=rate_cl))
pd.DataFrame(s6).to_csv(OUT / 's6_levels.csv', index=False)

# S7 close location value
clv = ((C - L) / (H - L)).where(T & (H > L))
s7 = []
on_n = P['r_on'].shift(-1)
id_n = P['r_id'].shift(-1)
on_a = on_n.sub(on_n.mean(axis=1), axis=0)
id_a = id_n.sub(id_n.mean(axis=1), axis=0)
for lo, hi in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)):
    m = (clv >= lo) & (clv < hi)
    for pn, (a, b) in PER.items():
        s7.append(dict(clv=f'{lo:.1f}-{min(hi,1):.1f}', period=pn, next_overnight_abn_bps=on_a.where(m).loc[a:b].stack().mean() * 1e4,
                       next_intraday_abn_bps=id_a.where(m).loc[a:b].stack().mean() * 1e4))
    record('S7 CLV', f'{lo:.1f}-{min(hi,1):.1f}', m, (1, 5))
pd.DataFrame(s7).to_csv(OUT / 's7_clv.csv', index=False)

# S8 correlation structure
r = P['r_cc']
mk = np.log1p(P['idx_ret'].fillna(0))
s8 = []
for i in range(60, len(dates), 21):
    w = r.iloc[i - 60:i]
    cols = [t for t in tick if E.iloc[i - 1][t] and w[t].notna().sum() >= 50]
    if len(cols) < 15:
        continue
    cm = w[cols].corr(min_periods=40).to_numpy()
    avg = np.nanmean(cm[~np.eye(len(cols), dtype=bool)])
    mret = mk.iloc[i - 60:i].sum()
    s8.append(dict(date=dates[i - 1], stocks=len(cols), avg_corr=avg, market_60d=np.expm1(mret)))
S8 = pd.DataFrame(s8)
S8['market'] = pd.cut(S8.market_60d, [-9, -.1, .1, 9], labels=['fell >10%', 'between', 'rose >10%'])
S8.to_csv(OUT / 's8_correlation_windows.csv', index=False)
S8.groupby('market', observed=True).avg_corr.agg(['mean', 'size']).to_csv(OUT / 's8_correlation.csv')

# S9 regime durations
lab = regime_proxy(st)['regime'].loc['2000-01-01':'2025-08-15']
run_id = (lab != lab.shift()).cumsum()
spells = lab.groupby(run_id).agg(['first', 'size'])
spells.columns = ['regime', 'days']
spells.index.name = 'spell'
s9 = spells.groupby('regime').days.agg(['mean', 'median', 'max', 'size'])
tm = pd.crosstab(spells.regime, spells.regime.shift(-1), normalize='index')
s9.to_csv(OUT / 's9_spells.csv')
tm.to_csv(OUT / 's9_transitions.csv')

# S10 gaps >= 2%
gap = O.where(T) / prev - 1
low5 = L.where(T)[::-1].rolling(5, min_periods=1).min()[::-1]
high5 = H.where(T)[::-1].rolling(5, min_periods=1).max()[::-1]
s10 = []
for pn, (a, b) in PER.items():
    g, pcx = gap.loc[a:b], prev.loc[a:b]
    up, dn = g >= .02, g <= -.02
    s10.append(dict(period=pn, gap_up_2pct=int(up.values.sum()), up_filled_same_day=float(((L.loc[a:b] <= pcx) & up).values.sum() / up.values.sum()),
                    up_filled_5d=float(((low5.loc[a:b] <= pcx) & up).values.sum() / up.values.sum()), gap_down_2pct=int(dn.values.sum()),
                    down_filled_same_day=float(((H.loc[a:b] >= pcx) & dn).values.sum() / dn.values.sum()),
                    down_filled_5d=float(((high5.loc[a:b] >= pcx) & dn).values.sum() / dn.values.sum())))
pd.DataFrame(s10).to_csv(OUT / 's10_gaps.csv', index=False)

D = pd.DataFrame(EV)
D.to_csv(OUT / 'events.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
for f in ['s0_grid', 's1_limits', 's2_swing_persistence', 's3_retracement', 's3_legs', 's3_hazard', 's4_squeeze', 's5_round', 's6_levels', 's8_correlation', 's9_spells', 's9_transitions', 's10_gaps']:
    print('==', f); print(pd.read_csv(OUT / f'{f}.csv').round(4).to_string(index=False))
print('== s7'); print(pd.read_csv(OUT / 's7_clv.csv').round(1).pivot_table(index='clv', columns='period', values=['next_overnight_abn_bps', 'next_intraday_abn_bps']).to_string())
Dm = D[D.period == '2000-25'].pivot_table(index=['structure', 'variant', 'h'], columns='universe', values=['effect_pct', 't'])
Ds = D[D.period.isin(SUB) & (D.universe == 'all')].pivot_table(index=['structure', 'variant', 'h'], columns='period', values='effect_pct')
Dm.columns = [f'{a}_{b}' for a, b in Dm.columns]
print('== events'); print(Dm.round(2).join(Ds.round(2)).to_string())
