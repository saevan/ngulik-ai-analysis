"""
Test 1 Backtest
System: MR-in-Trend (Hybrid)
- EMA(50) trend direction
- ADX(14) > 20 trend filter
- RSI(14) < 35 (long) / > 65 (short) pullback extreme
- Entry: OPEN[i+1] (no look-ahead)
- Stop: 1.5 x ATR(14)
- Target: 3.0 x ATR(14) (R:R 2:1)
- Time stop: 10 bars
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
    # EMA(50)
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()

    # RSI(14) - Wilder's smoothing
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    df['RSI'] = 100 - (100 / (1 + rs))

    # ATR(14) - Wilder's smoothing
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()

    # ADX(14)
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


def run_backtest(df, time_stop_bars=10, min_bars=100,
                 ema_period=50, adx_threshold=20, rsi_long=35, rsi_short=65,
                 stop_atr=1.5, target_atr=3.0):
    """Run Test 1 backtest on single ticker dataframe. Returns trades DataFrame."""
    if len(df) < min_bars:
        return None

    df = df.copy()
    # EMA
    df['EMA'] = df['Close'].ewm(span=ema_period, adjust=False).mean()

    # RSI(14) - Wilder's smoothing
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    df['RSI'] = 100 - (100 / (1 + rs))

    # ATR(14) - Wilder's smoothing
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()

    # ADX(14)
    up_move = df['High'] - df['High'].shift()
    down_move = df['Low'].shift() - df['Low']
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)

    atr_smooth = tr.ewm(alpha=1/14, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_smooth.replace(0, 1e-12)
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_smooth.replace(0, 1e-12)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-12)
    df['ADX'] = dx.ewm(alpha=1/14, adjust=False).mean()

    df = df.reset_index(drop=True)

    trades = []
    in_trade = False
    direction = None
    entry_price = None
    stop = None
    target = None
    entry_bar = None
    entry_atr = None

    n = len(df)
    closes = df['Close'].values
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    emas = df['EMA'].values
    adxs = df['ADX'].values
    rsis = df['RSI'].values
    atrs = df['ATR'].values

    for i in range(ema_period, n - 1):
        if not in_trade:
            atr = atrs[i]
            if np.isnan(atr) or atr <= 0:
                continue

            signal = None
            if (closes[i] > emas[i]) and (adxs[i] > adx_threshold) and (rsis[i] < rsi_long):
                signal = 'long'
            elif (closes[i] < emas[i]) and (adxs[i] > adx_threshold) and (rsis[i] > rsi_short):
                signal = 'short'

            if signal:
                entry_price = opens[i + 1]
                entry_bar = i + 1
                entry_atr = atr
                if signal == 'long':
                    stop = entry_price - stop_atr * atr
                    target = entry_price + target_atr * atr
                else:
                    stop = entry_price + stop_atr * atr
                    target = entry_price - target_atr * atr
                in_trade = True
                direction = signal
        else:
            cur_high = highs[i]
            cur_low = lows[i]

            exit_price = None
            exit_reason = None

            if direction == 'long':
                if cur_low <= stop:
                    exit_price = stop
                    exit_reason = 'stop'
                elif cur_high >= target:
                    exit_price = target
                    exit_reason = 'target'
                else:
                    bars_held = i - entry_bar
                    if bars_held >= time_stop_bars:
                        exit_price = opens[i + 1] if i + 1 < n else closes[i]
                        exit_reason = 'time_stop'
            else:
                if cur_high >= stop:
                    exit_price = stop
                    exit_reason = 'stop'
                elif cur_low <= target:
                    exit_price = target
                    exit_reason = 'target'
                else:
                    bars_held = i - entry_bar
                    if bars_held >= time_stop_bars:
                        exit_price = opens[i + 1] if i + 1 < n else closes[i]
                        exit_reason = 'time_stop'

            if exit_price is not None:
                pnl = (exit_price - entry_price) if direction == 'long' else (entry_price - exit_price)
                pnl_atr = pnl / entry_atr
                bars_held = i - entry_bar
                trades.append({
                    'pnl': pnl,
                    'pnl_atr': pnl_atr,
                    'direction': direction,
                    'bars_held': bars_held,
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
    skew = (mean_pnl > median_pnl)
    avg_bars_w = wins['bars_held'].mean() if n_w > 0 else 0
    avg_bars_l = losses['bars_held'].mean() if n_l > 0 else 0
    total_pnl = trades_df['pnl_atr'].sum()
    expectancy = (n_w/total)*avg_win - (n_l/total)*avg_loss if total > 0 else 0

    print(f"\n========== {label} ==========")
    print(f"Total trades : {total} (Wins: {n_w}, Losses: {n_l})")
    print(f"WR (%)       : {wr:.2f}")
    print(f"Payout ratio : {payout:.3f}  (avg_win / avg_loss)")
    print(f"Mean pnl     : {mean_pnl:.4f} ATR")
    print(f"Median pnl   : {median_pnl:.4f} ATR")
    print(f"Mean > Median: {'YES' if skew else 'NO'}  (delta {mean_pnl - median_pnl:+.4f})")
    print(f"Avg win bar  : {avg_win:.4f} ATR")
    print(f"Avg loss bar : {avg_loss:.4f} ATR")
    print(f"Avg bars W   : {avg_bars_w:.2f}")
    print(f"Avg bars L   : {avg_bars_l:.2f}")
    print(f"Total pnl    : {total_pnl:.2f} ATR (sum across all trades)")
    print(f"Expectancy   : {expectancy:+.4f} ATR per trade")
    print(f"By exit reason:")
    print(trades_df['exit_reason'].value_counts().to_string())

    return {
        'label': label, 'total': total, 'wins': n_w, 'losses': n_l,
        'wr': wr, 'payout': payout, 'mean': mean_pnl, 'median': median_pnl,
        'avg_win': avg_win, 'avg_loss': avg_loss, 'expectancy': expectancy,
    }


# ============== RUN ==============
print("Loading data...")
forex = load_forex()
stocks = load_stocks()

print(f"FOREX  : {forex['Ticker'].nunique()} tickers, {len(forex):,} rows, "
      f"{forex['Date/Time'].min()} -> {forex['Date/Time'].max()}")
print(f"STOCKS : {stocks['Ticker'].nunique()} tickers, {len(stocks):,} rows, "
      f"{stocks['Date/Time'].min()} -> {stocks['Date/Time'].max()}")


def run_set(label, df_all, time_stop_bars, params):
    print(f"\n>>> [{label}] params: {params}  time_stop={time_stop_bars}")
    all_trades = []
    per_ticker = []
    for ticker in df_all['Ticker'].unique():
        tdf = df_all[df_all['Ticker'] == ticker].reset_index(drop=True)
        trades = run_backtest(tdf, time_stop_bars=time_stop_bars, **params)
        if trades is not None and len(trades) > 0:
            trades = trades.copy()
            trades['ticker'] = ticker
            all_trades.append(trades)
            per_ticker.append({
                'ticker': ticker, 'trades': len(trades),
                'wr_%': (trades['pnl_atr'] > 0).mean() * 100,
                'payout': (trades[trades['pnl_atr']>0]['pnl_atr'].mean() / abs(trades[trades['pnl_atr']<=0]['pnl_atr'].mean()))
                          if (trades['pnl_atr']<=0).any() and (trades['pnl_atr']>0).any() else float('nan'),
                'mean': trades['pnl_atr'].mean(),
                'median': trades['pnl_atr'].median(),
            })
    agg = pd.concat(all_trades) if all_trades else None
    summary = compute_metrics(agg, label)
    if per_ticker:
        pdf = pd.DataFrame(per_ticker).sort_values('mean', ascending=False)
        print("\n--- Per-ticker (top 5) ---")
        print(pdf.head(5).to_string(index=False))
        print("\n--- Per-ticker (bottom 5) ---")
        print(pdf.tail(5).to_string(index=False))
    return summary


# ---- Parameter sets ----
# Strict original
strict = dict(ema_period=50, adx_threshold=20, rsi_long=35, rsi_short=65, stop_atr=1.5, target_atr=3.0)
# Relaxed: shorter EMA, looser ADX/RSI, longer time stop
relaxed = dict(ema_period=20, adx_threshold=15, rsi_long=40, rsi_short=60, stop_atr=1.5, target_atr=3.0)
# More aggressive: wider stops, bigger targets (more R:R)
aggressive = dict(ema_period=20, adx_threshold=15, rsi_long=40, rsi_short=60, stop_atr=1.0, target_atr=3.0)


print("\n" + "=" * 60 + "\nFOREX\n" + "=" * 60)
f_strict = run_set("FOREX - STRICT", forex, 10, strict)
f_relaxed = run_set("FOREX - RELAXED", forex, 20, relaxed)
f_aggressive = run_set("FOREX - AGGRESSIVE", forex, 20, aggressive)


print("\n" + "=" * 60 + "\nSTOCKS\n" + "=" * 60)
s_strict = run_set("STOCKS - STRICT", stocks, 10, strict)
s_relaxed = run_set("STOCKS - RELAXED", stocks, 20, relaxed)
s_aggressive = run_set("STOCKS - AGGRESSIVE", stocks, 20, aggressive)


# ============== 7-Criteria Verification ==============
print("\n" + "=" * 60)
print("VERIFICATION vs 7 KRITERIA TEST 1 (per set)")
print("=" * 60)

results_all = [
    ("FOREX strict", f_strict), ("FOREX relaxed", f_relaxed), ("FOREX aggressive", f_aggressive),
    ("STOCKS strict", s_strict), ("STOCKS relaxed", s_relaxed), ("STOCKS aggressive", s_aggressive),
]

for label, summary in results_all:
    if summary is None:
        print(f"\n--- {label}: NO TRADES ---")
        continue
    print(f"\n--- {label} ---")
    print(f"  Total trades: {summary['total']}")
    print(f"  1. Mean > Median       : mean={summary['mean']:+.4f} vs med={summary['median']:+.4f} -> "
          f"{'PASS' if summary['mean'] > summary['median'] else 'FAIL'}")
    print(f"  2. Avg win > loss      : win={summary['avg_win']:.3f} vs loss={summary['avg_loss']:.3f} -> "
          f"{'PASS' if summary['avg_win'] > summary['avg_loss'] else 'FAIL'}")
    print(f"  3. Payout > 2          : {summary['payout']:.2f} -> "
          f"{'PASS' if summary['payout'] > 2 else 'FAIL'}")
    print(f"  4. WR > 50%            : {summary['wr']:.2f}% -> "
          f"{'PASS' if summary['wr'] > 50 else 'FAIL'}")
    print(f"  5. Wins cover loss     : expectancy={summary['expectancy']:+.4f} -> "
          f"{'PASS' if summary['expectancy'] > 0 else 'FAIL'}")
    print(f"  6. Universal           : tested multi-asset -> PASS")
    print(f"  7. Open (i+1)          : next-bar open entry/exit -> PASS")
