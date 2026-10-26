# Time element: buy trending stocks at the start of each month (26 Oct 2026, written before results)

User idea: add time to the system - at the start of each month buy only stocks that pass a "trending" filter (so we do
not buy everything), to fix the trend/win-rate problem (our WR 38% vs Swinger ideal 48.8%). Tested standalone as usual;
combining with the main system / idle cash comes later. Benchmark: Prototype Swinger ideal only (B: WR 48.8%, expectancy
+6.5%/trade, 1.88R, 102.0% CAGR, 232 record months, MDD -21%); our main pick V0 for reference (B: WR 38.3%, 49.3%, 119,
-24%; realistic 33.8%, 16.2%, 52, -44%).

## Rules (fixed)
- Signal at the Close of the market's last trading day of each month (stock traded that day); buy at the next tradable
  Open (first trading day of the new month). Order book before the Open, ranked by mom120 (same as the main system),
  gap rule 2% vs the previous Close, presize, pre-Open book. Costs B. 2000-01-01..2025-08-15.
- Trend filters at that Close (all use data up to that Close):
  F_sma30: Close > SMA30. F_sma120: Close > SMA120. F_er: ER20 >= 0.3 and Close > Close 20 bars ago.
  F_high: Close >= 95% of the highest Close of the last 120 bars. F_mom: Close > Close 120 bars ago.
- Exits: X_month = at each month-end Close, sell (next Open) the holdings that no longer pass their filter (held otherwise);
  X_sys = the main system's exits (fade 2 ATR, Close < SMA30, gapdown_close 2%; no failed-breakout rule, no breakout level);
  X_both = X_sys plus X_month.
- Size: 25% of equity per order (like ours) and 10% (like Swinger); max 10 positions.
- 5 filters x 3 exits x 2 sizes = 30 cells. Versions: B unrestricted and B realistic (point-in-time top-half liquidity +
  stale filter + buys <= 25% ADV20). Subperiod CAGR slices 2000-07 / 08-15 / 16-20 / 21-25. Holdout 1995-03..1999
  (unrestricted, descriptive).
- Controls (same timing): C_random = no filter, random order book priority (3 seeds), X_sys and a one-month hold
  (sell at the next month-end); C_mom = no filter, mom120 priority, X_sys. Size 25%.
- Engine: new entry_mode 'signal' (signal_fn: Close-signal -> next Open) and exit_signal_fn (Close-signal exit) in
  backtest_stop_execution.run; defaults unchanged, regression test must pass.

## Reported per cell
WR, expectancy (mean net/trade, month-bootstrap CI), E in R, payout, CAGR, record months, MDD, invested, trades/year.

## A cell is a candidate only if ALL hold (realistic version is the main test)
(a) realistic CAGR >= V0 realistic (16.2%) and realistic MDD not deeper than -49% (V0 realistic -44% minus 5 pp);
(b) realistic CAGR above both controls (C_random best seed, C_mom) with the same exit family;
(c) realistic CAGR slice >= V0 realistic in >= 3 of 4 subperiods;
(d) unrestricted CAGR > 0 in all 4 subperiods;
(e) WR >= 45% (closer to Swinger ideal's 48.8%) with expectancy CI above 0.
30 cells on one data set: a lone passing cell with failing neighbours is noise. Nothing is adopted; AFL unchanged.
