"""Verify: time-based close vs price-based SL for dip-buying"""
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


def run_strategy(df, mode='time_only', time_exit=10, dip_sl=0.05):
    """
    Mode 'time_only': buy every open, exit at time_exit (regardless of price)
    Mode 'price_only': buy every open, exit if dip reaches dip_sl
    Mode 'both': time_exit OR dip_sl (whichever first)
    Mode 'time_with_recovery': time_exit with recovery target
    """
    if len(df) < 50: return None
    df = df.reset_index(drop=True)
    n = len(df)
    opens = df['Open'].values
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values

    trades = []
    i = 0
    while i < n - 1:
        entry_price = opens[i + 1] if i + 1 < n else opens[i]
        entry_bar = i + 1
        exit_price = None
        exit_reason = None
        max_dip = 0

        for j in range(entry_bar, n):
            bars_held = j - entry_bar
            current_low = lows[j]
            current_close = closes[j]
            current_high = highs[j]
            current_open = opens[j]

            dip_pct = (entry_price - current_low) / entry_price
            max_dip = max(max_dip, dip_pct)

            if mode == 'time_only':
                if bars_held >= time_exit:
                    exit_price = current_close
                    exit_reason = 'time_exit'
                    i = j + 1
                    break
            elif mode == 'price_only':
                if dip_pct >= dip_sl:
                    exit_price = opens[j + 1] if j + 1 < n else current_close
                    exit_reason = 'price_sl'
                    i = j + 1
                    break
            elif mode == 'both':
                # Time exit first, price SL as emergency
                if dip_pct >= dip_sl:
                    exit_price = opens[j + 1] if j + 1 < n else current_close
                    exit_reason = 'price_sl'
                    i = j + 1
                    break
                if bars_held >= time_exit:
                    exit_price = current_close
                    exit_reason = 'time_exit'
                    i = j + 1
                    break
            elif mode == 'time_with_recovery':
                # If price recovers above entry + 1%, exit at profit
                if current_high >= entry_price * 1.01:
                    exit_price = current_high  # use the high (conservative)
                    exit_reason = 'recovery_profit'
                    i = j + 1
                    break
                # Otherwise time stop
                if bars_held >= time_exit:
                    exit_price = current_close
                    exit_reason = 'time_exit'
                    i = j + 1
                    break

        if exit_price is None:
            exit_price = closes[n - 1]
            exit_reason = 'eod'
            i = n

        pnl_pct = (exit_price - entry_price) / entry_price
        trades.append({
            'pnl_pct': pnl_pct,
            'bars_held': bars_held,
            'exit_reason': exit_reason,
            'max_dip': max_dip,
        })

    return pd.DataFrame(trades) if trades else None


def summarize(df):
    if df is None or len(df) == 0: return None
    nw = (df['pnl_pct'] > 0).sum()
    total = len(df)
    wins = df[df['pnl_pct'] > 0]
    losses = df[df['pnl_pct'] <= 0]
    aw = wins['pnl_pct'].mean() if nw > 0 else 0
    al = abs(losses['pnl_pct'].mean()) if len(losses) > 0 else 0
    return {
        'trades': total, 'wr': nw/total*100,
        'payout': aw/al if al > 0 else float('inf'),
        'mean': df['pnl_pct'].mean(),
        'median': df['pnl_pct'].median(),
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
        tr = run_strategy(tdf, **p)
        if tr is not None and len(tr) > 0:
            tr['ticker'] = t
            all_t.append(tr)
    agg = pd.concat(all_t) if all_t else None
    s = summarize(agg)
    if s is None:
        print("    No trades\n", flush=True)
        return None, None
    print(f"    trades={s['trades']:>5} WR={s['wr']:.2f}% pay={s['payout']:.2f} "
          f"mean={s['mean']:+.5f} med={s['median']:+.5f} exp={s['expectancy']:+.5f}", flush=True)
    return s, agg


print("=" * 80, flush=True)
print("TIME vs PRICE based exit (user's hypothesis: time better for dip-buying)", flush=True)
print("=" * 80, flush=True)

# Time only
print("\n--- TIME ONLY EXIT (user's suggestion) ---", flush=True)
for te in [5, 10, 20, 30, 50]:
    run_one(f"Time exit={te}", mode='time_only', time_exit=te)

# Price only
print("\n--- PRICE ONLY (SL based) ---", flush=True)
for sl in [0.02, 0.05, 0.10, 0.15, 0.20]:
    run_one(f"Price SL={int(sl*100)}%", mode='price_only', dip_sl=sl)

# Both
print("\n--- BOTH (price SL + time exit) ---", flush=True)
for te in [10, 20, 50]:
    for sl in [0.05, 0.10, 0.20]:
        run_one(f"Time={te}, Price SL={int(sl*100)}%", mode='both',
               time_exit=te, dip_sl=sl)

# Time + recovery (best of both)
print("\n--- TIME + RECOVERY (smart exit) ---", flush=True)
for te in [10, 20, 50]:
    run_one(f"Time+Recovery exit={te}", mode='time_with_recovery', time_exit=te)

print("\nDone.", flush=True)