"""Two nested ranges: small bounces inside a medium range, with limit orders (plan: nested_range_results/PLAN.md)."""
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

OUT = ROOT / 'nested_range_results'
COST, COST_USER = .009, .006
GRID = list(product((20, 40), (5, 10), ('small high', 'medium mid'), (0., .03), (10, 20), (True, False)))
PER = {'2000-25': ('2000-01-01', '2025-08-15'), 'train 2000-15': ('2000-01-01', '2015-12-31'), 'test 2016-25': ('2016-01-01', '2025-08-15'),
       '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'), '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
G = {}


def prep(t):
    f = G['fr'][t]; f = f[f.tradable].reset_index(drop=True)
    o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close']); d = f['Date/Time'].to_numpy()
    H, L = pd.Series(h), pd.Series(l)
    P = dict(o=o, h=h, l=l, c=c, d=d)
    for n in (5, 10, 20, 40):
        P[f'H{n}'], P[f'L{n}'] = H.rolling(n).max().to_numpy(), L.rolling(n).min().to_numpy()
    base = np.zeros(len(c), bool); nd = pd.DatetimeIndex(d[1:])
    base[:-1] = (G['lab'].reindex(nd).to_numpy() == 'sideways') & np.isin(d[1:], G['ok'][t]) & (d[1:] >= np.datetime64('2000-01-01')) & (d[1:] <= np.datetime64('2025-08-15'))
    P['base'] = base & np.isfinite(P['L40'])
    return P


def sim(cell, seed=None, counts=None):
    nm, ns, tg, s, T, conf = cell
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t in G['fr']:
        P = G['cache'][t]; o, h, l, c, d = P['o'], P['h'], P['l'], P['c'], P['d']; n = len(c)
        Hm, Lm, Hs, Ls = P[f'H{nm}'], P[f'L{nm}'], P[f'H{ns}'], P[f'L{ns}']
        valid = P['base'] & (Hs > Ls * 1.02)
        if rng is None:
            cond = valid & (Hm / Lm - 1 >= .10) & (Hm / Lm - 1 < .40)
            if conf:
                cond &= (Ls - Lm) / (Hm - Lm) <= .5
            ks = np.flatnonzero(cond)
        else:
            pool = np.flatnonzero(valid); k_ = counts.get(t, 0)
            ks = np.sort(rng.choice(pool, min(k_, len(pool)), replace=False)) if k_ and len(pool) else np.array([], int)
        busy = -1
        for k in ks:
            i = k + 1
            if i <= busy or i + T >= n or not l[i] < Ls[k]:
                continue
            e = min(o[i], Ls[k]); tgt = Hs[k] if tg == 'small high' else (Hm[k] + Lm[k]) / 2; stp = Lm[k] * (1 - s)
            if tgt <= e:
                continue
            for j in range(i, i + T):
                if j > i and h[j] > tgt:
                    px, je, why = max(o[j], tgt), j, 'target'; break
                if c[j] < stp:
                    px, je, why = o[j + 1], j + 1, 'stop'; break
                if j == i + T - 1:
                    px, je, why = c[j], j, 'time'; break
            out.append((t, d[i], np.log(px / e), je - i + 1, why))
            busy = je
    R = pd.DataFrame(out, columns=['ticker', 'entry', 'gross', 'bars', 'why']); R['net_B'] = R.gross - COST
    return R


def run_cell(cell):
    X = sim(cell); counts = X.groupby('ticker').size().to_dict()
    C = pd.concat([sim(cell, zlib.crc32(f'{cell}-{s}'.encode()), counts) for s in range(5)])
    rows = []
    for pn, (a, b) in PER.items():
        x = X[(X.entry >= np.datetime64(a)) & (X.entry <= np.datetime64(b))]; y = C[(C.entry >= np.datetime64(a)) & (C.entry <= np.datetime64(b))]
        base = dict(Nm=cell[0], Ns=cell[1], target=cell[2], stop=cell[3], time=cell[4], confluence=cell[5], period=pn,
                    trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25))
        if len(x) < 5:
            rows.append(base); continue
        dd = x.groupby('entry').net_B.mean().reindex(G['cal'].loc[a:b].index); m, se, _ = nw(dd.to_numpy(), cell[4])
        wn = x.net_B > 0; aw, al = x.gross[wn].mean(), x.gross[~wn].mean()
        rows.append(dict(base, win_rate=wn.mean(), breakeven_wr=(-al + COST) / (aw - al) if wn.any() and (~wn).any() else np.nan, avg_win_pct=aw * 100,
                         avg_loss_pct=al * 100, gross_pct=x.gross.mean() * 100, net_B_pct=m * 100, t=m / se if se else np.nan,
                         net_user_fee_pct=(x.gross.mean() - COST_USER) * 100, control_net_pct=y.net_B.mean() * 100 if len(y) else np.nan,
                         exit_target=(x.why == 'target').mean(), exit_stop=(x.why == 'stop').mean(), exit_time=(x.why == 'time').mean(), avg_bars=x.bars.mean()))
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
            D = pd.DataFrame([r for rows in p.map(run_cell, GRID, chunksize=2) for r in rows])
    D.to_csv(OUT / 'results_all.csv', index=False)
    key = ['Nm', 'Ns', 'target', 'stop', 'time', 'confluence']
    full = D[D.period == '2000-25'].set_index(key); tr = D[D.period == 'train 2000-15'].set_index(key); te = D[D.period == 'test 2016-25'].set_index(key)
    subs = D[D.period.isin(['2000-07', '2008-15', '2016-20', '2021-25'])].groupby(key).net_B_pct.apply(lambda s: int((s > 0).sum()))
    S = full[['trades_per_year', 'win_rate', 'breakeven_wr', 'avg_win_pct', 'avg_loss_pct', 'gross_pct', 'net_B_pct', 't', 'net_user_fee_pct', 'control_net_pct',
              'exit_target', 'exit_stop', 'exit_time', 'avg_bars']].join(tr[['trades_per_year', 'net_B_pct', 't']].add_prefix('train_')).join(
        te[['net_B_pct', 't', 'control_net_pct']].add_prefix('test_')).join(subs.rename('subperiods_positive'))
    S.to_csv(OUT / 'summary.csv')
    elig = tr[tr.trades_per_year >= 10]; pick = elig.net_B_pct.idxmax(); r = te.loc[pick]
    okp = r.net_B_pct > 0 and r.t >= 2 and r.net_B_pct > r.control_net_pct and subs.loc[pick] >= 3
    pd.set_option('display.width', 320); pd.set_option('display.max_rows', 100)
    print(S.sort_values('train_net_B_pct', ascending=False).head(16).round(2).to_string())
    print('cells', len(S), '| full net > 0:', int((S.net_B_pct > 0).sum()), '| train net > 0:', int((S.train_net_B_pct > 0).sum()),
          '| test net > 0 & t >= 2:', int(((S.test_net_B_pct > 0) & (S.test_t >= 2)).sum()), '| gross > 0:', int((S.gross_pct > 0).sum()),
          '| user-fee net > 0:', int((S.net_user_fee_pct > 0).sum()), '| above control:', int((S.net_B_pct > S.control_net_pct).sum()))
    print('PICK (train):', pick, '| test net %.2f%% t %.2f control %.2f%% | subperiods %d | PASSES: %s' % (r.net_B_pct, r.t, r.control_net_pct, subs.loc[pick], okp))
