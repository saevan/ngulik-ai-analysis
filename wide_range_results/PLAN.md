# Wider / longer ranges: is there a range big enough that fees do not eat the edge? (27 Oct 2026, before results)
User: check whether larger ranges can be exploited without being eroded by fees. Earlier range tests (20-60 bar ranges,
widths in ATR) all lost before costs. New here: ranges measured in % width and over longer windows.
Range at the Close of day t over the last N bars (N = 20, 60, 120, 250): H = highest High, L = lowest Low, width = H/L - 1,
position = (Close - L)/(H - L). Range-bound = the stock's own ER over N bars < 0.3.
Width buckets: 10-20%, 20-40%, 40-80%, >80%.
Entry: position <= 0.2 (bottom 20% of the range), bought at the next Open (one position per stock at a time).
Exits: target = range mid or top zone (L + 0.8 (H - L)), limit fill at max(Open, target) when High reaches it;
stop: Close below L x 0.97 -> next Open (variant: no stop); time stop N/2 bars at the Close.
Grid: 4 N x 4 widths x 2 targets x 2 stops = 64 cells. Realistic universe (point-in-time liquidity + stale filter), cost B
0.90% round trip, 2000-01-01..2025-08-15.
Control per cell: random entries (5 seeds) on days with the same N / width / ER condition and position <= 0.5, same
exits, same number of trades per stock.
A cell passes only if ALL: net per trade > 0 with Newey-West t >= 3 (daily series by signal date, lag 20); net > 0 in >= 3
of 4 subperiods (2000-07, 08-15, 16-20, 21-25); gross above its random control. Also reported: trades/year, win rate,
average win/loss, a cost-A (fee only, 0.40%) view.
