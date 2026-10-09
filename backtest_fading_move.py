"""Fading move strategy:
- Buy at every bar open
- If price drops X% → exit at next open (or close)
- The deeper the dip, the higher the recovery target (asymmetric)
- Re-enter next open

Multiple variants:
F1: Fixed % stop (e.g., -2%) exit at next open
F2: Tiered stop (lighter dip = exit fast, deeper = wait for bigger recovery)
F3: Hold to fixed time if drop doesn't recover
"""

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


def run_fading(df, dip_thresh=0.02, recovery_mult=1.0, time_exit=10, mode='simple'):
    """
    Fading move strategy.

    Mode 'simple': if price drops `dip_thresh` from entry, exit at next open (lock loss)
    Mode 'tiered': deeper dip → bigger recovery target before exit
                  dip 0-2% → exit at next open
                  dip 2-5% → wait for recovery to 1.0x dip
                  dip >5% → wait for recovery to 1.5x dip
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

        # Track the trade
        bars_held = 0
        exit_price = None
        exit_reason = None
        max_dip = 0  # max % drop from entry

        for j in range(entry_bar, n):
            bars_held = j - entry_bar
            current_low = lows[j]
            current_close = closes[j]
            current_high = highs[j]
            current_open = opens[j]

            # Calculate current dip from entry
            dip_pct = (entry_price - current_low) / entry_price
            max_dip = max(max_dip, dip_pct)

            # Mode: simple — fixed % stop
            if mode == 'simple':
                if dip_pct >= dip_thresh:
                    # Exit at next open
                    exit_price = opens[j + 1] if j + 1 < n else current_close
                    exit_reason = 'dip_stop'
                    i = j + 1
                    break
                elif bars_held >= time_exit:
                    exit_price = opens[j + 1] if j + 1 < n else current_close
                    exit_reason = 'time_exit'
                    i = j + 1
                    break

            # Mode: tiered — exit depends on dip depth
            elif mode == 'tiered':
                # Recovery target: bigger if deeper dip
                # If max_dip ever reached >= dip_thresh, hold for recovery
                if max_dip >= dip_thresh:
                    # Recovery target = max_dip * recovery_mult
                    target_price = entry_price * (1 - max_dip * recovery_mult)
                    if current_high >= target_price and current_close >= target_price * 0.999:
                        # Recovery achieved (close above target)
                        exit_price = current_close
                        exit_reason = 'recovery'
                        i = j + 1
                        break

                # Time stop
                if bars_held >= time_exit:
                    exit_price = current_close
                    exit_reason = 'time_exit'
                    i = j + 1
                    break

            # Mode: hold_until — if dip < thresh, just hold for fixed time
            elif mode == 'hold_until':
                if bars_held >= time_exit:
                    exit_price = current_close
                    exit_reason = 'time_exit'
                    i = j + 1
                    break

        if exit_price is None:
            # End of data
            exit_price = closes[n - 1]
            exit_reason = 'eod'
            i = n

        pnl_pct = (exit_price - entry_price) / entry_price
        trades.append({
            'pnl_pct': pnl_pct,
            'bars_held': bars_held,
            'exit_reason': exit_reason,
            'max_dip': max_dip,
            'entry_price': entry_price,
            'exit_price': exit_price,
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


def run_strategy(name, **p):
    print(f">>> {name}: {p}", flush=True)
    all_t = []
    for t in stocks['Ticker'].unique():
        tdf = stocks[stocks['Ticker'] == t].reset_index(drop=True)
        tr = run_fading(tdf, **p)
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


print("=== FADING MOVE STRATEGY ===\n", flush=True)

# Simple mode: dip-based stop
print("--- SIMPLE mode (dip-based stop, exit at next open) ---", flush=True)
run_strategy("Dip=1%, time=10", dip_thresh=0.01, time_exit=10, mode='simple')
run_strategy("Dip=2%, time=10", dip_thresh=0.02, time_exit=10, mode='simple')
run_strategy("Dip=3%, time=10", dip_thresh=0.03, time_exit=10, mode='simple')
run_strategy("Dip=5%, time=10", dip_thresh=0.05, time_exit=10, mode='simple')
run_strategy("Dip=2%, time=5", dip_thresh=0.02, time_exit=5, mode='simple')
run_strategy("Dip=2%, time=20", dip_thresh=0.02, time_exit=20, mode='simple')

# Tiered mode: hold for recovery with multiplier
print("\n--- TIERED mode (recover to entry + dip*mult) ---", flush=True)
run_strategy("Tiered rec_mult=1.0", dip_thresh=0.02, recovery_mult=1.0, time_exit=30, mode='tiered')
run_strategy("Tiered rec_mult=0.5", dip_thresh=0.02, recovery_mult=0.5, time_exit=30, mode='tiered')
run_strategy("Tiered rec_mult=1.5", dip_thresh=0.02, recovery_mult=1.5, time_exit=30, mode='tiered')
run_strategy("Tiered rec_mult=2.0", dip_thresh=0.02, recovery_mult=2.0, time_exit=30, mode='tiered')
run_strategy("Tiered rec_mult=0.5, dip=3%", dip_thresh=0.03, recovery_mult=0.5, time_exit=30, mode='tiered')

# Hold until mode
print("\n--- HOLD UNTIL mode (just hold N bars) ---", flush=True)
run_strategy("Hold 5 bars", time_exit=5, mode='hold_until')
run_strategy("Hold 10 bars", time_exit=10, mode='hold_until')
run_strategy("Hold 20 bars", time_exit=20, mode='hold_until')

print("\nDone.", flush=True)
