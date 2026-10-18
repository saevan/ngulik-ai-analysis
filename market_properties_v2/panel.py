"""Shared daily panel for the market-properties v2 study (Kompas100 file, 100 current tickers, 1994-07-12..2025-08-15).

Matrices are Date x Ticker on the market calendar (union of trading dates). Bars with Volume 0 are not tradable: their
prices are ignored, returns across them are measured from the last tradable Close. Simple daily |returns| >= 50% are
treated as data errors or unadjusted corporate actions (123 cases, e.g. PWON 17 -> 87 -> 17 in Mar 2000): their returns
are NaN and the jump is removed from the CLEAN log-price levels lnP/lnO/lnH/lnL (cumulative clean log returns), which
all level-based signals (HHV, momentum, SMA) and forward returns should use. Forward returns enter at the NEXT market
day's Open (stock must be tradable that day) and exit at the Close h market days after the signal day (last tradable
Close carried); windows are measured on the clean levels.
Build once with `python market_properties_v2/panel.py`; load with `load()`.
"""
from pathlib import Path
import pickle, sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CACHE = HERE / 'cache' / 'panel.pkl'
SUBPERIODS = {'P1': ('2000-01-01', '2007-12-31'), 'P2': ('2008-01-01', '2015-12-31'),
              'P3': ('2016-01-01', '2020-12-31'), 'P4': ('2021-01-01', '2025-12-31')}
MAIN = ('2000-01-01', '2025-12-31')
P0 = ('1994-01-01', '1999-12-31')   # warm-up only in earlier portfolio backtests; secondary check, 27-36 tickers
HORIZONS = (1, 5, 10, 20, 60)


def build():
    sys.path.insert(0, str(ROOT))
    import grid_search_timehunter as engine
    df, _ = engine.load_data('stocks')
    piv = lambda c: df.pivot(index='Date/Time', columns='Ticker', values=c).sort_index()
    O, H, L, C, V = (piv(c) for c in ['Open', 'High', 'Low', 'Close', 'Volume'])
    T = piv('tradable').reindex_like(C).fillna(False).astype(bool)
    first = C.apply(lambda s: s.first_valid_index())
    Ct = C.where(T)
    Cff = Ct.ffill()
    prev = Cff.shift(1)
    simple = Ct / prev - 1
    bad = simple.abs() >= .5
    r_cc = np.log(Ct / prev).mask(bad)
    r_on = np.log(O.where(T) / prev).mask(bad)
    r_id = np.log(Ct / O.where(T)).mask(bad)
    listed = C.notna().cumsum() > 0
    lnP = r_cc.fillna(0.).cumsum().where(listed)            # clean log Close level (flat on non-tradable days)
    lnO = (lnP.shift(1) + r_on).where(T)                    # clean log Open level
    lnH = (lnP + np.log(H / C)).where(T)
    lnL = (lnP + np.log(L / C)).where(T)
    fo = {h: (lnP.shift(-h) - lnO.shift(-1)) for h in HORIZONS}
    fc = {h: (lnP.shift(-h) - lnP).where(T) for h in HORIZONS}
    ew = simple.mask(bad).mean(axis=1)
    P = dict(O=O, H=H, L=L, C=C, V=V, T=T, Cff=Cff, lnP=lnP, lnO=lnO, lnH=lnH, lnL=lnL, bad=bad,
             value=(Ct * V).where(T), r_cc=r_cc, r_on=r_on, r_id=r_id,
             fo=fo, fc=fc, idx_ret=ew, idx_n=simple.mask(bad).notna().sum(axis=1), first=first,
             post2018=sorted(first[first >= pd.Timestamp('2018-01-01')].index), bad_count=int(bad.sum().sum()))
    CACHE.parent.mkdir(exist_ok=True)
    with open(CACHE, 'wb') as f:
        pickle.dump(P, f, protocol=pickle.HIGHEST_PROTOCOL)
    return P


def load():
    if not CACHE.exists():
        return build()
    with open(CACHE, 'rb') as f:
        return pickle.load(f)


def universe(P, name):
    """'all' = 100 tickers; 'pre2018' = without the 20 tickers whose first bar is 2018 or later."""
    cols = P['C'].columns
    return list(cols) if name == 'all' else [c for c in cols if c not in set(P['post2018'])]


if __name__ == '__main__':
    P = build()
    print('days', len(P['C']), 'tickers', P['C'].shape[1], 'post2018', len(P['post2018']), 'bad returns masked', P['bad_count'])
