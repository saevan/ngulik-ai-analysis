"""Fading move: hybrid — hold N bars but exit early on deep dip"""
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


def run_hybrid(df, time_exit=20, dip_thresh=0.05):
    """Buy every open. If dip >= threshold, exit next open. Else hold for time_exit bars."""
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
            current_high = highs[j]
            current_close = closes[j]
            current_open = opens[j]

            dip_pct = (entry_price - current_low) / entry_price
            max_dip = max(max_dip, dip_pct)

            # Early exit on deep dip
            if dip_pct >= dip_thresh:
                exit_price = opens[j + 1] if j + 1 < n else current_close
                exit_reason = 'dip_stop'
                i = j + 1
                break

            # Time exit
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
        'avg_win': aw, 'avg_loss': al,
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
        tr = run_hybrid(tdf, **p)
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
    if 'exit_reason' in agg.columns:
        for r in agg['exit_reason'].value_counts().items():
            print(f"      {r[0]}: {r[1]}", flush=True)
    return s, agg


print("=== HYBRID FADING ===\n", flush=True)

run_one("Hold=20, no dip stop", time_exit=20, dip_thresh=99.0)
run_one("Hold=20, dip=10%", time_exit=20, dip_thresh=0.10)
run_one("Hold=20, dip=5%", time_exit=20, dip_thresh=0.05)
run_one("Hold=20, dip=3%", time_exit=20, dip_thresh=0.03)
run_one("Hold=10, dip=5%", time_exit=10, dip_thresh=0.05)
run_one("Hold=10, dip=3%", time_exit=10, dip_thresh=0.03)
run_one("Hold=5, dip=5%", time_exit=5, dip_thresh=0.05)
run_one("Hold=5, dip=3%", time_exit=5, dip_thresh=0.03)
run_one("Hold=30, dip=5%", time_exit=30, dip_thresh=0.05)
run_one("Hold=50, dip=5%", time_exit=50, dip_thresh=0.05)

print("\nDone.", flush=True)
