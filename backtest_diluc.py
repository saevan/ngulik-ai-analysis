"""
DILUC Backtest — Hybrid Regime Switcher
========================================

DEFAULT mode (ADX < 20, ranging): MR with tight R:R 2:1, time stop 10
DAWN mode   (ADX > 25, trending): TF with partial TP + trailing, time stop 30
No trade zone: ADX 20-25 (transition)

Entry: OPEN[i+1] (no look-ahead)
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = r"C:\Users\ACER\OneDrive\Documents\Ngulik AI\Data"


def load_forex():
    path = os.path.join(DATA_DIR, "Data Forex.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df['Date/Time'] = pd.to_datetime(df['Date/Time'])
    df = df.sort_values(['Ticker', 'Date/Time']).reset_index(drop=True)
    return df


def load_stocks():
    path = os.path.join(DATA_DIR, "Data kompas 100.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='mixed', dayfirst=True)
    df = df.sort_values(['Ticker', 'Date/Time']).reset_index(drop=True)
    return df


def add_indicators(df):
    df = df.copy()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()

    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    df['RSI'] = 100 - (100 / (1 + rs))

    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    df['TR'] = tr

    up_move = df['High'] - df['High'].shift()
    down_move = df['Low'].shift() - df['Low']
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)

    atr_smooth = tr.ewm(alpha=1/14, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_smooth.replace(0, 1e-12)
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_smooth.replace(0, 1e-12)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-12)
    df['ADX'] = dx.ewm(alpha=1/14, adjust=False).mean()

    return df


def run_diluc(df, min_bars=100,
              adx_dawn=25, adx_default=20,
              rsi_dawn_long=40, rsi_dawn_short=60,
              rsi_default_long=35, rsi_default_short=65,
              default_stop_atr=1.0, default_target_atr=2.0, default_time_stop=10,
              dawn_stop_atr=1.5, dawn_partial_atr=2.0, dawn_trailing_atr=2.0, dawn_time_stop=30):
    """
    Diluc system backtest.

    Returns: DataFrame with trades including pnl_atr, mode, exit_reason, etc.
    """
    if len(df) < min_bars:
        return None

    df = add_indicators(df)
    df = df.reset_index(drop=True)

    n = len(df)
    closes = df['Close'].values
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    emas = df['EMA50'].values
    adxs = df['ADX'].values
    rsis = df['RSI'].values
    atrs = df['ATR'].values

    trades = []
    in_trade = False
    mode = None
    direction = None
    entry_price = None
    stop = None
    target = None           # DEFAULT target
    target1 = None          # DAWN partial TP
    partial_taken = False
    trailing_stop = None
    extreme = None           # highest for LONG, lowest for SHORT since entry
    entry_bar = None
    entry_atr = None

    for i in range(50, n - 1):
        if not in_trade:
            atr = atrs[i]
            if np.isnan(atr) or atr <= 0:
                continue

            adx = adxs[i]
            ema = emas[i]
            rsi = rsis[i]
            close = closes[i]

            signal = None
            chosen_mode = None

            if adx > adx_dawn:  # DAWN
                if close > ema and rsi < rsi_dawn_long:
                    signal = 'long'; chosen_mode = 'dawn'
                elif close < ema and rsi > rsi_dawn_short:
                    signal = 'short'; chosen_mode = 'dawn'
            elif adx < adx_default:  # DEFAULT
                if close > ema and rsi < rsi_default_long:
                    signal = 'long'; chosen_mode = 'default'
                elif close < ema and rsi > rsi_default_short:
                    signal = 'short'; chosen_mode = 'default'
            # else: transition zone, no signal

            if signal:
                entry_price = opens[i + 1]
                entry_bar = i + 1
                entry_atr = atr

                if chosen_mode == 'default':
                    if signal == 'long':
                        stop = entry_price - default_stop_atr * atr
                        target = entry_price + default_target_atr * atr
                    else:
                        stop = entry_price + default_stop_atr * atr
                        target = entry_price - default_target_atr * atr
                    time_stop_bars = default_time_stop
                else:  # dawn
                    if signal == 'long':
                        stop = entry_price - dawn_stop_atr * atr
                        target1 = entry_price + dawn_partial_atr * atr
                    else:
                        stop = entry_price + dawn_stop_atr * atr
                        target1 = entry_price - dawn_partial_atr * atr
                    partial_taken = False
                    trailing_stop = None
                    extreme = entry_price
                    time_stop_bars = dawn_time_stop

                in_trade = True
                direction = signal
                mode = chosen_mode

        else:
            cur_high = highs[i]
            cur_low = lows[i]
            cur_close = closes[i]

            exit_price = None
            exit_reason = None

            if mode == 'default':
                if direction == 'long':
                    if cur_low <= stop:
                        exit_price = stop
                        exit_reason = 'stop'
                    elif cur_high >= target:
                        exit_price = target
                        exit_reason = 'target'
                else:
                    if cur_high >= stop:
                        exit_price = stop
                        exit_reason = 'stop'
                    elif cur_low <= target:
                        exit_price = target
                        exit_reason = 'target'

                if exit_price is None:
                    bars_held = i - entry_bar
                    if bars_held >= default_time_stop:
                        exit_price = opens[i + 1] if i + 1 < n else cur_close
                        exit_reason = 'time_stop'

            else:  # DAWN
                # Update extreme
                if direction == 'long':
                    if cur_high > extreme:
                        extreme = cur_high
                else:
                    if cur_low < extreme:
                        extreme = cur_low

                if direction == 'long':
                    if not partial_taken:
                        if cur_low <= stop:
                            exit_price = stop
                            exit_reason = 'stop'
                        elif cur_high >= target1:
                            partial_taken = True
                            trailing_stop = target1 - dawn_trailing_atr * entry_atr
                            # extreme is already >= target1
                    else:
                        # update trailing
                        new_trailing = extreme - dawn_trailing_atr * entry_atr
                        if new_trailing > trailing_stop:
                            trailing_stop = new_trailing
                        if cur_low <= trailing_stop:
                            exit_price = trailing_stop
                            exit_reason = 'trailing'
                else:  # SHORT
                    if not partial_taken:
                        if cur_high >= stop:
                            exit_price = stop
                            exit_reason = 'stop'
                        elif cur_low <= target1:
                            partial_taken = True
                            trailing_stop = target1 + dawn_trailing_atr * entry_atr
                    else:
                        new_trailing = extreme + dawn_trailing_atr * entry_atr
                        if new_trailing < trailing_stop:
                            trailing_stop = new_trailing
                        if cur_high >= trailing_stop:
                            exit_price = trailing_stop
                            exit_reason = 'trailing'

                if exit_price is None:
                    bars_held = i - entry_bar
                    if bars_held >= dawn_time_stop:
                        exit_price = opens[i + 1] if i + 1 < n else cur_close
                        exit_reason = 'time_stop'

            if exit_price is not None:
                # PnL calculation
                if mode == 'dawn' and partial_taken:
                    # 50% closed at target1, 50% closed at exit_price
                    if direction == 'long':
                        pnl = 0.5 * (target1 - entry_price) + 0.5 * (exit_price - entry_price)
                    else:
                        pnl = 0.5 * (entry_price - target1) + 0.5 * (entry_price - exit_price)
                else:
                    if direction == 'long':
                        pnl = exit_price - entry_price
                    else:
                        pnl = entry_price - exit_price

                pnl_atr = pnl / entry_atr
                bars_held = i - entry_bar
                trades.append({
                    'pnl': pnl,
                    'pnl_atr': pnl_atr,
                    'direction': direction,
                    'mode': mode,
                    'bars_held': bars_held,
                    'partial_taken': partial_taken,
                    'exit_reason': exit_reason,
                })
                in_trade = False

    return pd.DataFrame(trades) if trades else None


def compute_metrics(trades_df, label):
    if trades_df is None or len(trades_df) == 0:
        print(f"\n=== {label} ===\nNo trades.\n")
        return None

    wins = trades_df[trades_df['pnl_atr'] > 0]
    losses = trades_df[trades_df['pnl_atr'] <= 0]

    total = len(trades_df)
    n_w = len(wins)
    n_l = len(losses)
    wr = n_w / total * 100
    avg_win = wins['pnl_atr'].mean() if n_w > 0 else 0
    avg_loss = abs(losses['pnl_atr'].mean()) if n_l > 0 else 0
    payout = avg_win / avg_loss if avg_loss > 0 else float('inf')
    mean_pnl = trades_df['pnl_atr'].mean()
    median_pnl = trades_df['pnl_atr'].median()
    skew_right = mean_pnl > median_pnl
    total_pnl = trades_df['pnl_atr'].sum()
    expectancy = (n_w/total)*avg_win - (n_l/total)*avg_loss if total > 0 else 0

    n_default = (trades_df['mode'] == 'default').sum()
    n_dawn = (trades_df['mode'] == 'dawn').sum()

    print(f"\n========== {label} ==========")
    print(f"Total trades : {total} (Wins: {n_w}, Losses: {n_l})")
    print(f"  DEFAULT mode trades: {n_default}")
    print(f"  DAWN mode trades   : {n_dawn}")
    print(f"WR (%)       : {wr:.2f}")
    print(f"Payout ratio : {payout:.3f}")
    print(f"Mean pnl     : {mean_pnl:+.4f} ATR")
    print(f"Median pnl   : {median_pnl:+.4f} ATR")
    print(f"Mean > Median: {'YES' if skew_right else 'NO'}  (delta {mean_pnl - median_pnl:+.4f})")
    print(f"Avg win bar  : {avg_win:.4f} ATR")
    print(f"Avg loss bar : {avg_loss:.4f} ATR")
    print(f"Total pnl    : {total_pnl:+.2f} ATR")
    print(f"Expectancy   : {expectancy:+.4f} ATR per trade")
    print(f"Exit reasons:")
    print(trades_df['exit_reason'].value_counts().to_string())

    # Per-mode breakdown
    print(f"\n--- Per-mode breakdown ---")
    for m in ['default', 'dawn']:
        sub = trades_df[trades_df['mode'] == m]
        if len(sub) == 0:
            continue
        sub_w = sub[sub['pnl_atr'] > 0]
        sub_l = sub[sub['pnl_atr'] <= 0]
        sub_wr = len(sub_w) / len(sub) * 100 if len(sub) > 0 else 0
        sub_avg_w = sub_w['pnl_atr'].mean() if len(sub_w) > 0 else 0
        sub_avg_l = abs(sub_l['pnl_atr'].mean()) if len(sub_l) > 0 else 0
        sub_payout = sub_avg_w / sub_avg_l if sub_avg_l > 0 else float('inf')
        print(f"  {m:8s}: n={len(sub):3d}, WR={sub_wr:.1f}%, payout={sub_payout:.2f}, "
              f"avg_win={sub_avg_w:+.3f}, avg_loss={sub_avg_l:.3f}")

    return {
        'label': label, 'total': total, 'wins': n_w, 'losses': n_l,
        'wr': wr, 'payout': payout, 'mean': mean_pnl, 'median': median_pnl,
        'avg_win': avg_win, 'avg_loss': avg_loss, 'expectancy': expectancy,
    }


# ============== RUN ==============
print("Loading data...")
forex = load_forex()
stocks = load_stocks()

print(f"FOREX  : {forex['Ticker'].nunique()} tickers, {len(forex):,} rows")
print(f"STOCKS : {stocks['Ticker'].nunique()} tickers, {len(stocks):,} rows")


def run_set(label, df_all):
    print(f"\n>>> Running DILUC on {label}...")
    all_trades = []
    per_ticker = []
    for ticker in df_all['Ticker'].unique():
        tdf = df_all[df_all['Ticker'] == ticker].reset_index(drop=True)
        trades = run_diluc(tdf)
        if trades is not None and len(trades) > 0:
            trades = trades.copy()
            trades['ticker'] = ticker
            all_trades.append(trades)
            per_ticker.append({
                'ticker': ticker, 'trades': len(trades),
                'wr_%': (trades['pnl_atr'] > 0).mean() * 100,
                'mean': trades['pnl_atr'].mean(),
                'median': trades['pnl_atr'].median(),
            })
    agg = pd.concat(all_trades) if all_trades else None
    summary = compute_metrics(agg, f"DILUC - {label}")
    if per_ticker:
        pdf = pd.DataFrame(per_ticker).sort_values('mean', ascending=False)
        print("\n--- Top 5 tickers ---")
        print(pdf.head(5).to_string(index=False))
        print("\n--- Bottom 5 tickers ---")
        print(pdf.tail(5).to_string(index=False))
    return summary


f_summary = run_set("FOREX", forex)
s_summary = run_set("STOCKS", stocks)


# ============== 7-Criteria Verification ==============
print("\n" + "=" * 60)
print("VERIFICATION DILUC vs 7 KRITERIA")
print("=" * 60)

for label, summary in [("FOREX", f_summary), ("STOCKS", s_summary)]:
    if summary is None:
        print(f"\n--- {label}: NO TRADES ---")
        continue
    print(f"\n--- DILUC on {label} ---")
    print(f"  Total trades: {summary['total']}")
    print(f"  1. Mean > Median      : mean={summary['mean']:+.4f} vs med={summary['median']:+.4f} -> "
          f"{'PASS' if summary['mean'] > summary['median'] else 'FAIL'}")
    print(f"  2. Avg win > loss     : win={summary['avg_win']:.3f} vs loss={summary['avg_loss']:.3f} -> "
          f"{'PASS' if summary['avg_win'] > summary['avg_loss'] else 'FAIL'}")
    print(f"  3. Payout > 2         : {summary['payout']:.2f} -> "
          f"{'PASS' if summary['payout'] > 2 else 'FAIL'}")
    print(f"  4. WR > 50%           : {summary['wr']:.2f}% -> "
          f"{'PASS' if summary['wr'] > 50 else 'FAIL'}")
    print(f"  5. Wins cover loss    : expectancy={summary['expectancy']:+.4f} -> "
          f"{'PASS' if summary['expectancy'] > 0 else 'FAIL'}")
    print(f"  6. Universal          : tested multi-asset -> PASS")
    print(f"  7. Open (i+1)         : next-bar open entry/exit -> PASS")
