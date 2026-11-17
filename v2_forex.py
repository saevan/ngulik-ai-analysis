"""V2 on forex, both directions via inverted pairs, vs Swinger ideal (plan: v2_forex_results/PLAN.md). Descriptive."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from backtest_timehunter_cross_market import forex_daily
from backtest_breakout_er import efficiency_ratio
from evaluate_swinger_like_finalists import PropCosts
from monthly_trend_entry import trend

OUT = Path(__file__).resolve().parent / 'v2_forex_results'
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
COSTS = {'gross': 0., '0.05% RT': .00025, '0.10% RT': .0005}
HALVES = {'H1 2023-05..2024-10': ('2023-05-01', '2024-10-31'), 'H2 2024-11..2026-05': ('2024-11-01', '2026-05-31')}
CAP = 1e9


def frames_for(offset):
    d = forex_daily(engine.load_data('forex')[0], offset)
    fr = {}
    for t, f in d.groupby('Ticker', sort=True):
        f = f.sort_values('Date/Time').reset_index(drop=True)[['Ticker', 'Date/Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'tradable']]
        fr[t] = f
        g = f.copy(); g['Ticker'] = t + '_inv'
        g['Open'], g['High'], g['Low'], g['Close'] = 1 / f.Open, 1 / f.Low, 1 / f.High, 1 / f.Close
        fr[t + '_inv'] = g
    return fr


def v2_kwargs(fr, slip):
    cal = pd.Series(pd.DatetimeIndex(sorted(set(pd.concat([f['Date/Time'] for f in fr.values()])))))
    me_set = set(cal.groupby(cal.dt.to_period('M')).max())
    me = lambda f: f['Date/Time'].isin(me_set).to_numpy(bool)
    k = rc.kw(BASE, 'B')
    k.update(extra_signal_fn=lambda f: me(f) & f.tradable.to_numpy(bool) & trend('F_mom', f) & (efficiency_ratio(f.Close, 20) >= .3).fillna(False).to_numpy(bool),
             extra_exit_signal_fn=lambda f: me(f) & ~trend('F_mom', f), extra_size_div=10, extra_first=True, extra_max_frac=.35,
             failed_exit=None, cost_model=PropCosts(buy_fee=0., sell_fee=0., slip=slip))
    return k


def metrics(eq, tr, fr):
    eq = eq.equity if hasattr(eq, 'equity') else eq
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    tr = tr.copy(); tr['entry_date'] = pd.to_datetime(tr.entry_date); tr['exit_date'] = pd.to_datetime(tr.exit_date)
    w = tr.net_return > 0
    r = dict(CAGR=(eq.iloc[-1] / CAP) ** (1 / yrs) - 1, MDD=(eq / eq.cummax() - 1).min(), trades=len(tr), trades_per_year=len(tr) / yrs, win_rate=w.mean(),
             avg_win=tr.net_return[w].mean(), avg_loss=tr.net_return[~w].mean(), payoff=tr.net_return[w].mean() / -tr.net_return[~w].mean() if (~w).any() and w.any() else np.nan,
             expectancy=tr.net_return.mean(), median_bars=tr.bars.median())
    for h, (a, b) in HALVES.items():
        e = eq.loc[a:b]; x = tr[(tr.entry_date >= a) & (tr.entry_date <= b)]
        r[f'{h} ann'] = (e.iloc[-1] / e.iloc[0]) ** (365.25 / max((e.index[-1] - e.index[0]).days, 1)) - 1 if len(e) > 1 else np.nan
        r[f'{h} trades'] = len(x); r[f'{h} expectancy'] = x.net_return.mean() if len(x) else np.nan
    # days on which a pair and its inverse were held at the same time
    days = {}
    for t in tr.itertuples():
        base = t.ticker.replace('_inv', ''); d = fr[t.ticker]['Date/Time']
        days.setdefault((base, t.ticker.endswith('_inv')), set()).update(d[(d >= t.entry_date) & (d <= t.exit_date)].tolist())
    r['overlap_days'] = sum(len(days.get((p, False), set()) & days.get((p, True), set())) for p in {k[0] for k in days})
    return r


if __name__ == '__main__':
    rows, per = [], []
    with np.errstate(invalid='ignore', divide='ignore'):
        for offset in (4, 0):
            fr = frames_for(offset)
            for cname, slip in COSTS.items():
                eq, tr = run(fr, start='2023-05-01', **v2_kwargs(fr, slip))
                inv = float((eq.market_value / eq.equity).mean())
                rows.append(dict(system='V2', session=f'{offset:02d}:00', cost=cname, invested=inv, **metrics(eq, tr, fr)))
                if offset == 4:
                    tr['direction'] = np.where(tr.ticker.str.endswith('_inv'), 'short', 'long'); tr['pair'] = tr.ticker.str.replace('_inv', '')
                    for (p, dr), x in tr.groupby(['pair', 'direction']):
                        per.append(dict(system='V2', cost=cname, pair=p, direction=dr, trades=len(x), win_rate=(x.net_return > 0).mean(), expectancy=x.net_return.mean(), sum_return=x.net_return.sum()))
                    if cname == 'gross':
                        tr.to_csv(OUT / 'v2_trades_gross_04.csv', index=False); eq.to_csv(OUT / 'v2_equity_gross_04.csv')
                c, t, _ = run_portfolio(fr, 'afl_ideal', buy_fee=0., sell_fee=0., slip=slip)
                inv = float((c.market_value / c.equity).mean())
                rows.append(dict(system='Swinger ideal', session=f'{offset:02d}:00', cost=cname, invested=inv, **metrics(c, t, fr)))
    R = pd.DataFrame(rows); R.to_csv(OUT / 'results.csv', index=False)
    P = pd.DataFrame(per); P.to_csv(OUT / 'per_pair.csv', index=False)
    pd.set_option('display.width', 320); pd.set_option('display.max_rows', 100)
    print(R.round(3).to_string(index=False))
    print(P[P.cost == '0.10% RT'].round(3).to_string(index=False))
