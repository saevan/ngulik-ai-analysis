"""Independent verifier for range_size_modules.py (21 Oct 2026). Does NOT import range_size_modules.py.

Part 1  recomputes four cells from scratch (own indicators, own exit loops) and compares with results.csv / trades.csv:
        (small, fade, stock_er, narrowing), (small, breakout, stock_er, narrowing), (small, breakout, stock_er, no narrowing),
        (large, breakout, market, narrowing flag True = no narrowing rule for large).
Part 2  audits the breakout cells:
        - the original random control (is it random? is it fair for a buy stop?)
        - fairer controls: same-distance random buy stops on random eligible days (same stock, same exit geometry in ATR),
          next-Open entry on every condition day (no breakout trigger), condition days on which the stop was NOT hit
        - concentration by ticker / year, 2021-25 by year, post call-auction extension
        - execution: strict High > level, level on the price grid (empirical adjusted grid and modern IDX ticks), +1 tick fill,
          0.5% buffer like the main system, gap rules 2% / 0.5% (Open above the base level H)
        - relation with the main breakout system (HHV20 buy stop, prior-bar ER20 >= 0.2): same breakout + exit by ER and W buckets
Run: python range_size_modules_results/verify_range_size.py      (prints tables, writes verify_range_size_out.csv)
"""
import sys
import multiprocessing as mp
from pathlib import Path
import numpy as np, pandas as pd
from numpy.lib.stride_tricks import sliding_window_view as swv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu
import pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy

D0, D1 = np.datetime64('2000-01-01'), np.datetime64('2025-08-15')
COST = .009
PER = {'2000-25': ('2000-01-01', '2025-08-15'), '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
       '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
P = {}
CAL = None


# ----------------------------------------------------------------------------------------------- indicators (own code)
def rolling(x, n, how):
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = getattr(swv(x, n), how)(axis=1)
    return out


def wilder_atr(h, l, c, n=14):
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1)
    out = np.full(len(c), np.nan)
    if len(c) >= n:
        v = tr[:n].mean()
        out[n - 1] = v
        for k in range(n, len(c)):
            v += (tr[k] - v) / n
            out[k] = v
    return out


def eff_ratio(c, n=20):
    out = np.full(len(c), np.nan)
    if len(c) > n:
        ad = np.abs(np.diff(c))                       # ad[k] = |c[k+1]-c[k]|
        den = swv(ad, n).sum(axis=1)                  # den[m] = sum ad[m..m+n-1] -> bar t = m+n
        num = np.abs(c[n:] - c[:-n])
        with np.errstate(invalid='ignore', divide='ignore'):
            out[n:] = num / den
    return out


def idx_tick(price):
    return np.select([price < 200, price < 500, price < 2000, price < 5000], [1., 2., 5., 10.], 25.)


def emp_tick(o, h, l, c):
    px = np.c_[o, h, l, c]
    g = np.abs(px[:, :, None] - px[:, None, :]).reshape(len(c), 16)
    g = np.where(g > 1e-9, g, np.inf).min(axis=1)
    g = np.where(np.isfinite(g), g, np.nan)
    return pd.Series(g).shift(1).rolling(60, min_periods=10).min().to_numpy()


def prep(t, f, okd, side):
    f = f[f['tradable'].to_numpy(bool)].reset_index(drop=True)
    if len(f) < 300:
        return None
    o, h, l, c = (f[k].to_numpy(float) for k in ('Open', 'High', 'Low', 'Close'))
    d = f['Date/Time'].to_numpy('datetime64[ns]')
    H, L, A = rolling(h, 20, 'max'), rolling(l, 20, 'min'), wilder_atr(h, l, c)
    with np.errstate(invalid='ignore', divide='ignore'):
        W = (H - L) / A
    W20 = np.full(len(W), np.nan)
    W20[20:] = W[:-20]
    base = np.isin(d, okd) & (d >= D0) & (d <= D1) & np.isfinite(W) & (A > 0)
    return dict(o=o, h=h, l=l, c=c, d=d, H=H, L=L, A=A, W=W, W20=W20, ER=eff_ratio(c), base=base, side=np.isin(d, side),
                et=emp_tick(o, h, l, c), year=d.astype('datetime64[Y]').astype(int) + 1970)


def cell_mask(p, size, side, narrowing):
    m = p['base'].copy()
    er = np.nan_to_num(p['ER'], nan=-1.)
    erok = np.isfinite(p['ER'])
    m &= {'stock_er': erok & (er < .3), 'market': p['side'], 'all': np.ones(len(m), bool),
          'er_lt_02': erok & (er < .2), 'er_02_03': (er >= .2) & (er < .3), 'er_ge_02': er >= .2, 'er_ge_03': er >= .3}[side]
    W = p['W']
    m &= {'small': W < 4, 'large': W >= 6, 'mid': (W >= 4) & (W < 6), 'any': np.isfinite(W)}[size]
    if narrowing and size == 'small':                    # as in the plan/original: narrowing only defines the small range
        with np.errstate(invalid='ignore'):
            if narrowing == 'raw':                           # sensitivity: price range R[t] <= 0.7 R[t-20] (not ATR-normalised)
                R = p['H'] - p['L']
                R20 = np.full(len(R), np.nan)
                R20[20:] = R[:-20]
                m &= R <= .7 * R20
            else:
                m &= W <= .7 * p['W20']
    return m


# ----------------------------------------------------------------------------------------------- exits (own code)
def brk_exit(p, e, mid):
    o, h, c = p['o'], p['h'], p['c']
    n = len(c)
    top, top_at, j = h[e], e, e
    while j < n:
        if h[j] > top:
            top, top_at = h[j], j
        below = c[j] < mid
        if (below or j - top_at >= 5) and j + 1 < n:
            return j + 1, o[j + 1], 'mid' if below else 'no_new_high'
        if j == e + 40:
            return j, c[j], 'time'
        j += 1
    return None


def fade_exit(p, i, tgt, stop, maxb):
    o, h, c = p['o'], p['h'], p['c']
    n = len(c)
    for j in range(i + 1, i + maxb + 1):
        if j >= n:
            return None
        if h[j] >= tgt:
            return j, max(o[j], tgt), 'target'
        if c[j] < stop and j + 1 < n:
            return j + 1, o[j + 1], 'stop'
        if j == i + maxb:
            return j, c[j], 'time'
    return None


# ----------------------------------------------------------------------------------------------- simulation
def breakout_level(p, i, o_):
    H, A = p['H'][i], p['A'][i]
    if o_.get('buffer') == 'pct':
        lvl = H * 1.005
    else:
        lvl = H + .1 * A
    tick = None
    if o_.get('grid') == 'emp':
        tick = p['et'][i]
    elif o_.get('grid') == 'idx':
        tick = float(idx_tick(np.array([p['c'][i]]))[0])
    if tick is not None and np.isfinite(tick) and tick > 0:
        k = max(np.ceil(round((lvl - H) / tick, 9)), 1)
        lvl = max(H + k * tick, lvl)
    return lvl, tick


def run(args):
    """args = (label, size, logic, side, narrowing, opts). opts['entry'] in stop|close|open|nobreak_close."""
    label, size, logic, side, narrowing, o_ = args
    entry = o_.get('entry', 'stop')
    rng = np.random.default_rng(o_['seed']) if 'seed' in o_ else None
    out = []
    for t, p in P.items():
        o, h, l, c, H, L, A = (p[k] for k in ('o', 'h', 'l', 'c', 'H', 'L', 'A'))
        n = len(c)
        m = cell_mask(p, size, side, narrowing)
        R = H - L
        mid = (H + L) / 2
        sig = m & (c <= L + .25 * R) if logic == 'fade' else m.copy()
        if rng is not None:                              # original-style control: k random condition days, entry at the Close
            pool = np.flatnonzero(m)
            k = int(sig.sum())
            sig = np.zeros(n, bool)
            if k and len(pool):
                sig[rng.choice(pool, min(k, len(pool)), replace=False)] = True
        busy = -1
        for i in np.flatnonzero(sig):
            if i <= busy or i + 1 >= n:
                continue
            extra = {}
            if logic == 'fade' or entry == 'close':
                e, px = i, c[i]
                if logic == 'fade':
                    tgt = H[i] - .25 * R[i] if size == 'small' else mid[i]
                    res = fade_exit(p, i, tgt, L[i] - .5 * A[i], 10 if size == 'small' else 20)
                else:
                    res = brk_exit(p, e, mid[i])
            elif entry == 'open':
                e, px = i + 1, o[i + 1]
                res = brk_exit(p, e, mid[i])
            else:
                lvl, tick = breakout_level(p, i, o_)
                hit = h[i + 1] >= lvl if o_.get('touch', True) else h[i + 1] > lvl
                if entry == 'nobreak_close':
                    if hit:
                        continue
                    e, px = i + 1, c[i + 1]
                    res = brk_exit(p, e, mid[i])
                else:
                    if not hit:
                        continue
                    g = o_.get('gap_skip')
                    if g is not None and o[i + 1] > H[i] * (1 + g):
                        continue
                    e, px = i + 1, max(o[i + 1], lvl)
                    if o_.get('slip_ticks') and tick is not None and np.isfinite(tick):
                        px = min(h[i + 1], px + o_['slip_ticks'] * tick)
                    extra = dict(gap=o[i + 1] > lvl, gap_pct=o[i + 1] / H[i] - 1, dist_atr=(lvl - c[i]) / A[i])
                    res = brk_exit(p, e, mid[i])
            if res is None:
                break
            out.append(dict(ticker=t, signal=p['d'][i], entry=p['d'][e], gross=np.log(res[1] / px), reason=res[2], bars=res[0] - e,
                            er=p['ER'][i], W=p['W'][i], year=int(p['year'][i]), **extra))
            busy = res[0]
    T = pd.DataFrame(out)
    if len(T):
        T['net'] = T.gross - COST
    return label, T


def run_samedist(args):
    """Fair control for a buy stop: k random eligible days per stock (pool 'all' or 'er<.3'), each gets the (stop distance above
    the Close, level-to-mid distance) in ATR of a random actual condition day of that stock; same fill and exit rule."""
    label, size, side, narrowing, pool_kind, seed = args
    rng = np.random.default_rng(seed)
    out = []
    for t, p in P.items():
        o, h, c, H, L, A = (p[k] for k in ('o', 'h', 'c', 'H', 'L', 'A'))
        n = len(c)
        m = cell_mask(p, size, side, narrowing)
        I = np.flatnonzero(m)
        if not len(I):
            continue
        dist = (H[I] + .1 * A[I] - c[I]) / A[I]
        md = (H[I] + .1 * A[I] - (H[I] + L[I]) / 2) / A[I]
        pool = np.flatnonzero(cell_mask(p, 'any', 'all' if pool_kind == 'all' else 'stock_er', False))
        J = np.sort(rng.choice(pool, min(len(I), len(pool)), replace=False))
        pick = rng.integers(0, len(I), len(J))
        busy = -1
        for j, q in zip(J, pick):
            if j <= busy or j + 1 >= n:
                continue
            lvl = c[j] + dist[q] * A[j]
            if h[j + 1] < lvl:
                continue
            e, px = j + 1, max(o[j + 1], lvl)
            res = brk_exit(p, e, lvl - md[q] * A[j])
            if res is None:
                break
            out.append(dict(ticker=t, signal=p['d'][j], gross=np.log(res[1] / px), reason=res[2], bars=res[0] - e))
            busy = res[0]
    T = pd.DataFrame(out)
    T['net'] = T.gross - COST
    return label, T


# ----------------------------------------------------------------------------------------------- statistics
def summarize(T, label):
    rows = []
    for pn, (s, e) in PER.items():
        x = T[(T.signal >= np.datetime64(s)) & (T.signal <= np.datetime64(e))] if len(T) else T
        cal = CAL[(CAL >= np.datetime64(s)) & (CAL <= np.datetime64(e))]
        r = dict(label=label, period=pn, trades=len(x))
        if len(x):
            dm = x.groupby('signal').net.mean().reindex(cal)
            m, se, _ = nw(dm.values, 20)
            dg = x.groupby('signal').gross.mean().reindex(cal)
            mg, seg, _ = nw(dg.values, 20)
            r.update(gross_pct=x.gross.mean() * 100, t_gross=mg / seg if seg else np.nan, net_B_pct=m * 100,
                     t_net_B=m / se if se else np.nan, win_rate_B=(x.net > 0).mean(), avg_bars=x.bars.mean(),
                     **{f'share_{k}': v for k, v in x.reason.value_counts(normalize=True).items()})
        rows.append(r)
    return rows


def t_vs(T, ref):
    """NW t of (per-day mean gross - ref) on the full period, ref treated as a fixed number."""
    dg = (T.groupby('signal').gross.mean() - ref).reindex(CAL[(CAL >= D0) & (CAL <= D1)])
    m, se, _ = nw(dg.values, 20)
    return m / se if se else np.nan


def main():
    global CAL
    st, _ = engine.load_data('stocks')
    fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
    okd = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in fr}
    reg = regime_proxy(st)['regime']
    side = np.array(reg.index[reg == 'sideways'], dtype='datetime64[ns]')
    CAL = np.array(sorted(st['Date/Time'].unique()), dtype='datetime64[ns]')
    for t, f in fr.items():
        q = prep(t, f, okd[t], side)
        if q is not None:
            P[t] = q

    MAIN4 = [('small', 'fade', 'stock_er', True), ('small', 'breakout', 'stock_er', True), ('small', 'breakout', 'stock_er', False),
             ('large', 'breakout', 'market', True)]
    jobs = [(str(cl), *cl, {}) for cl in MAIN4]
    # original-style controls (20 seeds; for the breakout the 'random' draw is a permutation of all condition days)
    for cl in MAIN4:
        for s in range(20):
            jobs.append((f'ctl_orig|{cl}|{s}', *cl, dict(entry='close', seed=10_000 + s)))
    SB = ('small', 'breakout', 'stock_er', True)
    SBN = ('small', 'breakout', 'stock_er', False)
    LB = ('large', 'breakout', 'market', True)
    for cl in (SB, SBN, LB):
        jobs += [(f'cond_open|{cl}', *cl, dict(entry='open')), (f'nobreak_close|{cl}', *cl, dict(entry='nobreak_close'))]
    # remaining fade cells (is every fade below its original-style control, and significantly?)
    FADES = [('small', 'fade', 'market', True), ('large', 'fade', 'stock_er', True), ('large', 'fade', 'market', True),
             ('small', 'fade', 'stock_er', False), ('small', 'fade', 'market', False)]
    for cl in FADES:
        jobs.append((str(cl), *cl, {}))
        for s in range(20):
            jobs.append((f'ctl_orig|{cl}|{s}', *cl, dict(entry='close', seed=10_000 + s)))
    jobs.append(("raw_narrowing|('small', 'breakout', 'stock_er', 'raw')", 'small', 'breakout', 'stock_er', 'raw', {}))
    # execution variants on the small-range breakout cells
    VAR = {'strict_gt': dict(touch=False), 'grid_emp': dict(grid='emp'), 'grid_emp+1tick': dict(grid='emp', slip_ticks=1),
           'grid_idx': dict(grid='idx'), 'grid_idx+1tick': dict(grid='idx', slip_ticks=1), 'buffer_0.5pct': dict(buffer='pct'),
           'buffer_0.5pct_grid_emp': dict(buffer='pct', grid='emp'), 'gap_skip_2pct': dict(gap_skip=.02), 'gap_skip_0.5pct': dict(gap_skip=.005),
           'main_like(0.5pct,grid,gap2%)': dict(buffer='pct', grid='emp', gap_skip=.02)}
    for cl in (SB, SBN):
        for k, v in VAR.items():
            jobs.append((f'var:{k}|{cl}', *cl, v))
    # same breakout rule + exit on other condition sets (relation with the main system)
    for sz in ('any', 'small', 'mid', 'large'):
        for sd in ('all', 'er_lt_02', 'er_02_03', 'er_ge_02', 'er_ge_03'):
            jobs.append((f'bucket|{sz}|{sd}', sz, 'breakout', sd, False, {}))
    sjobs = [(f'samedist|{pk}|{cl}|{s}', cl[0], cl[2], cl[3], pk, 20_000 + s) for cl in (SB, SBN, LB) for pk in ('all', 'er03') for s in range(20)]

    ctx = mp.get_context('fork')
    with ctx.Pool(4) as pool:
        res = dict(pool.map(run, jobs, chunksize=1))
        res.update(dict(pool.map(run_samedist, sjobs, chunksize=1)))

    pd.set_option('display.width', 260, 'display.max_columns', 40, 'display.max_rows', 400)
    allrows = []

    # ---------------- Part 1: reproduction
    print('\n=== PART 1: independent recomputation vs results.csv / trades.csv ===')
    R = pd.read_csv(HERE / 'results_all.csv')
    TR = pd.read_csv(HERE / 'trades.csv', parse_dates=['signal'])
    for cl in MAIN4:
        T = res[str(cl)]
        rows = summarize(T, str(cl))
        ctl = np.mean([res[f'ctl_orig|{cl}|{s}'].gross.mean() for s in range(20)]) * 100
        ctl_n = [len(res[f'ctl_orig|{cl}|{s}']) for s in range(20)]
        for r in rows:
            r['control_orig_gross_pct'] = ctl
        allrows += rows
        mine = pd.DataFrame(rows).set_index('period')
        ref = R[(R['size'] == cl[0]) & (R.logic == cl[1]) & (R.sideways == cl[2]) & (R.narrowing == cl[3])].set_index('period')
        cmp_ = pd.DataFrame({'trades_mine': mine.trades, 'trades_ref': ref.trades, 'gross_mine': mine.gross_pct, 'gross_ref': ref.gross_pct,
                             'netB_mine': mine.net_B_pct, 'netB_ref': ref.net_B_pct, 't_mine': mine.t_net_B, 't_ref': ref.t_net_B,
                             'wr_mine': mine.win_rate_B, 'wr_ref': ref.win_rate_B, 'ctl_mine': ctl, 'ctl_ref': ref.control20_gross_pct})
        print(f'\n{cl}  control trades per seed min/max {min(ctl_n)}/{max(ctl_n)}  control seeds distinct gross means: '
              f'{len(set(round(res[f"ctl_orig|{cl}|{s}"].gross.mean(), 12) for s in range(20)))}')
        print(cmp_.round(3).to_string())
        sh = [c for c in mine.columns if c.startswith('share_')]
        print('exit shares (mine, 2000-25):', mine.loc['2000-25', sh].round(3).to_dict())
        x = TR[TR.cell == str(cl)].merge(T[['ticker', 'signal', 'gross', 'reason']], on=['ticker', 'signal'], how='outer', suffixes=('_ref', '_mine'), indicator=True)
        both = x[x._merge == 'both']
        print(f'trade-level match: both {len(both)}, only_ref {int((x._merge == "left_only").sum())}, only_mine {int((x._merge == "right_only").sum())}, '
              f'max |gross diff| {np.abs(both.gross_ref - both.gross_mine).max():.2e}, reason mismatches {int((both.reason_ref != both.reason_mine).sum())}')

    # ---------------- Part 2a: controls
    print('\n=== PART 2a: controls for the breakout cells (gross % per trade, full period) ===')
    crow = []
    for cl in (SB, SBN, LB):
        T = res[str(cl)]
        g = T.gross.mean()
        ent = dict(cell=str(cl), trades=len(T), gross_pct=g * 100, t_gross=summarize(T, '')[0]['t_gross'])
        ent['ctl_orig_close_gross_pct'] = np.mean([res[f'ctl_orig|{cl}|{s}'].gross.mean() for s in range(20)]) * 100
        for pk in ('all', 'er03'):
            Ts = [res[f'samedist|{pk}|{cl}|{s}'] for s in range(20)]
            cg = np.mean([x.gross.mean() for x in Ts])
            ent[f'samedist_{pk}_gross_pct'] = cg * 100
            ent[f'samedist_{pk}_seed_sd_pct'] = np.std([x.gross.mean() for x in Ts]) * 100
            ent[f'samedist_{pk}_trades'] = np.mean([len(x) for x in Ts])
            ent[f't_cell_minus_samedist_{pk}'] = t_vs(T, cg)
            for pn, (s, e) in list(PER.items())[1:]:
                ent[f'samedist_{pk}_{pn}'] = np.mean([x[(x.signal >= np.datetime64(s)) & (x.signal <= np.datetime64(e))].gross.mean() for x in Ts]) * 100
        for pn, (s, e) in list(PER.items())[1:]:
            ent[f'cell_{pn}'] = T[(T.signal >= np.datetime64(s)) & (T.signal <= np.datetime64(e))].gross.mean() * 100
        for k in ('cond_open', 'nobreak_close'):
            x = res[f'{k}|{cl}']
            ent[f'{k}_gross_pct'] = x.gross.mean() * 100
            ent[f'{k}_trades'] = len(x)
        crow.append(ent)
    C = pd.DataFrame(crow).set_index('cell').T
    print(C.round(3).to_string())
    for cl in (SB, SBN, LB):
        allrows += [dict(r, label=f'samedist_all_seed0|{cl}') for r in summarize(res[f'samedist|all|{cl}|0'], '')]
    # fade cell: is it worse than the original control?
    R0 = pd.read_csv(HERE / 'results.csv')
    print()
    for FC in [('small', 'fade', 'stock_er', True)] + FADES:
        fctl = np.mean([res[f'ctl_orig|{FC}|{s}'].gross.mean() for s in range(20)])
        ref = R0[(R0['size'] == FC[0]) & (R0.logic == FC[1]) & (R0.sideways == FC[2]) & (R0.narrowing == FC[3])].iloc[0]
        print(f'fade {FC}: trades {len(res[str(FC)])} (ref {ref.trades}), gross {res[str(FC)].gross.mean() * 100:.3f}% (ref {ref.gross_pct:.3f}) '
              f'vs control {fctl * 100:.3f}% (ref {ref.control20_gross_pct:.3f}); NW t of difference {t_vs(res[str(FC)], fctl):.2f}; '
              f'NW t gross {summarize(res[str(FC)], "")[0]["t_gross"]:.2f}')
    x = res["raw_narrowing|('small', 'breakout', 'stock_er', 'raw')"]
    r = summarize(x, '')
    print(f'\nsmall breakout stock_er with RAW price narrowing (R <= .7 R[t-20]): trades {r[0]["trades"]}, gross {r[0]["gross_pct"]:.3f}%, '
          f'netB {r[0]["net_B_pct"]:.3f}% (t {r[0]["t_net_B"]:.2f}), 2016-20 {r[3]["net_B_pct"]:.3f}, 2021-25 {r[4]["net_B_pct"]:.3f}')

    # ---------------- Part 2b: concentration
    print('\n=== PART 2b: concentration of the small-range breakout (stock ER < .3) ===')
    for cl in (SB, SBN):
        T = res[str(cl)].copy()
        bt = T.groupby('ticker').gross.agg(['count', 'sum', 'mean']).sort_values('sum', ascending=False)
        tot = T.gross.sum()
        print(f'\n{cl}: {len(T)} trades in {T.ticker.nunique()} tickers; sum of log gross {tot:.2f}; '
              f'top-5 tickers {bt["sum"].head(5).sum() / tot:.0%} of the sum, top-10 {bt["sum"].head(10).sum() / tot:.0%}; '
              f'tickers with positive mean {int((bt["mean"] > 0).sum())}/{len(bt)}')
        print('top 8 tickers:\n', (bt.head(8).assign(mean=lambda z: z['mean'] * 100)).round(3).to_string())
        ex5 = T[~T.ticker.isin(bt.index[:5])]
        ex10 = T[~T.ticker.isin(bt.index[:10])]
        r5, r10 = summarize(ex5, '')[0], summarize(ex10, '')[0]
        print(f'without top-5 tickers: gross {r5["gross_pct"]:.3f}%  netB {r5["net_B_pct"]:.3f}% (t {r5["t_net_B"]:.2f}); '
              f'without top-10: gross {r10["gross_pct"]:.3f}%  netB {r10["net_B_pct"]:.3f}% (t {r10["t_net_B"]:.2f})')
        by = T.groupby('year').agg(n=('gross', 'size'), gross_pct=('gross', 'mean'), net_pct=('net', 'mean'), wr=('net', lambda z: (z > 0).mean()),
                                  sum_log=('gross', 'sum'))
        by[['gross_pct', 'net_pct']] *= 100
        print('by year:\n', by.round(3).T.to_string())
        yrs = by.sort_values('sum_log', ascending=False)
        x = T[~T.year.isin(yrs.index[:3])]
        r3 = summarize(x, '')[0]
        print(f'top-3 years {list(yrs.index[:3])} = {yrs.sum_log.head(3).sum() / tot:.0%} of the sum; without them gross {r3["gross_pct"]:.3f}% '
              f'netB {r3["net_B_pct"]:.3f}% (t {r3["t_net_B"]:.2f})')
        post = T[T.signal >= np.datetime64('2024-12-09')]
        print(f'since 9 Dec 2024 (call auction extension): n {len(post)}, gross {post.gross.mean() * 100:.3f}%, net {post.net.mean() * 100:.3f}%')
        g = T.groupby('gap').gross.agg(['count', 'mean'])
        g['mean'] *= 100
        print('gap-through fills (Open above the level) vs not:\n', g.round(3).to_string())
        T['erb'] = pd.cut(T.er, [-1, .1, .2, .3], labels=['<.1', '.1-.2', '.2-.3'], right=False)
        e = T.groupby('erb', observed=True).agg(n=('gross', 'size'), gross_pct=('gross', 'mean'))
        e['gross_pct'] *= 100
        e['share'] = e.n / len(T)
        print('by ER20 at the signal bar (.2-.3 = would also be armed in the main system):\n', e.round(3).to_string())

    # ---------------- Part 2c: execution variants
    print('\n=== PART 2c: execution variants (full period and 2016-25) ===')
    vrows = []
    for cl in (SB, SBN):
        base = summarize(res[str(cl)], 'base')
        vrows.append(dict(cell=str(cl), variant='base (H+0.1ATR, touch, fill max(O,level))', **{k: base[0][k] for k in ('trades', 'gross_pct', 'net_B_pct', 't_net_B')},
                          net_2016_20=base[3]['net_B_pct'], net_2021_25=base[4]['net_B_pct']))
        for k in VAR:
            s = summarize(res[f'var:{k}|{cl}'], k)
            allrows += [dict(r, label=f'var:{k}|{cl}') for r in s]
            vrows.append(dict(cell=str(cl), variant=k, **{q: s[0][q] for q in ('trades', 'gross_pct', 'net_B_pct', 't_net_B')},
                              net_2016_20=s[3]['net_B_pct'], net_2021_25=s[4]['net_B_pct']))
    print(pd.DataFrame(vrows).round(3).to_string(index=False))

    # ---------------- Part 2d: buckets
    print('\n=== PART 2d: same breakout (H+0.1ATR buy stop, 5-bar/mid/40 exit) on other condition sets, no narrowing ===')
    brows = []
    for sz in ('any', 'small', 'mid', 'large'):
        for sd in ('all', 'er_lt_02', 'er_02_03', 'er_ge_02', 'er_ge_03'):
            s = summarize(res[f'bucket|{sz}|{sd}'], f'{sz}|{sd}')
            allrows += [dict(r, label=f'bucket|{sz}|{sd}') for r in s]
            brows.append(dict(W=sz, ER=sd, trades=s[0]['trades'], gross_pct=s[0].get('gross_pct'), t_gross=s[0].get('t_gross'),
                              net_B_pct=s[0].get('net_B_pct'), t_net_B=s[0].get('t_net_B'),
                              **{f'net_{pn}': s[k].get('net_B_pct') for k, pn in enumerate(PER) if k}))
    print(pd.DataFrame(brows).round(3).to_string(index=False))

    pd.DataFrame(allrows).to_csv(HERE / 'verify_range_size_out.csv', index=False)


if __name__ == '__main__':
    main()
