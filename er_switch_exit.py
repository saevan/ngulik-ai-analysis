"""ER switch exit for the Logic 2 range systems (plan: er_switch_exit_results/PLAN.md)."""
import sys
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
import nested_range as nr, pivot_range as pr

OUT = ROOT / 'er_switch_exit_results'
COST = .009
EXITS = ['price stop', 'ER20 >= 0.2', 'ER20 >= 0.3', 'market leaves sideways', 'price stop + ER20 >= 0.3']
CELLS = [('nested',) + c for c in nr.GRID] + [('pivot',) + c for c in pr.GRID]
GRID = [(c, e) for c in CELLS for e in EXITS]
PER = {'2000-25': ('2000-01-01', '2025-08-15'), 'train 2000-15': ('2000-01-01', '2015-12-31'), 'test 2016-25': ('2016-01-01', '2025-08-15'),
       '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'), '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
G = {}


def prep(t):
    P = nr.prep(t); Q = pr.prep(t); P.update({k: v for k, v in Q.items() if k.startswith(('L0', 'H0'))})
    C = pd.Series(P['c']); P['er'] = ((C - C.shift(20)).abs() / C.diff().abs().rolling(20).sum()).to_numpy()
    side = np.ones(len(C), bool); side[:-1] = G['lab'].reindex(pd.DatetimeIndex(P['d'][1:])).to_numpy() == 'sideways'
    P['side_next'] = side
    return P


def signals(cell, P):
    c = P['c']
    if cell[0] == 'nested':
        _, nm, ns, tg, s, T, conf = cell
        Hm, Lm, Hs, Ls = P[f'H{nm}'], P[f'L{nm}'], P[f'H{ns}'], P[f'L{ns}']
        cond = P['base'] & (Hs > Ls * 1.02) & (Hm / Lm - 1 >= .10) & (Hm / Lm - 1 < .40)
        if conf:
            cond &= (Ls - Lm) / (Hm - Lm) <= .5
    else:
        _, (xm, xs), tg, s, T = cell
        Lm, Hm, Ls, Hs = P[f'L{xm}'], P[f'H{xm}'], P[f'L{xs}'], P[f'H{xs}']
        cond = P['base'] & np.isfinite(Lm) & np.isfinite(Hm) & np.isfinite(Ls) & np.isfinite(Hs) & (c > Ls) & (Hs > Ls * 1.02) & (Hm > Lm) & \
            (c >= Lm) & (c <= Hm) & ((Ls - Lm) / (Hm - Lm) <= .5)
    cond &= P['er'] < .2                                    # Logic 2 only enters while the stock is choppy
    return np.flatnonzero(cond), Hm, Lm, Hs, Ls, tg, s, T


def sim(cell, ex, trace=False):
    out = []
    for t in G['fr']:
        P = G['cache'][t]; o, h, l, c, d, er = P['o'], P['h'], P['l'], P['c'], P['d'], P['er']; n = len(c)
        ks, Hm, Lm, Hs, Ls, tg, s, T = signals(cell, P)
        busy = -1
        for k in ks:
            i = k + 1
            if i <= busy or i + T >= n or not l[i] < Ls[k]:
                continue
            e = min(o[i], Ls[k]); tgt = Hs[k] if tg == 'small high' else (Hm[k] + Lm[k]) / 2; stp = Lm[k] * (1 - s)
            if tgt <= e:
                continue
            er_hit = None
            for j in range(i, i + T):
                if er_hit is None and er[j] >= .3:
                    er_hit = (j - i + 1, c[j] / e - 1)
                if j > i and h[j] > tgt:
                    px, je, why = max(o[j], tgt), j, 'target'; break
                stop = (ex in ('price stop', 'price stop + ER20 >= 0.3') and c[j] < stp) or (ex == 'ER20 >= 0.2' and er[j] >= .2) or \
                       (ex in ('ER20 >= 0.3', 'price stop + ER20 >= 0.3') and er[j] >= .3) or (ex == 'market leaves sideways' and not P['side_next'][j])
                if stop:
                    px, je, why = o[j + 1], j + 1, 'stop'; break
                if j == i + T - 1:
                    px, je, why = c[j], j, 'time'; break
            out.append((t, d[i], np.log(px / e), je - i + 1, why) + ((er_hit[0] if er_hit else np.nan, er_hit[1] if er_hit else np.nan, px / e - 1) if trace else ()))
            busy = je
    cols = ['ticker', 'entry', 'gross', 'bars', 'why'] + (['bars_to_er03', 'ret_at_er03', 'ret_exit'] if trace else [])
    R = pd.DataFrame(out, columns=cols); R['net_B'] = R.gross - COST
    return R


def run(args):
    cell, ex = args
    X = sim(cell, ex); rows = []
    for pn, (a, b) in PER.items():
        x = X[(X.entry >= np.datetime64(a)) & (X.entry <= np.datetime64(b))]
        base = dict(system=cell[0], cell=str(cell[1:]), exit=ex, period=pn, trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25))
        if len(x) < 5:
            rows.append(base); continue
        dd = x.groupby('entry').net_B.mean().reindex(G['cal'].loc[a:b].index); m, se, _ = nw(dd.to_numpy(), cell[-2] if cell[0] == 'nested' else cell[-1])
        wn = x.net_B > 0
        rows.append(dict(base, win_rate=wn.mean(), avg_win_pct=x.gross[wn].mean() * 100, avg_loss_pct=x.gross[~wn].mean() * 100, gross_pct=x.gross.mean() * 100,
                         net_B_pct=m * 100, t=m / se if se else np.nan, stop_share=(x.why == 'stop').mean(), target_share=(x.why == 'target').mean()))
    return rows


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
    G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['lab'] = regime_proxy(st)['regime']
    for mod in (nr, pr):
        mod.G.update(G)
    with np.errstate(invalid='ignore', divide='ignore'):
        G['cache'] = {t: prep(t) for t in G['fr']}
        with Pool(4) as p:
            D = pd.DataFrame([r for rows in p.map(run, GRID, chunksize=8) for r in rows])
        D.to_csv(OUT / 'results_all.csv', index=False)
        F = D[D.period == '2000-25']
        S = F.groupby(['system', 'exit'])[['trades_per_year', 'win_rate', 'avg_win_pct', 'avg_loss_pct', 'gross_pct', 'net_B_pct', 'stop_share', 'target_share']].mean()
        S['cells'] = F.groupby(['system', 'exit']).size(); S['cells_net_pos'] = F.assign(p=F.net_B_pct > 0).groupby(['system', 'exit']).p.sum()
        S['best_net'] = F.groupby(['system', 'exit']).net_B_pct.max()
        picks = []
        for (sy, ex), g in D[D.period == 'train 2000-15'].groupby(['system', 'exit']):
            g = g[g.trades_per_year >= 10]
            if not len(g):
                continue
            c = g.loc[g.net_B_pct.idxmax(), 'cell']
            te = D[(D.system == sy) & (D.exit == ex) & (D.cell == c)].set_index('period')
            sp = int((te.loc[['2000-07', '2008-15', '2016-20', '2021-25'], 'net_B_pct'] > 0).sum())
            r = te.loc['test 2016-25']
            picks.append(dict(system=sy, exit=ex, cell=c, train_net=te.loc['train 2000-15', 'net_B_pct'], test_net=r.net_B_pct, test_t=r.t, subperiods_positive=sp,
                              passes=bool(r.net_B_pct > 0 and r.t >= 2 and sp >= 3)))
        PK = pd.DataFrame(picks)
        S.to_csv(OUT / 'summary_by_exit.csv'); PK.to_csv(OUT / 'training_picks.csv', index=False)
        tr = []
        for _, row in PK[PK.exit == 'price stop'].iterrows():
            cell = (row.system,) + eval(row.cell, {'np': np})
            X = sim(cell, 'price stop', trace=True); s_ = X[X.why == 'stop']
            tr.append(dict(system=row.system, cell=row.cell, stopped_trades=len(s_), share_reached_er03_before_stop=s_.bars_to_er03.notna().mean(),
                           median_bars_to_er03=s_.bars_to_er03.median(), median_bars_to_stop=s_.bars.median(),
                           mean_ret_at_er03=s_.ret_at_er03.mean() * 100, mean_ret_at_stop=s_.ret_exit.mean() * 100))
        TR = pd.DataFrame(tr); TR.to_csv(OUT / 'stopped_trades_er_timing.csv', index=False)
    pd.set_option('display.width', 250)
    print(S.round(2).to_string()); print(PK.round(2).to_string(index=False)); print(TR.round(2).to_string(index=False))
