# Market structure battery v3 (26 Oct 2026, written before results)
User: list the structures that exist in the market (like "red and green candles are balanced") that we can use later.
Already measured (market_properties_v2, 62 tests; candle balance 26 Oct) are not repeated. New structures, Kompas100
panel 2000-2025.08 (market_properties_v2/panel.py: clean log levels, forward returns from the next Open), subperiods
2000-07 / 08-15 / 16-20 / 21-25, universe 'all' and 'eligible' (point-in-time top-half liquidity + stale filter).

S0 Data grid: share of Closes that are integers / on today's IDX tick grid (are prices unadjusted?).
S1 Auto-reject (ARA/ARB, approximate bands 35/25/20% by price; ARB 7% 2020-03-10..2023-06-04): frequency; next-day
   gap and Open-to-Close; abnormal return from the next Open over 1/5/20 days.
S2 Swing structure (pivot = bar whose High/Low is the extreme of +-3 bars, known 3 bars later): HH+HL vs LH+LL state;
   persistence (P next confirmed swing high is higher | state); abnormal return from next Open over 5/20 days by state.
S3 Swing legs (descriptive): up/down leg length and size; retracement depth of the down-leg vs the prior up-leg; P(next
   up-leg makes a new high | retracement bucket <38.2 / 38.2-61.8 / 61.8-100 / >100%); hazard of an up-leg ending by age.
S4 Volatility squeeze: ATR10/ATR100 in the bottom 10% of the stock's own past 250 days -> next 10-day range / ATR and
   |return| vs unconditional; direction (abnormal fo10).
S5 Round numbers: (if prices are on the grid) for prices 1,000-10,000: touch from below of a level ending in 00 vs 50
   (same spacing): P(Close above the level | High touched it), and abnormal fo5 after closing above.
S6 Prior extremes as resistance/support: touch of the prior 60-day high from below (distance from prior Close d): P(Close
   >= level | High >= level) vs arbitrary levels at the same distance d (all stock-days); same for the 60-day low.
S7 Close location in the day's range (CLV quintiles): next overnight, next intraday, abnormal fo5.
S8 Correlation structure: average pairwise 60-day correlation of daily returns (eligible stocks, sampled every 21 days)
   when the market fell > 10% / rose > 10% / in between over that window.
S9 Regime durations: spell lengths of uptrend / sideways / downtrend labels and the spell-to-spell transition matrix.
S10 Gaps >= 2% up / down: filled the same day / within 5 days, by subperiod.

"Usable" (event types S1, S2, S4, S5, S7): abnormal effect NW t >= 3 (lags = h), same sign in >= 3 of 4 subperiods,
same sign in the eligible universe; for a standalone trade also |effect| > 0.9% (cost B), otherwise a filter/sizing/risk
structure. Descriptive structures (S0, S3, S6, S8, S9, S10) are reported with their stability across subperiods.
