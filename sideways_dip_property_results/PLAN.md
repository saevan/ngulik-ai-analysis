# Second logic, step 1: property test "buy a dip in a strong stock at the Close, sell at the Open h days later"
(20 Oct 2026, written before any result)

Question: in sideways markets, does a dip in a stock whose long trend is still up recover enough, within a few days, to beat
the 0.90% round-trip cost when bought at the Close (closing auction) and sold at an Open (price + time)?

Data: market_properties_v2 panel (clean log levels lnP/lnO/lnH/lnL), 2000-01-01..2025-08-15.
Universe: realistic = stock liquid at the time (top half by 120-day traded value, >= 250 bars) and not stale (>= 90% traded
days, <= 10% one-price bars in the prior 60), same as pit_universe.py / pit_stale_liquidity.py; 'all' reported as context.
Signal at the Close of day t (stock tradable on t):
- sideways: primary = market regime 'sideways' on day t (er20 definition of analyze_sk5_regimes, label from Close t-1);
  secondary = the stock's own ER20 at Close t < 0.3.
- strong: lnP[t] > SMA200 of lnP (primary). weak = lnP[t] <= SMA200 (comparison group).
- dip: primary D1 = Close in the bottom 20% of the 10-day High-Low range (window t-9..t);
  secondary D2 = Close at least 2 ATR14 below the highest Close of t-9..t.
Trade: buy at Close t, sell at Open t+h, h = 1..10 (stock must trade on t+h; otherwise dropped, counts reported).
Return = lnO[t+h] - lnP[t] (log), net = minus 0.90% (cost B); 0.40% (A) reported.
Comparisons: (a) weak-stock dips, (b) all sideways stock-days (no dip, no trend filter) from the same Close,
(c) execution control for the same events: Open t+1 -> Open t+1+h and Close t -> Close t+h.
Statistics: mean of daily means (each signal day weighs 1), Newey-West t with lags = h; event-weighted means; 5th/95th
percentiles; periods 2000-25, 2000-07, 2008-15, 2016-20, 2021-25.
Pass (to build the logic): for strong-dip events under the primary definitions there is an h with net (cost B) > 0 and
t >= 3.25 (Bonferroni over 10 horizons x 2 dips x 2 sideways definitions), net > 0 in at least 3 of the 4 subperiods, and
strong minus weak > 0 at that h. Otherwise the 'buy the dip of strong stocks' second logic is not supported.
AFL unchanged.
