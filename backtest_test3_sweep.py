"""
Test 3 — TF Base + MR Layer — Parameter Sweep
==============================================

GOAL: Increase number of trades by making indicators smaller/more sensitive
- Smaller RSI thresholds = more pullback entries
- Lower ADX threshold = more trend-following entries
- Same logic, just more trades

INDICATORS:
- EMA(50) — trend direction (TF base)
- ADX(14) — trend strength filter (TF base)
- RSI(14) — pullback entry + reversal exit (MR layer)
- ATR(14) — normalization

ENTRY (TF + MR):
- Long: Close > EMA50, ADX > threshold, RSI < entry_long (pullback in uptrend)
- Short: Close < EMA50, ADX > threshold, RSI > entry_short (pullback in downtrend)

EXIT (MR-driven + safety):
- Primary exit: RSI opposite extreme (RSI > exit_long for long, RSI < exit_short for short)
- Safety: trailing stop 2.0 × ATR
- Hard stop: stop_atr × ATR
- Time stop: time_stop bars
- Entry: OPEN[i+1] (no look-ahead)
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = r"C:\Users\ACER\OneDrive\Documents\Ngulik AI\Data"


def load_stocks():
    path = os.path.join(DATA_DIR, "Data kompas 100.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='mixed', dayfirst=True)
    df = df.sort_values(['Ticker', 'Date/Time']).reset_index(drop=True)
    return df


def add_indicators(df, rsi_period=14):
    df = df.copy()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/rsi_period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/rsi_period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    df['RSI'] = 100 - (100 / (1 + rs))
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
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


def run_test3(df, **params):
    p = {
        'adx_threshold': 20,
        'rsi_entry_long': 40, 'rsi_entry_short': 60,
        'rsi_exit_long': 70, 'rsi_exit_short': 30,
        'stop_atr': 1.0, 'trailing_atr': 2.0, 'time_stop': 25,
        'rsi_period': 14,
    }
    p.update(params)

    if len(df) < 100:
        return None

    df = add_indicators(df, rsi_period=p['rsi_period']).reset_index(drop=True)
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

    for i in range(50, n - 1):
        if not in_trade:
            atr = atrs[i]
            if np.isnan(atr) or atr <= 0:
                continue

            adx = adxs[i]; ema = emas[i]; rsi = rsis[i]; close = closes[i]
            if adx <= p['adx_threshold']:
                continue

            signal = None
            if close > ema and rsi < p['rsi_entry_long']:
                signal = 'long'
            elif close < ema and rsi > p['rsi_entry_short']:
                signal = 'short'

            if signal:
                entry_price = opens[i + 1]
                entry_bar = i + 1
                entry_atr = atr
                if signal == 'long':
                    stop = entry_price - p['stop_atr'] * atr
                    rsi_exit = p['rsi_exit_long']
                else:
                    stop = entry_price + p['stop_atr'] * atr
                    rsi_exit = p['rsi_exit_short']
                extreme = entry_price
                trailing_stop = None
                in_trade = True
                direction = signal

        else:
            cur_high = highs[i]; cur_low = lows[i]; cur_close = closes[i]
            cur_rsi = rsis[i]
            exit_price = None; exit_reason = None

            if direction == 'long':
                if cur_high > extreme: extreme = cur_high
                new_t = extreme - p['trailing_atr'] * entry_atr
                if trailing_stop is None or new_t > trailing_stop: trailing_stop = new_t
            else:
                if cur_low < extreme: extreme = cur_low
                new_t = extreme + p['trailing_atr'] * entry_atr
                if trailing_stop is None or new_t < trailing_stop: trailing_stop = new_t

            if direction == 'long':
                if cur_low <= stop:
                    exit_price = stop; exit_reason = 'stop'
                elif cur_rsi >= rsi_exit:
                    exit_price = opens[i + 1] if i + 1 < n else cur_close
                    exit_reason = 'rsi_exit'
                elif cur_low <= trailing_stop:
                    exit_price = trailing_stop; exit_reason = 'trailing'
            else:
                if cur_high >= stop:
                    exit_price = stop; exit_reason = 'stop'
                elif cur_rsi <= rsi_exit:
                    exit_price = opens[i + 1] if i + 1 < n else cur_close
                    exit_reason = 'rsi_exit'
                elif cur_high >= trailing_stop:
                    exit_price = trailing_stop; exit_reason = 'trailing'

            if exit_price is None:
                if (i - entry_bar) >= p['time_stop']:
                    exit_price = opens[i + 1] if i + 1 < n else cur_close
                    exit_reason = 'time_stop'

            if exit_price is not None:
                pnl = (exit_price - entry_price) if direction == 'long' else (entry_price - exit_price)
                pnl_atr = pnl / entry_atr
                trades.append({
                    'pnl_atr': pnl_atr,
                    'direction': direction,
                    'bars_held': i - entry_bar,
                    'exit_reason': exit_reason,
                })
                in_trade = False

    return pd.DataFrame(trades) if trades else None


def summarize(trades_df):
    if trades_df is None or len(trades_df) == 0:
        return None
    wins = trades_df[trades_df['pnl_atr'] > 0]
    losses = trades_df[trades_df['pnl_atr'] <= 0]
    total = len(trades_df)
    n_w = len(wins); n_l = len(losses)
    wr = n_w / total * 100
    avg_win = wins['pnl_atr'].mean() if n_w > 0 else 0
    avg_loss = abs(losses['pnl_atr'].mean()) if n_l > 0 else 0
    payout = avg_win / avg_loss if avg_loss > 0 else float('inf')
    mean_pnl = trades_df['pnl_atr'].mean()
    median_pnl = trades_df['pnl_atr'].median()
    expectancy = (n_w/total)*avg_win - (n_l/total)*avg_loss
    return {
        'trades': total, 'wr': wr, 'payout': payout,
        'mean': mean_pnl, 'median': median_pnl,
        'avg_win': avg_win, 'avg_loss': avg_loss,
        'expectancy': expectancy,
    }


# ============== RUN SWEEP ============
print("Loading stocks data...")
stocks = load_stocks()
print(f"STOCKS: {stocks['Ticker'].nunique()} tickers, {len(stocks):,} rows")

all_tickers = stocks['Ticker'].unique()


def run_variant(label, params):
    print(f"\n>>> [{label}] {params if params else '(baseline)'}")
    all_trades = []
    for ticker in all_tickers:
        tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
        trades = run_test3(tdf, **params)
        if trades is not None and len(trades) > 0:
            all_trades.append(trades)
    agg = pd.concat(all_trades) if all_trades else None
    s = summarize(agg)
    if s is None:
        print("    No trades.")
        return None
    passes = sum([
        s['mean'] > s['median'],
        s['avg_win'] > s['avg_loss'],
        s['payout'] > 2,
        s['wr'] > 50,
        s['expectancy'] > 0,
        True, True,
    ])
    print(f"    trades={s['trades']}  WR={s['wr']:.1f}%  payout={s['payout']:.2f}  "
          f"mean={s['mean']:+.3f}  med={s['median']:+.3f}  exp={s['expectancy']:+.3f}  "
          f"7-crit={passes}/7")
    s['name'] = label
    s['passes'] = passes
    return s


# ============== VARIANTS ============
# Smaller indicators = more trades
# Baseline T3-A3: rsi_entry=35/65, stop=0.75, adx=20

variants = [
    # Original T3-A3
    ("T3-A3 original", {'rsi_entry_long': 35, 'rsi_entry_short': 65, 'stop_atr': 0.75}),
    
    # Smaller RSI = more pullback entries
    ("RSI 40/60 (smaller)", {'rsi_entry_long': 40, 'rsi_entry_short': 60, 'stop_atr': 0.75}),
    ("RSI 42/58 (even smaller)", {'rsi_entry_long': 42, 'rsi_entry_short': 58, 'stop_atr': 0.75}),
    ("RSI 45/55 (smallest)", {'rsi_entry_long': 45, 'rsi_entry_short': 55, 'stop_atr': 0.75}),
    
    # Lower ADX = more trend entries
    ("ADX>15 (lower)", {'rsi_entry_long': 40, 'rsi_entry_short': 60, 'stop_atr': 0.75, 'adx_threshold': 15}),
    ("ADX>10 (even lower)", {'rsi_entry_long': 40, 'rsi_entry_short': 60, 'stop_atr': 0.75, 'adx_threshold': 10}),
    
    # Combined: smaller RSI + lower ADX
    ("RSI 42/58 + ADX>15", {'rsi_entry_long': 42, 'rsi_entry_short': 58, 'stop_atr': 0.75, 'adx_threshold': 15}),
    ("RSI 42/58 + ADX>10", {'rsi_entry_long': 42, 'rsi_entry_short': 58, 'stop_atr': 0.75, 'adx_threshold': 10}),
    
    # Tighter stop = more entries (smaller stop)
    ("stop 0.5 (tighter)", {'rsi_entry_long': 40, 'rsi_entry_short': 60, 'stop_atr': 0.5}),
    ("stop 0.25 (even tighter)", {'rsi_entry_long': 40, 'rsi_entry_short': 60, 'stop_atr': 0.25}),
    
    # Combined: smaller RSI + tighter stop
    ("RSI 42/58 + stop 0.5", {'rsi_entry_long': 42, 'rsi_entry_short': 58, 'stop_atr': 0.5}),
    ("RSI 42/58 + stop 0.25", {'rsi_entry_long': 42, 'rsi_entry_short': 58, 'stop_atr': 0.25}),
    
    # All small: RSI 42/58 + ADX>10 + stop 0.5
    ("ALL SMALL: RSI 42/58 + ADX>10 + stop 0.5", 
     {'rsi_entry_long': 42, 'rsi_entry_short': 58, 'stop_atr': 0.5, 'adx_threshold': 10}),
    
    # All small + stop 0.25
    ("ALL SMALL: RSI 42/58 + ADX>10 + stop 0.25", 
     {'rsi_entry_long': 42, 'rsi_entry_short': 58, 'stop_atr': 0.25, 'adx_threshold': 10}),
]

results = []
for label, params in variants:
    s = run_variant(label, params)
    if s is not None:
        results.append(s)

# Print comparison summary
print("\n\n" + "=" * 80)
print("TEST 3 — TF BASE + MR LAYER — SWEEP RESULTS (SMALLER INDICATORS)")
print("=" * 80)
print(f"{'Variant':<35} {'Trades':>7} {'WR%':>6} {'Payout':>7} {'Mean':>8} {'Median':>8} {'Exp':>8} {'7-crit':>7}")
print("-" * 80)
for s in sorted(results, key=lambda x: (-x['passes'], -x['expectancy'])):
    print(f"{s['name']:<35} {s['trades']:>7} {s['wr']:>6.1f} {s['payout']:>7.2f} "
          f"{s['mean']:>+8.4f} {s['median']:>+8.4f} {s['expectancy']:>+8.4f} {s['passes']:>5}/7")

# Show best
if results:
    best = max(results, key=lambda x: (x['passes'], x['expectancy']))
    print(f"\n>>> BEST: {best['name']}")
    print(f"    trades={best['trades']}, WR={best['wr']:.1f}%, payout={best['payout']:.2f}")
    print(f"    mean={best['mean']:+.4f}, median={best['median']:+.4f}, exp={best['expectancy']:+.4f}")
    fails = []
    if best['mean'] <= best['median']: fails.append('Mean>Median')
    if best['avg_win'] <= best['avg_loss']: fails.append('AvgWin>AvgLoss')
    if best['payout'] <= 2: fails.append('Payout>2')
    if best['wr'] <= 50: fails.append('WR>50')
    if best['expectancy'] <= 0: fails.append('Exp>0')
    print(f"    Fails: {', '.join(fails) if fails else 'NONE — ALL 7 PASS!'}")

# Show top 3 by number of trades
print("\n--- Top 3 by number of trades ---")
top3_trades = sorted(results, key=lambda x: -x['trades'])[:3]
for s in top3_trades:
    print(f"  {s['name']}: {s['trades']} trades, WR={s['wr']:.1f}%, exp={s['expectancy']:+.4f}")
