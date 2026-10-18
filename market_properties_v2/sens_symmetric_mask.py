"""Sensitivity (not pre-registered): the pre-registered panel masks simple daily |returns| >= 50%, which masks the
+50% leg of a spike but keeps its reverting leg (-33%), leaving 26 permanent spurious level shifts (flagged by the W1
analyst; mostly 1998-2003 penny stocks at the Rp50 floor). This rebuilds the panel with a symmetric log threshold
|ln(1+r)| >= ln 1.5 (both legs masked) into cache/panel_sym.pkl and reruns families A-D on it.
Writes results/SENS_symmask_ABCD.csv (primary rows on the symmetric panel)."""
import pickle
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import panel

SYM = HERE / 'cache' / 'panel_sym.pkl'


def build_sym():
    import grid_search_timehunter as engine
    df, _ = engine.load_data('stocks')
    piv = lambda c: df.pivot(index='Date/Time', columns='Ticker', values=c).sort_index()
    O, H, L, C, V = (piv(c) for c in ['Open', 'High', 'Low', 'Close', 'Volume'])
    T = piv('tradable').reindex_like(C).fillna(False).astype(bool)
    first = C.apply(lambda s: s.first_valid_index())
    Ct = C.where(T)
    prev = Ct.ffill().shift(1)
    lr = np.log(Ct / prev)
    bad = lr.abs() >= np.log(1.5)
    simple = (Ct / prev - 1).mask(bad)
    r_cc = lr.mask(bad)
    r_on = np.log(O.where(T) / prev).mask(bad)
    r_id = np.log(Ct / O.where(T)).mask(bad)
    listed = C.notna().cumsum() > 0
    lnP = r_cc.fillna(0.).cumsum().where(listed)
    lnO = (lnP.shift(1) + r_on).where(T)
    lnH = (lnP + np.log(H / C)).where(T)
    lnL = (lnP + np.log(L / C)).where(T)
    fo = {h: (lnP.shift(-h) - lnO.shift(-1)) for h in panel.HORIZONS}
    fc = {h: (lnP.shift(-h) - lnP).where(T) for h in panel.HORIZONS}
    P = dict(O=O, H=H, L=L, C=C, V=V, T=T, Cff=Ct.ffill(), lnP=lnP, lnO=lnO, lnH=lnH, lnL=lnL, bad=bad,
             value=(Ct * V).where(T), r_cc=r_cc, r_on=r_on, r_id=r_id, fo=fo, fc=fc, idx_ret=simple.mean(axis=1),
             idx_n=simple.notna().sum(axis=1), first=first,
             post2018=sorted(first[first >= pd.Timestamp('2018-01-01')].index), bad_count=int(bad.sum().sum()))
    with open(SYM, 'wb') as f:
        pickle.dump(P, f, protocol=pickle.HIGHEST_PROTOCOL)
    return P


if __name__ == '__main__':
    if not SYM.exists():
        P = build_sym()
        print('symmetric panel built; masked', P['bad_count'])
    panel.CACHE = SYM
    import abcd_battery as ab
    print('masked in loaded panel:', ab.P['bad_count'])
    rows = []
    for fn in [ab.family_a, ab.family_b, ab.family_c, ab.family_d]:
        rows += fn()
    res = pd.DataFrame(rows)
    res.to_csv(HERE / 'results' / 'SENS_symmask_ABCD.csv', index=False)
    base = pd.concat([pd.read_csv(HERE / 'results' / f'{k}_tests.csv') for k in 'ABCD'])
    m = base[['test_id', 'eff_MAIN', 't_MAIN']].merge(res[['test_id', 'eff_MAIN', 't_MAIN']], on='test_id', suffixes=('_base', '_sym'))
    pd.set_option('display.width', 200)
    print(m.round(3).to_string(index=False))
