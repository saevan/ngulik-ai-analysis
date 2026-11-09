# The bounces inside sideways ranges: how big, how long, how much is catchable (9 Nov 2026, written before results)
User: show me the bounces of the ranges during sideways. Descriptive only.

Swings: zigzag on each stock's Close with a reversal threshold X = 3% / 5% / 10%. A swing low is confirmed when the Close
rises X% above it; a swing high is confirmed when the Close falls X% below it. An up-leg (bounce) runs from a swing low
to the next swing high.
Each bounce is labelled by the market condition (`regime_proxy`) on the day its low is confirmed (the day a real-time
trader could act). The stock must be eligible that day (realistic universe). Also reported: the subset with the stock's
own ER20 < 0.2 that day. Period: confirmations 2000-01-01..2025-08-15.

Per X and condition:
- bounces per year;
- median / mean bounce size (low → high) and the preceding drop (high → low);
- median bars low → high;
- real-time catch: buy at the Close confirming the low, sell at the Close confirming the high (this gives up about X at
  each end); mean catch, mean catch after cost B 0.9%, share of bounces with catch after cost > 0.
Also the median 20-day range width (H20/L20 − 1) per condition, as the size of the "room" inside a range.
