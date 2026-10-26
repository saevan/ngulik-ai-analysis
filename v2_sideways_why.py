"""Why is V2's expectancy per trade higher than Swinger ideal's for trades ENTERED in a sideways market? (26 Oct 2026,
descriptive). For trades entered on a sideways-labelled day: split by kind (breakout / monthly), holding length, return
per bar held, median vs mean (big-winner dependence), and where the move happened while held: daily Close-to-Close log
returns from the entry bar to the exit-decision bar attributed to the market condition of each day.
Scenario B 2000-2025.08. Writes quality_vs_swinger_results/v2_sideways_why.csv"""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from analyze_portfolio_regimes import regime_proxy
import wr_gap_v1 as w

G = w.G
st, _ = engine.load_data('stocks')
G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
lab = regime_proxy(st)['regime']
YRS = (pd.Timestamp('2025-08-15') - pd.Timestamp('2000-01-01')).days / 365.25
S = {}
with np.errstate(invalid='ignore', divide='ignore'):
    for v in ('realistic', 'unrestricted'):
        S[f'V2 {v}'] = run(G['fr'], start='2000-01-01', **dict(w.kw(v, True, None), failed_exit=None))[1]
t = run_portfolio(G['fr'], 'afl_ideal', slip=.0025)[1]
t['kind'] = 'swinger'
S['Swinger ideal'] = t
rows = []
for name, T in S.items():
    T = T[pd.to_datetime(T.entry_date) <= '2025-08-15'].copy()
    T = T[lab.reindex(pd.to_datetime(T.entry_date)).to_numpy() == 'sideways']
    rec = []
    for r in T.itertuples():
        f = G['fr'][r.ticker]
        d = f['Date/Time'].values
        i, j = int(np.searchsorted(d, np.datetime64(r.entry_date))), int(np.searchsorted(d, np.datetime64(r.exit_date)))
        close_exit = name == 'Swinger ideal' or r.reason.endswith('gapdown_close') or r.reason.startswith('period_end')
        k = j if close_exit else max(i, j - 1)
        c = f.Close.to_numpy()
        lr = np.diff(np.log(c[i:k + 1]))
        days = pd.DatetimeIndex(d[i + 1:k + 1])
        g = lab.reindex(days).to_numpy()
        rec.append(dict(kind=r.kind, net=r.net_return, bars=r.bars, up=lr[g == 'uptrend'].sum(), side=lr[g == 'sideways'].sum(),
                        down=lr[g == 'downtrend'].sum(), n_up=(g == 'uptrend').sum(), n_side=(g == 'sideways').sum(), n_down=(g == 'downtrend').sum()))
    R = pd.DataFrame(rec)
    for kd in ['all'] + sorted(R.kind.unique()) if name != 'Swinger ideal' else ['all']:
        x = R if kd == 'all' else R[R.kind == kd]
        nd = x[['n_up', 'n_side', 'n_down']].sum()
        top = x.net.sort_values(ascending=False)
        rows.append(dict(system=name, kind=kd, trades_per_year=len(x) / YRS, win_rate=(x.net > 0).mean(), mean_net=x.net.mean(),
                         median_net=x.net.median(), mean_without_top10pct=top.iloc[len(top) // 10:].mean(), mean_bars=x.bars.mean(),
                         net_per_bar=x.net.mean() / x.bars.mean(), share_days_up=nd.n_up / nd.sum(), share_days_side=nd.n_side / nd.sum(),
                         share_days_down=nd.n_down / nd.sum(), logret_on_up_days=x.up.mean(), logret_on_side_days=x.side.mean(),
                         logret_on_down_days=x.down.mean()))
D = pd.DataFrame(rows)
D.to_csv('quality_vs_swinger_results/v2_sideways_why.csv', index=False)
pd.set_option('display.width', 260); pd.set_option('display.max_columns', 30)
print(D.round(4).to_string(index=False))
