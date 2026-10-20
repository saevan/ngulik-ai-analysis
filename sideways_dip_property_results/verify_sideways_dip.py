"""Independent verification of the sideways-dip property test (PLAN.md in this folder).

Does NOT import sideways_dip_property.py / sideways_dip_explore.py / sideways_dip_holdout_1994.py.
Every signal is rebuilt here from the panel; eligibility and the market regime are rebuilt here too and compared with the
helpers (pit_universe, pit_stale_liquidity, analyze_sk5_regimes.regimes). Also runs audits (look-ahead by truncation,
h alignment, survivorship, bad-jump contamination, execution sensitivities, Close-exit and cost A).
Run: python sideways_dip_property_results/verify_sideways_dip.py
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from panel import load
from mpstats import nw

pd.set_option('display.width', 250); pd.set_option('display.max_rows', 400); pd.set_option('display.max_columns', 40)
P = load()
lnP, lnO, lnH, lnL, T, BAD = P['lnP'], P['lnO'], P['lnH'], P['lnL'], P['T'], P['bad']
C, O, H, L, V = P['C'], P['O'], P['H'], P['L'], P['V']
cal, TK = lnP.index, lnP.columns
CB, CA = .009, .004
PER = {'2000-25': ('2000-01-01', '2025-08-15'), '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
       '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15'), '1994-99': ('1994-01-01', '1999-12-31')}
SUBS = ['2000-07', '2008-15', '2016-20', '2021-25']


# ---------------------------------------------------------------- signal construction (own code, causal by design)
def wilder_atr(h, l, c, n=14):
    """Wilder ATR via ewm(alpha=1/n) seeded with the simple mean of the first n true ranges."""
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    out = np.full(len(c), np.nan)
    if len(c) < n:
        return out
    x = pd.Series(tr[n - 1:].copy())
    x.iloc[0] = tr[:n].mean()
    out[n - 1:] = x.ewm(alpha=1 / n, adjust=False).mean().values
    return out


def market_regime(Craw, shift=1):
    """er20 label on the equal-weight proxy of raw (ffilled) Closes; shift=1 -> label known at Close t-1."""
    cl = Craw.ffill()
    r = cl.pct_change(fill_method=None).mean(axis=1).fillna(0)
    ix = (1 + r).cumprod() * 100
    travel = ix.diff().abs().rolling(20).sum()
    er = (ix.diff(20).abs() / travel.replace(0, np.nan)).mask(travel == 0, 0)
    d = ix.diff(20)
    lab = pd.Series('sideways', index=ix.index)
    lab[(er >= .3) & (d > 0)] = 'uptrend'
    lab[(er >= .3) & (d < 0)] = 'downtrend'
    lab[er.isna()] = 'unknown'
    return lab.shift(shift).fillna('unknown') if shift else lab


def eligibility_own(C, V, O, H, L, frac=.5):
    val = C * V                                           # NaN where the ticker has no bar (same as helper's union frame)
    bars = val.notna().cumsum().shift(1)
    v = val.rolling(120, min_periods=60).mean().shift(1)
    rk = v.rank(axis=1, ascending=False)
    n = v.notna().sum(axis=1)
    pit = (bars >= 250) & rk.le(np.ceil(n * frac), axis=0)
    st = pd.DataFrame(False, index=C.index, columns=C.columns)
    for t in C.columns:
        m = C[t].notna()
        f = pd.DataFrame(dict(O=O[t][m], H=H[t][m], L=L[t][m], C=C[t][m], V=V[t][m]))
        traded = (f.V > 0).astype(float)
        one = ((f.O == f.H) & (f.H == f.L) & (f.L == f.C) & (f.V > 0)).astype(float)
        ok = (traded.rolling(60).mean().shift(1) >= .9) & (one.rolling(60).mean().shift(1) <= .1)
        st.loc[ok.index[ok.values], t] = True
    return pit.fillna(False).astype(bool) & st


def signals(Pd):
    lnP, lnH, lnL, T, C, H, L = (Pd[k] for k in ['lnP', 'lnH', 'lnL', 'T', 'C', 'H', 'L'])
    S = {}
    a = lnP.to_numpy()
    cs = np.vstack([np.zeros((1, a.shape[1])), np.nancumsum(np.nan_to_num(a), axis=0)])
    cnt = np.vstack([np.zeros((1, a.shape[1])), np.cumsum(np.isfinite(a), axis=0)])
    k = 200
    sm = np.full(a.shape, np.nan)
    sm[k - 1:] = (cs[k:] - cs[:-k]) / k
    full = np.full(a.shape, False); full[k - 1:] = (cnt[k:] - cnt[:-k]) == k
    sma200 = pd.DataFrame(np.where(full, sm, np.nan), index=lnP.index, columns=lnP.columns)
    S['strong'] = lnP > sma200
    S['weak'] = lnP <= sma200
    hh = lnH.rolling(10, min_periods=8).max(); ll = lnL.rolling(10, min_periods=8).min()
    S['pos'] = (lnP - ll) / (hh - ll)
    S['d1'] = S['pos'] <= .2
    travel = lnP.diff().abs().rolling(20).sum()
    S['side_stk'] = ((lnP - lnP.shift(20)).abs() / travel) < .3
    atr = pd.DataFrame(np.nan, index=lnP.index, columns=lnP.columns)
    for t in lnP.columns:
        m = (T[t] & C[t].notna()).to_numpy()
        if m.any():
            atr.loc[m, t] = wilder_atr(H[t].to_numpy(float)[m], L[t].to_numpy(float)[m], C[t].to_numpy(float)[m])
    S['atr'] = atr
    Ct = C.where(T)
    S['drop'] = Ct.rolling(10, min_periods=8).max() - Ct
    for kk in [1, 2, 3, 4]:
        S[f'{kk}atr'] = S['drop'] >= kk * atr
    # clean-level variant of the drop (window max expressed in today's raw units; removes masked jumps)
    S['drop_clean'] = Ct * (np.exp(lnP.where(T).rolling(10, min_periods=8).max() - lnP) - 1)
    S['4atr_clean'] = S['drop_clean'] >= 4 * atr
    sma50 = lnP.rolling(50, min_periods=50).mean()
    S['sma200_sma50up'] = S['strong'] & (sma50 > sma50.shift(10))
    S['mom'] = lnP.shift(21) - lnP.shift(141)
    S['mom_top20'] = S['mom'].rank(axis=1, pct=True) >= .8
    S['side_mkt'] = pd.DataFrame(np.repeat((market_regime(C) == 'sideways').to_numpy()[:, None], lnP.shape[1], 1),
                                 index=lnP.index, columns=lnP.columns)
    return S


S = signals(P)
base = T & ~BAD & lnP.notna()

# ---------------------------------------------------------------- helpers comparison (eligibility, regime)
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_sk5_regimes import regimes
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
ELIG = pd.DataFrame(False, index=cal, columns=TK)
for t in TK:
    ELIG.loc[ELIG.index.isin(list(pit[t] & stale[t])), t] = True
elig_own = eligibility_own(C, V, O, H, L)
reg_helper = regimes(st)['er20']['regime'].reindex(cal)
reg_own = market_regime(C)
print('== helper agreement')
print('eligibility cells differ (own vs helper):', int((elig_own != ELIG).values.sum()), 'of', ELIG.size,
      '| eligible stock-days 2000-25:', int(ELIG.loc['2000':].values.sum()))
print('regime label days differ (own vs helper):', int((reg_own != reg_helper).sum()),
      '| sideways share 2000-25:', round((reg_own.loc['2000':] == 'sideways').mean(), 3))
U = ELIG


# ---------------------------------------------------------------- statistics
def stat(R, M, per, h, cost=CB):
    a, b = PER[per]
    X = R.where(M).loc[a:b]
    m, se, n = nw(X.mean(axis=1).to_numpy(), h)
    v = X.to_numpy()[np.isfinite(X.to_numpy())]
    return dict(events=len(v), days=n, gross=m * 100, t_gross=m / se if se else np.nan, net=(m - cost) * 100,
                t_net=(m - cost) / se if se else np.nan, ev_gross=v.mean() * 100 if len(v) else np.nan)


def R_c2o(h): return lnO.shift(-h) - lnP
def R_c2c(h): return (lnP.shift(-h) - lnP).where(T.shift(-h, fill_value=False))      # exit Close t+h, stock must trade t+h
def R_c2c_raw(h): return lnP.shift(-h) - lnP                                          # as in the main script (stale Close allowed)
def R_o2o(h): return lnO.shift(-(1 + h)) - lnO.shift(-1)


print('\n== h alignment check (one event): lnO.shift(-h) row is t+h market days')
ev = (base & U & S['side_mkt'] & S['strong'] & S['d1']).loc['2010']
t0, tk = ev.stack()[lambda x: x].index[0]
i0 = cal.get_loc(t0)
for h in [1, 4]:
    print(f'  {tk} t={t0.date()} h={h}: R={R_c2o(h).loc[t0, tk]:.5f}  manual lnO[{cal[i0 + h].date()}]-lnP[t]={lnO[tk].iloc[i0 + h] - lnP[tk].iloc[i0]:.5f}')

# ---------------------------------------------------------------- 1. primary result
SD, WD, ALLS = (base & U & S['side_mkt'] & S['strong'] & S['d1'], base & U & S['side_mkt'] & S['weak'] & S['d1'], base & U & S['side_mkt'])
rows = []
for h in range(1, 11):
    R = R_c2o(h)
    s = {p: stat(R, SD, p, h) for p in ['2000-25'] + SUBS}
    w = stat(R, WD, '2000-25', h)
    a = stat(R, ALLS, '2000-25', h)
    rows.append(dict(h=h, events=s['2000-25']['events'], gross=s['2000-25']['gross'], t_gross=s['2000-25']['t_gross'],
                     net_B=s['2000-25']['net'], t_net_B=s['2000-25']['t_net'], net_A=s['2000-25']['gross'] - CA * 100,
                     **{f'netB_{p}': s[p]['net'] for p in SUBS}, subs_pos=sum(s[p]['net'] > 0 for p in SUBS),
                     weak_gross=w['gross'], strong_minus_weak=s['2000-25']['gross'] - w['gross'], all_side_gross=a['gross'],
                     passes=bool(s['2000-25']['net'] > 0 and s['2000-25']['t_net'] >= 3.25 and sum(s[p]['net'] > 0 for p in SUBS) >= 3
                                 and s['2000-25']['gross'] > w['gross'])))
prim = pd.DataFrame(rows)
print('\n== 1. PRIMARY (realistic, market sideways, strong=lnP>SMA200, D1, Close t -> Open t+h), %')
print(prim.round(3).to_string(index=False))
ref = pd.read_csv(HERE / 'primary_verdict.csv')
print('max |net_B - primary_verdict.csv|:', float(np.abs(prim.net_B.values - ref.net_B_pct.values).max()),
      ' max |t diff|:', float(np.abs(prim.t_net_B.values - ref.t_net_B.values).max()),
      ' max |strong-weak diff|:', float(np.abs(prim.strong_minus_weak.values - ref.strong_minus_weak_pct.values).max()))

# alternatives: exit at the Close of t+h, cost A, simple (arithmetic) returns, Open t+1 entry
alt = []
for h in range(1, 11):
    r = dict(h=h)
    for nm, R in [('c2o', R_c2o(h)), ('c2c', R_c2c(h)), ('c2c_stale_ok', R_c2c_raw(h)), ('o2o', R_o2o(h)),
                  ('c2o_simple', np.expm1(R_c2o(h))), ('c2c_simple', np.expm1(R_c2c(h)))]:
        x = stat(R, SD, '2000-25', h)
        r[f'{nm}_gross'] = x['gross']; r[f'{nm}_netB'] = x['net']; r[f'{nm}_netA'] = x['gross'] - CA * 100
        r[f'{nm}_tnetA'] = (x['gross'] / 100 - CA) / (x['gross'] / 100 / x['t_gross']) if x['t_gross'] else np.nan
    alt.append(r)
alt = pd.DataFrame(alt)
print('\n== 3. PRIMARY strong-dip under alternatives (2000-25, %): exit at Close t+h, cost A (0.40%), simple returns')
print(alt[['h', 'c2o_gross', 'c2o_netA', 'c2o_tnetA', 'c2c_gross', 'c2c_netB', 'c2c_netA', 'c2c_tnetA', 'c2c_stale_ok_gross',
           'o2o_gross', 'c2o_simple_gross', 'c2o_simple_netA', 'c2c_simple_gross']].round(3).to_string(index=False))

# subperiods under cost A, close-to-open and close-to-close
sa = []
for h in range(1, 11):
    for nm, R in [('c2o', R_c2o(h)), ('c2c', R_c2c(h))]:
        sa.append(dict(h=h, ret=nm, **{p: stat(R, SD, p, h, CA)['net'] for p in SUBS}))
sa = pd.DataFrame(sa)
sa['subs_pos_A'] = (sa[SUBS] > 0).sum(axis=1)
print('\n   cost-A net by subperiod (%):')
print(sa.round(3).to_string(index=False))

# ---------------------------------------------------------------- 1b. exploratory grid (rebuilt) and best cell
SIDES = {'market': S['side_mkt'], 'stock_er': S['side_stk']}
STR = {'sma200': S['strong'], 'sma200_sma50up': S['sma200_sma50up'], 'mom_top20': S['mom_top20']}
DIPS = {'1atr': S['1atr'], '2atr': S['2atr'], '3atr': S['3atr'], '4atr': S['4atr'], 'range20': S['pos'] <= .2, 'range10': S['pos'] <= .1}
B = base & U
g = []
RC = {h: R_c2o(h) for h in range(1, 11)}
for sn, Sd in SIDES.items():
    for gn, Gm in STR.items():
        for dn, D in DIPS.items():
            M = B & Sd & Gm & D
            for h in range(1, 11):
                x = stat(RC[h], M, '2000-25', h)
                g.append(dict(sideways=sn, strength=gn, dip=dn, h=h, events=x['events'], gross=x['gross'], net=x['net'], t_net=x['t_net']))
g = pd.DataFrame(g)
eg = pd.read_csv(HERE / 'exploratory_grid.csv')
mg = g.merge(eg, on=['sideways', 'strength', 'dip', 'h'])
print('\n== 1b. exploratory grid rebuilt:', len(g), 'cells; max |net diff| vs exploratory_grid.csv:',
      float(np.abs(mg.net - mg['net_2000-25']).max()), '| max |events diff|:', int(np.abs(mg.events_x - mg.events_y).max()))
print('   cells with net>0:', int((g.net > 0).sum()), '| net>0 & t_net>=2:', int(((g.net > 0) & (g.t_net >= 2)).sum()),
      '| gross>0:', int((g.gross > 0).sum()))
print(g.sort_values('net', ascending=False).head(5).round(3).to_string(index=False))

BEST = B & S['side_stk'] & S['mom_top20'] & S['4atr']
print('\n== BEST CELL (stock ER20<0.3, mom top quintile, Close >= 4 ATR14 below 10d high Close), h=9, cost B unless noted (%)')
bc = []
for p in ['2000-25'] + SUBS + ['1994-99']:
    for nm, R in [('c2o', R_c2o(9)), ('c2c', R_c2c(9)), ('c2o_simple', np.expm1(R_c2o(9)))]:
        x = stat(R, BEST, p, 9)
        bc.append(dict(period=p, ret=nm, events=x['events'], days=x['days'], gross=x['gross'], net_B=x['net'], t_net_B=x['t_net'],
                       net_A=x['gross'] - CA * 100, t_net_A=(x['gross'] / 100 - CA) / (x['gross'] / 100 / x['t_gross']) if x['t_gross'] else np.nan,
                       ev_net_B=x['ev_gross'] - CB * 100))
bc = pd.DataFrame(bc)
print(bc.round(3).to_string(index=False))
ho = pd.read_csv(HERE / 'holdout_1994_99.csv').iloc[0]
print('holdout_1994_99.csv h=9: net', round(ho.net_B_1994_99, 3), 't', round(ho.t, 3), 'events', ho.events_1994_99)

# ---------------------------------------------------------------- 2. audits
print('\n== 2a. look-ahead by truncation: recompute every signal on data cut at t0, compare row t0')
rng = np.random.default_rng(0)
dates = sorted(rng.choice(cal[(cal >= '1996-01-01')], 6, replace=False))
keys = ['strong', 'd1', 'side_stk', '2atr', '4atr', 'mom_top20', 'side_mkt', 'sma200_sma50up']
bad_cnt = {k: 0 for k in keys}
for d0 in dates:
    Pc = {k: P[k].loc[:d0] for k in ['lnP', 'lnH', 'lnL', 'T', 'C', 'H', 'L']}
    Sc = signals(Pc)
    for k in keys:
        bad_cnt[k] += int((Sc[k].loc[d0] != S[k].loc[d0]).sum())
el_c = eligibility_own(C.loc[:dates[-1]], V.loc[:dates[-1]], O.loc[:dates[-1]], H.loc[:dates[-1]], L.loc[:dates[-1]])
print('   mismatches per signal over', len(dates), 'cut dates:', bad_cnt,
      '| eligibility mismatch at last cut:', int((el_c.loc[dates[-1]] != elig_own.loc[dates[-1]]).sum()))
# same-day regime label (Close t) instead of Close t-1
side_now = pd.DataFrame(np.repeat((market_regime(C, 0) == 'sideways').to_numpy()[:, None], len(TK), 1), index=cal, columns=TK)
print('   regime label uses Close t-1 (helper vs own shift=1 identical above). Same-day label sensitivity, primary strong dip:')
print('   ', {h: round(stat(R_c2o(h), base & U & side_now & S['strong'] & S['d1'], '2000-25', h)['net'], 3) for h in [1, 4, 9]})

print('\n== 2b. momentum rank universe: rank over all listed panel stocks (incl. ineligible / non-tradable) vs eligible only')
mom_el = S['mom'].where(base & U).rank(axis=1, pct=True) >= .8
nel = (S['mom'].notna()).sum(axis=1); nel2 = S['mom'].where(base & U).notna().sum(axis=1)
print('   avg stocks ranked per day 2000-25: all', round(nel.loc['2000':].mean(), 1), '| eligible', round(nel2.loc['2000':].mean(), 1))
for nm, Mm in [('rank_all(as main)', S['mom_top20']), ('rank_eligible', mom_el)]:
    M = B & S['side_stk'] & Mm & S['4atr']
    print('  ', nm, {p: (lambda x: f"net {x['net']:.2f} t {x['t_net']:.2f} n {x['events']}")(stat(R_c2o(9), M, p, 9)) for p in ['2000-25', '1994-99']})

print('\n== 2c. survivorship / delisting')
last = C.apply(lambda s: s.last_valid_index())
print('   tickers with last bar before 2025-08-15:', int((last < cal[-1]).sum()), 'of', len(TK),
      '| listed in 1995/2000/2010/2020:', [int(C.loc[str(y)].notna().any().sum()) for y in [1995, 2000, 2010, 2020]])
for h in [4, 9]:
    R = R_c2o(h)
    for nm, M in [('primary', SD), ('best', BEST)]:
        drp = (M & R.isna()).loc['2000':'2025-07-31']
        print(f'   {nm} h={h}: events dropped because stock not tradable at t+h (excl. sample end): {int(drp.values.sum())}')

print('\n== 2d. bad-jump (>=50%) contamination')
Bf = BAD.astype(float)
for h, nm, M in [(4, 'primary', SD), (9, 'best', BEST)]:
    fwd = sum(Bf.shift(-k) for k in range(1, h + 1)) > 0
    print(f'   {nm} h={h}: events whose forward window holds a masked jump (return set to 0 on that day):',
          int((M & fwd).loc['2000':].values.sum()))
win = Bf.rolling(10, min_periods=1).sum() > 0
print('   best cell events with a masked jump inside the 10-day dip window (raw-Close dip may be an unadjusted corporate action):',
      int((BEST & win).loc['2000':].values.sum()), '/', int(BEST.loc['2000':'2025-08-05'].values.sum()), '| 1994-99:',
      int((BEST & win).loc[:'1999'].values.sum()))
BEST_CLEAN = B & S['side_stk'] & S['mom_top20'] & S['4atr_clean']
for p in ['2000-25', '1994-99']:
    x = stat(R_c2o(9), BEST & ~win, p, 9); y = stat(R_c2o(9), BEST_CLEAN, p, 9)
    print(f'   {p}: best cell excl. jump windows net {x["net"]:.3f} t {x["t_net"]:.2f} n {x["events"]} | '
          f'drop measured on clean levels net {y["net"]:.3f} t {y["t_net"]:.2f} n {y["events"]}')

print('\n== 2e. execution: where does the gross come from (primary strong dip, 2000-25, % gross)')
on = stat(lnO.shift(-1) - lnP, SD, '2000-25', 1)['gross']
on_all = stat(lnO.shift(-1) - lnP, ALLS, '2000-25', 1)['gross']
print(f'   overnight Close t -> Open t+1: strong dip {on:.3f} | all sideways stock-days {on_all:.3f}')
for h in [4, 9]:
    print(f'   h={h}: Close t->Open t+h {stat(R_c2o(h), SD, "2000-25", h)["gross"]:.3f} | Open t+1->Open t+1+h {stat(R_o2o(h), SD, "2000-25", h)["gross"]:.3f}'
          f' | best cell: c2o {stat(R_c2o(h), BEST, "2000-25", h)["gross"]:.3f} o2o {stat(R_o2o(h), BEST, "2000-25", h)["gross"]:.3f}')
# signal known one day earlier (fully executable at Close t), hold to Open t+h
SDl = SD.shift(1, fill_value=False) & base
BEl = BEST.shift(1, fill_value=False) & base
print('   signal from Close t-1, buy Close t: primary h=4 net', round(stat(R_c2o(4), SDl, '2000-25', 4)['net'], 3),
      '| best h=9 net', round(stat(R_c2o(9), BEl, '2000-25', 9)['net'], 3), 't', round(stat(R_c2o(9), BEl, '2000-25', 9)['t_net'], 2))
op = (O == C.ffill().shift(1)).where(T)
print('   share of tradable bars with Open == previous Close (tick-size / thin pre-opening):',
      round(float(op.loc['2000':].stack().mean()), 3))

print('\n== 2f. robustness of the 1994-99 replication of the best cell (net B %, t, events)')
for nm, Mm in [('rank_all', S['mom_top20']), ('rank_eligible', mom_el)]:
    M = B & S['side_stk'] & Mm & S['4atr']
    print('  ', nm, {h: (lambda x: f"{x['net']:.2f}/{x['t_net']:.2f}/{x['events']}")(stat(R_c2o(h), M, '1994-99', h)) for h in [8, 9, 10]})
ev = BEST.loc[:'1999'].sum(axis=1); ev = ev[ev > 0]
print('   1994-99 best-cell events by year:', ev.groupby(ev.index.year).sum().to_dict(),
      '| first eligible date:', ELIG.any(axis=1).idxmax().date(), '| avg eligible stocks/day 1995-99:', round(ELIG.loc['1995':'1999'].sum(axis=1).mean(), 1))
X = R_c2o(9).where(BEST).loc[:'1999']
print('   1994-99 per-year mean net B (event-weighted):', ((X.stack().dropna().groupby(lambda i: i[0].year).mean() - CB) * 100).round(2).to_dict())
X = R_c2o(9).where(BEST).loc['2000':]
v = X.stack().dropna()
print('   2000-25 best-cell events by ticker (top 5 share):', round(v.groupby(level=1).size().nlargest(5).sum() / len(v), 3),
      '| excl. top-1 contributing ticker, net B:',
      round((lambda tk: stat(R_c2o(9), BEST & (np.arange(len(TK))[None, :] != list(TK).index(tk)), '2000-25', 9)['net'])(v.groupby(level=1).sum().idxmax()), 3))

print('\n== 2g. all pre-registered strong-dip cells (realistic, close->open, 2000-25): best net B over h')
D2 = S['2atr']
for sn, Sd in [('market', S['side_mkt']), ('stock_er', S['side_stk'])]:
    for dn, D in [('D1', S['d1']), ('D2', D2)]:
        M = base & U & Sd & S['strong'] & D
        r = [(h, stat(R_c2o(h), M, '2000-25', h)) for h in range(1, 11)]
        h, x = max(r, key=lambda z: z[1]['net'])
        print(f'   {sn:8s} {dn}: best h={h} gross {x["gross"]:.3f} net B {x["net"]:.3f} t {x["t_net"]:.2f} n {x["events"]}')
