"""Final refinement: no-stop + tight trailing variants"""
import os
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, r"C:\Users\ACER\OneDrive\Documents\Ngulik AI")
from backtest_exit_variants import load, add_ind, run_6b_variant, summarize

print("Loading...", flush=True)
stocks = load()
print("Done.\n", flush=True)


def run(name, **p):
    print(f">>> {name}: {p}", flush=True)
    all_t = []
    for t in stocks['Ticker'].unique():
        tdf = stocks[stocks['Ticker'] == t].reset_index(drop=True)
        tr = run_6b_variant(tdf, **p)
        if tr is not None and len(tr) > 0:
            tr['ticker'] = t
            all_t.append(tr)
    agg = pd.concat(all_t) if all_t else None
    s = summarize(agg)
    if s is None:
        print("    No trades\n", flush=True)
        return None, None
    print(f"    trades={s['trades']:>4} WR={s['wr']:.2f}% pay={s['payout']:.2f} "
          f"mean={s['mean']:+.3f} med={s['median']:+.3f} exp={s['expectancy']:+.3f}", flush=True)
    return s, agg


print("=== FINAL REFINEMENT ===\n", flush=True)

# Best so far variants
results = []

results.append(run("Best candidate: no stop, trail=3", stop_atr=None, trailing_atr=3.0))
results.append(run("No stop, trail=2.5", stop_atr=None, trailing_atr=2.5))
results.append(run("No stop, trail=2", stop_atr=None, trailing_atr=2.0))
results.append(run("No stop, trail=4", stop_atr=None, trailing_atr=4.0))
results.append(run("Wide stop=5, trail=3", stop_atr=5.0, trailing_atr=3.0))
results.append(run("No stop, trail=3, short time", stop_atr=None, trailing_atr=3.0,
                   time_strong=50, time_mod=20, time_weak=5))
results.append(run("No stop, trail=3, long time", stop_atr=None, trailing_atr=3.0,
                   time_strong=200, time_mod=100, time_weak=20))

print("\n=== SUMMARY ===", flush=True)
for r in [r for r, _ in results if r is not None]:
    print(f"  WR={r['wr']:.1f}% pay={r['payout']:.2f} "
          f"mean={r['mean']:+.3f} med={r['median']:+.3f} exp={r['expectancy']:+.3f}", flush=True)
