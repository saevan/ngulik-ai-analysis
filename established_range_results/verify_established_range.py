"""Independent verifier for established_range.py (does NOT import it).

Part 1 recomputes three pre-registered cells for 'established' and 'not established':
  (40, .25, 2, close, stock_er), (40, .25, 3, close, stock_er), (60, .2, 2, limit, market)
  -> trades, gross mean, mean-of-daily-means net B (0.90%) with Newey-West t (lags 20), share target / stop exits,
     and the 20-seed random control (incl. how many control trades actually survive per cell).
Part 2 audits: both-zone bars, close-entry profit room, limit entry-bar stop, persistence sample size,
     breakdown/bounce shares by number of prior visits.
Part 3 (EXPLORATORY, not pre-registered) rescue attempts:
  (a) narrow range (R <= 6 ATR) or >= 3 full bottom->top swings, (b) bullish confirmation bar in the bottom zone,
  (c) take profit at range mid. Each compared with the not-established group under the same modification.
"""
import sys
import zlib
from pathlib import Path
import numpy as np, pandas as pd
from numpy.lib.stride_tricks import sliding_window_view as swv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw  # noqa: E402
import grid_search_timehunter as engine  # noqa: E402
import pit_universe as pu, pit_stale_liquidity as psl  # noqa: E402
from analyze_portfolio_regimes import regime_proxy  # noqa: E402

COST = .009
S0, S1 = np.datetime64('2000-01-01'), np.datetime64('2025-08-15')


def wilder_atr_prev(h, l, c, n=14):
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1)
    out = np.full(len(c), np.nan)
    if len(c) < n:
        return out
    a = tr[:n].mean()
    out[n - 1] = a
    for i in range(n, len(c)):
        a = a + (tr[i] - a) / n
        out[i] = a
    return np.r_[np.nan, out[:-1]]  # value usable at bar t = ATR through t-1


def prev_extreme(x, M, fn):
    """fn over bars t-M..t-1 (bar t excluded)."""
    out = np.full(len(x), np.nan)
    if len(x) > M:
        out[M:] = fn(swv(x, M), axis=1)[:len(x) - M]
    return out


def zone_stats(l, h, idx, M, bot, top):
    """Vectorised compressed zone-visit counts for candidate bars idx over window idx-M..idx-1.
    Returns nb, nt (visits), swings_up (bottom->top transitions), both (bars touching both zones)."""
    if len(idx) == 0:
        z = np.zeros(0, int)
        return z, z, z, z
    W_l = swv(l, M)[idx - M]
    W_h = swv(h, M)[idx - M]
    inb = W_l <= bot[idx, None]
    intp = W_h >= top[idx, None]
    both = (inb & intp).sum(1)
    lab = np.where(inb & ~intp, 1, np.where(intp & ~inb, 2, 0))
    valid = lab > 0
    pos = np.where(valid, np.arange(M)[None, :], -1)
    last = np.maximum.accumulate(pos, axis=1)              # last valid position up to and including k
    prevpos = np.c_[np.full((len(idx), 1), -1), last[:, :-1]]
    prevlab = np.where(prevpos >= 0, np.take_along_axis(lab, np.maximum(prevpos, 0), 1), 0)
    newv = valid & (lab != prevlab)
    nb = (newv & (lab == 1)).sum(1)
    nt = (newv & (lab == 2)).sum(1)
    sw = (newv & (lab == 2) & (prevlab == 1)).sum(1)
    return nb, nt, sw, both


def walk(i, epx, tgt, stop, o, h, c, n, stop_on_entry_bar=False):
    """Exit: TP limit (High >= tgt, fill max(Open,tgt)) checked before the close stop (Close < stop -> next Open);
    time stop Close of bar i+20. Returns (exit_bar, price, reason) or None at end of data."""
    if stop_on_entry_bar and c[i] < stop and i + 1 < n:
        return i + 1, o[i + 1], 'stop'
    for j in range(i + 1, i + 21):
        if j >= n:
            return None
        if h[j] >= tgt:
            return j, max(o[j], tgt), 'target'
        if c[j] < stop and j + 1 < n:
            return j + 1, o[j + 1], 'stop'
    return i + 20, c[i + 20], 'time'


class Stock:
    def __init__(self, t, f, okdates, side):
        f = f[f.tradable].reset_index(drop=True)
        self.t, self.n = t, len(f)
        self.o, self.h, self.l, self.c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close'])
        self.d = f['Date/Time'].to_numpy('datetime64[ns]')
        self.A = wilder_atr_prev(self.h, self.l, self.c)
        c = self.c
        net = np.abs(c[20:] - c[:-20])
        path = np.convolve(np.abs(np.diff(c)), np.ones(20), 'valid')
        er = np.full(self.n, np.nan)
        er[20:] = net / path
        self.er_prev = np.r_[np.nan, er[:-1]]
        self.base = np.isin(self.d, okdates) & (self.d >= S0) & (self.d <= S1)
        self.mkt_side = np.isin(self.d, side)
        self.cache = {}

    def rng_(self, M, z):
        k = (M, z)
        if k not in self.cache:
            U = prev_extreme(self.h, M, np.max)
            D = prev_extreme(self.l, M, np.min)
            R = U - D
            self.cache[k] = dict(U=U, D=D, R=R, bot=D + z * R, top=U - z * R, mid=D + .5 * R)
        return self.cache[k]


def simulate(stocks, M, z, nmin, entry, side, mode, var=None, seed=None, counts=None, audit=None):
    """mode: established / not_established / pooled / control. var: dict of exploratory modifications."""
    var = var or {}
    rows = []
    rng = np.random.default_rng(seed) if seed is not None else None
    for s in stocks:
        if s.n < 300:
            continue
        g = s.rng_(M, z)
        U, D, R, bot, top, mid = g['U'], g['D'], g['R'], g['bot'], g['top'], g['mid']
        o, h, l, c, A = s.o, s.h, s.l, s.c, s.A
        with np.errstate(invalid='ignore', divide='ignore'):
            ok = s.base & np.isfinite(R) & (R > 0) & np.isfinite(A) & (top / bot - 1 >= .03)
            ok &= (s.er_prev < .3) if side == 'stock_er' else s.mkt_side
            stopv = D - .5 * A
            if mode == 'control':
                pool = np.flatnonzero(ok & (c <= D + .5 * R) & (c >= stopv))
                k = counts.get(s.t, 0)
                cand = np.sort(rng.choice(pool, min(k, len(pool)), replace=False)) if k and len(pool) else np.zeros(0, int)
            else:
                if entry == 'limit':
                    sig = ok & (l < bot)          # no use of Close[t] for the limit entry
                else:
                    sig = ok & (l <= bot) & (c >= stopv)
                if var.get('confirm'):
                    sig &= (c > o) & (c >= (h + l) / 2)
                    if var.get('confirm') == 'in_zone':
                        sig &= c <= bot
                if var.get('narrow'):
                    sig &= R <= var['narrow'] * A
                if var.get('room_vs_entry') and entry == 'close':
                    tg = mid if var.get('target') == 'mid' else top
                    sig &= tg / c - 1 >= .03
                idx = np.flatnonzero(sig)
                nb, nt, sw, both = zone_stats(l, h, idx, M, bot, top)
                est = (nb >= nmin) & (nt >= nmin)
                if var.get('swings'):
                    est = sw >= var['swings']
                if audit is not None:
                    audit.setdefault('both_zone_windows', 0)
                    audit['both_zone_windows'] += int((both > 0).sum())
                    audit.setdefault('cand_windows', 0)
                    audit['cand_windows'] += len(idx)
                if mode == 'established':
                    cand = idx[est]
                elif mode == 'not_established':
                    cand = idx[~est]
                else:
                    cand = idx
                nbmap = dict(zip(idx, nb))
        busy = -1
        for i in cand:
            if i <= busy or i + 1 >= s.n:
                continue
            if entry == 'limit' and mode != 'control':
                epx = min(o[i], bot[i])
            else:
                epx = c[i]
            tgt = mid[i] if var.get('target') == 'mid' else top[i]
            res = walk(i, epx, tgt, stopv[i], o, h, c, s.n, stop_on_entry_bar=var.get('entry_bar_stop', False))
            if res is None:
                break
            rows.append((s.t, s.d[i], np.log(res[1] / epx), res[2], res[0] - i, epx, c[i], bot[i], top[i], stopv[i],
                         nbmap.get(i, -1) if mode != 'control' else -1, R[i] / A[i]))
            busy = res[0]
    T = pd.DataFrame(rows, columns=['ticker', 'signal', 'gross', 'reason', 'bars', 'epx', 'close_t', 'bot', 'top', 'stop', 'nb', 'R_atr'])
    T['net_B'] = T.gross - COST
    return T


def stats(T, cal):
    out = dict(trades=len(T), gross_pct=np.nan, net_B_pct=np.nan, t_net_B=np.nan, share_target=np.nan, share_stop=np.nan)
    if len(T) == 0:
        return out
    daily = T.groupby('signal').net_B.mean().reindex(cal)
    m, se, _ = nw(daily.values, 20)
    out.update(gross_pct=T.gross.mean() * 100, net_B_pct=m * 100, t_net_B=m / se if se else np.nan,
               share_target=(T.reason == 'target').mean(), share_stop=(T.reason == 'stop').mean(),
               share_time=(T.reason == 'time').mean())
    return out


def main():
    pd.set_option('display.width', 250)
    pd.set_option('display.max_columns', 40)
    st, _ = engine.load_data('stocks')
    fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
    okd = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in fr}
    reg = regime_proxy(st)['regime']
    side = np.array(reg.index[reg == 'sideways'], dtype='datetime64[ns]')
    cal = pd.DatetimeIndex(sorted(st['Date/Time'].unique()))
    cal = cal[(cal >= pd.Timestamp('2000-01-01')) & (cal <= pd.Timestamp('2025-08-15'))]
    stocks = [Stock(t, f, okd[t], side) for t, f in fr.items()]

    ref = pd.read_csv(Path(__file__).parent / 'results_all.csv')
    ref = ref[ref.period == '2000-25']
    refm = pd.read_csv(Path(__file__).parent / 'results.csv')

    print('=== PART 1: recompute of three cells (full period 2000-01-01..2025-08-15) ===')
    cells = [(40, .25, 2, 'close', 'stock_er'), (40, .25, 3, 'close', 'stock_er'), (60, .2, 2, 'limit', 'market')]
    rows = []
    keep = {}
    for cell in cells:
        audit = {}
        for mode in ['established', 'not_established']:
            T = simulate(stocks, *cell, mode, audit=audit if mode == 'established' else None)
            keep[(cell, mode)] = T
            r = dict(M=cell[0], z=cell[1], n=cell[2], entry=cell[3], sideways=cell[4], mode=mode, **stats(T, cal))
            q = ref[(ref.M == cell[0]) & np.isclose(ref.z, cell[1]) & (ref.n == cell[2]) & (ref.entry == cell[3]) &
                    (ref.sideways == cell[4]) & (ref['mode'] == mode)].iloc[0]
            r.update(ref_trades=q.trades, ref_gross=q.gross_pct, ref_netB=q.net_B_pct, ref_t=q.t_net_B,
                     ref_tgt=q.share_target, ref_stop=q.share_stop)
            rows.append(r)
        # control exactly as specified: counts per ticker from the established trades of THIS cell
        E = keep[(cell, 'established')]
        counts = E.groupby('ticker').size().to_dict()
        cg, cn, cg_lim = [], [], []
        for sd in range(20):
            C = simulate(stocks, *cell, 'control', seed=zlib.crc32(f'{cell}-{sd}'.encode()), counts=counts)
            cg.append(C.gross.mean())
            cn.append(len(C))
        qref = refm[(refm.M == cell[0]) & np.isclose(refm.z, cell[1]) & (refm.n == cell[2]) & (refm.entry == cell[3]) & (refm.sideways == cell[4])].iloc[0]
        rows[-2].update(control_gross=np.mean(cg) * 100, control_trades_mean=np.mean(cn), ref_control=qref.control20_gross_pct)
        # fairer control: same entry rule (incl. limit), random sample of ALL touches (any history), matched count
        P = simulate(stocks, *cell, 'pooled')
        rows[-2].update(pooled_all_touches_gross=P.gross.mean() * 100, pooled_trades=len(P))
        print(f'{cell}: both-zone bars present in {audit["both_zone_windows"]} of {audit["cand_windows"]} candidate windows')
    R1 = pd.DataFrame(rows)
    print(R1.round(3).to_string(index=False))

    print('\n=== PART 2: audits ===')
    E = keep[(cells[0], 'established')]
    room = E.top / E.close_t - 1
    print('close entry (40,.25,2): share close above bottom-zone edge', round((E.close_t > E.bot).mean(), 3),
          '| share with actual room to target < 3%:', round((room < .03).mean(), 3),
          '| gross of those', round(E.gross[room < .03].mean() * 100, 3), '% vs room>=3%', round(E.gross[room >= .03].mean() * 100, 3), '%')
    L = keep[(cells[2], 'established')]
    print('limit (60,.2,2,market): share entries whose entry-bar Close < stop', round((L.close_t < L.stop).mean(), 3),
          '| gross of those', round(L.gross[L.close_t < L.stop].mean() * 100, 3), '%')
    Lb = simulate(stocks, *cells[2], 'established', var=dict(entry_bar_stop=True))
    Lbn = simulate(stocks, *cells[2], 'not_established', var=dict(entry_bar_stop=True))
    print('limit (60,.2,2,market) with stop also checked at entry-bar close: est', stats(Lb, cal), '\n   not-est', stats(Lbn, cal))
    # breakdown vs bounce by prior visit count (pooled touches, close entry, stock_er)
    print('\nOutcome by prior bottom visits nb (pooled close touches, stock_er, gross % / share target / share stop):')
    for M, z in [(40, .25), (60, .2)]:
        P = simulate(stocks, M, z, 2, 'close', 'stock_er', 'pooled')
        P['nbk'] = P.nb.clip(upper=4)
        print(M, z)
        print(P.groupby('nbk').agg(trades=('gross', 'size'), gross_pct=('gross', lambda x: x.mean() * 100),
                                    tgt=('reason', lambda x: (x == 'target').mean()), stop=('reason', lambda x: (x == 'stop').mean()),
                                    time=('reason', lambda x: (x == 'time').mean()), R_atr=('R_atr', 'median')).round(3).to_string())
    # persistence sample size
    tr = pd.read_csv(Path(__file__).parent / 'trades_established.csv', parse_dates=['signal'])
    tr = tr[tr.cell == str((40, .25, 2, 'close', 'stock_er'))]
    tr['year'] = tr.signal.dt.year
    gy = tr.groupby(['ticker', 'year']).size()
    q = gy[gy >= 3].reset_index()
    by = {y: set(g.ticker) for y, g in q.groupby('year')}
    usable = {y: len(by[y] & by.get(y + 1, set())) for y in by if len(by[y] & by.get(y + 1, set())) >= 8}
    print('\npersistence: ticker-years with >=3 trades:', len(q), 'of', len(gy), '; usable year pairs (>=8 common stocks):', usable)

    print('\n=== PART 3: EXPLORATORY rescue attempts (not pre-registered; stock_er sideways unless noted) ===')
    variants = {
        'base': {},
        'a1_narrow_R<=6ATR': dict(narrow=6),
        'a2_swings>=3': dict(swings=3),
        'b_confirm_bar': dict(confirm='bar'),
        'b_confirm_close_in_zone': dict(confirm='in_zone'),
        'c_tp_mid': dict(target='mid'),
        'c_tp_mid_room3_vs_entry': dict(target='mid', room_vs_entry=True),
        'a1+b+c': dict(narrow=6, confirm='bar', target='mid'),
        'a2+b+c': dict(swings=3, confirm='bar', target='mid'),
    }
    rows = []
    for M in [40, 60]:
        for z in [.2, .25]:
            for nmin in [2, 3]:
                for entry in ['close', 'limit']:
                    for vn, v in variants.items():
                        if entry == 'limit' and (v.get('confirm') or v.get('room_vs_entry')):
                            continue
                        if v.get('swings') and nmin == 3:
                            continue  # swings variant replaces the n rule; run it once per (M,z,entry)
                        E = simulate(stocks, M, z, nmin, entry, 'stock_er', 'established', var=v)
                        NE = simulate(stocks, M, z, nmin, entry, 'stock_er', 'not_established', var=v)
                        se, sn = stats(E, cal), stats(NE, cal)
                        rows.append(dict(M=M, z=z, n=nmin if not v.get('swings') else 'sw3', entry=entry, variant=vn,
                                         est_trades=se['trades'], est_gross=se['gross_pct'], est_netB=se['net_B_pct'], est_t=se['t_net_B'],
                                         est_tgt=se['share_target'], est_stop=se['share_stop'],
                                         ne_trades=sn['trades'], ne_gross=sn['gross_pct'], ne_netB=sn['net_B_pct']))
    X = pd.DataFrame(rows)
    X['gross_pos_and_above_ne'] = (X.est_gross > 0) & (X.est_gross > X.ne_gross)
    print(X.round(3).to_string(index=False))
    print('\nSummary by variant (median over cells):')
    print(X.groupby('variant')[['est_trades', 'est_gross', 'ne_gross', 'est_netB', 'est_t', 'est_tgt', 'est_stop']].median().round(3).to_string())
    print('\ncells where established gross > 0 and > not-established:', int(X.gross_pos_and_above_ne.sum()), 'of', len(X))
    print('cells where established net B > 0:', int((X.est_netB > 0).sum()))
    X.to_csv(Path(__file__).parent / 'verify_exploratory.csv', index=False)


if __name__ == '__main__':
    main()
