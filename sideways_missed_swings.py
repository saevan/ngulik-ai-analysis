"""Do we sit out the up-and-down swings in sideways markets? (user question, 20 Oct 2026)
1. Exposure (share of equity invested) and entries per year by market regime ('er20' definition of analyze_sk5_regimes).
2. Hindsight swing inventory: per stock, zigzag up-legs (trough -> peak, reversal threshold 5% and 10%) on daily Closes;
   each leg is labelled with the market regime on its trough day. For every leg: did our system hold that stock on any day
   inside the leg, and how much of the leg's log return fell on days we held it.
Hindsight legs are NOT a tradable benchmark: turning points are only known afterwards.
Systems: v2 main pick, scenario B, unrestricted and realistic (PIT liquidity + stale filter + 25% ADV20 cap), 2000-2025."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu
import pit_stale_liquidity as psl
from analyze_sk5_regimes import regimes
from backtest_stop_execution import run

OUT = Path(__file__).resolve().parent / 'sideways_swings_results'
OUT.mkdir(exist_ok=True)
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
lab = regimes(st)['er20']['regime']
k = rc.kw(pu.BASE, 'B')
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
sys_ = {}
with np.errstate(invalid='ignore', divide='ignore'):
    sys_['unrestricted'] = run(fr, start='2000-01-01', **k)
    sys_['realistic'] = run(fr, start='2000-01-01', **dict(k, liq_cap=.25, gate_dates={t: pit[t] & stale[t] for t in fr}))
rows = []
held = {}
for name, (eq, tr) in sys_.items():
    T = pd.DataFrame(tr)
    eq = eq.loc['2000-01-01':]
    w = (eq.market_value / eq.equity) if 'market_value' in eq else None
    d = pd.DataFrame({'w': w, 'reg': lab.reindex(eq.index)})
    T['reg'] = lab.reindex(pd.to_datetime(T.entry_date)).values
    yrs = d.groupby('reg').size() / 252
    for g, x in d.groupby('reg'):
        tg = T[T.reg == g]
        rows.append(dict(system=name, regime=g, share_days=len(x) / len(d), avg_invested=float(x.w.mean()),
                         days_fully_cash=float((x.w < .01).mean()), entries_per_year=len(tg) / yrs[g],
                         win_rate=float((tg.net_return > 0).mean()), avg_trade=float(tg.net_return.mean())))
    hs = {}
    for r in T.itertuples():
        hs.setdefault(r.ticker, []).append((pd.Timestamp(r.entry_date), pd.Timestamp(r.exit_date)))
    held[name] = hs
pd.DataFrame(rows).to_csv(OUT / 'exposure_by_regime.csv', index=False)


def zigzag(c, th):
    legs, mode, lo_i, hi_i = [], None, 0, 0
    for i in range(1, len(c)):
        if c[i] > c[hi_i]: hi_i = i
        if c[i] < c[lo_i]: lo_i = i
        if mode != 'up' and c[i] >= c[lo_i] * (1 + th):
            mode, hi_i = 'up', i
            trough = lo_i
        elif mode == 'up' and c[i] <= c[hi_i] * (1 - th):
            legs.append((trough, hi_i)); mode, lo_i = 'down', i
    return legs


legs = []
for t, f in fr.items():
    f = f[f.tradable].reset_index(drop=True)
    c = f.Close.to_numpy(float)
    dates = f['Date/Time'].to_numpy()
    for th in [.05, .10]:
        for a, b in zigzag(c, th):
            if dates[a] < np.datetime64('2000-01-01'): continue
            seg = pd.Series(np.log(c[a:b + 1]), index=pd.to_datetime(dates[a:b + 1])).diff().dropna()
            row = dict(ticker=t, th=th, start=pd.Timestamp(dates[a]), end=pd.Timestamp(dates[b]), days=b - a,
                       leg_return=float(c[b] / c[a] - 1), regime=lab.get(pd.Timestamp(dates[a]), 'unknown'))
            for name, hs in held.items():
                m = np.zeros(len(seg), bool)
                for e0, e1 in hs.get(t, []):
                    m |= (seg.index > e0) & (seg.index <= e1)
                row[f'held_any_{name}'] = bool(m.any())
                row[f'captured_share_{name}'] = float(seg[m].sum() / seg.sum()) if seg.sum() > 0 else np.nan
            legs.append(row)
L = pd.DataFrame(legs)
L.to_csv(OUT / 'legs.csv', index=False)
summ = L.groupby(['th', 'regime']).agg(legs_per_year=('ticker', lambda s: len(s) / 25.6), median_leg=('leg_return', 'median'),
                                       median_days=('days', 'median'),
                                       held_any_unrestricted=('held_any_unrestricted', 'mean'), held_any_realistic=('held_any_realistic', 'mean'),
                                       captured_unrestricted=('captured_share_unrestricted', 'mean'), captured_realistic=('captured_share_realistic', 'mean')).reset_index()
summ.to_csv(OUT / 'legs_summary.csv', index=False)
pd.set_option('display.width', 250)
print(pd.DataFrame(rows).round(3).to_string(index=False))
print(summ.round(3).to_string(index=False))
