"""Classic mean-reversion indicators as Logic 2 (plan: mr_indicator_grid_results/PLAN.md)."""
import sys, zlib
from itertools import product
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy

OUT = ROOT / 'mr_indicator_grid_results'
COST, COST_USER = .009, .006
SIG = ['S1 RSI14 < 30', 'S2 RSI14 back above 30', 'S3 RSI2 < 5', 'S4 RSI3 < 10', 'S5 Stoch < 20 cross up', 'S6 Close < lower BB',
       'S7 back above lower BB', 'S8 Williams %R < -90', 'S9 CCI back above -100', 'S10 IBS < 0.2', 'S11 z-score < -2', 'S12 MFI14 < 20']
ENTRY = ['next Open', 'limit Close - 0.5 ATR']
EXIT = ['Close > SMA5 (max 10)', 'Close > SMA20 (max 20)', 'time 5']
SCOPE = ['sideways', 'all days']
GRID = list(product(SIG, ENTRY, EXIT, SCOPE))
PER = {'2000-25': ('2000-01-01', '2025-08-15'), 'train 2000-15': ('2000-01-01', '2015-12-31'), 'test 2016-25': ('2016-01-01', '2025-08-15'),
       '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'), '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
G = {}


def rsi(C, n):
    dl = C.diff(); up = dl.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def cross_up(x, level):
    return (x > level) & (x.shift(1) <= level)


def prep(t):
    f = G['fr'][t]; f = f[f.tradable].reset_index(drop=True)
    o, h, l, c, v = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close', 'Volume']); d = f['Date/Time'].to_numpy()
    C, H, L, V = pd.Series(c), pd.Series(h), pd.Series(l), pd.Series(v)
    r14 = rsi(C, 14)
    k14 = 100 * (C - L.rolling(14).min()) / (H.rolling(14).max() - L.rolling(14).min()); d3 = k14.rolling(3).mean()
    m20, s20 = C.rolling(20).mean(), C.rolling(20).std(ddof=0); lower = m20 - 2 * s20
    tp = (H + L + C) / 3; mad = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True); cci = (tp - tp.rolling(20).mean()) / (.015 * mad)
    m10, s10 = C.rolling(10).mean(), C.rolling(10).std(ddof=0)
    mf = tp * V; pos = mf.where(tp > tp.shift(1), 0.).rolling(14).sum(); neg = mf.where(tp < tp.shift(1), 0.).rolling(14).sum(); mfi = 100 - 100 / (1 + pos / neg)
    sig = {SIG[0]: r14 < 30, SIG[1]: cross_up(r14, 30), SIG[2]: rsi(C, 2) < 5, SIG[3]: rsi(C, 3) < 10,
           SIG[4]: (k14 < 20) & (k14 > d3) & (k14.shift(1) <= d3.shift(1)), SIG[5]: C < lower, SIG[6]: (C > lower) & (C.shift(1) <= lower.shift(1)),
           SIG[7]: k14 < 10, SIG[8]: (cci > -100) & (cci.shift(1) <= -100), SIG[9]: (H > L) & ((C - L) / (H - L) < .2),
           SIG[10]: (C - m10) / s10 < -2, SIG[11]: mfi < 20}
    sig = {k: x.fillna(False).to_numpy(bool) for k, x in sig.items()}
    tr = pd.concat([H - L, (H - C.shift()).abs(), (L - C.shift()).abs()], axis=1).max(axis=1); atr = tr.rolling(14).mean().to_numpy()
    nd = pd.DatetimeIndex(d[1:])
    elig = np.zeros(len(c), bool)
    elig[:-1] = np.isin(d[1:], G['ok'][t]) & (d[1:] >= np.datetime64('2000-01-01')) & (d[1:] <= np.datetime64('2025-08-15'))
    elig &= np.isfinite(atr) & np.isfinite(m20.to_numpy())
    side = np.zeros(len(c), bool); side[:-1] = G['lab'].reindex(nd).to_numpy() == 'sideways'
    return dict(o=o, h=h, l=l, c=c, d=d, atr=atr, sma5=C.rolling(5).mean().to_numpy(), sma20=m20.to_numpy(), sig=sig,
                base={'sideways': elig & side, 'all days': elig})


def sim(cell, seed=None, counts=None):
    sg, en, ex, sc = cell
    tmax = 10 if 'SMA5' in ex else (20 if 'SMA20' in ex else 5)
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t in G['fr']:
        P = G['cache'][t]; o, l, c, d = P['o'], P['l'], P['c'], P['d']; n = len(c); base = P['base'][sc]
        if rng is None:
            ks = np.flatnonzero(base & P['sig'][sg])
        else:
            pool = np.flatnonzero(base); k_ = counts.get(t, 0)
            ks = np.sort(rng.choice(pool, min(k_, len(pool)), replace=False)) if k_ and len(pool) else np.array([], int)
        busy = -1
        for k in ks:
            i = k + 1
            if i <= busy or i + tmax >= n:
                continue
            if en == 'next Open':
                e = o[i]
            else:
                lim = c[k] - .5 * P['atr'][k]
                if not l[i] < lim:
                    continue
                e = min(o[i], lim)
            for j in range(i, i + tmax):
                if 'SMA5' in ex and c[j] > P['sma5'][j]:
                    px, je = o[j + 1], j + 1; break
                if 'SMA20' in ex and c[j] > P['sma20'][j]:
                    px, je = o[j + 1], j + 1; break
                if j == i + tmax - 1:
                    px, je = c[j], j; break
            out.append((t, d[i], np.log(px / e), je - i + 1))
            busy = je
    T = pd.DataFrame(out, columns=['ticker', 'entry', 'gross', 'bars']); T['net_B'] = T.gross - COST
    return T


def run_cell(cell):
    T = sim(cell); counts = T.groupby('ticker').size().to_dict()
    C = pd.concat([sim(cell, zlib.crc32(f'{cell}-{s}'.encode()), counts) for s in range(5)])
    rows = []
    for pn, (a, b) in PER.items():
        x = T[(T.entry >= np.datetime64(a)) & (T.entry <= np.datetime64(b))]; y = C[(C.entry >= np.datetime64(a)) & (C.entry <= np.datetime64(b))]
        base = dict(signal=cell[0], entry=cell[1], exit=cell[2], scope=cell[3], period=pn, trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25))
        if len(x) < 5:
            rows.append(base); continue
        dd = x.groupby('entry').net_B.mean().reindex(G['cal'].loc[a:b].index); m, se, _ = nw(dd.to_numpy(), 10)
        wn = x.net_B > 0; aw, al = x.gross[wn].mean(), x.gross[~wn].mean()
        rows.append(dict(base, win_rate=wn.mean(), breakeven_wr=(-al + COST) / (aw - al) if wn.any() and (~wn).any() else np.nan, avg_win_pct=aw * 100,
                         avg_loss_pct=al * 100, gross_pct=x.gross.mean() * 100, net_B_pct=m * 100, t=m / se if se else np.nan,
                         net_user_fee_pct=(x.gross.mean() - COST_USER) * 100, control_net_pct=y.net_B.mean() * 100 if len(y) else np.nan))
    return rows


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
    G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['lab'] = regime_proxy(st)['regime']
    with np.errstate(invalid='ignore', divide='ignore'):
        G['cache'] = {t: prep(t) for t in G['fr']}
        with Pool(4) as p:
            D = pd.DataFrame([r for rows in p.map(run_cell, GRID, chunksize=4) for r in rows])
    D.to_csv(OUT / 'results_all.csv', index=False)
    key = ['signal', 'entry', 'exit', 'scope']
    full = D[D.period == '2000-25'].set_index(key); tr = D[D.period == 'train 2000-15'].set_index(key); te = D[D.period == 'test 2016-25'].set_index(key)
    subs = D[D.period.isin(['2000-07', '2008-15', '2016-20', '2021-25'])].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum()))
    S = full[['trades_per_year', 'win_rate', 'breakeven_wr', 'avg_win_pct', 'avg_loss_pct', 'gross_pct', 'net_B_pct', 't', 'net_user_fee_pct', 'control_net_pct']].join(
        tr[['trades_per_year', 'net_B_pct', 't']].add_prefix('train_')).join(te[['net_B_pct', 't', 'control_net_pct']].add_prefix('test_')).join(subs.rename('subperiods_positive'))
    S.to_csv(OUT / 'summary.csv')
    side = tr.xs('sideways', level='scope'); elig = side[side.trades_per_year >= 10]
    pk = elig.net_B_pct.idxmax(); pick = pk + ('sideways',); r = te.loc[pick]
    okp = r.net_B_pct > 0 and r.t >= 2 and r.net_B_pct > r.control_net_pct and subs.loc[pick] >= 3
    pd.set_option('display.width', 300); pd.set_option('display.max_rows', 300)
    print(S.sort_values('train_net_B_pct', ascending=False).head(20).round(2).to_string())
    for sc in SCOPE:
        x = S.xs(sc, level='scope')
        print(sc, '| cells', len(x), '| full net > 0:', int((x.net_B_pct > 0).sum()), '| train net > 0:', int((x.train_net_B_pct > 0).sum()),
              '| test net > 0 & t >= 2:', int(((x.test_net_B_pct > 0) & (x.test_t >= 2)).sum()), '| gross > 0:', int((x.gross_pct > 0).sum()),
              '| above control:', int((x.net_B_pct > x.control_net_pct).sum()), '| mean signal - control pp: %.2f' % (x.net_B_pct - x.control_net_pct).mean())
    print('PICK (train, sideways):', pick, '| test net %.2f%% t %.2f control %.2f%% | subperiods %d | PASSES: %s' % (r.net_B_pct, r.t, r.control_net_pct, subs.loc[pick], okp))
