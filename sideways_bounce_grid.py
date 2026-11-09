"""Grid search for a sideways Logic 2: what predicts a bounce? (plan: sideways_bounce_grid_results/PLAN.md)."""
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

OUT = ROOT / 'sideways_bounce_grid_results'
COST, COST_USER = .009, .006
TRIG = ['T1 RSI2 < 10', 'T2 3 lower closes', 'T3 bottom 20% of range', 'T4 Close < SMA20 - 1.5 ATR']
FILT = ['F0 none', 'F1 Close > SMA200', 'F2 volume dry-up', 'F3 lower wick', 'F4 breadth < 30%', 'F5 stock ER20 < 0.2', 'F6 volume spike']
ENTRY = ['next Open', 'limit Close - 0.5 ATR']
EXIT = ['Close > SMA5', 'Close > prior High', 'time 5']
GRID = list(product(TRIG, FILT, ENTRY, EXIT))
PER = {'2000-25': ('2000-01-01', '2025-08-15'), 'train 2000-15': ('2000-01-01', '2015-12-31'), 'test 2016-25': ('2016-01-01', '2025-08-15'),
       '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'), '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
G = {}
START, END = '2000-01-01', '2025-08-15'   # entry window for prep (the holdout check changes it)


def prep(t):
    f = G['fr'][t]; f = f[f.tradable].reset_index(drop=True)
    o, h, l, c, v = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close', 'Volume']); d = f['Date/Time'].to_numpy()
    C, V, H, L = pd.Series(c), pd.Series(v), pd.Series(h), pd.Series(l)
    dl = C.diff(); up = dl.clip(lower=0).ewm(alpha=.5, adjust=False).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=.5, adjust=False).mean()
    rsi2 = (100 - 100 / (1 + up / dn)).to_numpy()
    tr = pd.concat([H - L, (H - C.shift()).abs(), (L - C.shift()).abs()], axis=1).max(axis=1); atr = tr.rolling(14).mean().to_numpy()
    sma20 = C.rolling(20).mean().to_numpy()
    hh, ll = H.rolling(20).max().to_numpy(), L.rolling(20).min().to_numpy()
    trig = {TRIG[0]: rsi2 < 10, TRIG[1]: ((C < C.shift(1)) & (C.shift(1) < C.shift(2)) & (C.shift(2) < C.shift(3))).to_numpy(),
            TRIG[2]: (c - ll) / (hh - ll) <= .2, TRIG[3]: c < sma20 - 1.5 * atr}
    er = ((C - C.shift(20)).abs() / C.diff().abs().rolling(20).sum()).to_numpy()
    filt = {FILT[0]: np.ones(len(c), bool), FILT[1]: c > C.rolling(200).mean().to_numpy(),
            FILT[2]: (V.rolling(5).mean() / V.rolling(60).mean()).to_numpy() < .7, FILT[3]: (h > l) & ((c - l) / (h - l) >= .5),
            FILT[4]: G['breadth'].reindex(pd.DatetimeIndex(d)).to_numpy() < .3, FILT[5]: er < .2,
            FILT[6]: (V / V.shift(1).rolling(20).mean()).to_numpy() > 2}
    base = np.zeros(len(c), bool)
    nd = pd.DatetimeIndex(d[1:])
    base[:-1] = (G['lab'].reindex(nd).to_numpy() == 'sideways') & np.isin(d[1:], G['ok'][t]) & (d[1:] >= np.datetime64(START)) & (d[1:] <= np.datetime64(END))
    base &= np.isfinite(atr) & np.isfinite(sma20)
    return dict(o=o, h=h, l=l, c=c, d=d, atr=atr, sma5=C.rolling(5).mean().to_numpy(), trig=trig, filt=filt, base=base)


def sim(cell, seed=None, counts=None):
    tg, fl, en, ex = cell
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t in G['fr']:
        P = G['cache'][t]; o, h, l, c, d = P['o'], P['h'], P['l'], P['c'], P['d']; n = len(c)
        if rng is None:
            ks = np.flatnonzero(P['base'] & P['trig'][tg] & P['filt'][fl])
        else:
            pool = np.flatnonzero(P['base']); k_ = counts.get(t, 0)
            ks = np.sort(rng.choice(pool, min(k_, len(pool)), replace=False)) if k_ and len(pool) else np.array([], int)
        busy = -1
        for k in ks:
            i = k + 1
            if i <= busy or i + 10 >= n:
                continue
            if en == 'next Open':
                e = o[i]
            else:
                lim = c[k] - .5 * P['atr'][k]
                if not l[i] < lim:
                    continue
                e = min(o[i], lim)
            for j in range(i, i + 10):
                if ex == 'Close > SMA5' and c[j] > P['sma5'][j]:
                    px, je = o[j + 1], j + 1; break
                if ex == 'Close > prior High' and c[j] > h[j - 1]:
                    px, je = o[j + 1], j + 1; break
                if (ex == 'time 5' and j == i + 4) or j == i + 9:
                    px, je = c[j], j; break
            out.append((t, d[i], np.log(px / e), je - i + 1))
            busy = je
    T = pd.DataFrame(out, columns=['ticker', 'entry', 'gross', 'bars'])
    T['net_B'] = T.gross - COST
    return T


def run_cell(cell):
    T = sim(cell)
    counts = T.groupby('ticker').size().to_dict()
    C = pd.concat([sim(cell, zlib.crc32(f'{cell}-{s}'.encode()), counts) for s in range(5)])
    rows = []
    for pn, (a, b) in PER.items():
        x = T[(T.entry >= np.datetime64(a)) & (T.entry <= np.datetime64(b))]
        y = C[(C.entry >= np.datetime64(a)) & (C.entry <= np.datetime64(b))]
        if len(x) < 5:
            rows.append(dict(trigger=cell[0], filter=cell[1], entry=cell[2], exit=cell[3], period=pn, trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25)))
            continue
        dd = x.groupby('entry').net_B.mean().reindex(G['cal'].loc[a:b].index)
        m, se, _ = nw(dd.to_numpy(), 10)
        wn = x.net_B > 0; aw, al = x.gross[wn].mean(), x.gross[~wn].mean()
        rows.append(dict(trigger=cell[0], filter=cell[1], entry=cell[2], exit=cell[3], period=pn,
                         trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25), win_rate=wn.mean(),
                         breakeven_wr=(-al + COST) / (aw - al) if wn.any() and (~wn).any() else np.nan, avg_win_pct=aw * 100, avg_loss_pct=al * 100,
                         gross_pct=x.gross.mean() * 100, net_B_pct=m * 100, t=m / se if se else np.nan, net_B_event_pct=x.net_B.mean() * 100,
                         net_user_fee_pct=(x.gross.mean() - COST_USER) * 100, control_net_pct=y.net_B.mean() * 100 if len(y) else np.nan, avg_bars=x.bars.mean()))
    return rows


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
    G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['lab'] = regime_proxy(st)['regime']
    above = {}
    for t, f in G['fr'].items():
        f = f[f.tradable].set_index('Date/Time'); above[t] = (f.Close > f.Close.rolling(20).mean()).where(f.Close.rolling(20).mean().notna())
    G['breadth'] = pd.DataFrame(above).mean(axis=1)
    with np.errstate(invalid='ignore', divide='ignore'):
        G['cache'] = {t: prep(t) for t in G['fr']}
        with Pool(4) as p:
            D = pd.DataFrame([r for rows in p.map(run_cell, GRID, chunksize=4) for r in rows])
    D.to_csv(OUT / 'results_all.csv', index=False)
    key = ['trigger', 'filter', 'entry', 'exit']
    full = D[D.period == '2000-25'].set_index(key); tr = D[D.period == 'train 2000-15'].set_index(key); te = D[D.period == 'test 2016-25'].set_index(key)
    subs = D[D.period.isin(['2000-07', '2008-15', '2016-20', '2021-25'])].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum()))
    S = full[['trades_per_year', 'win_rate', 'breakeven_wr', 'avg_win_pct', 'avg_loss_pct', 'gross_pct', 'net_B_pct', 't', 'net_user_fee_pct', 'control_net_pct', 'avg_bars']].join(
        tr[['trades_per_year', 'net_B_pct', 't']].add_prefix('train_')).join(te[['trades_per_year', 'net_B_pct', 't', 'control_net_pct']].add_prefix('test_')).join(subs.rename('subperiods_positive'))
    S.to_csv(OUT / 'summary.csv')
    elig = tr[tr.trades_per_year >= 10]
    pick = elig.net_B_pct.idxmax(); r = te.loc[pick]
    ok = r.net_B_pct > 0 and r.t >= 2 and r.net_B_pct > r.control_net_pct and subs.loc[pick] >= 3
    pd.set_option('display.width', 300); pd.set_option('display.max_rows', 200)
    print(S.sort_values('train_net_B_pct', ascending=False).head(25).round(2).to_string())
    print('cells', len(S), '| full net > 0:', int((S.net_B_pct > 0).sum()), '| train net > 0:', int((S.train_net_B_pct > 0).sum()),
          '| test net > 0 & t >= 2:', int(((S.test_net_B_pct > 0) & (S.test_t >= 2)).sum()), '| gross > 0:', int((S.gross_pct > 0).sum()))
    print('PICK (train):', pick, '| test net %.2f%% t %.2f control %.2f%% | subperiods %d | PASSES: %s' % (r.net_B_pct, r.t, r.control_net_pct, subs.loc[pick], ok))
