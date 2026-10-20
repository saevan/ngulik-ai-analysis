# Second logic for choppy stocks: buy the bottom of the range, sell toward the top (20 Oct 2026, before results)

User idea: a logic that is the inverse of logic 1 (breakout, trades only when ER says "trending") and trades only when ER
says choppy, to earn the up-and-down swings of sideways markets. Earlier versions (8-9 Oct: inverted signals, inverse
market switch, range escape, RSI2/support) failed after costs, but they used the old execution and the full survivor
universe. This retest uses the realistic universe and real limit-order mechanics. Per the user's 7 Oct rule the module
must work standalone before it is combined with logic 1.

Rules (causal, daily bars, one position per stock, realistic universe: liquid at the time and not stale):
- Active only if the stock's prior-bar ER20 < th (choppy).
- Entry: buy limit at LB = lowest Low of the previous N bars, placed before the Open; filled if Low[t] < LB (trades
  through), at min(Open[t], LB).
- Exit (from the next bar): sell limit at the target (mid = (LB + UB)/2 or top = UB, UB = highest High of the previous N
  bars at entry), filled if High > target at max(Open, target); stop: Close < entry - k x ATR14 -> sell next Open
  (k = 2, or no stop); time stop: sell at the Close of bar 20.
- Grid: N {10, 20} x target {mid, top} x th {0.3, 0.2} x stop {2 ATR, none} = 16 variants, all reported.
Costs: B = 0.90% round trip (A = 0.40%). Statistic: mean net return per trade, averaged per entry day, Newey-West t (lags 20).
Pass (standalone): net B > 0 with t >= 3 in 2000-25 and positive in at least 3 of 2000-07, 2008-15, 2016-20, 2021-25.
Only a passing variant goes on to a portfolio test combined with logic 1. AFL unchanged.
