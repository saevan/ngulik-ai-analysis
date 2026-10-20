"""Stale-data and liquidity variants on top of the point-in-time rule (plan addendum in pit_universe_results/PLAN.md).
Also a trade diagnostic: share of entries on one-price bars and order size versus the entry day's traded value."""
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
from backtest_stop_execution import run
from backtest_open_next import stats
import pit_universe as pu

OUT = Path(__file__).resolve().parent / 'pit_universe_results'
G = {}


def stale_ok(fr):
    out = {}
    for t, f in fr.items():
        f = f.set_index('Date/Time')
        traded = (f.Volume > 0).astype(float)
        one = ((f.Open == f.High) & (f.High == f.Low) & (f.Low == f.Close) & (f.Volume > 0)).astype(float)
        ok = (traded.rolling(60).mean().shift(1) >= .9) & (one.rolling(60).mean().shift(1) <= .1)
        out[t] = set(ok.index[ok.values])
    return out


def job(a):
    var, w = a
    s, e = pu.W[w]
    fr = {t: g for t, f in G['fr'].items() if len(g := f[f['Date/Time'] <= e])}
    k = rc.kw(pu.BASE, 'B')
    gates = []
    if 'pit' in var:
        gates.append(G['pit'])
    if 'stale' in var:
        gates.append(G['stale'])
    if gates:
        k['gate_dates'] = {t: set.intersection(*[g[t] for g in gates]) for t in fr}
    if 'cap' in var:
        k['liq_cap'] = .25
    with np.errstate(invalid='ignore', divide='ignore'):
        eq, tr = run(fr, start=s, **k)
    st = stats(eq, tr)
    row = dict(variant=var, window=w, **{x: st[x] for x in ['cagr', 'records', 'mdd', 'n', 'wr', 'invested']})
    if w == 'full' and len(tr):
        T = pd.DataFrame(tr)
        bars = pd.concat([f.assign(Ticker=t) for t, f in G['fr'].items()])
        bars['one_price'] = (bars.Open == bars.High) & (bars.High == bars.Low) & (bars.Low == bars.Close)
        bars['value'] = bars.Close * bars.Volume
        dcol = next(c for c in ['entry_date', 'entry_day', 'date_in', 'entry'] if c in T.columns)
        m = T.merge(bars[['Ticker', 'Date/Time', 'one_price', 'value']], left_on=['ticker', dcol], right_on=['Ticker', 'Date/Time'], how='left')
        row['entries_on_one_price_bar'] = float(m.one_price.mean())
        if 'notional' in m.columns:
            r = m.notional / m.value
            row['median_order_vs_day_value'] = float(r.median())
            row['share_orders_gt_day_value'] = float((r > 1).mean())
    return row


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    G['pit'] = pu.eligibility(G['fr'], .5)
    G['stale'] = stale_ok(G['fr'])
    vars_ = ['unrestricted', 'pit', 'pit_stale', 'pit_cap', 'pit_stale_cap', 'stale_cap']
    with Pool(4) as p:
        rows = p.map(job, [(v, w) for v in vars_ for w in pu.W], chunksize=1)
    d = pd.DataFrame(rows)
    d.to_csv(OUT / 'stale_liquidity.csv', index=False)
    d['v'] = d.apply(lambda r: f"{r.cagr * 100:.1f}/{int(r.records)}/{r.mdd * 100:.0f}", axis=1)
    pd.set_option('display.width', 250)
    print(d.pivot_table(index='variant', columns='window', values='v', aggfunc='first').to_string())
    print(d[d.window == 'full'].drop(columns=['v']).round(3).to_string(index=False))
