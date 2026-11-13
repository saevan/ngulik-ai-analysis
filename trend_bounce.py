"""Do higher-ER stocks give bigger bounces we can use? (plan: trend_bounce_results/PLAN.md)."""
import sys, zlib, time
from itertools import product
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from analyze_portfolio_regimes import regime_proxy
from sideways_swings import zigzag

OUT = ROOT / 'trend_bounce_results'
COST, COST_USER, TMAX = .009, .006, 60
A, B = '2000-01-01', '2025-08-15'
ERC = {'ER >= 0.2': lambda e: e >= .2, 'ER >= 0.3': lambda e: e >= .3, 'ER >= 0.5': lambda e: e >= .5, 'ER < 0.2 (reference)': lambda e: e < .2}
GRID = list(product((.03, .05, .10), list(ERC), ('up', 'any')))
PER = {'2000-25': ('2000-01-01', '2025-08-15'), 'train 2000-15': ('2000-01-01', '2015-12-31'), 'test 2016-25': ('2016-01-01', '2025-08-15'),
       '2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'), '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', '2025-08-15')}
KEY = ['X', 'er', 'direction']
BINS, LAB = [-np.inf, .2, .3, .4, .5, np.inf], ['< 0.2', '0.2-0.3', '0.3-0.4', '0.4-0.5', '>= 0.5']
G = {}


def prep(t):
    f = G['fr'][t]; f = f[f.tradable].reset_index(drop=True)
    o, h, l, c = (f[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close']); d = f['Date/Time'].to_numpy()
    C = pd.Series(c); P = dict(o=o, c=c, d=d)
    P['er20'] = ((C - C.shift(20)).abs() / C.diff().abs().rolling(20).sum()).to_numpy()
    P['up'] = (C > C.shift(20)).to_numpy()
    P['mk'] = G['lab'].reindex(pd.DatetimeIndex(d)).fillna('unknown').to_numpy()
    base = np.zeros(len(c), bool); nd = pd.DatetimeIndex(d[1:])
    base[:-1] = np.isin(d[1:], G['ok'][t]) & (d[1:] >= np.datetime64(A)) & (d[1:] <= np.datetime64(B))
    P['base'] = base & np.isfinite(P['er20'])            # eligible on k+1
    P['lows'] = {x: {cf: (idx, price) for idx, price, kind, cf in zigzag(c, x) if kind == -1} for x in (.03, .05, .10)}
    P['legs'] = {}
    for x in (.03, .05, .10):                            # descriptive legs: low -> next high
        p = zigzag(c, x); legs = []
        for a_, b_, z_ in zip(p, p[1:], p[2:]):
            if a_[2] == 1 and b_[2] == -1 and z_[2] == 1 and P['base'][b_[3]]:
                k = b_[3]; legs.append((P['er20'][k], P['up'][k], z_[1] / b_[1] - 1, c[z_[3]] / c[k] - 1))
        P['legs'][x] = legs
    return P


def sim(cell, seed=None, counts=None):
    x, erk, dr = cell; fer = ERC[erk]
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t in G['fr']:
        P = G['cache'][t]; o, c, d, er, up, mk = P['o'], P['c'], P['d'], P['er20'], P['up'], P['mk']; n = len(c)
        state = P['base'] & fer(er) & (up if dr == 'up' else True)
        if rng is None:
            ks = sorted(k for k in P['lows'][x] if state[k])
        else:
            pool = np.flatnonzero(state); k_ = counts.get(t, 0)
            ks = np.sort(rng.choice(pool, min(k_, len(pool)), replace=False)) if k_ and len(pool) else []
        busy = -1
        for k in ks:
            i = k + 1
            if i <= busy or i + 1 >= n:
                continue
            e = o[i]; L = P['lows'][x][k][1] if rng is None else c[k] * (1 - x); hi = c[i]
            for j in range(i, min(n - 1, i + TMAX)):
                hi = max(hi, c[j])
                if c[j] <= hi * (1 - x) or c[j] < L:
                    px, je, why = o[j + 1], j + 1, ('stop' if c[j] < L else 'trail'); break
                if j == i + TMAX - 1 or j == n - 2:
                    px, je, why = c[j], j, 'time'; break
            out.append((t, d[i], np.log(px / e), je - i + 1, why, mk[i]))
            busy = je
    R = pd.DataFrame(out, columns=['ticker', 'entry', 'gross', 'bars', 'why', 'market']); R['net_B'] = R.gross - COST
    return R


def stats(x, a, b):
    dd = x.groupby('entry').net_B.mean().reindex(G['cal'].loc[a:b].index); m, se, _ = nw(dd.to_numpy(), 20)
    wn = x.net_B > 0; aw, al = x.gross[wn].mean(), x.gross[~wn].mean()
    return dict(trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25), win_rate=wn.mean(),
                breakeven_wr=(-al + COST) / (aw - al) if wn.any() and (~wn).any() else np.nan, avg_win_pct=aw * 100, avg_loss_pct=al * 100,
                payoff=aw / -al if (~wn).any() and wn.any() else np.nan, gross_pct=x.gross.mean() * 100, net_B_pct=m * 100, t=m / se if se else np.nan,
                net_user_fee_pct=(x.gross.mean() - COST_USER) * 100, trail_share=(x.why == 'trail').mean(), stop_share=(x.why == 'stop').mean(),
                time_share=(x.why == 'time').mean(), avg_bars=x.bars.mean())


def run_cell(cell):
    X = sim(cell); counts = X.groupby('ticker').size().to_dict()
    C = pd.concat([sim(cell, zlib.crc32(f'{cell}-{s}'.encode()), counts) for s in range(5)])
    rows = []
    for pn, (a, b) in PER.items():
        x = X[(X.entry >= np.datetime64(a)) & (X.entry <= np.datetime64(b))]; y = C[(C.entry >= np.datetime64(a)) & (C.entry <= np.datetime64(b))]
        base = dict(zip(KEY, cell), period=pn)
        if len(x) < 5:
            rows.append(dict(base, trades_per_year=len(x) / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25))); continue
        rows.append(dict(base, **stats(x, a, b), control_net_pct=y.net_B.mean() * 100 if len(y) else np.nan))
    return rows, X


if __name__ == '__main__':
    t0 = time.time()
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
    G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['lab'] = regime_proxy(st)['regime']
    with np.errstate(invalid='ignore', divide='ignore'):
        G['cache'] = {t: prep(t) for t in G['fr']}
        # Part 1: descriptive
        legs = pd.DataFrame([(x, *lg) for P in G['cache'].values() for x in (.03, .05, .10) for lg in P['legs'][x]], columns=['X', 'er', 'up', 'bounce', 'catch'])
        legs['er_bucket'] = pd.cut(legs.er, BINS, labels=LAB, right=False)
        D1 = legs.groupby(['X', 'er_bucket', 'up'], observed=True).agg(bounces=('bounce', 'size'), bounce_median=('bounce', 'median'), bounce_p75=('bounce', lambda s: s.quantile(.75)),
                                                                       bounce_p90=('bounce', lambda s: s.quantile(.9)), share_ge_10=('bounce', lambda s: (s >= .1).mean()),
                                                                       share_ge_20=('bounce', lambda s: (s >= .2).mean()), catch_net_mean=('catch', lambda s: (s - COST).mean()),
                                                                       catch_net_pos=('catch', lambda s: ((s - COST) > 0).mean())).reset_index()
        D1.to_csv(OUT / 'bounce_by_er_direction.csv', index=False)
        # Part 2: rule test
        allrows, trades = [], {}
        for cell in GRID:
            rows, X = run_cell(cell); allrows += rows; trades[cell] = X
        D = pd.DataFrame(allrows)
    D.to_csv(OUT / 'results_all.csv', index=False)
    full = D[D.period == '2000-25'].set_index(KEY); tr = D[D.period == 'train 2000-15'].set_index(KEY); te = D[D.period == 'test 2016-25'].set_index(KEY)
    subs = D[D.period.isin(['2000-07', '2008-15', '2016-20', '2021-25'])].groupby(KEY).net_B_pct.apply(lambda s: int((s > 0).sum()))
    S = full.drop(columns='period').join(tr[['trades_per_year', 'net_B_pct', 't']].add_prefix('train_')).join(
        te[['net_B_pct', 't', 'control_net_pct']].add_prefix('test_')).join(subs.rename('subperiods_positive'))
    S.to_csv(OUT / 'summary.csv')
    pd.set_option('display.width', 340); pd.set_option('display.max_rows', 200)
    print(D1.round(3).to_string(index=False)); print(S.round(2).to_string())
    el = tr[(tr.trades_per_year >= 10) & (tr.index.get_level_values('er') != 'ER < 0.2 (reference)')]
    pick = el.net_B_pct.idxmax(); r = te.loc[pick]
    ok = r.net_B_pct > 0 and r.t >= 2 and r.net_B_pct > r.control_net_pct and subs.loc[pick] >= 3
    print('PICK (train):', pick, '| train net %.2f%% | test net %.2f%% t %.2f control %.2f%% | subperiods %d | PASSES: %s' % (el.loc[pick, 'net_B_pct'], r.net_B_pct, r.t, r.control_net_pct, subs.loc[pick], ok))
    X = trades[pick]; X['period'] = np.where(X.entry < np.datetime64('2016-01-01'), 'train', 'test')
    M = X.groupby(['market', 'period']).agg(trades=('net_B', 'size'), net_pct=('net_B', lambda s: s.mean() * 100), win_rate=('net_B', lambda s: (s > 0).mean()), avg_bars=('bars', 'mean')).reset_index()
    M.to_csv(OUT / 'pick_by_market.csv', index=False); print(M.round(3).to_string(index=False))
    print('cells 24 | net > 0:', int((S.net_B_pct > 0).sum()), '| above control:', int((S.net_B_pct > S.control_net_pct).sum()), '| test net > 0 & t >= 2:', int(((S.test_net_B_pct > 0) & (S.test_t >= 2)).sum()), '| %.0fs' % (time.time() - t0))
