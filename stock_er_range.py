"""Stock-level ER range check (plan: stock_er_range_results/PLAN.md). Writes stock_er_range_results/*.csv"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy

OUT = ROOT / 'stock_er_range_results'
PER = {'2000-25': ('2000-01-01', '2025-08-15'), '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'),
       '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
state = regime_proxy(st)['regime'].shift(-1)          # market state at the Close of day t
cal = pd.DatetimeIndex(sorted(st['Date/Time'].unique()))
rng = np.random.default_rng(20261030)


def atr(h, l, c, n=14):
    tr = h - l
    tr[1:] = np.maximum(tr[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def cls(er):
    return np.where(er < .2, 'choppy <0.2', np.where(er < .3, 'mid 0.2-0.3', 'trending >=0.3'))


mov, fp, trades = [], [], []
for t, f in fr.items():
    f = f[f.tradable].reset_index(drop=True)
    n = len(f)
    if n < 300:
        continue
    o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close'])
    d = f['Date/Time'].to_numpy()
    A = atr(h.copy(), l, c)
    H = pd.Series(h).rolling(20).max().to_numpy()
    L = pd.Series(l).rolling(20).min().to_numpy()
    mid = (H + L) / 2
    cc = pd.Series(c)
    er = ((cc - cc.shift(20)).abs() / cc.diff().abs().rolling(20).sum()).to_numpy()
    ok = np.isin(d, np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]')) & (d >= np.datetime64('2000-01-01')) & \
         (d <= np.datetime64('2025-08-15')) & np.isfinite(er) & np.isfinite(H) & (A > 0)
    k_ = cls(np.nan_to_num(er))
    msd = (state.reindex(d).to_numpy() == 'sideways')
    ar = np.r_[np.nan, np.abs(np.diff(np.log(c)))]
    mov.append(pd.DataFrame({'cls': k_[ok], 'mkt_sideways': msd[ok], 'absret': ar[ok], 'atr_pct': (A / c)[ok]}))
    valid = np.arange(n) + 10 < n
    starts = np.flatnonzero(np.arange(n - 11) >= 1)
    for side in ('bottom', 'top'):
        ev = np.flatnonzero(ok & valid & ((c <= L + .25 * A) if side == 'bottom' else (c >= H - .25 * A)))
        if not len(ev):
            continue
        up_lvl = mid[ev] if side == 'bottom' else H[ev] + A[ev]          # level hit by rising prices
        dn_lvl = L[ev] - A[ev] if side == 'bottom' else mid[ev]          # level hit by falling prices
        idx = ev[:, None] + np.arange(1, 11)[None, :]
        HH, LL = h[idx], l[idx]
        def first(hh, ll, up, dn):
            hu, hd = hh >= up[:, None], ll <= dn[:, None]
            fu = np.where(hu.any(1), hu.argmax(1), 99)
            fd = np.where(hd.any(1), hd.argmax(1), 99)
            # same-bar double hit: adverse first (bottom: down is adverse; top: up is adverse)
            up_first = (fu < fd) if side == 'bottom' else (fu < fd) & False | (fu < fd)
            if side == 'bottom':
                mid_first = (fu < fd) & (fu < 99)
                adverse = (fd <= fu) & (fd < 99)
            else:
                mid_first = (fd < fu) & (fd < 99)
                adverse = (fu <= fd) & (fu < 99)
            return mid_first, adverse
        a_mid, a_adv = first(HH, LL, up_lvl, dn_lvl)
        s = rng.choice(starts, (len(ev), 20))
        rel_h = h[s[..., None] + np.arange(1, 11)] / c[s][..., None]
        rel_l = l[s[..., None] + np.arange(1, 11)] / c[s][..., None]
        bm, ba = [], []
        for b in range(20):
            m_, a_ = first(c[ev][:, None] * rel_h[:, b, :], c[ev][:, None] * rel_l[:, b, :], up_lvl, dn_lvl)
            bm.append(m_); ba.append(a_)
        fp.append(pd.DataFrame({'side': side, 'date': d[ev], 'cls': k_[ev], 'mkt_sideways': msd[ev], 'mid_first': a_mid, 'adverse_first': a_adv,
                                'boot_mid_first': np.mean(bm, 0), 'boot_adverse_first': np.mean(ba, 0)}))
    # trade on bottom touches
    busy = -1
    for i in np.flatnonzero(ok & valid & (c <= L + .25 * A)):
        if i <= busy:
            continue
        e, tgt, stp = i + 1, mid[i], L[i] - A[i]
        px, j_end = None, None
        for j in range(e, min(i + 11, n)):
            if h[j] >= tgt:
                px, j_end = max(o[j], tgt), j; break
            if c[j] < stp and j + 1 < n:
                px, j_end = o[j + 1], j + 1; break
            if j == i + 10:
                px, j_end = c[j], j
        if px is None:
            continue
        trades.append((t, d[i], k_[i], msd[i], np.log(px / o[e])))
        busy = j_end
M = pd.concat(mov)
Mv = M.groupby(['cls']).agg(abs_daily_ret=('absret', 'mean'), atr_pct=('atr_pct', 'mean'), share=('absret', 'size'))
Mv['share'] /= Mv.share.sum()
Mv.to_csv(OUT / 'movement.csv')
F = pd.concat(fp)
rows = []
for (side, k), x in F.groupby(['side', 'cls']):
    for scope, y in (('all days', x), ('market sideways', x[x.mkt_sideways])):
        dd = y.assign(ex=y.mid_first.astype(float) - y.boot_mid_first).groupby('date').ex.mean().reindex(cal[(cal >= '2000') & (cal <= '2025-08-15')])
        m, se, _ = nw(dd.to_numpy(), 10)
        rows.append(dict(side=side, cls=k, scope=scope, events=len(y), p_mid_first=y.mid_first.mean(), boot_p_mid_first=y.boot_mid_first.mean(),
                         p_adverse_first=y.adverse_first.mean(), boot_p_adverse_first=y.boot_adverse_first.mean(), excess_mid_pp=m * 100,
                         t=m / se if se else np.nan))
R = pd.DataFrame(rows)
R.to_csv(OUT / 'first_passage.csv', index=False)
T = pd.DataFrame(trades, columns=['ticker', 'signal', 'cls', 'mkt_sideways', 'gross'])
T['net_B'] = T.gross - .009
tr = []
for k, x in T.groupby('cls'):
    for pn, (a, b) in PER.items():
        y = x[(x.signal >= np.datetime64(a)) & (x.signal <= np.datetime64(b))]
        dd = y.groupby('signal').net_B.mean().reindex(cal[(cal >= a) & (cal <= b)])
        m, se, _ = nw(dd.to_numpy(), 10)
        tr.append(dict(cls=k, period=pn, trades=len(y), gross_pct=y.gross.mean() * 100, net_B_pct=m * 100, t=m / se if se else np.nan,
                       win_rate=(y.net_B > 0).mean(), sideways_only_net_pct=(y[y.mkt_sideways].net_B.mean() * 100)))
TR = pd.DataFrame(tr)
TR.to_csv(OUT / 'trades_by_class.csv', index=False)
pd.set_option('display.width', 220)
print(Mv.round(4).to_string()); print(R.round(3).to_string(index=False)); print(TR.round(2).to_string(index=False))
