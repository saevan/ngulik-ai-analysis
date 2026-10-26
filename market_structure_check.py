"""Basic market structure checks on the IDX Kompas100 data (26 Oct 2026, descriptive).
1. Red/green candle balance per day / week / month (candle = Close vs Open of that bar; also Close vs previous Close),
   per stock (traded bars only) and for the equal-weight market proxy; by period; average size of green vs red candles.
2. Other basic structures: fat tails (kurtosis, share of moves beyond 3 sd), volatility clustering (autocorrelation of
   |return|), sign autocorrelation of returns, up/down move size asymmetry, gap fill within the same day.
Writes market_structure_results/*.csv"""
import numpy as np, pandas as pd
import grid_search_timehunter as engine

st, _ = engine.load_data('stocks')
st = st[st.tradable & (st['Date/Time'] <= '2025-08-15')].copy()
st['period'] = pd.cut(st['Date/Time'].dt.year, [1993, 1999, 2007, 2015, 2020, 2025], labels=['1994-99', '2000-07', '2008-15', '2016-20', '2021-25'])
rows = []


def balance(df, tf, scope):
    g = df.Close > df.Open
    r = df.Close < df.Open
    upc = df.Close > df.prev_close
    dnc = df.Close < df.prev_close
    body = df.Close / df.Open - 1
    rows.append(dict(scope=scope, timeframe=tf, bars=len(df), green=g.mean(), red=r.mean(), flat=1 - g.mean() - r.mean(),
                     close_up=upc.mean(), close_down=dnc.mean(), close_flat=1 - upc.mean() - dnc.mean(),
                     avg_green_body=body[g].mean(), avg_red_body=body[r].mean()))


def resample(f, rule):
    s = f.set_index('Date/Time')
    o = s.Open.resample(rule).first(); c = s.Close.resample(rule).last()
    out = pd.DataFrame({'Open': o, 'Close': c}).dropna()
    out['prev_close'] = out.Close.shift(1)
    return out.dropna()


per = {'D': [], 'W': [], 'ME': []}
for t, f in st.groupby('Ticker'):
    f = f.sort_values('Date/Time')
    d = f[['Date/Time', 'Open', 'Close', 'period']].copy()
    d['prev_close'] = f.Close.shift(1)
    per['D'].append(d.dropna(subset=['prev_close']))
    for rule in ('W', 'ME'):
        x = resample(f, rule)
        x['period'] = pd.cut(x.index.year, [1993, 1999, 2007, 2015, 2020, 2025], labels=['1994-99', '2000-07', '2008-15', '2016-20', '2021-25'])
        per[rule].append(x)
for rule, name in (('D', 'daily'), ('W', 'weekly'), ('ME', 'monthly')):
    df = pd.concat(per[rule])
    balance(df, name, 'stocks, all')
    for p, x in df.groupby('period', observed=True):
        balance(x, name, f'stocks, {p}')
# market proxy (equal-weight daily return index)
closes = st.pivot(index='Date/Time', columns='Ticker', values='Close')
ret = closes.pct_change(fill_method=None).mean(axis=1).fillna(0)
idx = (1 + ret).cumprod()
for rule, name in (('D', 'daily'), ('W', 'weekly'), ('ME', 'monthly')):
    c = idx if rule == 'D' else idx.resample(rule).last()
    o = c.shift(1)
    df = pd.DataFrame({'Open': o, 'Close': c, 'prev_close': o}).dropna()
    balance(df, name, 'market EW index (close-to-close)')
B = pd.DataFrame(rows)
B.to_csv('market_structure_results/candle_balance.csv', index=False)

# 2. other structures (daily stock log returns, traded bars)
st = st.sort_values(['Ticker', 'Date/Time'])
st['r'] = np.log(st.Close / st.groupby('Ticker').Close.shift(1))
st['gap'] = st.Open / st.groupby('Ticker').Close.shift(1) - 1
st['pc'] = st.groupby('Ticker').Close.shift(1)
x = st.dropna(subset=['r'])
z = x.groupby('Ticker').r.transform(lambda s: (s - s.mean()) / s.std())
ac = lambda s, lag=1: s.autocorr(lag)
o = dict(
    kurtosis_daily=float(x.groupby('Ticker').r.apply(lambda s: s.kurt()).median()),
    share_beyond_3sd=float((z.abs() > 3).mean()), normal_share_beyond_3sd=0.0027,
    autocorr_abs_return_lag1=float(x.groupby('Ticker').r.apply(lambda s: ac(s.abs())).median()),
    autocorr_abs_return_lag10=float(x.groupby('Ticker').r.apply(lambda s: ac(s.abs(), 10)).median()),
    autocorr_return_lag1=float(x.groupby('Ticker').r.apply(ac).median()),
    autocorr_market_return_lag1=float(np.log1p(ret).autocorr(1)),
    avg_up_day=float(x.r[x.r > 0].mean()), avg_down_day=float(x.r[x.r < 0].mean()),
    share_up_days=float((x.r > 0).mean()), share_down_days=float((x.r < 0).mean()),
    gap_up_share=float((x.gap > 0).mean()), gap_down_share=float((x.gap < 0).mean()),
    gap_up_filled_same_day=float((x[x.gap > .005].Low <= x[x.gap > .005].pc).mean()),
    gap_down_filled_same_day=float((x[x.gap < -.005].High >= x[x.gap < -.005].pc).mean()),
)
pd.Series(o).to_csv('market_structure_results/other_structures.csv')
pd.set_option('display.width', 220)
print(B.round(3).to_string(index=False))
print(pd.Series(o).round(4).to_string())
