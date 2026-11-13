"""Logic 2 candidate: relative-momentum rotation for idle cash in sideways markets (plan: momentum_rotation_results/PLAN.md)."""
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

OUT = ROOT / 'momentum_rotation_results'
A, B = '2000-01-01', '2025-08-15'
BUY_FEE, SELL_FEE, SLIP, CAP0, ADV_CAP, PARK = .0015, .0025, .0025, 1e9, .25, .04
SCORES = ['MOM12-1', 'mom120', 'mom60']
FILTERS = ['none', 'ER20 >= 0.2']
GATES = ['sideways', 'not downtrend', 'always']
NS = [5, 10]
REBAL = ['monthly', 'weekly']
EXITS = ['rebalance only', 'rebalance + Close < SMA30']
GRID = list(product(SCORES, FILTERS, GATES, NS, REBAL, EXITS))
SUB = {'2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'), '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', B)}
KEY = ['score', 'filter', 'gate', 'N', 'rebalance', 'exit']
G = {}


def setup():
    st, _ = engine.load_data('stocks')
    fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
    cal = pd.DatetimeIndex(sorted(st['Date/Time'].unique())); tick = sorted(fr)
    cols = {k: {} for k in ['O', 'C', 'adv', 'MOM12-1', 'mom120', 'mom60', 'er20', 'sma30', 'elig']}
    last = {}
    for t in tick:
        f = fr[t]; f = f[f.tradable].set_index('Date/Time'); c = f.Close
        cols['O'][t] = f.Open; cols['C'][t] = c
        cols['adv'][t] = (f.Close * f.Volume).shift(1).rolling(20).mean()
        cols['MOM12-1'][t] = c.shift(20) / c.shift(250) - 1
        cols['mom120'][t] = c / c.shift(120) - 1
        cols['mom60'][t] = c / c.shift(60) - 1
        cols['er20'][t] = (c - c.shift(20)).abs() / c.diff().abs().rolling(20).sum()
        cols['sma30'][t] = c.rolling(30).mean()
        cols['elig'][t] = pd.Series(1., index=pd.DatetimeIndex(sorted(pit[t] & stale[t])))
        last[t] = f.index[-1]
    for k, d in cols.items():
        G[k] = pd.DataFrame(d).reindex(cal)[tick]
    G['elig'] = G['elig'].fillna(0.).to_numpy() > 0
    for k in ['O', 'C', 'adv', 'MOM12-1', 'mom120', 'mom60', 'er20', 'sma30']:
        G[k] = G[k].to_numpy(float)
    G['cal'], G['tick'] = cal, tick
    G['last'] = np.array([cal.get_loc(last[t]) for t in tick])
    G['lab'] = regime_proxy(st)['regime'].reindex(cal).fillna('unknown').to_numpy()
    G['i0'] = int(cal.searchsorted(pd.Timestamp(A)))
    G['iB'] = int(cal.searchsorted(pd.Timestamp(B), side='right')) - 1
    pos_idx = pd.Series(np.arange(len(cal)), index=cal)
    G['rebal'] = {k: (pos_idx.groupby(cal.to_period(p)).transform('max').to_numpy() == np.arange(len(cal))) for k, p in [('monthly', 'M'), ('weekly', 'W')]}


def sim(cell, seed=None, static=False):
    score_k, filt, gate, N, reb, ex = cell
    S, ER, SMA, O, C, ADV, EL = G[score_k], G['er20'], G['sma30'], G['O'], G['C'], G['adv'], G['elig']
    lab, cal, rebal, last, tick = G['lab'], G['cal'], G['rebal'][reb], G['last'], G['tick']
    rng = np.random.default_rng(seed) if seed is not None else None
    i0, iB, nt = G['i0'], G['iB'], len(tick)
    s_fixed = rng.random(nt) if (rng is not None and static) else None   # static random ranking (control 2)
    cash = equity = CAP0; pos = {}; pend_sell = set(); pend_buy = []
    lastC = np.full(nt, np.nan); eq, cs, mvs, npos = [], [], [], []; trades = []

    def close_out(j, i, px, reason):
        nonlocal cash
        p = pos.pop(j); pro = p['qty'] * px * (1 - SELL_FEE); cash += pro
        trades.append((tick[j], cal[p['i']], cal[i], pro / p['cost'] - 1, i - p['i'] + 1, reason))

    for i in range(i0, iB + 1):
        o, c = O[i], C[i]
        for j in list(pend_sell):                      # exits at the Open; a pending sell waits until executable
            if j not in pos:
                pend_sell.discard(j)
            elif np.isfinite(o[j]):
                close_out(j, i, o[j] * (1 - SLIP), 'rebalance'); pend_sell.discard(j)
        budget = equity / N
        for j in pend_buy:                             # entries at the Open; orders are valid for this day only
            if j in pos or len(pos) >= N or not np.isfinite(o[j]):
                continue
            amt = min(budget, cash)
            amt = min(amt, ADV_CAP * ADV[i, j]) if np.isfinite(ADV[i, j]) else 0.
            if amt <= 1e-3:
                continue
            px = o[j] * (1 + SLIP); pos[j] = dict(qty=amt / (px * (1 + BUY_FEE)), cost=amt, i=i); cash -= amt
        pend_buy = []
        fin = np.isfinite(c); lastC = np.where(fin, c, lastC)
        for j in list(pos):                            # a stock's last bar, or the end of the period
            if i == last[j] or i == iB:
                close_out(j, i, lastC[j] * (1 - SLIP), 'last bar' if i == last[j] else 'period end')
        mv = sum(p['qty'] * lastC[j] * (1 - SLIP) * (1 - SELL_FEE) for j, p in pos.items())
        equity = cash + mv
        eq.append(equity); cs.append(cash); mvs.append(mv); npos.append(len(pos))
        if ex == 'rebalance + Close < SMA30':
            for j in pos:
                if fin[j] and c[j] < SMA[i, j]:
                    pend_sell.add(j)
        if rebal[i] and i + 1 <= iB:
            s = S[i] if rng is None else (s_fixed if static else rng.random(nt))
            cand = EL[i + 1] & np.isfinite(s) & fin
            if filt == 'ER20 >= 0.2':
                cand &= ER[i] >= .2
            if rng is None:
                cand &= s > 0
            key = np.where(cand, s, -np.inf); order = np.argsort(-key, kind='stable')
            rank = np.empty(nt, int); rank[order] = np.arange(nt)
            for j in list(pos):
                if not cand[j] or rank[j] >= 2 * N:
                    pend_sell.add(j)
            g = lab[i + 1]
            if gate == 'always' or (gate == 'sideways' and g == 'sideways') or (gate == 'not downtrend' and g in ('sideways', 'uptrend')):
                free = N - sum(1 for j in pos if j not in pend_sell)
                for j in order:
                    if free <= 0 or not cand[j]:
                        break
                    if j in pos or j in pend_sell:
                        continue
                    pend_buy.append(j); free -= 1
    idx = cal[i0:iB + 1]
    D = pd.DataFrame(dict(equity=eq, cash=cs, market_value=mvs, positions=npos), index=idx)
    T = pd.DataFrame(trades, columns=['ticker', 'entry_date', 'exit_date', 'net_return', 'bars', 'reason'])
    return D, T


def ann(y):
    return float((1 + y).prod() ** (252 / len(y)) - 1) if len(y) else np.nan


def report(D, T, Dc=None, Dc2=None):
    eq = D.equity; dr = eq.pct_change().fillna(eq.iloc[0] / CAP0 - 1)
    g = pd.Series(G['lab'], index=G['cal']).reindex(dr.index); inv = D.market_value / D.equity
    r = dict(CAGR=(eq.iloc[-1] / CAP0) ** (365.25 / (eq.index[-1] - pd.Timestamp(A)).days) - 1, MDD=(eq / eq.cummax() - 1).min())
    for k in ('sideways', 'uptrend', 'downtrend'):
        y = dr[g == k]; r[f'{k}_ann'] = ann(y); r[f'{k}_invested'] = float(inv[g == k].mean())
    side = dr[g == 'sideways']
    m, se, _ = nw(side.to_numpy(), 20); r['sideways_t'] = m / se if se else np.nan
    for k, (a, b) in SUB.items():
        r[f'side_ann {k}'] = ann(side.loc[a:b])
    r['train_side_ann'] = ann(side.loc[:'2015-12-31']); r['test_side_ann'] = ann(side.loc['2016-01-01':])
    m, se, _ = nw(side.loc['2016-01-01':].to_numpy(), 20); r['test_side_t'] = m / se if se else np.nan
    if Dc is not None:
        drc = Dc.pct_change().fillna(Dc.iloc[0] / CAP0 - 1); sc = drc[g == 'sideways']
        r['control_side_ann'] = ann(sc); r['test_control_side_ann'] = ann(sc.loc['2016-01-01':])
        d = (side - sc).loc['2016-01-01':]; m, se, _ = nw(d.to_numpy(), 20); r['test_vs_control_t'] = m / se if se else np.nan
    if Dc2 is not None:
        drc = Dc2.pct_change().fillna(Dc2.iloc[0] / CAP0 - 1); sc = drc[g == 'sideways']
        r['control2_side_ann'] = ann(sc); r['test_control2_side_ann'] = ann(sc.loc['2016-01-01':])
    yrs = (pd.Timestamp(B) - pd.Timestamp(A)).days / 365.25
    w = T.net_return > 0
    r.update(trades_per_year=len(T) / yrs, win_rate=w.mean(), avg_win=T.net_return[w].mean(), avg_loss=T.net_return[~w].mean(),
             payoff=T.net_return[w].mean() / -T.net_return[~w].mean() if (~w).any() and w.any() else np.nan, median_bars=T.bars.median())
    return r


if __name__ == '__main__':
    t0 = time.time()
    with np.errstate(invalid='ignore', divide='ignore'):
        setup()
        print('setup %.0fs' % (time.time() - t0), flush=True)
        rows = []
        for n_, cell in enumerate(GRID):
            D, T = sim(cell)
            Dc = pd.concat([sim(cell, zlib.crc32(f'{cell}-{s}'.encode()))[0].equity for s in range(5)], axis=1).mean(axis=1)
            Dc2 = pd.concat([sim(cell, zlib.crc32(f'{cell}-static-{s}'.encode()), static=True)[0].equity for s in range(5)], axis=1).mean(axis=1)
            rows.append(dict(zip(KEY, cell), **report(D, T, Dc, Dc2)))
            if n_ % 12 == 11:
                print('cells %d/%d  %.0fs' % (n_ + 1, len(GRID), time.time() - t0), flush=True)
        R = pd.DataFrame(rows); R.to_csv(OUT / 'results.csv', index=False)
        G['ew'] = np.where(np.isfinite(G['C']), 1., np.nan)      # context: equal weight of all eligible stocks, monthly
        De, Te = sim(('ew', 'none', 'always', 100, 'monthly', 'rebalance only'))
        E = report(De, Te); pd.Series(E).to_csv(OUT / 'ew_benchmark.csv')
    gated = R[R.gate != 'always']
    pick = gated.loc[gated.train_side_ann.idxmax()]
    nsub = lambda row: sum(int(row[f'side_ann {k}'] > 0) for k in SUB)
    rule = lambda df: (df.test_side_ann >= PARK) & (df.test_side_t >= 2) & (df.test_side_ann > df.test_control_side_ann) & (df.apply(nsub, axis=1) >= 3)
    passes = bool(rule(gated.loc[[pick.name]]).iloc[0]); n_pass = int(rule(gated).sum())
    rule2 = lambda df: rule(df) & (df.test_side_ann > df.test_control2_side_ann); n_pass2 = int(rule2(gated).sum())
    pd.set_option('display.width', 320); pd.set_option('display.max_rows', 200)
    show = KEY + ['CAGR', 'MDD', 'sideways_ann', 'sideways_invested', 'sideways_t', 'control_side_ann', 'control2_side_ann', 'uptrend_ann', 'downtrend_ann', 'train_side_ann', 'test_side_ann', 'test_side_t', 'test_control_side_ann', 'test_control2_side_ann', 'trades_per_year', 'win_rate', 'payoff']
    print(R.sort_values('train_side_ann', ascending=False)[show].head(24).round(3).to_string(index=False))
    print('EW benchmark:', {k: round(float(v), 3) for k, v in E.items() if k in ('CAGR', 'MDD', 'sideways_ann', 'uptrend_ann', 'downtrend_ann')})
    print('gated cells', len(gated), '| sideways_ann > 0:', int((gated.sideways_ann > 0).sum()), '| sideways_ann >= 4%:', int((gated.sideways_ann >= PARK).sum()),
          '| above control:', int((gated.sideways_ann > gated.control_side_ann).sum()), '| above static control:', int((gated.sideways_ann > gated.control2_side_ann).sum()),
          '| pass test rule:', n_pass, '| pass incl. static control:', n_pass2)
    print('PICK (train):', tuple(pick[KEY]), '| train side %.1f%% | test side %.1f%% t %.2f control %.1f%% static control %.1f%% | subperiods %d | PASSES: %s' % (
        pick.train_side_ann * 100, pick.test_side_ann * 100, pick.test_side_t, pick.test_control_side_ann * 100, pick.test_control2_side_ann * 100, nsub(pick), passes))
    print('total %.0fs' % (time.time() - t0))
