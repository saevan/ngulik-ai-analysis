# Property-driven levers on the v2 main pick (20 Oct 2026)

Plan committed before results (`PLAN.md`); code `property_levers.py`; numbers `results.csv`. Base reproduces the v2 main pick
exactly (B: 40.1/74, 79.2/29, 54.1/20, full 49.3/119). Swinger ideal is a fresh Rp1bn start per window (B validation 91.8/45 and
test 65.7/42 match the earlier audit).

Scenario B (fee + 0.25%/side), CAGR % / record months / MDD %:

| Variant | 2000-15 | 2016-20 | 2021-25 | 2000-25 | 2000-25 w/o 2018+ listings |
|---|---|---|---|---|---|
| Swinger ideal | 116.8/145/-16 | 91.8/45/-21 | 65.7/42/-18 | 102.0/232/-21 | 98.3/227/-19 |
| V0 base (main pick) | 40.1/74/-23 | 79.2/29/-23 | 54.1/20/-24 | 49.3/119/-24 | 41.6/106/-31 |
| V1 no gap_skip | 38.2/71 | 69.7/26 | 71.5/27 | 49.7/122/-23 | 39.3/102 |
| V2 no failed exit | 32.5/64 | 73.1/29 | 78.0/28 | 47.6/119/-29 | 36.5/100 |
| V3 ER >= 0.3 | 38.4/60 | 54.4/22 | 31.5/14 | 39.5/95/-40 | 34.6/84 |
| V4 ER >= 0.5 | 40.4/67 | 35.9/20 | 38.8/18 | 40.0/107/-30 | 34.9/96 |
| V5 rank by ER | 33.6/55 | 49.9/26 | 29.9/8 | 37.6/90/-37 | 30.2/83 |
| V6 no gapdown_close | 38.3/69 | 78.9/29 | 51.9/20 | 47.5/114/-24 | 40.2/100 |
| V7 = V1+V2 | 29.7/56 | 69.0/27 | 90.5/29 | 45.7/108/-25 | 33.3/88 |
| V8 = V1+V2+V5 | 37.0/59 | 56.0/26 | 31.1/7 | 40.1/93/-47 | 34.1/91 |

Pre-registered decision (CAGR better in train AND validation AND test):
- V1, V2: better only in 2021-25 (1 of 3) -> NOT SUPPORTED. Their 2021-25 gain disappears without the 20 post-2018 listings.
- V3, V4, V5: NOT SUPPORTED (worse in validation and test; V4 train +0.3 pp only).
- V6: removing gapdown_close lowers CAGR in all three windows -> the existing rule is confirmed.
Event-level properties (ER, gap, failed breakout) did not translate into portfolio gains: higher ER or ER ranking leaves
slots idle and lowers records; removing rules helps only in the 2021-25 sample driven by new listings.
The main pick stays unchanged. Same caveats as v2: all windows seen before, survivorship, capacity, 25% sizing. AFL unchanged.
