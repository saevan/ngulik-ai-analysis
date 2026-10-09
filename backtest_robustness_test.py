"""
Test pernyataan: "Kalau logic benar → hasil konsisten across many trades.
Kalau hasil beda → logic salah atau kurang data."

Approach: Untuk T3-A3 (winner 7/7), periksa per-trade breakdown.
Kalau logic benar, harusnya distribusi trade masuk akal.
Kalau ada outlier besar yang swing hasil, itu suspect (overfit atau kurang data).
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


def run_test3_with_metadata(df, ticker_label,
                              adx_threshold=20,
                              rsi_entry_long=35, rsi_entry_short=65,
                              rsi_exit_long=70, rsi_exit_short=30,
                              stop_atr=0.75, trailing_atr=2.0, time_stop=25):
    """Returns trades WITH metadata for per-trade analysis."""
    if len(df) < 100:
        return None

    df = add_indicators(df).reset_index(drop=True)
    n = len(df)
    closes = df['Close'].values
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    emas = df['EMA50'].values
    adxs = df['ADX'].values
    rsis = df['RSI'].values
    atrs = df['ATR'].values
    dates = df['Date/Time'].values if 'Date/Time' in df.columns else None

    trades = []
    in_trade = False

    for i in range(50, n - 1):
        if not in_trade:
            atr = atrs[i]
            if np.isnan(atr) or atr <= 0:
                continue

            adx = adxs[i]; ema = emas[i]; rsi = rsis[i]; close = closes[i]
            if adx <= adx_threshold:
                continue

            signal = None
            if close > ema and rsi < rsi_entry_long:
                signal = 'long'
            elif close < ema and rsi > rsi_entry_short:
                signal = 'short'

            if signal:
                entry_price = opens[i + 1]
                entry_bar = i + 1
                entry_atr = atr
                entry_rsi = rsi
                entry_adx = adx
                if signal == 'long':
                    stop = entry_price - stop_atr * atr
                    rsi_exit = rsi_exit_long
                else:
                    stop = entry_price + stop_atr * atr
                    rsi_exit = rsi_exit_short
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
                new_t = extreme - trailing_atr * entry_atr
                if trailing_stop is None or new_t > trailing_stop: trailing_stop = new_t
            else:
                if cur_low < extreme: extreme = cur_low
                new_t = extreme + trailing_atr * entry_atr
                if trailing_stop is None or new_t < trailing_stop: trailing_stop = new_t

            if direction == 'long':
                if cur_low <= stop: exit_price, exit_reason = stop, 'stop'
                elif cur_rsi >= rsi_exit:
                    exit_price = opens[i + 1] if i + 1 < n else cur_close
                    exit_reason = 'rsi_exit'
                elif cur_low <= trailing_stop: exit_price, exit_reason = trailing_stop, 'trailing'
            else:
                if cur_high >= stop: exit_price, exit_reason = stop, 'stop'
                elif cur_rsi <= rsi_exit:
                    exit_price = opens[i + 1] if i + 1 < n else cur_close
                    exit_reason = 'rsi_exit'
                elif cur_high >= trailing_stop: exit_price, exit_reason = trailing_stop, 'trailing'

            if exit_price is None:
                if (i - entry_bar) >= time_stop:
                    exit_price = opens[i + 1] if i + 1 < n else cur_close
                    exit_reason = 'time_stop'

            if exit_price is not None:
                pnl = (exit_price - entry_price) if direction == 'long' else (entry_price - exit_price)
                pnl_atr = pnl / entry_atr
                trades.append({
                    'ticker': ticker_label,
                    'direction': direction,
                    'pnl_atr': pnl_atr,
                    'bars_held': i - entry_bar,
                    'exit_reason': exit_reason,
                    'entry_rsi': entry_rsi,
                    'entry_adx': entry_adx,
                    'entry_atr': entry_atr,
                })
                in_trade = False

    return pd.DataFrame(trades) if trades else None


# ============== RUN ==============
print("Loading data...")
stocks = load_stocks()
print(f"STOCKS: {stocks['Ticker'].nunique()} tickers\n")

print("=" * 80)
print("PER-TRADE BREAKDOWN — T3-A3 (winner 7/7)")
print("=" * 80)

all_trades = []
for ticker in stocks['Ticker'].unique():
    tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
    tr = run_test3_with_metadata(tdf, ticker)
    if tr is not None and len(tr) > 0:
        all_trades.append(tr)

trades_df = pd.concat(all_trades) if all_trades else None
print(f"Total trades: {len(trades_df)}")

# Sort by pnl_atr ascending (worst to best)
trades_sorted = trades_df.sort_values('pnl_atr').reset_index(drop=True)

print("\n--- TRADE-BY-TRADE (sorted worst → best) ---")
print(f"{'#':>3} {'Ticker':<7} {'Dir':<6} {'PnL ATR':>9} {'Bars':>5} {'Exit':>10} {'Entry RSI':>10} {'Entry ADX':>10}")
print("-" * 80)
for i, row in trades_sorted.iterrows():
    print(f"{i+1:>3} {row['ticker']:<7} {row['direction']:<6} {row['pnl_atr']:>+9.3f} "
          f"{row['bars_held']:>5} {row['exit_reason']:>10} {row['entry_rsi']:>10.2f} {row['entry_adx']:>10.2f}")

# Outlier detection
print("\n" + "=" * 80)
print("OUTLIER & ROBUSTNESS CHECK")
print("=" * 80)

mean_pnl = trades_df['pnl_atr'].mean()
median_pnl = trades_df['pnl_atr'].median()
std_pnl = trades_df['pnl_atr'].std()

print(f"\nMean: {mean_pnl:+.4f} ATR")
print(f"Median: {median_pnl:+.4f} ATR")
print(f"Std Dev: {std_pnl:.4f} ATR")
print(f"Skewness: {trades_df['pnl_atr'].skew():.3f}")
print(f"Kurtosis: {trades_df['pnl_atr'].kurtosis():.3f}")

# Coefficient of variation
cv = std_pnl / abs(mean_pnl) if mean_pnl != 0 else float('inf')
print(f"Coefficient of Variation (std/|mean|): {cv:.3f}")

# Top contributors
print(f"\nTop 5 winners (largest contributors to mean):")
top5 = trades_df.nlargest(5, 'pnl_atr')
total_pnl = trades_df['pnl_atr'].sum()
for _, row in top5.iterrows():
    pct = row['pnl_atr'] / total_pnl * 100
    print(f"  {row['ticker']:<7} {row['direction']:<6} pnl={row['pnl_atr']:+.3f} ({pct:>5.1f}% of total)")

print(f"\nBottom 5 losers:")
bot5 = trades_df.nsmallest(5, 'pnl_atr')
for _, row in bot5.iterrows():
    pct = row['pnl_atr'] / total_pnl * 100
    print(f"  {row['ticker']:<7} {row['direction']:<6} pnl={row['pnl_atr']:+.3f} ({pct:>5.1f}% of total)")

# Bootstrap test: leave-one-out to check if any single trade drives the result
print("\n" + "=" * 80)
print("BOOTSTRAP ROBUSTNESS — Leave-One-Out Test")
print("=" * 80)
print("(Kalau hapus 1 trade, apakah hasil masih positif?)")

loo_results = []
for i in range(len(trades_df)):
    sub = trades_df.drop(trades_df.index[i])
    n_w = (sub['pnl_atr'] > 0).sum()
    wr = n_w / len(sub) * 100
    avg_win = sub[sub['pnl_atr'] > 0]['pnl_atr'].mean() if n_w > 0 else 0
    avg_loss = abs(sub[sub['pnl_atr'] <= 0]['pnl_atr'].mean()) if (sub['pnl_atr'] <= 0).any() else 0
    payout = avg_win / avg_loss if avg_loss > 0 else float('inf')
    mean_p = sub['pnl_atr'].mean()
    med_p = sub['pnl_atr'].median()
    passes = sum([
        mean_p > med_p,
        avg_win > avg_loss,
        payout > 2,
        wr > 50,
        mean_p > 0,
        True, True
    ])
    loo_results.append({
        'dropped_ticker': trades_df.iloc[i]['ticker'],
        'dropped_pnl': trades_df.iloc[i]['pnl_atr'],
        'wr': wr, 'payout': payout, 'mean': mean_p, 'passes': passes
    })

loo_df = pd.DataFrame(loo_results)
print(f"\nLeave-One-Out Test:")
print(f"  WR (full): {trades_df['pnl_atr'].gt(0).mean()*100:.2f}%")
print(f"  WR after LOO: range [{loo_df['wr'].min():.2f}% - {loo_df['wr'].max():.2f}%]")
print(f"  Mean (full): {trades_df['pnl_atr'].mean():+.4f}")
print(f"  Mean after LOO: range [{loo_df['mean'].min():+.4f} - {loo_df['mean'].max():+.4f}]")
print(f"  7-criteria pass (full): {sum([mean_pnl > median_pnl, (trades_df[trades_df['pnl_atr']>0]['pnl_atr'].mean() if (trades_df['pnl_atr']>0).any() else 0) > (abs(trades_df[trades_df['pnl_atr']<=0]['pnl_atr'].mean()) if (trades_df['pnl_atr']<=0).any() else 1), (trades_df[trades_df['pnl_atr']>0]['pnl_atr'].mean() / abs(trades_df[trades_df['pnl_atr']<=0]['pnl_atr'].mean())) > 2, trades_df['pnl_atr'].gt(0).mean()*100 > 50, mean_pnl > 0, True, True])}/7")
print(f"  7-criteria after LOO: {loo_df['passes'].value_counts().to_dict()}")

# How often does dropping a single trade STILL give 7/7?
still_7 = (loo_df['passes'] == 7).sum()
print(f"\n  Trades where dropping STILL gives 7/7: {still_7}/{len(loo_df)} ({still_7/len(loo_df)*100:.1f}%)")

# How often does dropping a single trade break the WR > 50% requirement?
broken_wr = (loo_df['wr'] <= 50).sum()
print(f"  Trades where dropping breaks WR > 50%: {broken_wr}/{len(loo_df)} ({broken_wr/len(loo_df)*100:.1f}%)")

# Subsample bootstrap: take 50% of trades, check stability
print("\n" + "=" * 80)
print("SUBSAMPLE BOOTSTRAP (50% sample, 100 iterations)")
print("=" * 80)

np.random.seed(42)
boot_results = []
for _ in range(100):
    sample = trades_df.sample(frac=0.5, random_state=np.random.randint(0, 10000))
    n_w = (sample['pnl_atr'] > 0).sum()
    wr = n_w / len(sample) * 100
    avg_win = sample[sample['pnl_atr'] > 0]['pnl_atr'].mean() if n_w > 0 else 0
    avg_loss = abs(sample[sample['pnl_atr'] <= 0]['pnl_atr'].mean()) if (sample['pnl_atr'] <= 0).any() else 0
    payout = avg_win / avg_loss if avg_loss > 0 else float('inf')
    mean_p = sample['pnl_atr'].mean()
    boot_results.append({'wr': wr, 'payout': payout, 'mean': mean_p})

boot_df = pd.DataFrame(boot_results)
print(f"\nWR across 100 bootstraps: mean={boot_df['wr'].mean():.2f}%, "
      f"std={boot_df['wr'].std():.2f}%, range=[{boot_df['wr'].min():.2f}%, {boot_df['wr'].max():.2f}%]")
print(f"Payout: mean={boot_df['payout'].mean():.2f}, std={boot_df['payout'].std():.2f}")
print(f"Mean pnl: mean={boot_df['mean'].mean():+.4f}, std={boot_df['mean'].std():.4f}")

# % of bootstraps where WR > 50%
boot_wr_pass = (boot_df['wr'] > 50).sum()
boot_payout_pass = (boot_df['payout'] > 2).sum()
boot_exp_pass = (boot_df['mean'] > 0).sum()
print(f"\nBootstrap pass rates:")
print(f"  WR > 50%: {boot_wr_pass}/100 ({boot_wr_pass}%)")
print(f"  Payout > 2: {boot_payout_pass}/100 ({boot_payout_pass}%)")
print(f"  Expectancy > 0: {boot_exp_pass}/100 ({boot_exp_pass}%)")

# ============================================================
# FINAL VERDICT — Does user's claim hold?
# ============================================================
print("\n" + "=" * 80)
print("VERDICT — User's claim:")
print("Kalau logic benar → hasil stabil across subsamples")
print("Kalau logic salah → hasil bervariasi / butuh data lebih")
print("=" * 80)

# Stability score: how many bootstraps pass all 3 main criteria?
boot_df['all_pass'] = (boot_df['wr'] > 50) & (boot_df['payout'] > 2) & (boot_df['mean'] > 0)
all_pass_count = boot_df['all_pass'].sum()
print(f"\nBootstraps passing ALL 3 main criteria (WR>50%, Payout>2, Exp>0):")
print(f"  {all_pass_count}/100 ({all_pass_count}%)")
print()
if all_pass_count >= 80:
    print(">>> STRONG: Logic appears robust — high bootstrap pass rate suggests genuine edge")
elif all_pass_count >= 50:
    print(">>> MODERATE: Logic has edge but with significant variance — needs more data")
else:
    print(">>> WEAK: Logic may be overfit or insufficient data — result is fragile")
