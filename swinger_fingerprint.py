"""Swinger ideal fingerprint per market condition (plan: swinger_fingerprint_results/PLAN.md). Descriptive only."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_prototype_swinger import run_portfolio
from analyze_portfolio_regimes import regime_proxy

OUT = Path(__file__).resolve().parent / 'swinger_fingerprint_results'
SLIP, COST = .0025, .009
A, B = '2000-01-01', '2025-08-15'
YEARS = (pd.Timestamp(B) - pd.Timestamp(A)).days / 365.25


def features(f):
    c, h, l = f.Close, f.High, f.Low
    er = (c - c.shift(20)).abs() / c.diff().abs().rolling(20).sum()
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    hh, ll = h.rolling(20).max(), l.rolling(20).min()
    return pd.DataFrame({'stock_er20': er, 'ret_5d': c / c.shift(5) - 1, 'ret_20d': c / c.shift(20) - 1, 'ret_60d': c / c.shift(60) - 1,
                         'vs_sma30': c / c.rolling(30).mean() - 1, 'vs_sma120': c / c.rolling(120).mean() - 1,
                         'range20_pos': (c - ll) / (hh - ll), 'atr14_pct': tr.rolling(14).mean() / c,
                         'new_20d_close_high': (c >= c.shift(1).rolling(20).max()).astype(float)})


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    fr = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    reg = regime_proxy(st)['regime']
    _, T, _ = run_portfolio(fr, 'afl_ideal', slip=SLIP)
    T = T[(T.entry_date >= A) & (T.entry_date <= B)].copy()
    F = {t: features(f) for t, f in fr.items()}
    rows = []
    for r in T.itertuples():
        f = fr[r.ticker]; d = f['Date/Time'].values
        i = int(np.searchsorted(d, np.datetime64(r.entry_date))); j = int(np.searchsorted(d, np.datetime64(r.exit_date)))
        fill, xfill = r.entry_price / (1 + SLIP), r.exit_price / (1 - SLIP)
        ci, cj = f.Close.values[i], f.Close.values[j]
        rows.append(dict(ticker=r.ticker, entry_date=r.entry_date, regime=reg.get(r.entry_date, 'unknown'), net=r.net_return, bars=r.bars,
                         entry_leg=np.log(ci / fill), move_leg=np.log(cj / ci), exit_leg=np.log(xfill / cj),
                         cost_leg=np.log1p(r.net_return) - np.log(xfill / fill), c2c_net=cj / ci - 1 - COST, **F[r.ticker].iloc[i].to_dict()))
    E = pd.DataFrame(rows)
    E.to_csv(OUT / 'trades.csv.gz', index=False)

    # A + B per condition
    def char(x):
        w = x.net > 0; m = x.move_leg.sort_values(ascending=False)
        return pd.Series(dict(trades=len(x), trades_per_year=len(x) / YEARS, win_rate=w.mean(), avg_win_pct=x.net[w].mean() * 100,
                              avg_loss_pct=x.net[~w].mean() * 100, expectancy_pct=x.net.mean() * 100, median_bars=x.bars.median(),
                              entry_leg_pct=x.entry_leg.mean() * 100, move_leg_pct=x.move_leg.mean() * 100, exit_leg_pct=x.exit_leg.mean() * 100,
                              cost_leg_pct=x.cost_leg.mean() * 100, c2c_win_rate=(x.c2c_net > 0).mean(), c2c_expectancy_pct=x.c2c_net.mean() * 100,
                              c2c_median_pct=x.c2c_net.median() * 100, top5pct_share_of_move=m.head(max(1, int(round(len(m) * .05)))).sum() / m.sum() if m.sum() > 0 else np.nan))
    groups = {g: x for g, x in E.groupby('regime')}; groups['all'] = E
    C = pd.DataFrame({g: char(x) for g, x in groups.items()}).T
    C.to_csv(OUT / 'character_by_condition.csv')

    # C: entry features vs base rate (all tradable stock-days in the same condition)
    base = []
    for t, f in fr.items():
        x = F[t].copy(); x['date'] = f['Date/Time'].values; x = x[f.tradable.values & (x.date >= A) & (x.date <= B)]
        x['regime'] = x.date.map(reg).fillna('unknown'); base.append(x)
    base = pd.concat(base, ignore_index=True)
    cols = ['stock_er20', 'ret_5d', 'ret_20d', 'ret_60d', 'vs_sma30', 'vs_sma120', 'range20_pos', 'atr14_pct']
    srows = []
    for g in ['uptrend', 'sideways', 'downtrend']:
        e, b = E[E.regime == g], base[base.regime == g]
        for k in cols:
            srows.append(dict(regime=g, feature=k, swinger_median=e[k].median(), base_median=b[k].median()))
        srows.append(dict(regime=g, feature='share above SMA30', swinger_median=(e.vs_sma30 > 0).mean(), base_median=(b.vs_sma30 > 0).mean()))
        srows.append(dict(regime=g, feature='share above SMA120', swinger_median=(e.vs_sma120 > 0).mean(), base_median=(b.vs_sma120 > 0).mean()))
        srows.append(dict(regime=g, feature='share stock ER20 < 0.2', swinger_median=(e.stock_er20 < .2).mean(), base_median=(b.stock_er20 < .2).mean()))
        srows.append(dict(regime=g, feature='share new 20d closing high', swinger_median=e.new_20d_close_high.mean(), base_median=b.new_20d_close_high.mean()))
    S = pd.DataFrame(srows)
    S.to_csv(OUT / 'entry_features_vs_base.csv', index=False)

    # D: movement leg by pre-declared splits
    E['stock_choppy'] = np.where(E.stock_er20 < .2, 'stock ER20 < 0.2', 'stock ER20 >= 0.2')
    E['sma30_side'] = np.where(E.vs_sma30 > 0, 'above SMA30', 'below SMA30')
    drows = []
    for col in ['stock_choppy', 'sma30_side']:
        for (g, k), x in E.groupby(['regime', col]):
            drows.append(dict(regime=g, split=col, group=k, trades=len(x), share=len(x) / (E.regime == g).sum(), move_leg_pct=x.move_leg.mean() * 100,
                              c2c_win_rate=(x.c2c_net > 0).mean(), c2c_expectancy_pct=x.c2c_net.mean() * 100, expectancy_pct=x.net.mean() * 100))
    D = pd.DataFrame(drows)
    D.to_csv(OUT / 'move_by_split.csv', index=False)
    pd.set_option('display.width', 250)
    print(C.round(3).T.to_string()); print(S.round(3).to_string(index=False)); print(D.round(3).to_string(index=False))
