# Executable swing trading inside medium/large sideways ranges (30 Oct 2026, written before results)
Motivation (sideways_size_results): Swinger ideal earns most in choppy stocks with 10-40% 20-bar ranges (+5..+9% per
trade) by following 5-bar swings, not by fading. Its fills are not executable; here an executable version is tested
ONLY inside those ranges.
Setup (known at the previous Close t-1): stock's own ER20 < 0.2; 20-bar range width (H/L - 1) in the bucket; realistic
universe (point-in-time liquidity + stale filter); 2000-01-01..2025-08-15; cost B 0.90% round trip.
Entry: buy stop on day t at the highest High of the last 5 bars (t-5..t-1); fills when High >= level at max(Open, level)
(gap rule: skip if Open > level x 1.02). One position per stock at a time.
Exit: sell stop at the lowest Low of the last 5 bars (known before each day), fill at min(Open, level) when Low <= level;
variant T: also take profit with a limit at the 20-bar range high known at entry (fill max(Open, level)); time stop 40 bars.
Grid: width {10-20%, 20-40%, 10-40%} x entry position {any, lower half of the range at t-1} x exit {stop only, stop +
target} = 12 cells.
Control per cell: random entries (5 seeds) on days with the same condition and position filter, bought at the next Open,
same exits, same number of trades per stock.
A cell passes only if ALL: net per trade > 0 with Newey-West t >= 3 (daily series by entry date, lag 20); net > 0 in >= 3
of 4 subperiods; gross above its random control by >= 0.5 pp. Neighbours must agree (>= 2 of the 3 width buckets with the
same entry/exit positive) for a pass to count. Nothing is adopted without a portfolio test.
