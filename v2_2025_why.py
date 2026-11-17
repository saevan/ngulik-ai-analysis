"""Why did V2 win in 2025? (addendum in v2_lag_when_results/PLAN.md). Descriptive."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from analyze_portfolio_regimes import regime_proxy
import wr_gap_v1 as w

OUT = Path(__file__).resolve().parent / 'v2_lag_when_results'
Y0, Y1 = pd.Timestamp('2024-12-31'), pd.Timestamp('2025-08-15')
G = w.G
st, _ = engine.load_data('stocks')
G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
rp = regime_proxy(st)
first = {t: f['Date/Time'].min() for t, f in G['fr'].items()}
close = {t: f.set_index('Date/Time').Close for t, f in G['fr'].items()}
with np.errstate(invalid='ignore', divide='ignore'):
    cv, tv = run(G['fr'], start='2000-01-01', **dict(w.kw('realistic', True, None), failed_exit=None))
    cs, ts, _ = run_portfolio(G['fr'], 'afl_ideal', slip=.0025)


def year_pnl(c, t, qty_col, kind_col=None):
    t = t.copy(); t['entry_date'] = pd.to_datetime(t.entry_date); t['exit_date'] = pd.to_datetime(t.exit_date)
    t = t[(t.exit_date > Y0) & (t.entry_date <= Y1)]
    eq0 = float(c.equity.loc[:Y0].iloc[-1]); rows = []
    for r in t.itertuples():
        q = getattr(r, qty_col)
        start_val = q * close[r.ticker].loc[:Y0].iloc[-1] if r.entry_date <= Y0 else getattr(r, 'notional', None) or r.entry_cost
        end_val = q * r.exit_price * (1 - .0025) if r.exit_date <= Y1 else q * close[r.ticker].loc[:Y1].iloc[-1]
        if r.exit_date <= Y1:
            end_val = (getattr(r, 'pnl') + (r.notional if hasattr(r, 'notional') else r.entry_cost)) if r.entry_date > Y0 else end_val
        rows.append(dict(ticker=r.ticker, kind=getattr(r, kind_col) if kind_col else 'swinger', entry=r.entry_date.date(), exit=r.exit_date.date(),
                         bars=r.bars, trade_return=r.net_return, pnl_2025=end_val - start_val, listed=first[r.ticker].date()))
    P = pd.DataFrame(rows); P['share_of_2025_equity_gain'] = P.pnl_2025 / (float(c.equity.loc[:Y1].iloc[-1]) - eq0); P['pct_of_start_equity'] = P.pnl_2025 / eq0
    return P.sort_values('pnl_2025', ascending=False), eq0


Pv, e0v = year_pnl(cv, tv, 'q', 'kind')
Ps, e0s = year_pnl(cs, ts, 'quantity')
Pv.to_csv(OUT / 'y2025_v2_positions.csv', index=False); Ps.to_csv(OUT / 'y2025_swinger_positions.csv', index=False)
rv = cv.equity.loc[:Y1].iloc[-1] / e0v - 1; rs = cs.equity.loc[:Y1].iloc[-1] / e0s - 1
pd.set_option('display.width', 250)
print('V2 2025 %.1f%% | positions %d | by module %% of start equity:' % (rv * 100, len(Pv)), (Pv.groupby('kind').pct_of_start_equity.sum() * 100).round(1).to_dict())
for n in (1, 3, 5):
    print(f'  top {n} share of gain %.0f%% | 2025 return without top {n}: %.1f%%' % (Pv.head(n).share_of_2025_equity_gain.sum() * 100, (rv - Pv.head(n).pct_of_start_equity.sum()) * 100))
print(Pv.head(10).round(3).to_string(index=False))
print('V2 2025 positions win rate %.0f%%, median trade return %.1f%%' % ((Pv.pnl_2025 > 0).mean() * 100, Pv.trade_return.median() * 100))
print('\nSwinger 2025 %.1f%% | trades %d | win rate %.0f%% | median %.1f%%' % (rs * 100, len(Ps), (Ps.pnl_2025 > 0).mean() * 100, Ps.trade_return.median() * 100))
for n in (1, 3, 5):
    print(f'  top {n} share %.0f%% | without top {n}: %.1f%%' % (Ps.head(n).share_of_2025_equity_gain.sum() * 100, (rs - Ps.head(n).pct_of_start_equity.sum()) * 100))
print(Ps.head(5).round(3).to_string(index=False)); print(Ps.tail(5).round(3).to_string(index=False))
# overlap: Swinger trades in V2's top-5 stocks
top5 = list(Pv.head(5).ticker)
print('\nSwinger trades in V2 top-5 stocks during 2025:', Ps[Ps.ticker.isin(top5)].groupby('ticker').agg(trades=('pnl_2025', 'size'), pct=('pct_of_start_equity', 'sum'), median_bars=('bars', 'median')).round(3).to_dict('index'))
# 3. market by month
m = pd.DataFrame({'V2': cv.equity, 'Swinger': cs.equity, 'market': rp.proxy}).loc['2024-12-01':Y1].resample('ME').last().pct_change().dropna()
m['regime_mix'] = rp.regime.loc['2025-01-01':Y1].groupby(rp.regime.loc['2025-01-01':Y1].index.to_period('M')).agg(lambda s: s.value_counts(normalize=True).round(2).to_dict()).values
print((m[['V2', 'Swinger', 'market']] * 100).round(1).assign(regime=m.regime_mix).to_string())
m.to_csv(OUT / 'y2025_monthly.csv')
