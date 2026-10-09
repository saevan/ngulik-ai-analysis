"""Test: no hard stop, only trailing + time"""
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


def run_6b_variant(df, stop_atr=2.0, trailing_atr=3.0, time_strong=100, time_mod=50, time_weak=10):
    """6B with custom exit params."""
    if len(df) < 200: return None
    df = add_ind(df)
    n = len(df)
    closes = df['Close'].values; opens = df['Open'].values
    highs = df['High'].values; lows = df['Low'].values
    emas = df['EMA'].values; atrs = df['ATR'].values
    adxs = df['ADX'].values
    atr_ratios = df['ATR_ratio'].values

    trades = []
    in_trade = False; state = {}; cd = 0
    for i in range(60, n - 1):
        atr = atrs[i]
        if np.isnan(atr) or atr <= 0: continue
        if not in_trade:
            if cd > 0: cd -= 1; continue
            if any(np.isnan(x) for x in [atr_ratios[i], adxs[i]]): continue
            close = closes[i]; ema = emas[i]
            atr_ratio = atr_ratios[i]; adx = adxs[i]
            if (close > ema and atr_ratio < 0.6
                and (highs[i] - lows[i]) > atr * 1.5):
                entry_price = opens[i + 1]
                if stop_atr is not None:
                    stop = entry_price - stop_atr * atr
                else:
                    stop = None
                if adx > 25: ts = time_strong
                elif adx > 20: ts = time_mod
                else: ts = time_weak
                state = {'ep': entry_price, 'ea': atr, 'eb': i+1,
                         'stop': stop, 'ext': entry_price, 'tr': None, 'ts': ts}
                in_trade = True
            continue
        if highs[i] > state['ext']: state['ext'] = highs[i]
        new_t = state['ext'] - trailing_atr * state['ea']
        if state['tr'] is None or new_t > state['tr']: state['tr'] = new_t
        ep = None; er = None
        hit_stop = (state['stop'] is not None and lows[i] <= state['stop'])
        hit_trail = (state['tr'] is not None and lows[i] <= state['tr'])
        if hit_stop:
            ep = state['stop']; er = 'stop'
        elif hit_trail:
            ep = state['tr']; er = 'trail'
        if ep is None and (i - state['eb']) >= state['ts']:
            ep = opens[i + 1] if i + 1 < n else closes[i]; er = 'time'
        if ep is not None:
            pnl = (ep - state['ep']) / state['ea']
            trades.append({'pnl_atr': pnl, 'exit_reason': er,
                          'bars': i - state['eb']})
            in_trade = False; cd = 3
    return pd.DataFrame(trades) if trades else None


def summarize(df):
    if df is None or len(df) == 0: return None
    nw = (df['pnl_atr'] > 0).sum()
    total = len(df)
    wins = df[df['pnl_atr'] > 0]
    losses = df[df['pnl_atr'] <= 0]
    aw = wins['pnl_atr'].mean() if nw > 0 else 0
    al = abs(losses['pnl_atr'].mean()) if len(losses) > 0 else 0
    return {
        'trades': total, 'wr': nw/total*100,
        'payout': aw/al if al > 0 else float('inf'),
        'mean': df['pnl_atr'].mean(),
        'median': df['pnl_atr'].median(),
        'expectancy': (nw/total)*aw - (len(losses)/total)*al,
    }


print("Loading...", flush=True)
stocks = load()
print("Done.\n", flush=True)


def run_one(name, **p):
    print(f">>> {name}: {p}", flush=True)
    all_t = []
    for t in stocks['Ticker'].unique():
        tdf = stocks[stocks['Ticker'] == t].reset_index(drop=True)
        tr = run_6b_variant(tdf, **p)
        if tr is not None and len(tr) > 0:
            tr['ticker'] = t
            all_t.append(tr)
    agg = pd.concat(all_t) if all_t else None
    s = summarize(agg)
    if s is None:
        print("    No trades\n", flush=True)
        return None
    print(f"    trades={s['trades']:>4} WR={s['wr']:.2f}% pay={s['payout']:.2f} "
          f"mean={s['mean']:+.3f} med={s['median']:+.3f} exp={s['expectancy']:+.3f}", flush=True)
    return s


print("=== EXIT VARIATIONS ===\n", flush=True)

# Baseline 6B
print("Baseline 6B (current best):", flush=True)
run_one("Baseline", stop_atr=2.0, trailing_atr=3.0)

# No hard stop
print("\nTest 1: No hard stop, only trailing + time", flush=True)
run_one("No stop, trail=3, time", stop_atr=None, trailing_atr=3.0)

# Tighter stop
print("\nTest 2: Tighter stops (1.0 ATR)", flush=True)
run_one("Stop=1.0, trail=3", stop_atr=1.0, trailing_atr=3.0)

print("\nTest 3: Tighter stops (0.5 ATR)", flush=True)
run_one("Stop=0.5, trail=3", stop_atr=0.5, trailing_atr=3.0)

# Wider trailing
print("\nTest 4: Wider trailing (4.0 ATR)", flush=True)
run_one("Stop=2, trail=4", stop_atr=2.0, trailing_atr=4.0)

# Tighter trailing
print("\nTest 5: Tighter trailing (2.0 ATR)", flush=True)
run_one("Stop=2, trail=2", stop_atr=2.0, trailing_atr=2.0)

# Wider stop
print("\nTest 6: Wider stops (3.0 ATR)", flush=True)
run_one("Stop=3, trail=3", stop_atr=3.0, trailing_atr=3.0)

# Time stop emphasis
print("\nTest 7: Shorter time stops (5/20/50)", flush=True)
run_one("Short time stops", stop_atr=2.0, trailing_atr=3.0,
       time_strong=50, time_mod=20, time_weak=5)

print("\nTest 8: Very tight stop + tight trail", flush=True)
run_one("Stop=0.5, trail=1.5", stop_atr=0.5, trailing_atr=1.5)

print("\nDone.", flush=True)
