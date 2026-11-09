"""Logic A: 5-day swing breakout, executed realistically (plan: logic_a_swing5_results/PLAN.md)."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_prototype_swinger import signals, run_portfolio
from analyze_portfolio_regimes import regime_proxy

OUT = Path(__file__).resolve().parent / 'logic_a_swing5_results'
BUY_FEE, SELL_FEE, SLIP = .0015, .0025, .0025
A, B = '2000-01-01', '2025-08-15'
YRS = (pd.Timestamp(B) - pd.Timestamp(A)).days / 365.25
SUB = {'2000-07': ('2000-01-01', '2007-12-31'), '2008-15': ('2008-01-01', '2015-12-31'), '2016-20': ('2016-01-01', '2020-12-31'), '2021-25': ('2021-01-01', B)}


def prepare(fr, gate):
    data, cal = {}, {}
    for t, f in fr.items():
        s = signals(f, 5); c = f.Close
        d = {k: f[k].to_numpy() for k in ['Open', 'Close', 'tradable', 'Date/Time']}
        d['buy'], d['sell'] = s.buy.to_numpy(), s.sell.to_numpy()
        d['er20'] = ((c - c.shift(20)).abs() / c.diff().abs().rolling(20).sum()).to_numpy()
        d['adv'] = (f.Close * f.Volume).shift(1).rolling(20).mean().to_numpy(float)
        d['ok'] = np.isin(d['Date/Time'], np.array(sorted(gate[t]), dtype='datetime64[ns]')) if gate is not None else np.ones(len(f), bool)
        data[t] = d
        for i, day in enumerate(d['Date/Time']):
            if np.datetime64(A) <= day <= np.datetime64(B):
                cal.setdefault(pd.Timestamp(day), []).append((t, i))
    return data, cal


def run(data, cal, lab, variant, liq_cap):
    cap = 1e9; cash = cap; equity = cap
    pos, pend, last, daily, trades = {}, set(), {}, [], []
    days = sorted(cal)
    for n, day in enumerate(days):
        obs = sorted(cal[day]); budget = equity * .1; rg = lab.get(day, 'unknown')
        for t, i in obs:                      # exits at the Open
            d = data[t]
            if t in pos and i > 0 and d['sell'][i - 1]:
                pend.add(t)
            if t in pend and d['tradable'][i]:
                p = pos.pop(t); pend.discard(t)
                px = d['Open'][i] * (1 - SLIP); pro = p['qty'] * px * (1 - SELL_FEE); cash += pro
                trades.append(dict(ticker=t, entry_date=p['date'], exit_date=day, net_return=pro / p['cost'] - 1, bars=i - p['i'] + 1, regime=p['rg']))
        for t, i in obs:                      # entries at the Open
            d = data[t]
            if t in pos or i == 0 or not d['buy'][i - 1] or not d['tradable'][i] or not d['ok'][i] or len(pos) >= 10:
                continue
            er = d['er20'][i - 1]
            if variant == 'A1' and (rg == 'downtrend' or (rg == 'sideways' and not er >= .2)):
                continue
            if variant == 'A2' and rg in ('sideways', 'downtrend') and not er >= .2:
                continue
            amt = min(budget, cash)
            if liq_cap is not None:
                amt = min(amt, liq_cap * d['adv'][i]) if np.isfinite(d['adv'][i]) else 0.
            if amt <= 1e-3:
                continue
            px = d['Open'][i] * (1 + SLIP); qty = amt / (px * (1 + BUY_FEE)); cash -= amt
            pos[t] = dict(date=day, i=i, qty=qty, cost=amt, rg=rg)
        for t, i in obs:                      # mark at the Close, close out at a stock's last bar
            d = data[t]; last[t] = d['Close'][i]
            if t in pos and (i == len(d['Close']) - 1 or n == len(days) - 1):
                p = pos.pop(t); pend.discard(t); pro = p['qty'] * d['Close'][i] * (1 - SLIP) * (1 - SELL_FEE); cash += pro
                trades.append(dict(ticker=t, entry_date=p['date'], exit_date=day, net_return=pro / p['cost'] - 1, bars=i - p['i'] + 1, regime=p['rg']))
        mv = sum(p['qty'] * last[t] * (1 - SLIP) * (1 - SELL_FEE) for t, p in pos.items())
        equity = cash + mv
        daily.append(dict(date=day, equity=equity, market_value=mv))
    return pd.DataFrame(daily).set_index('date'), pd.DataFrame(trades)


def report(name, c, t, lab):
    rows = []
    eq = c.equity; dr = eq.pct_change().dropna(); g_ = lab.reindex(dr.index)
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    base = dict(system=name, CAGR=(eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1, MDD=(eq / eq.cummax() - 1).min())
    for k, (a, b) in SUB.items():
        e = eq.loc[a:b]; base[f'CAGR {k}'] = (e.iloc[-1] / e.iloc[0]) ** (365.25 / (e.index[-1] - e.index[0]).days) - 1
    t = t.copy(); t['regime'] = lab.reindex(pd.to_datetime(t.entry_date)).to_numpy()
    for g in ('uptrend', 'sideways', 'downtrend', 'all'):
        y = dr if g == 'all' else dr[g_ == g]
        x = t if g == 'all' else t[t.regime == g]; r = x.net_return; w = r > 0
        rows.append(dict(base, condition=g, ann_return=float((1 + y).prod() ** (252 / len(y)) - 1), invested=float((c.market_value / c.equity).reindex(y.index).mean()),
                         trades_per_year=len(x) / YRS, win_rate=w.mean(), avg_win=r[w].mean(), avg_loss=r[~w].mean(), payoff=r[w].mean() / -r[~w].mean(),
                         expectancy=r.mean(), median_bars=x.bars.median()))
    return rows


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    lab = regime_proxy(st)['regime']
    pit, stale = pu.eligibility(fr, .5), psl.stale_ok(fr)
    R = []
    with np.errstate(invalid='ignore', divide='ignore'):
        for ver, gate, cap in [('realistic', {t: pit[t] & stale[t] for t in fr}, .25), ('unrestricted', None, None)]:
            data, cal = prepare(fr, gate)
            for v in ('A0', 'A1', 'A2'):
                c, t = run(data, cal, lab, v, cap)
                t.to_csv(OUT / f'trades_{v}_{ver}.csv', index=False)
                R += report(f'{v} {ver}', c, t, lab)
        c, t, _ = run_portfolio(fr, 'afl_ideal', slip=SLIP)
        c = c.loc[:B]; t = t[pd.to_datetime(t.entry_date) <= B]
        R += report('Swinger ideal', c, t, lab)
    D = pd.DataFrame(R); D.to_csv(OUT / 'results.csv', index=False)
    pd.set_option('display.width', 250)
    print(D[D.condition == 'all'][['system', 'CAGR', 'MDD'] + [f'CAGR {k}' for k in SUB]].round(3).to_string(index=False))
    print(D[['system', 'condition', 'ann_return', 'invested', 'trades_per_year', 'win_rate', 'avg_win', 'avg_loss', 'payoff', 'expectancy', 'median_bars']].round(3).to_string(index=False))
