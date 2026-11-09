"""Cross-sectional short-term reversal for sideways markets (plan: xs_reversal_results/PLAN.md)."""
import sys, zlib
from itertools import product
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy

OUT = ROOT / 'xs_reversal_results'
COST, K = .009, 5
GRID = list(product((1, 5, 10), (5, 10), ('next Open', 'limit Close - 0.5 ATR')))
PER = {'2000-25': ('2000-01-01', '2025-08-15'), 'train 2000-15': ('2000-01-01', '2015-12-31'), 'test 2016-25': ('2016-01-01', '2025-08-15'),
       '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'), '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}


def build(fr, ok, lab):
    arr, cand = {}, []
    for t, f in fr.items():
        f = f[f.tradable].reset_index(drop=True)
        o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close']); d = f['Date/Time'].to_numpy()
        C, H, L = pd.Series(c), pd.Series(h), pd.Series(l)
        tr = pd.concat([H - L, (H - C.shift()).abs(), (L - C.shift()).abs()], axis=1).max(axis=1)
        arr[t] = dict(o=o, l=l, c=c, d=d, atr=tr.rolling(14).mean().to_numpy())
        nxt = np.zeros(len(c), bool); nd = pd.DatetimeIndex(d[1:])
        nxt[:-1] = (lab.reindex(nd).to_numpy() == 'sideways') & np.isin(d[1:], ok[t]) & (d[1:] >= np.datetime64('2000-01-01')) & (d[1:] <= np.datetime64('2025-08-15'))
        ks = np.flatnonzero(nxt & np.isfinite(arr[t]['atr']))
        cand.append(pd.DataFrame({'date': d[ks], 'ticker': t, 'k': ks, **{f'ret{n}': (C / C.shift(n) - 1).to_numpy()[ks] for n in (1, 5, 10)}}))
    return arr, pd.concat(cand, ignore_index=True).sort_values(['date', 'ticker'], kind='stable').reset_index(drop=True)


def picks(cand, L, mode, seed=None):
    x = cand.dropna(subset=[f'ret{L}'])
    if mode == 'random':
        x = x.assign(key=np.random.default_rng(seed).random(len(x))).sort_values(['date', 'key'], kind='stable')
    else:
        x = x.sort_values(['date', f'ret{L}'], ascending=[True, mode == 'losers'], kind='stable')
    return x.groupby('date', sort=True).head(K)


def sim(arr, P, H, entry):
    busy, out = {}, []
    for r in P.itertuples():
        a = arr[r.ticker]; i = r.k + 1; n = len(a['c'])
        if i <= busy.get(r.ticker, -1) or i + H - 1 >= n:
            continue
        if entry == 'next Open':
            e = a['o'][i]
        else:
            lim = a['c'][r.k] - .5 * a['atr'][r.k]
            if not a['l'][i] < lim:
                continue
            e = min(a['o'][i], lim)
        j = i + H - 1
        out.append((r.ticker, a['d'][i], np.log(a['c'][j] / e)))
        busy[r.ticker] = j
    T = pd.DataFrame(out, columns=['ticker', 'entry', 'gross']); T['net_B'] = T.gross - COST
    return T


def stats(x, cal, a, b, H):
    dd = x.groupby('entry').net_B.mean().reindex(cal.loc[a:b].index); m, se, _ = nw(dd.to_numpy(), H)
    wn = x.net_B > 0; aw, al = x.gross[wn].mean(), x.gross[~wn].mean()
    return dict(trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25), win_rate=wn.mean(), breakeven_wr=(-al + COST) / (aw - al),
                gross_pct=x.gross.mean() * 100, net_B_pct=m * 100, t=m / se if se else np.nan)


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
    ok = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in fr}
    cal = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    lab = regime_proxy(st)['regime']
    with np.errstate(invalid='ignore', divide='ignore'):
        arr, cand = build(fr, ok, lab)
        rows = []
        for L, H, entry in GRID:
            T = sim(arr, picks(cand, L, 'losers'), H, entry); W = sim(arr, picks(cand, L, 'winners'), H, entry)
            C = pd.concat([sim(arr, picks(cand, L, 'random', zlib.crc32(f'{L}-{H}-{entry}-{s}'.encode())), H, entry) for s in range(5)])
            for pn, (a, b) in PER.items():
                sel = lambda z: z[(z.entry >= np.datetime64(a)) & (z.entry <= np.datetime64(b))]
                x, w, y = sel(T), sel(W), sel(C)
                rows.append(dict(lookback=L, hold=H, entry=entry, period=pn, **stats(x, cal, a, b, H), control_net_pct=y.net_B.mean() * 100,
                                 winners_net_pct=w.net_B.mean() * 100, losers_minus_control_pp=(x.gross.mean() - y.gross.mean()) * 100))
    D = pd.DataFrame(rows); D.to_csv(OUT / 'results_all.csv', index=False)
    key = ['lookback', 'hold', 'entry']
    full = D[D.period == '2000-25'].set_index(key); tr = D[D.period == 'train 2000-15'].set_index(key); te = D[D.period == 'test 2016-25'].set_index(key)
    subs = D[D.period.isin(['2000-07', '2008-15', '2016-20', '2021-25'])].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum()))
    S = full.drop(columns='period').join(tr[['net_B_pct', 't']].add_prefix('train_')).join(te[['net_B_pct', 't', 'control_net_pct']].add_prefix('test_')).join(subs.rename('subperiods_positive'))
    S.to_csv(OUT / 'summary.csv')
    pick = tr.net_B_pct.idxmax(); r = te.loc[pick]
    okp = r.net_B_pct > 0 and r.t >= 2 and r.net_B_pct > r.control_net_pct and subs.loc[pick] >= 3
    pd.set_option('display.width', 300); print(S.round(2).to_string())
    print('PICK (train):', pick, '| test net %.2f%% t %.2f control %.2f%% | subperiods %d | PASSES: %s' % (r.net_B_pct, r.t, r.control_net_pct, subs.loc[pick], okp))
