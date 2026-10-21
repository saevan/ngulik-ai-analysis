"""Why does the lowest-low / no-new-trade-high logic lose? Diagnostic on its own trades (exploratory, no new rules).
For three representative cells: decompose each trade's gross return into the best point reached (MFE = log trade-high /
entry) minus the give-back (log trade-high / exit), measure the worst point (MAE), time to the peak; compare the entry's
forward returns with random eligible stock-days (entry information); split by the market regime at entry and by period.
Writes lowest_low_time_results/diagnosis.csv and diagnosis_paths.csv."""
import ast
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from analyze_portfolio_regimes import regime_proxy

T = pd.read_csv('lowest_low_time_results/trades.csv', parse_dates=['signal', 'exit'])
CELLS = ['(10, 3, \'none\', \'next_open\')', '(20, 5, \'none\', \'next_open\')', '(10, 10, \'none\', \'close\')']
st, _ = engine.load_data('stocks')
fr = {str(k): f[f.tradable].reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
reg = regime_proxy(st)['regime']
rows, paths = [], []
for cell in CELLS:
    N, x, filt, entry = ast.literal_eval(cell)
    tr = T[T.cell == cell]
    for r in tr.itertuples():
        f = fr[r.ticker]
        d = f['Date/Time'].values
        s = int(np.searchsorted(d, np.datetime64(r.signal)))
        e = int(np.searchsorted(d, np.datetime64(r.exit)))
        ei = s + 1 if entry == 'next_open' else s
        epx = f.Open.iat[ei] if entry == 'next_open' else f.Close.iat[s]
        xpx = f.Open.iat[e]
        hi = f.High.iloc[ei:e].max() if entry == 'next_open' else max(f.Close.iat[s], f.High.iloc[s + 1:e].max() if e > s + 1 else -np.inf)
        lo = f.Low.iloc[ei:e].min() if entry == 'next_open' else f.Low.iloc[s + 1:e].min() if e > s + 1 else f.Close.iat[s]
        pk = int(np.argmax(f.High.iloc[ei:e].values)) if e > ei else 0
        fwd = {h: np.log(f.Close.iat[min(s + h, len(f) - 1)] / epx) for h in (5, 10, 20)}
        rows.append(dict(cell=cell, ticker=r.ticker, signal=r.signal, gross=np.log(xpx / epx), mfe=np.log(hi / epx),
                         giveback=np.log(hi / xpx), mae=np.log(lo / epx), bars=e - ei, bars_to_peak=pk,
                         regime=reg.get(r.signal, 'unknown'), year=r.signal.year, **{f'fwd{h}': v for h, v in fwd.items()}))
D = pd.DataFrame(rows)
D.to_csv('lowest_low_time_results/diagnosis_trades.csv', index=False)
# random eligible stock-days: forward Close returns from the signal-day Close, same horizons (entry information baseline)
import pit_universe as pu, pit_stale_liquidity as psl
frall = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
pit, stale = pu.eligibility(frall, .5), psl.stale_ok(frall)
base = []
rng = np.random.default_rng(1)
for t, f in fr.items():
    ok = np.isin(f['Date/Time'].values, np.array(sorted(pit[t] & stale[t]), dtype='datetime64[ns]')) & (f['Date/Time'].values >= np.datetime64('2000-01-01'))
    idx = np.flatnonzero(ok)
    idx = idx[idx < len(f) - 21]
    if len(idx) == 0:
        continue
    for i in rng.choice(idx, min(300, len(idx)), replace=False):
        base.append({f'fwd{h}': np.log(f.Close.iat[i + h] / f.Close.iat[i]) for h in (5, 10, 20)} | dict(year=pd.Timestamp(f['Date/Time'].iat[i]).year))
B = pd.DataFrame(base)
out = []
for cell, g in D.groupby('cell'):
    w, l = g[g.gross > .009], g[g.gross <= .009]
    out.append(dict(cell=cell, trades=len(g), gross=g.gross.mean(), mfe=g.mfe.mean(), giveback=g.giveback.mean(), mae=g.mae.mean(),
                    share_mfe_above_cost=(g.mfe > .009).mean(), win_rate_B=(g.gross > .009).mean(),
                    win_mfe=w.mfe.mean(), win_giveback=w.giveback.mean(), loss_mfe=l.mfe.mean(), loss_giveback=l.giveback.mean(),
                    bars=g.bars.mean(), bars_to_peak=g.bars_to_peak.mean(),
                    fwd5=g.fwd5.mean(), fwd10=g.fwd10.mean(), fwd20=g.fwd20.mean(),
                    rand_fwd5=B.fwd5.mean(), rand_fwd10=B.fwd10.mean(), rand_fwd20=B.fwd20.mean(),
                    gross_2000_15=g[g.year <= 2015].gross.mean(), gross_2016_20=g[(g.year >= 2016) & (g.year <= 2020)].gross.mean(),
                    gross_2021_25=g[g.year >= 2021].gross.mean(),
                    **{f'gross_{k}': v for k, v in g.groupby('regime').gross.mean().items()},
                    **{f'share_{k}': v for k, v in g.regime.value_counts(normalize=True).items()}))
O = pd.DataFrame(out)
O.to_csv('lowest_low_time_results/diagnosis.csv', index=False)
pd.set_option('display.width', 250)
print((O.set_index('cell').T * 1).round(4).to_string())
