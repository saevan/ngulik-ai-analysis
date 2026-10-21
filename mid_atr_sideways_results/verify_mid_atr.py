"""Independent adversarial re-computation of mid_atr_sideways (does NOT import mid_atr_sideways.py).

Re-implements range / ATR / ER / z, the entries, the exit path, one-position handling and the random control from the
plan text, then
  1. recomputes four cells and compares them with results.csv,
  2. audits execution timing (signal at Close t vs previous Close vs entry at next Open), Close-at-Low, dropped
     end-of-data trades, width-threshold sensitivity, last_low vs below_mid overlap,
  3. checks concentration (ticker, year) and the 2021-25 sign of the wide / stock-ER group,
  4. recomputes the mid-reversion property slope (narrow class, plus medium/wide for context).
Run: python mid_atr_sideways_results/verify_mid_atr.py   (writes verify_*.csv next to this file)
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw  # noqa: E402
import grid_search_timehunter as engine  # noqa: E402
import pit_universe as pu, pit_stale_liquidity as psl  # noqa: E402
from analyze_portfolio_regimes import regime_proxy  # noqa: E402

COST_B = .009
START, END = pd.Timestamp('2000-01-01'), pd.Timestamp('2025-08-15')
PERIODS = {'2000-25': (START, END), '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
           '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
CLASSES = {'narrow': (0., 4.), 'medium': (4., 7.), 'wide': (7., np.inf)}


# ----------------------------------------------------------------------------------------------- features
def wilder_atr(h, l, c, n=14):
    """Wilder ATR (seed = simple mean of the first n true ranges, then RMA); written via ewm, not a loop."""
    if len(c) < n:
        return np.full(len(c), np.nan)
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    y = pd.Series(tr, dtype=float)
    seed = y.iloc[:n].mean()
    y.iloc[:n - 1] = np.nan
    y.iloc[n - 1] = seed
    return y.ewm(alpha=1. / n, adjust=False, ignore_na=True).mean().to_numpy()


def build_panel(st):
    fr = {str(k): g.reset_index(drop=True) for k, g in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
    reg = regime_proxy(st)['regime']
    side_days = set(reg.index[reg == 'sideways'])
    P = {}
    for t, g in fr.items():
        g = g[g.Volume > 0].reset_index(drop=True)          # tradable bars only (same as engine 'tradable')
        if len(g) < 300:
            continue
        d = pd.DatetimeIndex(g['Date/Time'])
        o, h, l, c = (g[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close'])
        H = np.array([np.nan] * 19 + [h[i - 19:i + 1].max() for i in range(19, len(h))])
        L = np.array([np.nan] * 19 + [l[i - 19:i + 1].min() for i in range(19, len(l))])
        A = wilder_atr(h, l, c)
        absd = np.r_[np.nan, np.abs(np.diff(c))]
        path = pd.Series(absd).rolling(20).sum().to_numpy()
        net = np.r_[np.full(20, np.nan), np.abs(c[20:] - c[:-20])]
        with np.errstate(invalid='ignore', divide='ignore'):
            er = net / path
            W = (H - L) / A
            mid = (H + L) / 2
            z = (c - mid) / A
        ok_dates = pit[t] & stale[t]
        elig = d.isin(list(ok_dates)) & (d >= START) & (d <= END)
        P[t] = dict(d=d, o=o, h=h, l=l, c=c, H=H, L=L, A=A, W=W, mid=mid, z=z, er=er,
                    elig=np.asarray(elig), mside=np.asarray(d.isin(list(side_days))))
    cal = pd.DatetimeIndex(sorted(st['Date/Time'].unique()))
    return P, cal


def entry_mask(p, entry, k_override=None):
    if entry == 'last_low':
        return (p['c'] - p['L']) <= .5 * p['A']
    k = float(entry.split('_')[-1]) if k_override is None else k_override
    return p['z'] <= -k


def base_mask(p, width, side, lo=None, hi=None):
    a, b = CLASSES[width]
    a = a if lo is None else lo
    b = b if hi is None else hi
    with np.errstate(invalid='ignore'):
        m = p['elig'] & np.isfinite(p['W']) & (p['A'] > 0) & (p['W'] >= a) & (p['W'] < b)
        m &= (p['er'] < .3) if side == 'stock_er' else p['mside']
    return m


# ----------------------------------------------------------------------------------------------- trade path
def walk(p, sbar, ebar, mode):
    """Return (exit_bar, exit_px, reason, entry_px) or None if skipped/incomplete.
    mode 'close': buy Close[ebar], scan ebar+1..ebar+10. mode 'open': buy Open[ebar], scan ebar..ebar+9.
    Target/stop levels come from the signal bar sbar."""
    o, h, c, n = p['o'], p['h'], p['c'], len(p['c'])
    tgt = p['mid'][sbar]
    stp = p['L'][sbar] - p['A'][sbar]
    if mode == 'close':
        px_in = c[ebar]
        first, last = ebar + 1, ebar + 10
    else:
        if ebar >= n:
            return 'incomplete'
        px_in = o[ebar]
        first, last = ebar, ebar + 9
    if px_in >= tgt:            # limit order at the mid: never buy at/above the target (only binds for lag/open)
        return 'skip'
    for j in range(first, min(last, n - 1) + 1):
        if h[j] >= tgt:
            return j, max(o[j], tgt), 'target', px_in
        if c[j] < stp:
            if j + 1 < n:
                return j + 1, o[j + 1], 'stop', px_in
            return 'incomplete'
        if j == last:
            return j, c[j], 'time', px_in
    return 'incomplete'


def simulate(P, width, entry, side, variant='base', control_seed=None, lo=None, hi=None, k_override=None):
    """variant: base (signal t, buy Close t) | lag (signal t-1, buy Close t, limit at mid) | open (signal t, buy Open t+1)."""
    rows, dropped = [], 0
    rng = np.random.default_rng(control_seed) if control_seed is not None else None
    for t, p in P.items():
        bm = base_mask(p, width, side, lo, hi)
        sig = bm & entry_mask(p, entry, k_override)
        n = len(p['c'])
        if rng is not None:
            pool = np.flatnonzero(bm & (p['c'] < p['mid']))
            k = int(sig.sum())
            sig = np.zeros(n, bool)
            if k and len(pool):
                sig[rng.choice(pool, size=min(k, len(pool)), replace=False)] = True
        sbars = np.flatnonzero(sig)
        busy = -1
        for s in sbars:
            if variant == 'base':
                e, mode = s, 'close'
            elif variant == 'lag':
                e, mode = s + 1, 'close'
                if e >= n or not p['elig'][e]:
                    continue
            else:
                e, mode = s + 1, 'open'
            if e <= busy:
                continue
            r = walk(p, s, e, mode)
            if r == 'skip':
                continue
            if r == 'incomplete':
                dropped += 1
                break                          # position still open at data end: nothing later can be taken
            j, px, why, px_in = r
            rows.append((t, p['d'][e], p['d'][s], np.log(px / px_in), why, j - e, p['W'][s], p['z'][s],
                         p['c'][s] == p['l'][s], np.log(p['o'][s + 1] / p['c'][s]) if s + 1 < n else np.nan,
                         np.log(p['mid'][s] / px_in)))
            busy = j
    T = pd.DataFrame(rows, columns=['ticker', 'date', 'sig_date', 'gross', 'reason', 'bars', 'W', 'z', 'close_at_low',
                                    'overnight', 'dist_to_mid'])
    T['net_B'] = T.gross - COST_B
    T.attrs['dropped'] = dropped
    return T


def metrics(T, cal, period='2000-25'):
    a, b = (pd.Timestamp(x) for x in PERIODS[period])
    z = T[(T.date >= a) & (T.date <= b)]
    if not len(z):
        return dict(period=period, trades=0)
    daily = z.groupby('date').net_B.mean().reindex(cal[(cal >= a) & (cal <= b)])
    m, se, nd = nw(daily.to_numpy(), 10)
    yrs = (b - a).days / 365.25
    return dict(period=period, trades=len(z), per_year=len(z) / yrs, gross_pct=z.gross.mean() * 100,
                net_B_event_pct=z.net_B.mean() * 100, net_B_daily_pct=m * 100,
                t_nw=(m / se) if se and se > 0 else np.nan, days=nd,
                share_target=(z.reason == 'target').mean(), share_stop=(z.reason == 'stop').mean(),
                share_time=(z.reason == 'time').mean(), avg_bars=z.bars.mean())


# ----------------------------------------------------------------------------------------------- property
def property_slope(P, cal):
    recs = []
    for t, p in P.items():
        c, o = p['c'], p['o']
        n = len(c)
        fwd = np.full(n, np.nan)
        fwd[:n - 10] = np.log(c[10:] / c[:-10])
        fwd_o = np.full(n, np.nan)                       # executable variant: Open t+1 -> Close t+10
        fwd_o[:n - 10] = np.log(c[10:] / o[1:n - 9])
        with np.errstate(invalid='ignore'):
            ok = p['elig'] & np.isfinite(p['W']) & (p['A'] > 0)
            side = ok & (p['er'] < .3)
        recs.append(pd.DataFrame(dict(ticker=t, date=p['d'][ok], z=p['z'][ok], W=p['W'][ok], fwd=fwd[ok], fwd_o=fwd_o[ok],
                                      side=side[ok])))
    R = pd.concat(recs, ignore_index=True)
    R = R[np.isfinite(R.fwd) & np.isfinite(R.z)]
    # plan: minus EW mean of ELIGIBLE stocks (all eligible, not only sideways ones)
    R['abn'] = R.fwd - R.groupby('date').fwd.transform('mean')
    R['abn_o'] = R.fwd_o - R.groupby('date').fwd_o.transform('mean')
    S = R[R.side].copy()
    out = []
    for wname, (a, b) in CLASSES.items():
        x = S[(S.W >= a) & (S.W < b)].copy()
        for ycol in ['abn', 'abn_o']:
            x = x[np.isfinite(x[ycol])]
            g = x.groupby('date')
            cnt = g.z.transform('size')
            zc = x.z - g.z.transform('mean')
            yc = x[ycol] - g[ycol].transform('mean')
            num = (zc * yc).groupby(x.date).sum()
            den = (zc * zc).groupby(x.date).sum()
            nn = cnt.groupby(x.date).first()
            sl = (num / den).where((nn >= 5) & (den > 0))
            for pn, (pa, pb) in PERIODS.items():
                pa, pb = pd.Timestamp(pa), pd.Timestamp(pb)
                s = sl.reindex(cal[(cal >= pa) & (cal <= pb)])
                m, se, nd = nw(s.to_numpy(), 10)
                out.append(dict(width=wname, y=ycol, period=pn, obs=int(((x.date >= pa) & (x.date <= pb)).sum()),
                                slope_pct_per_ATR=m * 100, t=m / se if se and se > 0 else np.nan, days=nd))
    # bucket means narrow (abn vs eligible universe)
    xb = S[(S.W < 4)]
    bk = xb.groupby(pd.cut(xb.z, [-9, -2, -1.5, -1, -.5, 0, .5, 1, 1.5, 2, 9]), observed=False).abn.agg(['mean', 'size'])
    return pd.DataFrame(out), bk


# ----------------------------------------------------------------------------------------------- main
def main():
    pd.set_option('display.width', 250)
    pd.set_option('display.max_columns', 40)
    st, _ = engine.load_data('stocks')
    P, cal = build_panel(st)
    print(f'tickers in panel: {len(P)}; last data date {st["Date/Time"].max().date()}')
    orig = pd.read_csv(OUT / 'results.csv')
    otr = pd.read_csv(OUT / 'trades.csv', parse_dates=['signal'])

    cells = [('medium', 'below_mid_1', 'stock_er'), ('narrow', 'last_low', 'stock_er'),
             ('wide', 'below_mid_2', 'stock_er'), ('wide', 'below_mid_2', 'market')]
    allrows, store = [], {}
    # ---------- 1. recompute + compare
    print('\n=== 1. recompute vs results.csv (2000-25) ===')
    for cell in cells:
        for var in ['base', 'lag', 'open']:
            T = simulate(P, *cell, variant=var)
            store[(cell, var)] = T
            for pn in PERIODS:
                allrows.append(dict(width=cell[0], entry=cell[1], sideways=cell[2], variant=var, dropped=T.attrs['dropped'],
                                    **metrics(T, cal, pn)))
        T = store[(cell, 'base')]
        ctl = [simulate(P, *cell, control_seed=1000 + s).gross.mean() for s in range(20)]
        o = orig[(orig.width == cell[0]) & (orig.entry == cell[1]) & (orig.sideways == cell[2]) & (orig.period == '2000-25')].iloc[0]
        m = metrics(T, cal)
        ot = otr[otr.cell == str(cell)]
        # trade-level match with the original trades.csv
        mk = T.assign(k=T.ticker + T.date.dt.strftime('%Y%m%d'))
        ok_ = ot.assign(k=ot.ticker + ot.signal.dt.strftime('%Y%m%d'))
        jj = mk.merge(ok_[['k', 'gross']], on='k', how='inner', suffixes=('', '_orig'))
        # control significance: signal daily mean gross vs control mean (treated as constant)
        dg = T.groupby('date').gross.mean().reindex(cal[(cal >= START) & (cal <= END)])
        md, sed, _ = nw(dg.to_numpy() - np.mean(ctl), 10)
        print(f'{cell}: n {m["trades"]} (orig {o.trades}), common trades {len(jj)}, max |gross diff| '
              f'{(jj.gross - jj.gross_orig).abs().max():.2e}; gross {m["gross_pct"]:.3f} (orig {o.gross_pct:.3f}); '
              f'netB event {m["net_B_event_pct"]:.3f} (orig {o.net_B_event_pct:.3f}); netB daily {m["net_B_daily_pct"]:.3f} '
              f't {m["t_nw"]:.2f} (orig {o.net_B_pct:.3f}, t {o.t_net_B:.2f}); target {m["share_target"]:.3f} '
              f'(orig {o.share_target:.3f}) stop {m["share_stop"]:.3f} (orig {o.share_stop:.3f}); '
              f'control20 {np.mean(ctl) * 100:.3f}+-{np.std(ctl) * 100:.3f} (orig {o.control20_gross_pct:.3f}); '
              f'daily(gross - control) {md * 100:.3f} t {md / sed:.2f}; dropped at data end {T.attrs["dropped"]}')
        Cm = pd.concat([simulate(P, *cell, control_seed=1000 + s) for s in range(3)])
        print(f'   mean distance to mid at entry: signal {T.dist_to_mid.mean() * 100:.2f}%  control {Cm.dist_to_mid.mean() * 100:.2f}%;'
              f' gross/dist signal {T.gross.mean() / T.dist_to_mid.mean():.3f} control {Cm.gross.mean() / Cm.dist_to_mid.mean():.3f}')
    R = pd.DataFrame(allrows)
    R.to_csv(OUT / 'verify_cells.csv', index=False)
    print('\n=== timing variants (base = signal Close t, buy Close t; lag = signal Close t-1, buy Close t with limit at mid;'
          ' open = signal Close t, buy Open t+1) ===')
    print(R[['width', 'entry', 'sideways', 'variant', 'period', 'trades', 'gross_pct', 'net_B_event_pct', 'net_B_daily_pct',
             't_nw', 'share_target', 'share_stop']].round(3).to_string(index=False))

    # ---------- 2. audit items
    print('\n=== 2. audit ===')
    for cell in cells:
        T = store[(cell, 'base')]
        cal_ = T[T.close_at_low]
        print(f'{cell}: close==day Low share {T.close_at_low.mean():.3f}; gross if close-at-low {cal_.gross.mean() * 100:.3f}% '
              f'(n {len(cal_)}) vs not {T[~T.close_at_low].gross.mean() * 100:.3f}%; mean overnight C(t)->O(t+1) '
              f'{T.overnight.mean() * 100:.3f}%; z>0 entries {(T.z > 0).sum()}; holding>10 bars {(T.bars > 10).sum()}')
    # last_low vs below_mid overlap in the narrow class
    ov = []
    for t, p in P.items():
        bm = base_mask(p, 'narrow', 'stock_er')
        ll, b1 = bm & entry_mask(p, 'last_low'), bm & entry_mask(p, 'below_mid_1')
        ov.append((ll.sum(), (ll & b1).sum(), b1.sum()))
    ov = np.array(ov).sum(0)
    print(f'narrow/stock_er raw signal days: last_low {ov[0]}, of which also z<=-1: {ov[1]} ({ov[1] / ov[0]:.1%}); below_mid_1 {ov[2]}')
    # width distribution of sideways eligible days
    Ws = np.concatenate([p['W'][base_mask(p, 'narrow', 'stock_er', 0, np.inf)] for p in P.values()])
    print(f'W on eligible stock-ER<0.3 days: n {len(Ws)}; share <4 {np.mean(Ws < 4):.3f}, 4-7 {np.mean((Ws >= 4) & (Ws < 7)):.3f},'
          f' >=7 {np.mean(Ws >= 7):.4f}; quantiles 5/50/95/99 {np.round(np.percentile(Ws, [5, 50, 95, 99]), 2)}')
    # threshold sensitivity
    sens = []
    for (w, e, s, lo, hi) in [('wide', 'below_mid_2', 'stock_er', 6, np.inf), ('wide', 'below_mid_2', 'stock_er', 8, np.inf),
                              ('wide', 'below_mid_2', 'stock_er', 5, np.inf), ('wide', 'below_mid_1.5', 'stock_er', 6, np.inf),
                              ('narrow', 'below_mid_1', 'stock_er', 0, 3.5), ('narrow', 'below_mid_1', 'stock_er', 0, 4.5),
                              ('medium', 'below_mid_2', 'stock_er', 4, 7), ('medium', 'below_mid_2', 'market', 4, 7)]:
        T = simulate(P, w, e, s, lo=lo, hi=hi)
        sens.append(dict(cell=f'{w}/{e}/{s}', W_range=f'[{lo},{hi})', **metrics(T, cal)))
    print(pd.DataFrame(sens)[['cell', 'W_range', 'trades', 'gross_pct', 'net_B_event_pct', 'net_B_daily_pct', 't_nw']].round(3).to_string(index=False))

    # ---------- 3. concentration of the wide / stock-ER group
    print('\n=== 3. wide / stock_er concentration ===')
    conc = []
    for e in ['below_mid_1', 'below_mid_1.5', 'below_mid_2', 'last_low']:
        T = store.get((('wide', e, 'stock_er'), 'base'))
        if T is None:
            T = simulate(P, 'wide', e, 'stock_er')
        by = T.groupby('ticker').gross.agg(['size', 'sum', 'mean']).sort_values('sum', ascending=False)
        tot = T.gross.sum()
        excl = {}
        for k in [1, 3, 5]:
            top = by.index[:k]
            excl[k] = T[~T.ticker.isin(top)].gross.mean() * 100
        loo = [T[T.ticker != tk].gross.mean() * 100 for tk in by.index]
        yr = T.groupby(T.date.dt.year).gross.agg(['size', 'mean'])
        conc.append(dict(entry=e, trades=len(T), tickers=len(by), gross_pct=T.gross.mean() * 100,
                         top1=by.index[0], top1_share_of_sum=by['sum'].iloc[0] / tot, top3_share_of_sum=by['sum'].iloc[:3].sum() / tot,
                         top5_share_of_sum=by['sum'].iloc[:5].sum() / tot, max_trades_one_ticker=int(by['size'].max()),
                         gross_ex_top1=excl[1], gross_ex_top3=excl[3], gross_ex_top5=excl[5], loo_min=min(loo), loo_max=max(loo),
                         median_gross_pct=T.gross.median() * 100, years_pos=int((yr['mean'] > 0).sum()), years=len(yr),
                         best_year=int(yr['mean'].idxmax()), best_year_n=int(yr.loc[yr['mean'].idxmax(), 'size'])))
        print(f'\n-- wide/{e}/stock_er: top tickers by sum of gross --')
        print((by.head(8) * [1, 100, 100]).round(2).to_string())
        print('-- by year (n, mean gross %) --')
        print(pd.DataFrame({'n': yr['size'], 'mean_pct': (yr['mean'] * 100).round(2)}).T.to_string())
    C = pd.DataFrame(conc)
    C.to_csv(OUT / 'verify_concentration.csv', index=False)
    print(C.round(3).to_string(index=False))
    # timing variants for all wide/stock_er entries
    tv = []
    for e in ['below_mid_1', 'below_mid_1.5', 'below_mid_2', 'last_low']:
        for var in ['base', 'lag', 'open']:
            T = store.get((('wide', e, 'stock_er'), var))
            if T is None:
                T = simulate(P, 'wide', e, 'stock_er', variant=var)
            for pn in ['2000-25', '2021-25']:
                tv.append(dict(entry=e, variant=var, **metrics(T, cal, pn)))
    TV = pd.DataFrame(tv)
    TV.to_csv(OUT / 'verify_wide_timing.csv', index=False)
    print('\n-- wide/stock_er by timing variant --')
    print(TV[['entry', 'variant', 'period', 'trades', 'gross_pct', 'net_B_event_pct', 'net_B_daily_pct', 't_nw']].round(3).to_string(index=False))

    # ---------- 4. property slope
    print('\n=== 4. property: FM slope of 10d abnormal fwd return on z (sideways = stock ER20<0.3) ===')
    PR, bk = property_slope(P, cal)
    PR.to_csv(OUT / 'verify_property.csv', index=False)
    print(PR.round(3).to_string(index=False))
    print('narrow buckets (abn vs all eligible, %):')
    print((bk.assign(mean=bk['mean'] * 100)).round(3).T.to_string())
    extra_checks(P, cal)


def extra_checks(P, cal):
    """Control significance for the medium below_mid_2 cells, touch-fill optimism, shape of the 'wide sideways' signals."""
    print('\n=== 5. extra checks ===')
    for cell in [('medium', 'below_mid_2', 'stock_er'), ('medium', 'below_mid_2', 'market'), ('narrow', 'below_mid_1', 'stock_er')]:
        T = simulate(P, *cell)
        ctl = [simulate(P, *cell, control_seed=2000 + s).gross.mean() for s in range(20)]
        dg = T.groupby('date').gross.mean().reindex(cal[(cal >= START) & (cal <= END)])
        m, se, _ = nw(dg.to_numpy() - np.mean(ctl), 10)
        g, gse, _ = nw(dg.to_numpy(), 10)
        print(f'{cell}: n {len(T)} gross {T.gross.mean() * 100:.3f} (daily {g * 100:.3f}, t {g / gse:.2f}); control '
              f'{np.mean(ctl) * 100:.3f}+-{np.std(ctl) * 100:.3f}; daily(gross - control) {m * 100:.3f} t {m / se:.2f}')
    for cell in [('wide', 'below_mid_2', 'stock_er'), ('medium', 'below_mid_1', 'stock_er')]:
        T = simulate(P, *cell)
        x = []
        for r in T[T.reason == 'target'].itertuples():
            p = P[r.ticker]
            e = int(np.searchsorted(p['d'].values, np.datetime64(r.date)))
            x.append((p['h'][e + r.bars] - p['mid'][e]) / p['mid'][e])
        x = np.array(x)
        print(f'{cell}: target exits {len(x)}; High within 0.05% of the mid (touch fill) {np.mean(x < .0005):.3f}, within 0.5% {np.mean(x < .005):.3f}')
    T = simulate(P, 'wide', 'below_mid_2', 'stock_er')
    a = []
    for r in T.itertuples():
        p = P[r.ticker]
        e = int(np.searchsorted(p['d'].values, np.datetime64(r.date)))
        a.append((np.log(p['c'][e] / p['c'][e - 20]), np.log(p['c'][e] / p['H'][e]), np.argmax(p['h'][e - 19:e + 1])))
    a = np.array(a)
    print(f'wide/below_mid_2/stock_er signals: median 20d log return {np.median(a[:, 0]):.3f}, median log(C/H20) {np.median(a[:, 1]):.3f},'
          f' share with the 20-bar High in the older half of the window {np.mean(a[:, 2] < 10):.2f}')
    tick_end = {t: p['d'][-1] for t, p in P.items()}
    print(f'last bar per ticker: min {min(tick_end.values()).date()}, max {max(tick_end.values()).date()} (all alive at data end -> current-constituent list)')


if __name__ == '__main__':
    main()
