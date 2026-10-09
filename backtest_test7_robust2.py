"""Direct robustness check for Test 7 winner 7A"""
import os
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd

DATA_DIR = r"C:\Users\ACER\OneDrive\Documents\Ngulik AI\Data"

def load():
    df = pd.read_csv(os.path.join(DATA_DIR, "Data kompas 100.csv"))
    df.columns = [c.strip() for c in df.columns]
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='mixed', dayfirst=True)
    df = df.sort_values(['Ticker', 'Date/Time']).reset_index(drop=True)
    return df

def add_ind(df):
    df = df.copy().reset_index(drop=True)
    df['EMA'] = df['Close'].ewm(span=50, adjust=False).mean()
    delta = df['Close'].diff()
    gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
    ag = gain.ewm(alpha=1/14, adjust=False).mean()
    al = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = ag / al.replace(0, 1e-12)
    df['RSI'] = 100 - (100 / (1 + rs))
    hl = df['High'] - df['Low']
    hc = (df['High'] - df['Close'].shift()).abs()
    lc = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    df['ATR_avg'] = df['ATR'].rolling(50).mean()
    df['ATR_ratio'] = df['ATR'] / df['ATR_avg'].replace(0, 1e-12)
    up = df['High'] - df['High'].shift()
    dn = df['Low'].shift() - df['Low']
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    atr_s = tr.ewm(alpha=1/14, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_s.replace(0, 1e-12)
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_s.replace(0, 1e-12)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-12)
    df['ADX'] = dx.ewm(alpha=1/14, adjust=False).mean()
    return df


def run_7A(df, p):
    """7A: trend + ADX>20 + RSI<45 + ATR<0.6 + breakout 1.5x"""
    if len(df) < 200: return None
    df = add_ind(df)
    n = len(df); closes = df['Close'].values; opens = df['Open'].values
    highs = df['High'].values; lows = df['Low'].values
    emas = df['EMA'].values; atrs = df['ATR'].values
    adxs = df['ADX'].values; rsis = df['RSI'].values
    atr_ratios = df['ATR_ratio'].values

    trades = []
    in_trade = False; state = {}; cd = 0
    for i in range(60, n - 1):
        atr = atrs[i]
        if np.isnan(atr) or atr <= 0: continue
        if not in_trade:
            if cd > 0: cd -= 1; continue
            if any(np.isnan(x) for x in [rsis[i], atr_ratios[i], adxs[i]]): continue
            close = closes[i]; ema = emas[i]
            rsi = rsis[i]; atr_ratio = atr_ratios[i]; adx = adxs[i]
            if (close > ema and adx > 20 and rsi < 45
                and atr_ratio < 0.6
                and (highs[i] - lows[i]) > atr * 1.5):
                entry_price = opens[i + 1]
                stop = entry_price - 2.0 * atr
                if adx > 25: ts = 100
                elif adx > 20: ts = 50
                else: ts = 10
                state = {'ep': entry_price, 'ea': atr, 'eb': i+1,
                         'stop': stop, 'ext': entry_price, 'tr': None, 'ts': ts}
                in_trade = True
            continue
        if highs[i] > state['ext']: state['ext'] = highs[i]
        new_t = state['ext'] - 3.0 * state['ea']
        if state['tr'] is None or new_t > state['tr']: state['tr'] = new_t
        ep = None; er = None
        if lows[i] <= state['stop']:
            ep = state['stop']; er = 'stop'
        elif lows[i] <= state['tr']:
            ep = state['tr']; er = 'trail'
        if ep is None and (i - state['eb']) >= state['ts']:
            ep = opens[i + 1] if i + 1 < n else closes[i]; er = 'time'
        if ep is not None:
            trades.append({'pnl_atr': (ep - state['ep']) / state['ea'],
                          'bars': i - state['eb'], 'ticker_idx': None})
            in_trade = False; cd = 3
    return pd.DataFrame(trades) if trades else None


print("Loading...", flush=True)
stocks = load()
print("Done.\n", flush=True)

print("Running 7A across all tickers...", flush=True)
all_t = []
for t in stocks['Ticker'].unique():
    tdf = stocks[stocks['Ticker'] == t].reset_index(drop=True)
    tr = run_7A(tdf, None)
    if tr is not None and len(tr) > 0:
        tr['ticker'] = t
        all_t.append(tr)
agg = pd.concat(all_t) if all_t else None
print(f"Total trades: {len(agg)}\n", flush=True)

print("--- TRADE-BY-TRADE (worst → best) ---", flush=True)
sorted_t = agg.sort_values('pnl_atr').reset_index(drop=True)
for i, row in sorted_t.iterrows():
    print(f"  #{i+1}: {row['ticker']:<7} bars={int(row['bars']):>3} pnl={row['pnl_atr']:+.3f}", flush=True)

total = agg['pnl_atr'].sum()
print(f"\nTotal PnL: {total:.3f}", flush=True)
top3 = agg.nlargest(3, 'pnl_atr')
print("Top 3 contributors:", flush=True)
for _, row in top3.iterrows():
    pct = row['pnl_atr'] / total * 100
    print(f"  {row['ticker']}: {row['pnl_atr']:+.3f} ({pct:.1f}%)", flush=True)

# Bootstrap 50% sample × 200 iter
print("\nBootstrap 50% × 200 iter:", flush=True)
np.random.seed(42)
boot = []
for _ in range(200):
    s = agg.sample(frac=0.5, random_state=np.random.randint(0, 100000))
    if len(s) > 0:
        nw = (s['pnl_atr'] > 0).sum()
        wr = nw / len(s) * 100
        boot.append({'wr': wr, 'pnl': s['pnl_atr'].mean()})

wrs = [b['wr'] for b in boot]
means = [b['pnl'] for b in boot]
print(f"  WR mean: {np.mean(wrs):.1f}% std: {np.std(wrs):.1f}% range: [{np.min(wrs):.1f}%, {np.max(wrs):.1f}%]", flush=True)
print(f"  WR>50%: {sum(w>50 for w in wrs)/len(wrs)*100:.1f}%", flush=True)
print(f"  Mean PnL mean: {np.mean(means):.3f}", flush=True)
print(f"  Mean>0: {sum(m>0 for m in means)/len(means)*100:.1f}%", flush=True)

# LOO
print("\nLeave-One-Out:", flush=True)
for i in range(len(agg)):
    sub = agg.drop(agg.index[i])
    if len(sub) == 0: continue
    nw = (sub['pnl_atr'] > 0).sum()
    wr = nw / len(sub) * 100
    mean = sub['pnl_atr'].mean()
    print(f"  Drop #{i+1} ({agg.iloc[i]['ticker']}, pnl={agg.iloc[i]['pnl_atr']:+.2f}): "
          f"WR={wr:.1f}% mean={mean:+.2f}", flush=True)
