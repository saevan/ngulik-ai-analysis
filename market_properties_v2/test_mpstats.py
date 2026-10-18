"""Sanity checks for the v2 panel and helpers: alignment, no look-ahead in forward returns, null behaviour of t-stats."""
import numpy as np, pandas as pd
from panel import load
from mpstats import event_series, Mean, sort_series, nw, ols_nw, bh_fdr

P = load()
C, O, T = P['C'], P['O'], P['T']
tk = 'BBCA'
s = pd.DataFrame({'O': O[tk], 'C': C[tk], 'T': T[tk]}).dropna()
d = s.index[s['T'].astype(bool).values][1000]
i = C.index.get_loc(d)
nxt = C.index[i + 1]
assert abs(P['fo'][1].loc[d, tk] - np.log(C.loc[nxt, tk] / O.loc[nxt, tk])) < 1e-12, 'fo[1] must be ln(C[t+1]/O[t+1])'
assert abs(P['fo'][5].loc[d, tk] - np.log(P['Cff'].loc[C.index[i + 5], tk] / O.loc[nxt, tk])) < 1e-9
# clean level removes the PWON Mar-2000 bad print: 5-day forward return across it stays small
assert abs(P['fc'][5].loc['2000-03-17', 'PWON']) < .3, P['fc'][5].loc['2000-03-17', 'PWON']
# Null: random events -> abnormal 20d mean ~ 0
rng = np.random.default_rng(7)
ts = []
for k in range(20):
    mask = pd.DataFrame(rng.random(C.shape) < .02, index=C.index, columns=C.columns)
    ser, n = event_series(P, mask, 20)
    ts.append(Mean(ser, 20).at('2000-01-01', '2025-12-31')[1])
ts = np.array(ts)
print('random-event t (20 draws): mean %.2f sd %.2f max|t| %.2f' % (ts.mean(), ts.std(), np.abs(ts).max()))
assert np.abs(ts).max() < 3.5 and ts.std() < 1.6
# Look-ahead planted signal must be detected
cheat = P['fo'][20] > 0
ser, n = event_series(P, cheat, 20)
assert Mean(ser, 20).at('2000-01-01', '2025-12-31')[1] > 10
# Random sort signal -> long-short t ~ N(0,1)
tt = []
for k in range(10):
    sig = pd.DataFrame(rng.random(C.shape), index=C.index, columns=C.columns)
    ss = sort_series(P, sig)
    tt.append(Mean(ss.hl, 2).at('2000-01-01', '2025-12-31')[1])
print('random-sort t (10 draws):', np.round(tt, 2))
assert np.abs(tt).max() < 3.5
# nw on iid noise vs analytic; ols dummy equals difference of means
x = rng.normal(size=5000)
m, se, n = nw(x, 0)
assert abs(se - x.std() / np.sqrt(5000)) / se < .01
D = (rng.random(5000) < .3).astype(float)
b, t, n = ols_nw(x, np.column_stack([np.ones(5000), D]), 5)
assert abs(b[1] - (x[D == 1].mean() - x[D == 0].mean())) < 1e-10
q = bh_fdr([.01, .04, .03, .2])
assert np.allclose(q, [.04, .0533333, .0533333, .2], atol=1e-6)
print('all checks passed; bad returns masked:', P['bad_count'])
