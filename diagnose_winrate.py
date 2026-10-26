"""Why is our win rate below 50%? Diagnostic on the v2 main pick's own trades (26 Oct 2026, exploratory, no new rules
adopted). Scenario B, 2000-2025, unrestricted and realistic (point-in-time liquidity + stale filter + 25% ADV20 cap);
Swinger ideal (B) for the same character figures.
1. Where losers come from: exit reason, holding time, entry-day behaviour, cost (trades positive before costs but
   negative after), market regime at entry, period.
2. Path of losers: how many were in profit (above the round-trip cost) at some Close before they were sold, and how big.
3. Counterfactual exits on the SAME entries (trade level, no portfolio effects): time exits after N bars, take profit at
   +X%, breakeven stop after +Y%, and price + time combinations - what they do to win rate AND to the average trade.
Writes winrate_diagnosis_results/*.csv"""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from analyze_portfolio_regimes import regime_proxy

OUT = Path(__file__).resolve().parent / 'winrate_diagnosis_results'
OUT.mkdir(exist_ok=True)
COST = .009   # round trip in scenario B: fees 0.15% + 0.25% and 0.25% slippage per side
SLIP = .0025
st, _ = engine.load_data('stocks')
fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
reg = regime_proxy(st)['regime']
BASE = dict(fam='F1', buffer=.005, channel=20, er_min=.2, exit='cand', failed=0., size_div=4)
pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
k = rc.kw(BASE, 'B')
with np.errstate(invalid='ignore', divide='ignore'):
    sysT = {'ours': run(fr, start='2000-01-01', **k)[1],
            'ours_realistic': run(fr, start='2000-01-01', **dict(k, liq_cap=.25, gate_dates={t: pit[t] & stale[t] for t in fr}))[1]}
sysT['swinger_ideal'] = run_portfolio(fr, 'afl_ideal', slip=.0025)[1]


def enrich(T):
    rows = []
    for r in T.itertuples():
        f = fr[r.ticker]
        d = f['Date/Time'].values
        i = int(np.searchsorted(d, np.datetime64(r.entry_date)))
        j = int(np.searchsorted(d, np.datetime64(r.exit_date)))
        e = r.entry_price / (1 + SLIP)   # fill before slippage (scenario B quotes buys at fill * 1.0025)
        ref_exit = r.reference_exit_price if hasattr(r, 'reference_exit_price') else r.exit_price / (1 - SLIP)
        closes = f.Close.values[i:j + 1]
        highs = f.High.values[i:j + 1]
        lows = f.Low.values[i:j + 1]
        held_closes = closes[:-1] if j > i else closes[:1]
        rows.append(dict(ticker=r.ticker, entry_date=r.entry_date, net=r.net_return, raw=ref_exit / e - 1, fill=e,
                         reason=r.reason, bars=r.bars, mfe=highs.max() / e - 1, mae=lows.min() / e - 1,
                         best_close=held_closes.max() / e - 1, entry_day_close=closes[0] / e - 1, regime=reg.get(r.entry_date, 'unknown'),
                         year=pd.Timestamp(r.entry_date).year, i=i, j=j))
    return pd.DataFrame(rows)


def counterfactual(E, name):
    """Same entries (fill before slippage); exits from the bar after entry, sold at that Close (take profit at the target,
    never better); cost 0.90% round trip. time_N and tpX_or_timeN replace ALL original exits (no stop);
    tp_X and be_after_Y are added on top of the original exits."""
    rows = []
    rules = [('original', None)] + [(f'time_{n}', ('time', n)) for n in (5, 10, 20, 40)] + \
            [(f'tp_{int(x*100)}', ('tp', x)) for x in (.03, .05, .10)] + [(f'be_after_{int(y*100)}', ('be', y)) for y in (.03, .05, .10)] + \
            [(f'tp{int(x*100)}_or_time{n}', ('tpt', x, n)) for x in (.05, .10) for n in (10, 20)]
    for lab, rule in rules:
        res = []
        for r in E.itertuples():
            if rule is None:
                res.append(r.net); continue
            f = fr[r.ticker]
            c, h = f.Close.values, f.High.values
            e = r.fill
            out = None
            last = min(len(c) - 1, r.i + 200)
            for b in range(r.i + 1, last + 1):
                if rule[0] in ('tp', 'be') and b >= r.j:   # otherwise keep the original exit
                    out = r.raw; break
                if rule[0] == 'time' and b - r.i >= rule[1]:
                    out = c[b] / e - 1; break
                if rule[0] in ('tp', 'tpt') and h[b] >= e * (1 + rule[1]):
                    out = rule[1]; break
                if rule[0] == 'tpt' and b - r.i >= rule[2]:
                    out = c[b] / e - 1; break
                if rule[0] == 'be' and h[r.i + 1:b + 1].max() >= e * (1 + rule[1]) and c[b] <= e:
                    out = c[b] / e - 1; break
            if out is None:
                out = r.raw
            res.append(out - COST if rule is not None else out)
        x = np.array(res)
        rows.append(dict(system=name, exit_rule=lab, win_rate=(x > 0).mean(), avg_trade=x.mean(), avg_win=x[x > 0].mean(),
                         avg_loss=x[x <= 0].mean(), payout=x[x > 0].mean() / -x[x <= 0].mean()))
    return rows


summ, cf = [], []
for name, T in sysT.items():
    E = enrich(T)
    E.to_csv(OUT / f'trades_{name}.csv', index=False)
    L = E[E.net <= 0]
    s = dict(system=name, trades=len(E), win_rate=(E.net > 0).mean(), win_rate_before_costs=(E.raw > 0).mean(),
             share_lost_to_cost=((E.raw > 0) & (E.net <= 0)).mean(),
             losers_ever_above_cost_at_a_close=(L.best_close > COST).mean(), losers_ever_above_5pct_at_a_close=(L.best_close > .05).mean(),
             losers_mfe_median=L.mfe.median(), losers_mae_median=L.mae.median(), losers_bars_median=L.bars.median(),
             winners_bars_median=E[E.net > 0].bars.median(), entry_day_close_below_entry=(E.entry_day_close < 0).mean(),
             wr_excluding_failed_breakouts=(E[~E.reason.str.startswith('failed')].net > 0).mean(),
             share_of_losers_failed_breakout=L.reason.str.startswith('failed').mean(),
             wr_if_entry_day_close_below=(E[E.entry_day_close < 0].net > 0).mean(), wr_if_entry_day_close_above=(E[E.entry_day_close >= 0].net > 0).mean())
    for g, x in E.groupby('reason'):
        s[f'share_{g}'] = len(x) / len(E); s[f'wr_{g}'] = (x.net > 0).mean()
    for g, x in E.groupby('regime'):
        s[f'wr_regime_{g}'] = (x.net > 0).mean()
    for pn, (a, b) in {'2000-07': (2000, 2007), '2008-15': (2008, 2015), '2016-20': (2016, 2020), '2021-25': (2021, 2025)}.items():
        s[f'wr_{pn}'] = (E[(E.year >= a) & (E.year <= b)].net > 0).mean()
    summ.append(s)
    if name != 'swinger_ideal':
        cf += counterfactual(E, name)
S = pd.DataFrame(summ)
S.to_csv(OUT / 'summary.csv', index=False)
C = pd.DataFrame(cf)
C.to_csv(OUT / 'counterfactual_exits.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
print(S.set_index('system').T.round(3).to_string())
print(C.round(4).to_string(index=False))
