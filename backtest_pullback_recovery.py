"""Verify user's claim: 'Setiap kenaikan baru, market akan bring harga turun dulu baru naik.
Setiap penurunan harga → anik (buy) lagi kalau tidak delisting'"""
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


def analyze_recovery(df):
    """For each dip from peak, measure probability and magnitude of recovery."""
    if len(df) < 100: return None

    df = df.reset_index(drop=True).copy()
    n = len(df)
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values

    # Find all-time-high up to each bar
    running_max = np.maximum.accumulate(highs)
    drawdown_pct = (closes - running_max) / running_max

    # For each dip level, check if recovered within N bars
    dip_events = []
    for i in range(20, n - 20):
        if drawdown_pct[i] <= -0.05:  # 5% dip
            entry_price = closes[i]
            # Check recovery within next 5, 10, 20, 50 bars
            recovered = {}
            for n_bars in [5, 10, 20, 50, 100, 200]:
                if i + n_bars < n:
                    max_future = np.max(highs[i+1:i+n_bars+1])
                    recovery_pct = (max_future - entry_price) / entry_price
                    recovered[f'r{n_bars}'] = recovery_pct > 0  # at least back to entry
                    recovered[f'r{n_bars}_new'] = recovery_pct  # magnitude
                else:
                    recovered[f'r{n_bars}'] = None
                    recovered[f'r{n_bars}_new'] = None
            recovered['dip_pct'] = drawdown_pct[i]
            recovered['bar_idx'] = i
            dip_events.append(recovered)

    return pd.DataFrame(dip_events) if dip_events else None


def analyze_pullback_recovery(df, dip_levels=[0.02, 0.05, 0.10, 0.15, 0.20]):
    """For each dip level, what's probability of recovery?"""
    if len(df) < 100: return None

    df = df.reset_index(drop=True).copy()
    n = len(df)
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    running_max = np.maximum.accumulate(highs)

    results = []
    for dip_level in dip_levels:
        dip_count = 0
        recovered_5 = 0
        recovered_10 = 0
        recovered_20 = 0
        recovered_50 = 0
        recovered_100 = 0
        recovered_200 = 0
        new_high_5 = 0
        new_high_20 = 0
        new_high_100 = 0

        for i in range(50, n - 200):
            # Is this bar at dip level?
            if closes[i] <= running_max[i] * (1 - dip_level):
                dip_count += 1
                entry_price = closes[i]

                # Check recovery within various periods
                if i + 5 < n:
                    future_highs = highs[i+1:i+6]
                    if np.any(future_highs >= entry_price * 1.01):
                        recovered_5 += 1
                if i + 10 < n:
                    future_highs = highs[i+1:i+11]
                    if np.any(future_highs >= entry_price * 1.01):
                        recovered_10 += 1
                if i + 20 < n:
                    future_highs = highs[i+1:i+21]
                    if np.any(future_highs >= entry_price * 1.01):
                        recovered_20 += 1
                if i + 50 < n:
                    future_highs = highs[i+1:i+51]
                    if np.any(future_highs >= entry_price * 1.01):
                        recovered_50 += 1
                if i + 100 < n:
                    future_highs = highs[i+1:i+101]
                    if np.any(future_highs >= entry_price * 1.01):
                        recovered_100 += 1
                if i + 200 < n:
                    future_highs = highs[i+1:i+201]
                    if np.any(future_highs >= entry_price * 1.01):
                        recovered_200 += 1

        results.append({
            'dip_level': f'{int(dip_level*100)}%',
            'dip_count': dip_count,
            'rec_5': recovered_5 / dip_count * 100 if dip_count > 0 else 0,
            'rec_10': recovered_10 / dip_count * 100 if dip_count > 0 else 0,
            'rec_20': recovered_20 / dip_count * 100 if dip_count > 0 else 0,
            'rec_50': recovered_50 / dip_count * 100 if dip_count > 0 else 0,
            'rec_100': recovered_100 / dip_count * 100 if dip_count > 0 else 0,
            'rec_200': recovered_200 / dip_count * 100 if dip_count > 0 else 0,
        })

    return pd.DataFrame(results)


print("Loading...", flush=True)
stocks = load()
print(f"Done. {stocks['Ticker'].nunique()} tickers.\n", flush=True)

# Aggregate across all tickers
print("=" * 80, flush=True)
print("USER CLAIM: 'Setiap penurunan → market akan recover (kalau tidak delisting)'", flush=True)
print("=" * 80, flush=True)
print("\nPullback recovery probability by dip depth:\n", flush=True)

all_results = []
for ticker in stocks['Ticker'].unique():
    tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
    res = analyze_pullback_recovery(tdf)
    if res is not None:
        all_results.append(res)

# Aggregate
combined = pd.concat(all_results).groupby('dip_level').agg({
    'dip_count': 'sum',
    'rec_5': 'mean',
    'rec_10': 'mean',
    'rec_20': 'mean',
    'rec_50': 'mean',
    'rec_100': 'mean',
    'rec_200': 'mean',
}).reset_index()

print(f"{'Dip':<10} {'N events':>10} {'Rec 5':>8} {'Rec 10':>8} {'Rec 20':>8} "
      f"{'Rec 50':>8} {'Rec 100':>8} {'Rec 200':>8}", flush=True)
print("-" * 75, flush=True)
for _, row in combined.iterrows():
    print(f"{row['dip_level']:<10} {int(row['dip_count']):>10} "
          f"{row['rec_5']:>7.1f}% {row['rec_10']:>7.1f}% {row['rec_20']:>7.1f}% "
          f"{row['rec_50']:>7.1f}% {row['rec_100']:>7.1f}% {row['rec_200']:>7.1f}%", flush=True)

print("\n** Interpretation:", flush=True)
print("  Rec 5:   recovered to entry+1% within 5 bars", flush=True)
print("  Rec 10:  recovered within 10 bars", flush=True)
print("  Rec 200: recovered within 200 bars", flush=True)

# Test 2: Is there a pattern that "new high is preceded by dip"?
print("\n" + "=" * 80, flush=True)
print("USER CLAIM 2: 'Setiap kenaikan baru, market bring harga down dulu baru naik'", flush=True)
print("=" * 80, flush=True)
print("\nProbability of a dip preceding a new all-time-high:\n", flush=True)

results_2 = []
for ticker in stocks['Ticker'].unique():
    tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
    n = len(tdf)
    if n < 200: continue
    closes = tdf['Close'].values
    highs = tdf['High'].values
    lows = tdf['Low'].values
    running_max_before = pd.Series(highs).cummax().values

    new_highs = 0
    new_highs_after_dip = 0
    for i in range(50, n - 50):
        # New all-time-high?
        is_new_high = highs[i] > running_max_before[i-1] if i > 0 else False
        if is_new_high:
            new_highs += 1
            # Did we have a dip recently (within last 20 bars)?
            recent_low = np.min(lows[i-20:i])
            recent_high_before = running_max_before[i-1]
            dip_pct = (recent_high_before - recent_low) / recent_high_before
            if dip_pct >= 0.02:
                new_highs_after_dip += 1

    if new_highs > 0:
        results_2.append({
            'ticker': ticker,
            'new_highs': new_highs,
            'after_dip': new_highs_after_dip,
            'pct': new_highs_after_dip / new_highs * 100,
        })

agg_2 = pd.DataFrame(results_2)
print(f"Total new all-time-highs across 100 stocks: {agg_2['new_highs'].sum():,}", flush=True)
print(f"  ... preceded by >=2% dip within 20 bars: {agg_2['after_dip'].sum():,}", flush=True)
pct = agg_2['after_dip'].sum() / agg_2['new_highs'].sum() * 100
print(f"  Percentage: {pct:.1f}%", flush=True)
print(f"  Average per stock: {agg_2['pct'].mean():.1f}%", flush=True)

print("\nDone.", flush=True)