# Lowest-low entry, no-new-trade-high exit (21 Oct 2026)

Plan first (`PLAN.md`), code `lowest_low_time.py`, independent re-derivation `verify_lowest_low_time.py` (trade-by-trade
identical). Realistic universe, 2000-2025, 36 cells (N 10/20/60 x x 3/5/10 x sideways filter on/off x entry next Open/Close).

- All 36 cells lose after cost B: gross -0.87% to +0.33% per trade; best net B -0.24% (t -0.64). None near the pass rule.
- The entry is no better than random entries with the same exit (20-seed control: signal below control in 31 of 36 cells,
  z -2.05..+0.71). x = 3 or 5 is worse than random; x = 10 is about equal.
- Character: win rate after cost 34-38%, average win 5-10%, average loss 4-8%, hold 6-19 bars. 2021-25 is the worst period
  (about -1.7% to -2.1% per trade for the best cells).
- Robust to readings: plan's re-entry rule (new low after the exit), touching the trade high restarts the count, trade
  high on Close, exit at the Close of the x-th bar, strict vs touching lows, sideways filter on/off. None turns positive.
Caveats: single-seed control in results.csv is not reproducible (hash seed); avg win/loss columns split on gross while
win rate uses net; the Close-entry variant partly peeks at the closing auction. None changes the conclusion. AFL unchanged.
