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

## Step 2 (added after step 1 results, before step 2 results): monthly watchlist gate on the main pick
The month-start trend filter used as a watchlist for OUR system: during month m the main pick's buy stop is armed only in
stocks that passed filter F at their last Close of month m-1; everything else unchanged (V0 rules, B). Filters F_sma30,
F_sma120, F_er, F_high, F_mom. Control: random watchlist, each stock-month in with probability 0.5 / 0.7 (3 seeds each).
Unrestricted and realistic (watchlist intersected with the point-in-time + stale gate). Report WR, expectancy, CAGR,
records, MDD, subperiods, watchlist pass rate.
Candidate only if: realistic CAGR >= V0 realistic and MDD not deeper by > 5 pp; realistic subperiods >= V0 in >= 3 of 4;
unrestricted CAGR >= V0 - 5 pp; realistic CAGR above every random-watchlist seed; WR above V0's in both versions.

## Step 3 (user clarification 26 Oct: do not replace the breakout entry, ADD the monthly entry; fixed before step 3 results)
One shared portfolio (Rp1bn, max 10 positions, costs B): the main pick unchanged (buy stop, its exits, 25% per order) PLUS
a monthly entry: at the market's last trading day of the month, stocks passing a trend filter (Close-signal) are bought at
the first trading day's Open (mom120 order, gap rule 2% vs previous Close; dropped if not tradable that day). Monthly
positions use the monthly exit only (sell next Open when the filter fails at a month-end Close; gapdown_close applies);
breakout positions keep their own exits. A stock already held is not bought again by either entry.
- Filters: F_mom (Close > Close 120 bars ago), F_sma120, F_er. Monthly order size 25% or 10% of equity.
- Priority when cash/slots bind: P1 = monthly orders first at the Open, then the pre-Open buy-stop book with what is
  left; P2 = the buy-stop book reserves first, monthly orders use the unreserved cash and slots.
- 3 x 2 x 2 = 12 cells, unrestricted and realistic. Controls: monthly random selection (no filter, random order, held
  one month) added the same way, 3 seeds, each size/priority. Reference: fixed 50/50 split V0 + standalone F_mom monthly.
- Engine: new options extra_signal_fn / extra_exit_signal_fn / extra_size_div / extra_first in backtest_stop_execution.run;
  defaults unchanged (regression test must pass).
Candidate only if ALL: realistic CAGR >= V0 realistic (16.2%) and MDD not deeper than -49%; realistic record months >= 52;
realistic subperiods >= V0 in >= 3 of 4; unrestricted CAGR >= 44.3% (V0 - 5 pp) and MDD not deeper than -29%; realistic
CAGR above every random-control seed with the same size/priority; combined WR above V0's in both versions.
Reported also: WR / expectancy per entry type, breakout trades lost to capital competition, invested share.
