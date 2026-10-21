"""Independent verifier for lowest_low_time.py (does NOT import it).

Re-implements the rules from lowest_low_time_results/PLAN.md with a different formulation:
  * N-bar low via sliding-window minima, "bars since last N-bar low" via a running max of low indices;
    signal at bar t when bars_since_low[t] == x (no new low in between, t itself not a low).
  * exit loop written separately, with switches for alternative readings.
Sections:
  1. reproduce three cells (and compare trade-by-trade with trades.csv / results.csv)
  2. rule audit variants (strict low, plan rule 'new low after the exit', x on all bars incl. zero-volume,
     ties extend the trade high, no 'break' on censored trades)
  3. alternative exit readings on the two best cells (trade high on Close, exit at Close of the x-th bar)
  4. multi-seed random control for all 36 cells (the main script uses one seed from hash(cell), which is
     randomised per Python process for str elements, so its control is not reproducible).
Run: python lowest_low_time_results/verify_lowest_low_time.py
"""
import sys
from itertools import product
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
from numpy.lib.stride_tricks import sliding_window_view as swv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy

OUT = Path(__file__).resolve().parent
START, END = np.datetime64('2000-01-01'), np.datetime64('2025-08-15')
COST_B = .009
SEEDS = 20
D = {}  # global data, filled in main before fork


def load():
    st, _ = engine.load_data('stocks')
    fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
    reg = regime_proxy(st)['regime']
    side = pd.DatetimeIndex(reg.index[reg == 'sideways'])
    cal = pd.DatetimeIndex(sorted(st['Date/Time'].unique()))
    data = {}
    for t, f in fr.items():
        dt = pd.DatetimeIndex(f['Date/Time'])
        elig = pd.DatetimeIndex(sorted(pit[t] & stale[t]))
        a = dict(o=f.Open.to_numpy(float), h=f.High.to_numpy(float), l=f.Low.to_numpy(float), c=f.Close.to_numpy(float),
                 d=dt.values, tr=f.tradable.to_numpy(bool),
                 ok=dt.isin(elig) & (dt.values >= START) & (dt.values <= END), side=dt.isin(side))
        data[t] = a
    return data, cal


def low_flags(l, N, strict):
    n = len(l)
    flag = np.zeros(n, bool)
    if n > N:
        prior = swv(l, N)[:-1].min(axis=1)  # prior[k] = min(l[k..k+N-1]) is the prior window of bar k+N
        flag[N:] = (l[N:] < prior) if strict else (l[N:] <= prior)
    return flag


def sim(t, cell, strict_low=False, rule='code', high_src='high', tie_new=False, exit_mode='next_open',
        allbars=False, seed=None, on_censor='break'):
    """Trades of one ticker. Returns (list of trades, n_censored)."""
    N, x, filt, entry = cell
    a = D['data'][t]
    tr = a['tr']
    if tr.sum() < 300:
        return [], 0
    sel = np.ones(len(tr), bool) if allbars else tr
    o, h, l, c, d, ok, side, trs = (a[k][sel] for k in ['o', 'h', 'l', 'c', 'd', 'ok', 'side', 'tr'])
    n = len(o)
    low = low_flags(l, N, strict_low)
    ar = np.arange(n)
    lastlow = np.maximum.accumulate(np.where(low, ar, -1))
    since = np.where(lastlow >= 0, ar - lastlow, -1)
    elig = ok & side if filt == 'sideways' else ok.copy()
    sig = (since == x) & elig
    if seed is not None:
        rng = np.random.default_rng(seed)
        pool = np.flatnonzero(elig)
        k = int(sig.sum())
        sig = np.zeros(n, bool)
        if k and len(pool):
            sig[rng.choice(pool, min(k, len(pool)), replace=False)] = True
    nxt_tr = np.r_[np.minimum.accumulate(np.where(trs, ar, n)[::-1])[::-1], n]  # first tradable index >= i
    hs = h if high_src == 'high' else c
    out, cens = [], 0
    busy, post = -1, -1
    for tt in np.flatnonzero(sig):
        if tt <= busy:
            continue
        if rule == 'plan' and seed is None and tt - x < post:  # the N-bar low must be on/after the exit fill
            continue
        if entry == 'next_open':
            e = nxt_tr[tt + 1] if tt + 1 < n else n
            if e >= n:
                continue
            e_px, hi = o[e], (h[e] if high_src == 'high' else c[e])
        else:
            if not trs[tt]:
                continue
            e, e_px, hi = tt, c[tt], c[tt]
        last, j, xi = e, e + 1, None
        while j < n:
            v = hs[j]
            if v > hi or (tie_new and v >= hi):
                hi, last = max(hi, v), j
            if j - last >= x:
                if exit_mode == 'next_open':
                    f_ = nxt_tr[j + 1] if j + 1 < n else n
                    if f_ < n:
                        xi, xpx, post_ = f_, o[f_], f_
                else:  # close of the x-th bar without a new high
                    f_ = nxt_tr[j]
                    if f_ < n:
                        xi, xpx, post_ = f_, c[f_], f_ + 1
                break
            j += 1
        if xi is None:
            cens += 1
            if on_censor == 'break':
                break
            continue
        out.append((t, d[tt], d[xi], np.log(xpx / e_px), xi - e))
        busy, post = xi, post_
    return out, cens


def run(args):
    cell, kw = args
    rows, cens = [], 0
    for t in D['data']:
        r, cz = sim(t, cell, **kw)
        rows += r
        cens += cz
    T = pd.DataFrame(rows, columns=['ticker', 'signal', 'exit', 'gross', 'bars'])
    return T, cens


def stats(T):
    cal = D['cal']
    cal = cal[(cal >= START) & (cal <= END)]
    net = T.gross - COST_B
    daily = net.groupby(T.signal).mean().reindex(cal)
    m, se, _ = nw(daily.values, 20)
    g = T.gross
    return dict(trades=len(T), gross_pct=g.mean() * 100, netB_event_pct=net.mean() * 100, netB_daily_pct=m * 100,
                t_nw=m / se, win_rate_netB=(net > 0).mean(), win_rate_gross=(g > 0).mean(),
                avg_win_gross_pct=g[g > 0].mean() * 100, avg_loss_gross_pct=g[g <= 0].mean() * 100,
                avg_win_net_pct=net[net > 0].mean() * 100, avg_loss_net_pct=net[net <= 0].mean() * 100,
                avg_bars=T.bars.mean())


def control(pool, cell, kw, seeds=SEEDS):
    res = pool.map(run, [(cell, dict(kw, seed=1000 + s)) for s in range(seeds)])
    S = pd.DataFrame([stats(T) for T, _ in res])
    return S


def fmt(d, keys=('trades', 'gross_pct', 'netB_event_pct', 'netB_daily_pct', 't_nw', 'win_rate_netB', 'avg_bars')):
    return '  '.join(f'{k}={d[k]:.3f}' if isinstance(d[k], float) else f'{k}={d[k]}' for k in keys)


def main():
    D['data'], D['cal'] = load()
    pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200); pd.set_option('display.max_columns', 40)
    R = pd.read_csv(OUT / 'results.csv')
    TR = pd.read_csv(OUT / 'trades.csv', parse_dates=['signal', 'exit'])
    cells3 = [(20, 5, 'none', 'next_open'), (10, 10, 'none', 'close'), (20, 10, 'sideways', 'next_open')]
    best2 = [(10, 10, 'none', 'close'), (10, 10, 'none', 'next_open')]
    with Pool(4) as pool:
        # ---------- 1. reproduce ----------
        print('=== 1. Reproduction (full period 2000-01-01..2025-08-15) ===')
        res = pool.map(run, [(c, {}) for c in cells3])
        for cell, (T, cz) in zip(cells3, res):
            s = stats(T)
            r = R[(R.N == cell[0]) & (R.x == cell[1]) & (R['filter'] == cell[2]) & (R.entry == cell[3]) & (R.kind == 'signal') & (R.period == '2000-25')].iloc[0]
            print(cell, 'censored-at-end:', cz)
            print('  verify :', fmt(s), f"avg_win_g={s['avg_win_gross_pct']:.2f} avg_loss_g={s['avg_loss_gross_pct']:.2f}")
            print('  results:', f"trades={r.trades} gross_pct={r.gross_pct:.3f} netB_event_pct={r.net_B_event_pct:.3f} "
                  f"netB_daily_pct={r.net_B_pct:.3f} t_nw={r.t_net_B:.3f} win_rate_netB={r.win_rate_B:.3f} avg_bars={r.avg_bars:.3f} "
                  f"avg_win_g={r.avg_win_pct:.2f} avg_loss_g={r.avg_loss_pct:.2f}")
            orig = TR[TR.cell == str(cell)][['ticker', 'signal', 'exit', 'gross', 'bars']].reset_index(drop=True)
            mine = T.assign(signal=pd.to_datetime(T.signal), exit=pd.to_datetime(T.exit)).reset_index(drop=True)
            m = orig.merge(mine, on=['ticker', 'signal'], how='outer', suffixes=('_o', '_v'), indicator=True)
            both = m[m._merge == 'both']
            print(f"  trade match vs trades.csv: only_orig={(m._merge == 'left_only').sum()} only_verify={(m._merge == 'right_only').sum()} "
                  f"exit_diff={(both.exit_o != both.exit_v).sum()} max|gross diff|={np.abs(both.gross_o - both.gross_v).max():.2e}")
        if 'quick' in sys.argv:
            return
        # ---------- 2. rule audit ----------
        print('\n=== 2. Rule-audit variants (signal; random control = mean of', SEEDS, 'seeds with the same variant) ===')
        variants = {'baseline(code)': {}, 'no_break_on_censor': dict(on_censor='continue'), 'strict_low(<)': dict(strict_low=True),
                    'plan_rule(new low after exit)': dict(rule='plan'), 'x_on_all_bars(incl zero-vol)': dict(allbars=True),
                    'tie_extends_trade_high(>=)': dict(tie_new=True)}
        rows = []
        for cell in cells3 + [best2[1]]:
            for vn, kw in variants.items():
                T, cz = run((cell, kw))
                s = stats(T)
                C = control(pool, cell, {k: v for k, v in kw.items() if k != 'rule'}, seeds=SEEDS if vn != 'no_break_on_censor' else 5)
                rows.append(dict(cell=str(cell), variant=vn, censored=cz, **{k: s[k] for k in ['trades', 'gross_pct', 'netB_event_pct', 'netB_daily_pct', 't_nw', 'win_rate_netB', 'avg_bars']},
                                 ctl_gross_mean=C.gross_pct.mean(), ctl_gross_sd=C.gross_pct.std(), ctl_netB_daily=C.netB_daily_pct.mean(),
                                 sig_minus_ctl_gross=s['gross_pct'] - C.gross_pct.mean(), z_vs_ctl_seeds=(s['gross_pct'] - C.gross_pct.mean()) / C.gross_pct.std()))
        A = pd.DataFrame(rows)
        print(A.round(3).to_string(index=False))
        # ---------- 3. alternative exit readings ----------
        print('\n=== 3. Alternative exit readings on the two best cells ===')
        alts = {'baseline: High trade-high, next Open': {}, 'trade-high on Close, next Open': dict(high_src='close'),
                'High trade-high, exit at Close of x-th bar': dict(exit_mode='close'),
                'Close trade-high, exit at Close of x-th bar': dict(high_src='close', exit_mode='close')}
        rows = []
        for cell in best2:
            for an, kw in alts.items():
                T, cz = run((cell, kw))
                s = stats(T)
                C = control(pool, cell, kw)
                sub = {}
                for pn, (a_, b_) in {'2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
                                     '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}.items():
                    z = T[(T.signal >= np.datetime64(a_)) & (T.signal <= np.datetime64(b_))]
                    sub[pn] = (z.gross - COST_B).mean() * 100
                rows.append(dict(cell=str(cell), reading=an, **{k: s[k] for k in ['trades', 'gross_pct', 'netB_event_pct', 'netB_daily_pct', 't_nw', 'win_rate_netB', 'avg_win_gross_pct', 'avg_loss_gross_pct', 'avg_bars']},
                                 ctl_gross_mean=C.gross_pct.mean(), ctl_gross_sd=C.gross_pct.std(), ctl_netB_daily=C.netB_daily_pct.mean(),
                                 **{f'netB_ev_{k}': v for k, v in sub.items()}))
        print(pd.DataFrame(rows).round(3).to_string(index=False))
        # ---------- 4. multi-seed control on all 36 cells ----------
        print('\n=== 4. All 36 cells: signal vs', SEEDS, '-seed random control (same stock, same signal count, same eligible/regime days, same exit) ===')
        grid = list(product([10, 20, 60], [3, 5, 10], ['sideways', 'none'], ['next_open', 'close']))
        sres = pool.map(run, [(c, {}) for c in grid])
        rows = []
        for cell, (T, _) in zip(grid, sres):
            s = stats(T)
            C = control(pool, cell, {})
            r = R[(R.N == cell[0]) & (R.x == cell[1]) & (R['filter'] == cell[2]) & (R.entry == cell[3]) & (R.period == '2000-25')]
            rows.append(dict(N=cell[0], x=cell[1], filter=cell[2], entry=cell[3], trades=s['trades'], gross=s['gross_pct'], netB_daily=s['netB_daily_pct'], t=s['t_nw'],
                             win_netB=s['win_rate_netB'], avg_win_g=s['avg_win_gross_pct'], avg_loss_g=s['avg_loss_gross_pct'],
                             ctl_trades=C.trades.mean(), ctl_gross=C.gross_pct.mean(), ctl_sd=C.gross_pct.std(), z=(s['gross_pct'] - C.gross_pct.mean()) / C.gross_pct.std(),
                             ctl_netB_daily=C.netB_daily_pct.mean(), ctl_netB_daily_sd=C.netB_daily_pct.std(),
                             z_daily=(s['netB_daily_pct'] - C.netB_daily_pct.mean()) / np.hypot(abs(s['netB_daily_pct'] / s['t_nw']), C.netB_daily_pct.std()),
                             win_gross=s['win_rate_gross'], avg_win_net=s['avg_win_net_pct'], avg_loss_net=s['avg_loss_net_pct'],
                             res_netB=r[r.kind == 'signal'].net_B_pct.iloc[0], res_ctl_netB=r[r.kind == 'random_control'].net_B_pct.iloc[0]))
        F = pd.DataFrame(rows)
        print(F.round(3).to_string(index=False))
        print(f"\ncells with net B daily > 0: {(F.netB_daily > 0).sum()} / 36; gross range {F.gross.min():.3f}..{F.gross.max():.3f}")
        print(f"cells signal gross > control mean: {(F.gross > F.ctl_gross).sum()} / 36; |z|>2: {(F.z.abs() > 2).sum()} (z>2: {(F.z > 2).sum()}, z<-2: {(F.z < -2).sum()})")
        print(f"mean z {F.z.mean():.2f}; by N: {F.groupby('N').z.mean().round(2).to_dict()}; by x: {F.groupby('x').z.mean().round(2).to_dict()}")
        print(f"z_daily (signal minus control on mean-of-daily-means net B, signal NW se and control seed sd combined): range {F.z_daily.min():.2f}..{F.z_daily.max():.2f}; cells z_daily>2: {(F.z_daily > 2).sum()}, <-2: {(F.z_daily < -2).sum()}")
        print(f"signal daily net B above 20-seed control mean: {(F.netB_daily > F.ctl_netB_daily).sum()} / 36; results.csv single-seed control vs 20-seed mean max |diff| {np.abs(F.res_ctl_netB - F.ctl_netB_daily).max():.3f}")
        print(f"win rate gross range {F.win_gross.min():.3f}..{F.win_gross.max():.3f}; avg win/loss split by net B: {F.avg_win_net.min():.2f}..{F.avg_win_net.max():.2f} / {F.avg_loss_net.min():.2f}..{F.avg_loss_net.max():.2f}")
        print(f"win rate netB range {F.win_netB.min():.3f}..{F.win_netB.max():.3f}; avg win gross {F.avg_win_g.min():.2f}..{F.avg_win_g.max():.2f}; avg loss gross {F.avg_loss_g.min():.2f}..{F.avg_loss_g.max():.2f}")


if __name__ == '__main__':
    main()
