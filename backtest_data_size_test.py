"""
Test pernyataan: "MA10 vs MA20 vs MA200, semua dengan logic sama, akan ~30% WR"
Plus test RSI14, RSI7, RSI21 dengan logic sama → cek apakah konsisten 30%.
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


def load_forex():
    path = os.path.join(DATA_DIR, "Data Forex.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df['Date/Time'] = pd.to_datetime(df['Date/Time'])
    df = df.sort_values(['Ticker', 'Date/Time']).reset_index(drop=True)
    return df


# ====== Pure MA crossover baseline (THE SIMPLEST POSSIBLE STRATEGY) ======
def run_ma_crossover(df, fast=10, slow=50):
    """Long when fast MA crosses above slow MA, exit when crosses below."""
    df = df.copy().reset_index(drop=True)
    df['MA_fast'] = df['Close'].rolling(fast).mean()
    df['MA_slow'] = df['Close'].rolling(slow).mean()

    n = len(df)
    closes = df['Close'].values
    ma_fast = df['MA_fast'].values
    ma_slow = df['MA_slow'].values

    trades = []
    in_trade = False
    entry_price = None
    entry_bar = None

    for i in range(1, n - 1):
        if not in_trade:
            # fast crosses above slow
            if ma_fast[i] > ma_slow[i] and ma_fast[i-1] <= ma_slow[i-1]:
                entry_price = closes[i + 1]  # next bar open approximation
                entry_bar = i + 1
                in_trade = True
        else:
            # fast crosses below slow → exit at next bar open
            if ma_fast[i] < ma_slow[i] and ma_fast[i-1] >= ma_slow[i-1]:
                exit_price = closes[i + 1] if i + 1 < n else closes[i]
                pnl = exit_price - entry_price
                pnl_pct = (pnl / entry_price) * 100
                trades.append({
                    'pnl_pct': pnl_pct,
                    'bars_held': i - entry_bar,
                })
                in_trade = False

    # Close any open trade at end
    if in_trade:
        pnl = closes[n-1] - entry_price
        pnl_pct = (pnl / entry_price) * 100
        trades.append({'pnl_pct': pnl_pct, 'bars_held': n-1 - entry_bar})

    return pd.DataFrame(trades) if trades else None


# ====== Pure RSI mean reversion baseline ======
def run_rsi_mr(df, period=14, oversold=30, overbought=70):
    """Buy when RSI < oversold, exit when RSI > 50."""
    df = df.copy().reset_index(drop=True)
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    df['RSI'] = 100 - (100 / (1 + rs))

    n = len(df)
    closes = df['Close'].values
    rsis = df['RSI'].values

    trades = []
    in_trade = False
    entry_price = None
    entry_bar = None

    for i in range(period, n - 1):
        if not in_trade:
            if rsis[i] < oversold:
                entry_price = closes[i + 1]
                entry_bar = i + 1
                in_trade = True
        else:
            if rsis[i] > 50:
                exit_price = closes[i + 1] if i + 1 < n else closes[i]
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'pnl_pct': pnl_pct,
                    'bars_held': i - entry_bar,
                })
                in_trade = False

    if in_trade:
        pnl_pct = (closes[n-1] - entry_price) / entry_price * 100
        trades.append({'pnl_pct': pnl_pct, 'bars_held': n-1 - entry_bar})

    return pd.DataFrame(trades) if trades else None


def summarize(trades_df):
    if trades_df is None or len(trades_df) == 0:
        return None
    wins = trades_df[trades_df['pnl_pct'] > 0]
    total = len(trades_df)
    n_w = len(wins)
    wr = n_w / total * 100 if total > 0 else 0
    return {'trades': total, 'wr': wr}


# ============== RUN TESTS ==============
print("=" * 80)
print("TEST: DOES THE SAME LOGIC PRODUCE ~SAME WR ACROSS PARAMETERS?")
print("=" * 80)

print("\nLoading data...")
stocks = load_stocks()
print(f"STOCKS: {stocks['Ticker'].nunique()} tickers, {len(stocks):,} rows\n")


# === Test 1: MA Crossover family — same logic, different periods ===
print("=" * 80)
print("EXPERIMENT 1: MA CROSSOVER LOGIC, VARYING PERIODS")
print("Logic: Long when fast MA crosses above slow MA, exit when crosses below")
print("=" * 80)

ma_pairs = [
    ("MA(5/15)", 5, 15),
    ("MA(10/20)", 10, 20),
    ("MA(10/50)", 10, 50),
    ("MA(20/50)", 20, 50),
    ("MA(20/100)", 20, 100),
    ("MA(50/100)", 50, 100),
    ("MA(50/200)", 50, 200),
    ("MA(100/200)", 100, 200),
]

print(f"\n{'MA Pair':<14} {'Total Trades':>13} {'WR%':>8} {'Verdict':>15}")
print("-" * 55)

ma_results = {}
for label, fast, slow in ma_pairs:
    all_trades = []
    for ticker in stocks['Ticker'].unique():
        tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
        tr = run_ma_crossover(tdf, fast, slow)
        if tr is not None and len(tr) > 0:
            all_trades.append(tr)
    agg = pd.concat(all_trades) if all_trades else None
    s = summarize(agg)
    if s:
        print(f"{label:<14} {s['trades']:>13} {s['wr']:>7.2f}%")
        ma_results[label] = s['wr']


# === Test 2: RSI Mean Reversion family — same logic, different periods ===
print("\n" + "=" * 80)
print("EXPERIMENT 2: RSI MEAN REVERSION LOGIC, VARYING PERIODS")
print("Logic: Buy when RSI < 30, exit when RSI > 50")
print("=" * 80)

rsi_periods = [7, 10, 14, 21, 28]
print(f"\n{'RSI period':<14} {'Total Trades':>13} {'WR%':>8} {'Verdict':>15}")
print("-" * 55)

rsi_results = {}
for period in rsi_periods:
    all_trades = []
    for ticker in stocks['Ticker'].unique():
        tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
        tr = run_rsi_mr(tdf, period=period, oversold=30, overbought=70)
        if tr is not None and len(tr) > 0:
            all_trades.append(tr)
    agg = pd.concat(all_trades) if all_trades else None
    s = summarize(agg)
    if s:
        print(f"RSI({period}){' ':>5} {s['trades']:>13} {s['wr']:>7.2f}%")
        rsi_results[f"RSI({period})"] = s['wr']


# === Test 3: MA Crossover on FOREX ===
print("\n" + "=" * 80)
print("EXPERIMENT 3: MA CROSSOVER ON FOREX (more data, different market)")
print("=" * 80)
forex = load_forex()
print(f"FOREX: {forex['Ticker'].nunique()} tickers\n")

forex_pairs = [
    ("MA(10/20)", 10, 20),
    ("MA(20/50)", 20, 50),
    ("MA(50/200)", 50, 200),
]
forex_results = {}
for label, fast, slow in forex_pairs:
    all_trades = []
    for ticker in forex['Ticker'].unique():
        tdf = forex[forex['Ticker'] == ticker].reset_index(drop=True)
        tr = run_ma_crossover(tdf, fast, slow)
        if tr is not None and len(tr) > 0:
            all_trades.append(tr)
    agg = pd.concat(all_trades) if all_trades else None
    s = summarize(agg)
    if s:
        print(f"{label} (forex): trades={s['trades']}, WR={s['wr']:.2f}%")
        forex_results[label] = s['wr']


# === Test 4: Data-size dependency — same strategy on different time slices ===
print("\n" + "=" * 80)
print("EXPERIMENT 4: WR STABILITY AS DATA INCREASES")
print("Same logic (MA10/MA50), measuring WR per cumulative time slice")
print("=" * 80)

all_trades_full = []
for ticker in stocks['Ticker'].unique():
    tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
    tr = run_ma_crossover(tdf, 10, 50)
    if tr is not None and len(tr) > 0:
        tr['ticker'] = ticker
        all_trades_full.append(tr)

agg_full = pd.concat(all_trades_full) if all_trades_full else None

# Random sub-sampling at different fractions
np.random.seed(42)
print(f"\n{'Data fraction':<15} {'Sample size':>12} {'WR%':>8}")
print("-" * 40)
for frac in [0.1, 0.25, 0.5, 0.75, 1.0]:
    n_sample = int(len(agg_full) * frac)
    sample = agg_full.sample(n=n_sample, random_state=42)
    n_w = (sample['pnl_pct'] > 0).sum()
    wr = n_w / len(sample) * 100
    print(f"{int(frac*100):>3}%         {n_sample:>12} {wr:>7.2f}%")


# === Summary ===
print("\n" + "=" * 80)
print("SUMMARY — Empirical verification of user's claim")
print("=" * 80)

print("\nMA Crossover family (stocks):")
for k, v in ma_results.items():
    print(f"  {k}: WR={v:.2f}%")
print(f"  Range: {min(ma_results.values()):.2f}% - {max(ma_results.values()):.2f}%")
print(f"  Std dev: {np.std(list(ma_results.values())):.2f}")

print("\nRSI Mean Reversion family (stocks):")
for k, v in rsi_results.items():
    print(f"  {k}: WR={v:.2f}%")
print(f"  Range: {min(rsi_results.values()):.2f}% - {max(rsi_results.values()):.2f}%")
print(f"  Std dev: {np.std(list(rsi_results.values())):.2f}")

print("\n" + "=" * 80)
print("VERDICT — User's claim: ~30% WR regardless of MA period")
print("=" * 80)
ma_avg = np.mean(list(ma_results.values()))
print(f"MA crossover avg WR across 8 variants: {ma_avg:.2f}%")
print(f"Variance from 30%: {abs(ma_avg - 30):.2f} pts")
