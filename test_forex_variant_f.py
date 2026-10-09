import pandas as pd
import numpy as np
import os
import sys
sys.path.insert(0, '.')
from backtest_diluc_sweep import run_diluc, summarize
from backtest_diluc import load_forex

print("Loading FOREX data...")
forex = load_forex()
print(f"FOREX: {forex['Ticker'].nunique()} tickers, {len(forex)} rows")

print("\nRunning Variant F on FOREX...")
all_trades = []
for ticker in forex['Ticker'].unique():
    tdf = forex[forex['Ticker'] == ticker].reset_index(drop=True)
    trades = run_diluc(tdf, adx_default=25, dawn_trailing_atr=3.0, dawn_stop_atr=1.0)
    if trades is not None and len(trades) > 0:
        all_trades.append(trades)
        print(f"  {ticker}: {len(trades)} trades")

print(f"\nTotal tickers with trades: {len(all_trades)}")
if all_trades:
    agg = pd.concat(all_trades)
    s = summarize(agg)
    print("\n=== Variant F on FOREX ===")
    print(f"Trades: {s['trades']}")
    print(f"WR: {s['wr']:.2f}%")
    print(f"Payout: {s['payout']:.2f}")
    print(f"Expectancy: {s['expectancy']:+.4f}")
    print(f"Mean: {s['mean']:+.4f}")
    print(f"Median: {s['median']:+.4f}")
else:
    print("No trades generated")
