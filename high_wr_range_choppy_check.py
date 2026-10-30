"""Were the stocks choppy enough? Diagnostic for high_wr_range.py (plan addendum in high_wr_range_results/PLAN.md)."""
import zlib
import numpy as np, pandas as pd
import high_wr_range as h
from high_wr_range import G, nw, engine, pu, psl, OUT
from analyze_portfolio_regimes import regime_proxy

CELLS = [(.03, 'none', 10), (.02, 'none', 20)]


def feats(t):
    o, hh, l, c, d, H, L, base, pos = h.prep(t)
    cc = pd.Series(c)
    er = lambda n: ((cc - cc.shift(n)).abs() / cc.diff().abs().rolling(n).sum()).to_numpy()
    e20, e60 = er(20), er(60)
    est = pd.Series(e20 < .2).astype(float).rolling(21).sum().to_numpy() == 21   # this bar and the previous 20
    return o, hh, c, d, H, L, base, pos, e20, e60, est


def sim(cell, seed=None, counts=None):
    tg, _, tmax = cell
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for t in G['fr']:
        o, hh, c, d, H, L, base, pos, e20, e60, est = feats(t)
        n = len(c)
        if rng is None:
            ks = np.flatnonzero(base & (pos <= .2))
        else:
            pool = np.flatnonzero(base & (pos <= .5)); k_ = counts.get(t, 0)
            ks = np.sort(rng.choice(pool, min(k_, len(pool)), replace=False)) if k_ and len(pool) else np.array([], int)
        busy = -1
        for k in ks:
            i = k + 1
            if i <= busy or i + tmax >= n:
                continue
            e = o[i]; tgt = e * (1 + tg)
            for j in range(i, i + tmax):
                if j > i and o[j] >= tgt:
                    px, je = o[j], j; break
                if hh[j] >= tgt:
                    px, je = tgt, j; break
                if j == i + tmax - 1:
                    px, je = c[j], j
            out.append((t, d[i], np.log(px / e), e20[k], est[k], e60[k] < .2, (c[i:je + 1] < L[k]).any(), e20[je] >= .3))
            busy = je
    T = pd.DataFrame(out, columns=['ticker', 'entry', 'gross', 'er20', 'established', 'er60_lt_02', 'closed_below_range_low', 'er20_at_exit_ge_03'])
    T['net_B'] = T.gross - .009
    T['regime'] = T.entry.map(G['reg']).fillna('unknown')
    T['er20_group'] = np.where(T.er20 < .1, 'ER20 < 0.1', 'ER20 0.1-0.2')
    return T


def stats(x, y, lag):
    wn = x.net_B > 0; aw, al = x.gross[wn].mean(), x.gross[~wn].mean()
    dd = x.groupby('entry').net_B.mean().reindex(G['cal'].loc['2000-01-01':'2025-08-15'].index)
    m, se, _ = nw(dd.to_numpy(), lag)
    return dict(trades=len(x), win_rate=wn.mean(), breakeven_wr=(-al + .009) / (aw - al), avg_win_pct=aw * 100, avg_loss_pct=al * 100,
                net_B_pct=x.net_B.mean() * 100, t=m / se if se else np.nan, control_net_pct=y.net_B.mean() * 100 if len(y) else np.nan,
                closed_below_range_low=x.closed_below_range_low.mean(), er20_at_exit_ge_03=x.er20_at_exit_ge_03.mean())


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
    G['cal'] = pd.Series(1, index=pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['cache'] = {}
    G['reg'] = regime_proxy(st)['regime']
    rows = []
    with np.errstate(invalid='ignore', divide='ignore'):
        for cell in CELLS:
            T = sim(cell)
            counts = T.groupby('ticker').size().to_dict()
            C = pd.concat([sim(cell, zlib.crc32(f'{cell}-{s}'.encode()), counts) for s in range(5)])
            lab = f'+{int(cell[0]*100)}%, no stop, {cell[2]} bars'
            rows.append(dict(cell=lab, split='all', group='all', **stats(T, C, cell[2])))
            for col in ['regime', 'er20_group', 'established', 'er60_lt_02', 'closed_below_range_low', 'er20_at_exit_ge_03']:
                for g, x in T.groupby(col):
                    rows.append(dict(cell=lab, split=col, group=str(g), **stats(x, C[C[col] == g], cell[2])))
    D = pd.DataFrame(rows)
    D.to_csv(OUT / 'choppy_check.csv', index=False)
    pd.set_option('display.width', 250)
    print(D.round(3).to_string(index=False))
