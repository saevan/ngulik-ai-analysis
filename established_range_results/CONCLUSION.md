# Established ranges in sideways: buy the bottom zone, take profit at the top (21 Oct 2026)

Plan first (`PLAN.md`); code `established_range.py`; independent re-derivation `verify_established_range.py` (all 32 cells
reproduced exactly) plus an exploratory rescue grid (`verify_exploratory.csv`). Realistic universe, 2000-2025, cost B 0.90%.

- All 32 cells lose even before costs: gross -0.4% to -2.2% per trade, net -1.3% to -2.9%. None passes.
- Ranges that already went back and forth do slightly worse than other ranges (28 of 32 cells, but only 2 with |t| >= 2)
  and worse than random lower-half entries.
- Mechanism (corrected by the verifier): more prior back-and-forth DOES give more take-profit hits (21% -> 47% as visits
  rise from 1 to 4+), because such ranges are narrower (6.8 -> 3.9 ATR). The target is therefore closer (+7.8% vs +11.8%
  average win) while the realized stop loss stays about -7% (Close-based stop sold at the next Open, often through a gap).
  More bounces, but too small to pay for the breakdowns.
- Exploratory rescues (not pre-registered): narrow ranges only, >= 3 full swings, bullish confirmation bar, take profit at
  the mid, and combinations: 1 of 92 rows has gross > 0 (+0.03%, noise), 0 of 92 are positive after cost.
- Stock-level persistence of range success could not be tested (only 2 usable year pairs).
AFL unchanged.
