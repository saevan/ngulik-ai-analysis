"""Robustness check Test 7 winner 7A"""
import sys
sys.path.insert(0, r"C:\Users\ACER\OneDrive\Documents\Ngulik AI")
from backtest_test7_self import *

print("Loading...", flush=True)
stocks = load_stocks()
print("Done.\n", flush=True)

params = dict(rsi_thresh=45, atr_ratio_thresh=0.6, breakout_mult=1.5, min_consec=1)
all_t = []
for t in stocks['Ticker'].unique():
    tdf = stocks[stocks['Ticker'] == t].reset_index(drop=True)
    tr = run_strategy(tdf, params, '7A_strict')
    if tr is not None and len(tr) > 0:
        tr['ticker'] = t
        all_t.append(tr)

agg = pd.concat(all_t) if all_t else None
print(f"Total trades: {len(agg)}", flush=True)

# Per-trade breakdown
print("\n--- TRADE-BY-TRADE ---", flush=True)
sorted_t = agg.sort_values('pnl_atr').reset_index(drop=True)
for i, row in sorted_t.iterrows():
    print(f"  #{i+1}: ticker={row['ticker']} bars={row['bars_held']:>3} pnl={row['pnl_atr']:+.3f}", flush=True)

# Top contributors
total_pnl = agg['pnl_atr'].sum()
print(f"\nTotal PnL: {total_pnl:.3f}", flush=True)
top2 = agg.nlargest(2, 'pnl_atr')
top2_pct = top2['pnl_atr'].sum() / total_pnl * 100
print(f"Top 2 contribution: {top2_pct:.1f}%", flush=True)
for _, row in top2.iterrows():
    print(f"  {row['ticker']}: {row['pnl_atr']:+.3f} ({row['pnl_atr']/total_pnl*100:.1f}%)", flush=True)

# Bootstrap
np.random.seed(42)
boot = []
for _ in range(200):
    sample = agg.sample(frac=0.5, random_state=np.random.randint(0, 100000))
    s = summarize(sample)
    if s:
        boot.append(s)

wrs = [b['wr'] for b in boot]
means = [b['mean'] for b in boot]
payouts = [b['payout'] for b in boot]
print(f"\nBootstrap (50% sample, 200 iter):", flush=True)
print(f"  WR mean: {np.mean(wrs):.1f}% std: {np.std(wrs):.1f}%", flush=True)
print(f"  WR range: [{np.min(wrs):.1f}% - {np.max(wrs):.1f}%]", flush=True)
print(f"  WR>50% pass rate: {sum(w>50 for w in wrs)/len(wrs)*100:.1f}%", flush=True)
print(f"  Exp>0 pass rate: {sum(m>0 for m in means)/len(means)*100:.1f}%", flush=True)
print(f"  Payout>2 pass rate: {sum(p>2 for p in payouts)/len(payouts)*100:.1f}%", flush=True)
all3 = sum(1 for w,m,p in zip(wrs, means, payouts) if w>50 and m>0 and p>2)
print(f"  ALL 3 pass: {all3}/{len(wrs)} = {all3/len(wrs)*100:.1f}%", flush=True)

# LOO
print(f"\nLeave-One-Out test:", flush=True)
for i in range(len(agg)):
    sub = agg.drop(agg.index[i])
    s = summarize(sub)
    if s:
        passes_7 = sum([s['mean']>s['median'], s['avg_win']>s['avg_loss'], s['payout']>2,
                       s['wr']>50, s['expectancy']>0, True, True])
        print(f"  Drop #{i+1} ({agg.iloc[i]['ticker']}, pnl={agg.iloc[i]['pnl_atr']:+.2f}): "
              f"WR={s['wr']:.1f}% pay={s['payout']:.2f} exp={s['expectancy']:+.2f} 7c={passes_7}/7", flush=True)
