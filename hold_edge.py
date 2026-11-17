"""Is holding winners longer our edge, and can it help chase Swinger ideal? (plan: hold_edge_results/PLAN.md)."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from analyze_portfolio_regimes import regime_proxy
import wr_gap_v1 as w
import logic_a_swing5 as la

OUT = Path(__file__).resolve().parent / 'hold_edge_results'
A, B = '2000-01-01', '2025-08-15'
BINS, LAB = [0, 10, 30, 60, 120, 10**6], ['<= 10', '11-30', '31-60', '61-120', '> 120']
G = w.G
st, _ = engine.load_data('stocks')
G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
lab = regime_proxy(st)['regime']
V2 = dict(w.kw('realistic', True, None), failed_exit=None)


def by_hold(t, name):
    t = t[pd.to_datetime(t.entry_date) <= B].copy(); t['hold'] = pd.cut(t.bars, BINS, labels=LAB)
    pnl = t.net_return * (t.notional if 'notional' in t else t.entry_cost) / 1e9 if False else t.net_return   # equal weight per trade
    tot = pnl[pnl.index].sum()
    return [dict(system=name, hold=str(k), share_trades=len(x) / len(t), win_rate=(x.net_return > 0).mean(), mean_return=x.net_return.mean(),
                 share_of_total_return=x.net_return.sum() / tot) for k, x in t.groupby('hold', observed=True)]


def sim_hold_exit(data, cal_, variant):
    """Logic A1 entries with a long-hold exit (H1: Close < SMA30; H2: also a 15% trail from the highest Close)."""
    cap = 1e9; cash = cap; equity = cap
    pos, pend, last, daily, trades = {}, set(), {}, [], []
    days = sorted(cal_)
    for n, day in enumerate(days):
        obs = sorted(cal_[day]); budget = equity * .1; rg = lab.get(day, 'unknown')
        for t, i in obs:
            d = data[t]
            if t in pend and d['tradable'][i]:
                p = pos.pop(t); pend.discard(t)
                px = d['Open'][i] * (1 - la.SLIP); pro = p['qty'] * px * (1 - la.SELL_FEE); cash += pro
                trades.append(dict(ticker=t, entry_date=p['date'], exit_date=day, net_return=pro / p['cost'] - 1, bars=i - p['i'] + 1, regime=p['rg']))
        for t, i in obs:
            d = data[t]
            if t in pos or i == 0 or not d['buy'][i - 1] or not d['tradable'][i] or not d['ok'][i] or len(pos) >= 10:
                continue
            er = d['er20'][i - 1]
            if rg == 'downtrend' or (rg == 'sideways' and not er >= .2):
                continue
            amt = min(budget, cash); amt = min(amt, .25 * d['adv'][i]) if np.isfinite(d['adv'][i]) else 0.
            if amt <= 1e-3:
                continue
            px = d['Open'][i] * (1 + la.SLIP); qty = amt / (px * (1 + la.BUY_FEE)); cash -= amt
            pos[t] = dict(date=day, i=i, qty=qty, cost=amt, rg=rg, hi=d['Close'][i])
        for t, i in obs:
            d = data[t]; last[t] = d['Close'][i]
            if t in pos:
                p = pos[t]; p['hi'] = max(p['hi'], d['Close'][i])
                if i == len(d['Close']) - 1 or n == len(days) - 1:
                    pos.pop(t); pend.discard(t); pro = p['qty'] * d['Close'][i] * (1 - la.SLIP) * (1 - la.SELL_FEE); cash += pro
                    trades.append(dict(ticker=t, entry_date=p['date'], exit_date=day, net_return=pro / p['cost'] - 1, bars=i - p['i'] + 1, regime=p['rg']))
                elif d['Close'][i] < d['sma30'][i] or (variant == 'H2' and d['Close'][i] <= p['hi'] * .85):
                    pend.add(t)
        mv = sum(p['qty'] * last[t] * (1 - la.SLIP) * (1 - la.SELL_FEE) for t, p in pos.items())
        equity = cash + mv
        daily.append(dict(date=day, equity=equity, market_value=mv))
    return pd.DataFrame(daily).set_index('date'), pd.DataFrame(trades)


if __name__ == '__main__':
    with np.errstate(invalid='ignore', divide='ignore'):
        cv, tv = run(G['fr'], start=A, **V2); cv = cv.loc[:B]
        cs, ts, _ = run_portfolio(G['fr'], 'afl_ideal', slip=.0025); cs = cs.loc[:B]
        # 1
        H = pd.DataFrame(by_hold(tv, 'V2 realistic') + by_hold(ts, 'Swinger ideal')); H.to_csv(OUT / 'return_by_hold.csv', index=False)
        # 2
        rows = []
        for mh in (None, 120, 60, 40, 20):
            c, t = (cv, tv) if mh is None else run(G['fr'], start=A, **dict(V2, max_hold=mh, extra_main_exits=False))
            c = c.loc[:B]; e = c.equity; yrs = (e.index[-1] - e.index[0]).days / 365.25
            rows.append(dict(max_hold=mh or 'none (V2)', CAGR=(e.iloc[-1] / 1e9) ** (1 / yrs) - 1, MDD=(e / e.cummax() - 1).min(), win_rate=(t.net_return > 0).mean(),
                             trades=len(t), median_bars=t.bars.median()))
        M = pd.DataFrame(rows); M.to_csv(OUT / 'max_hold_counterfactual.csv', index=False)
        # 3
        after = []
        for r in ts[pd.to_datetime(ts.entry_date) <= B].itertuples():
            f = G['fr'][r.ticker]; d = f['Date/Time'].to_numpy(); c = f.Close.to_numpy(float)
            j = int(np.searchsorted(d, np.datetime64(r.exit_date)))
            row = dict(ticker=r.ticker, exit_date=r.exit_date)
            for h in (20, 60):
                row[f'after_{h}'] = c[j + h] / c[j] - 1 if j + h < len(c) else np.nan
            row['max_60'] = c[j + 1:j + 61].max() / c[j] - 1 if j + 1 < len(c) else np.nan
            after.append(row)
        Af = pd.DataFrame(after); Af.to_csv(OUT / 'swinger_after_exit.csv', index=False)
        # 4
        fr = {t: f for t, f in G['fr'].items()}
        data, cal_ = la.prepare(fr, G['gate'])
        for t, f in fr.items():
            data[t]['sma30'] = f.Close.rolling(30).mean().to_numpy()
        R = []
        cA, tA = la.run(data, cal_, lab, 'A1', .25); R += la.report('A1 swing exit', cA, tA, lab)
        for v in ('H1', 'H2'):
            c, t = sim_hold_exit(data, cal_, v); R += la.report(f'A1 entry + {v} hold exit', c, t, lab)
            t.to_csv(OUT / f'trades_{v}.csv', index=False)
        R += la.report('V2 realistic', cv, tv[pd.to_datetime(tv.entry_date) <= B], lab)
        R += la.report('Swinger ideal', cs, ts[pd.to_datetime(ts.entry_date) <= B], lab)
        D = pd.DataFrame(R); D.to_csv(OUT / 'rule_test.csv', index=False)
    pd.set_option('display.width', 260)
    print(H.round(3).to_string(index=False)); print(M.round(3).to_string(index=False))
    print('Swinger after exit: mean 20d %.1f%% | mean 60d %.1f%% | median 60d %.1f%% | share max-60d >= 20%%: %.0f%% | share 60d >= 20%%: %.0f%%' % (
        Af.after_20.mean() * 100, Af.after_60.mean() * 100, Af.after_60.median() * 100, (Af.max_60 >= .2).mean() * 100, (Af.after_60 >= .2).mean() * 100))
    print(D[D.condition == 'all'][['system', 'CAGR', 'MDD', 'CAGR 2000-07', 'CAGR 2008-15', 'CAGR 2016-20', 'CAGR 2021-25', 'trades_per_year', 'win_rate', 'avg_win', 'avg_loss', 'payoff', 'expectancy', 'median_bars', 'invested']].round(3).to_string(index=False))
    print(D.pivot_table(index='system', columns='condition', values='ann_return').round(3).to_string())
