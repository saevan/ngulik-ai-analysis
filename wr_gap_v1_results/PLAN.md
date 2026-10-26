# What keeps our win rate below Swinger ideal? (V1, 26 Oct 2026, written before results)

System: V1 (see STRATEGY_NOTES 26 Oct: V0 + monthly F_mom & stock-ER entry, allowance 35%). Benchmark: Swinger ideal only
(B: WR 48.8%). Scenario B, 2000-01-01..2025-08-15, unrestricted and realistic.

## Part A - WR bridge (descriptive, trade level, same ledgers)
Each trade split into three legs:
- day 1: fill -> Close of the entry bar;
- holding: entry-bar Close -> Close of the bar where the exit was decided (ours: the bar before an Open exit, or the exit
  bar for Close exits; Swinger: the sell-signal bar);
- exit fill: decision Close -> exit fill.
Reported for V1 (breakout and monthly trades) and Swinger ideal:
- mean of each leg, and WR on three bases: as traded; Close-to-Close (holding leg only, costs 0.9% subtracted);
  as traded but with the fills replaced by the decision Closes;
- for Swinger ideal, its trades re-scored with entry and/or exit at the signal-bar Close, to measure how much of its WR
  comes from the signal-bar fills.

## Part B - executable test: confirm the breakout at the Close, buy at that Close
New engine mode entry_mode='close_fill' (default unchanged; regression must pass): at the Close of bar i, if Close >
HHV20 of the previous 20 Highs x (1+b) and the previous bar's ER20 >= 0.2, buy at that Close (pre-closing auction
approximation, cost B incl. 0.25% slippage), mom120 order, 25% orders; exits fade 2 ATR / Close < SMA30 (no failed exit:
the Close is above the level by construction). b = 0 and 0.5%. With and without the monthly module (V1 setup).
2 x 2 = 4 cells, unrestricted and realistic.
"Closes the WR gap" if WR >= 45% in both versions. Candidate to replace the buy stop only if also: realistic CAGR >= the
matching buy-stop system (V0 or V1) and MDD not more than 5 pp deeper; unrestricted CAGR >= matching system - 5 pp and
MDD not more than 5 pp deeper; realistic subperiods >= matching system in >= 3 of 4. Nothing adopted; AFL unchanged.
