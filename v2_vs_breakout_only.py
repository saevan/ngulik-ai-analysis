"""Own monthly exit vs existing exits vs no monthly module (26 Oct 2026): paired test of V2 (monthly module with its own exit)
against 'breakout only' (V2 without the monthly module). Monthly log-return difference with Newey-West t (lag 6), years
better, subperiods. Writes monthly_entry_main_exits_results/v2_vs_breakout_only.csv"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
import wr_gap_v1 as w
import monthly_f1_sma30 as mf

G = w.G
st, _ = engine.load_data('stocks')
G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
rows = []
for v in ('realistic', 'unrestricted'):
    eq = {}
    for cell in ('V2 now', 'breakout only'):
        with np.errstate(invalid='ignore', divide='ignore'):
            eq[cell] = run(G['fr'], start='2000-01-01', **mf.kw(v, cell))[0].equity.loc[:'2025-08-15']
    m = {k: e.resample('ME').last() for k, e in eq.items()}
    d = (np.log(m['V2 now']).diff() - np.log(m['breakout only']).diff()).dropna()
    mu, se, _ = nw(d.to_numpy(), 6)
    y = {k: pd.concat([pd.Series([1e9], index=[pd.Timestamp('1999-12-31')]), e]).resample('YE').last().pct_change().dropna() for k, e in eq.items()}
    rows.append(dict(version=v, monthly_diff_pct=mu * 100, t_nw=mu / se, months_better=float((d > 0).mean()),
                     years_better=int((y['V2 now'] > y['breakout only']).sum()), years=len(y['V2 now'])))
D = pd.DataFrame(rows)
D.to_csv('monthly_entry_main_exits_results/v2_vs_breakout_only.csv', index=False)
print(D.round(3).to_string(index=False))
