"""Test 7 batch 1 — entries with few trades"""
import sys
sys.path.insert(0, r"C:\Users\ACER\OneDrive\Documents\Ngulik AI")
from backtest_test6_v2 import (load_stocks, run_strategy, summarize, bootstrap_stability,
                                common_exit)

print("Loading...", flush=True)
stocks = load_stocks()
print("Done loading.\n", flush=True)


def run_entry(name, entry_mode, entry_params=None):
    if entry_params is None:
        entry_params = {}
    params = {**common_exit, **entry_params}
    print(f">>> {name}", flush=True)
    all_trades = []
    for ticker in stocks['Ticker'].unique():
        tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
        tr = run_strategy(tdf, params, entry_mode)
        if tr is not None and len(tr) > 0:
            tr['ticker'] = ticker
            all_trades.append(tr)
    agg = pd.concat(all_trades) if all_trades else None
    s = summarize(agg)
    if s is None:
        print("    No trades", flush=True)
        return None
    passes = sum([s['mean']>s['median'], s['avg_win']>s['avg_loss'], s['payout']>2,
                  s['wr']>50, s['expectancy']>0, True, True])
    print(f"    trades={s['trades']}  WR={s['wr']:.2f}%  payout={s['payout']:.2f}  "
          f"mean={s['mean']:+.3f}  exp={s['expectancy']:+.3f}  7-crit={passes}/7", flush=True)
    if s['trades'] >= 50:
        bs = bootstrap_stability(agg)
        if bs:
            print(f"    BS: WR={bs['wr_mean']:.1f}%, WR>50%:{bs['wr_pass_pct']:.0f}%, "
                  f"Exp>0:{bs['exp_pass_pct']:.0f}%, Payout>2:{bs['payout_pass_pct']:.0f}%", flush=True)
    s['name'] = name; s['passes'] = passes; s['trades_df'] = agg
    return s


import pandas as pd

results = []

# 7A: composite strict
results.append(run_entry("7A: trend+ADX+RSI<45+ATR<0.7+BO 1bar", '7A_strict',
                          dict(rsi_thresh=45, atr_ratio_thresh=0.7, breakout_mult=1.5, min_consec=1)))
results.append(run_entry("7A: trend+ADX+RSI<40+ATR<0.7+BO 1bar", '7A_strict',
                          dict(rsi_thresh=40, atr_ratio_thresh=0.7, breakout_mult=1.5, min_consec=1)))
results.append(run_entry("7A: trend+ADX+RSI<45+ATR<0.6+BO", '7A_strict',
                          dict(rsi_thresh=45, atr_ratio_thresh=0.6, breakout_mult=1.5, min_consec=1)))

# 7B: BB contraction
results.append(run_entry("7B: BB<0.6 + breakout", '7B_bb_breakout',
                          dict(bb_contract_thresh=0.6, breakout_mult=1.5, min_consec=1)))
results.append(run_entry("7B: BB<0.5 + breakout", '7B_bb_breakout',
                          dict(bb_contract_thresh=0.5, breakout_mult=1.5, min_consec=1)))

# 7C: HTF + LTF
results.append(run_entry("7C: EMA50>EMA200 + RSI<45 + ROC5>0", '7C_htf_ltf',
                          dict(rsi_thresh=45, adx_thresh=20, min_consec=1)))
results.append(run_entry("7C: EMA50>EMA200 + RSI<45 + ADX>15", '7C_htf_ltf',
                          dict(rsi_thresh=45, adx_thresh=15, min_consec=1)))

print("\n=== BATCH 1 SUMMARY ===", flush=True)
for r in sorted([r for r in results if r is not None], key=lambda x: (-x['passes'], -x['expectancy'])):
    print(f"  {r['name']:<55} trades={r['trades']:>5} WR={r['wr']:>5.1f}% pay={r['payout']:>4.2f} "
          f"exp={r['expectancy']:+.3f} 7c={r['passes']}/7", flush=True)
print("Done batch 1.", flush=True)
