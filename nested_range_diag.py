"""Descriptive addendum for nested_range: returns by exit type and how often the fill day also broke the medium-range low."""
import numpy as np, pandas as pd
import nested_range as nr
from nested_range import G, engine, pu, psl, regime_proxy, OUT

st, _ = engine.load_data('stocks')
G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
G['ok'] = {t: np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]') for t in G['fr']}
G['lab'] = regime_proxy(st)['regime']
rows = []
with np.errstate(invalid='ignore', divide='ignore'):
    G['cache'] = {t: nr.prep(t) for t in G['fr']}
    for cell in [(20, 5, 'small high', .03, 10, True), (40, 10, 'small high', .03, 20, True), (20, 10, 'medium mid', .03, 10, True)]:
        X = nr.sim(cell)
        for why, x in list(X.groupby('why')) + [('all', X)]:
            rows.append(dict(cell=str(cell), exit=why, share=len(x) / len(X), avg_gross_pct=x.gross.mean() * 100, avg_bars=x.bars.mean()))
        # share of fills where the fill day's Low also broke the medium-range low (a breakdown, not a bounce)
        br = []
        for t, g in X.groupby('ticker'):
            P = G['cache'][t]; idx = np.searchsorted(P['d'], g.entry.to_numpy())
            br += list(P['l'][idx] < P[f'L{cell[0]}'][idx - 1])
        rows.append(dict(cell=str(cell), exit='fill day broke medium low', share=float(np.mean(br))))
R = pd.DataFrame(rows); R.to_csv(OUT / 'exit_diagnostic.csv', index=False)
pd.set_option('display.width', 200); print(R.round(3).to_string(index=False))
