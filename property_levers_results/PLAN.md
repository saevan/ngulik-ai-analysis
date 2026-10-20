# Property-driven levers on the v2 main pick: pre-registered plan (20 Oct 2026, before any result)

Question from the user: how does our system perform now versus Swinger ideal, after the market-properties v2 study?
The v2 study changed nothing in the system yet. This test applies, one at a time, the rule changes that the property study
supports or rejects, on the v2 main pick, and compares every variant with Swinger ideal on the same windows.

Base V0 = v2 main pick `F1_ch20_er0.2_cand_f0.0_s4_b0.005` exactly as in `search_realistic_chase_v2.py` (buy stop 0.5% above
HHV20 on the price grid, touch fills/sells, pre-Open order book, prior-bar ER20 >= 0.2, mom120 priority, gap_skip 2%,
gapdown_close 2%, exits fade 2 ATR / Close < SMA30 / failed breakout, 25% of equity per order).

Variants (one change each unless stated), motivated by `market_properties_v2/CONCLUSION.md`:
- V1 no gap_skip (W1.9: no penalty for gap-through fills; critic C-b: gap-up breakout entries did better)
- V2 no failed-breakout exit (W1.10: failed breakouts do not underperform the market afterwards)
- V3 ER20 >= 0.3 (W1.7)            V4 ER20 >= 0.5 (W1.7 ER bins: effect concentrated at >= 0.5)
- V5 rank candidates by prior-bar ER20 instead of mom120 (W1.7 + D2/C-g: mom120 ranking not supported)
- V6 no gapdown_close (importance check: B4/X-E say it helped historically, less since Dec 2024)
- V7 = V1 + V2 (drop both unsupported rules)     V8 = V1 + V2 + V5

Windows: train 2000-2015, validation 2016-2020, test 2021-2025-08-15, full 2000-2025 (each a fresh Rp1bn start).
Scenarios: A = fee 0.15/0.25%; B = A + 0.25%/side slippage (main). Universe: all 100; plus pre2018 (80) for test and full in B.
Swinger ideal (afl_ideal, 10% per position) is recomputed as a fresh Rp1bn start per window, same scenarios.
Metrics: CAGR, record months (months with >= 1 new daily equity high), MDD, trades, win rate, payout, time invested.

Decision rule per lever V1-V6 (vs V0, scenario B, all universe), fixed now:
- SUPPORTED: CAGR higher in train AND validation AND test, full records >= V0 - 2, full MDD not worse than V0 by > 5 pp.
- MIXED: CAGR higher in exactly 2 of the 3 windows.  NOT SUPPORTED: otherwise.
V7/V8 are reported for information only (no selection). No variant becomes the new main system from this test alone:
all windows were already seen (properties were measured on 2000-2025, ~40,000 earlier runs). AFL is not changed.
