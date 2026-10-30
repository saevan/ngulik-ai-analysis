# Does each stock's OWN ER change the range picture? (30 Oct 2026, written before results)
User: check whether results differ if we classify by each stock's own ER instead of the market's.
Realistic universe (point-in-time liquidity + stale filter), 2000-01-01..2025-08-15. Stock classes by its own ER20 at the
Close of day t: choppy < 0.2, mid 0.2-0.3, trending >= 0.3; also split by the market label of that day (sideways / not).
1. Movement: mean |daily return| and ATR14% by class (is a "choppy" stock actually quiet?).
2. Range behaviour: day t with Close within 0.25 ATR14 of its 20-day low (bottom touch). Over the next 10 bars, which is
   hit first: the range mid ((20-day High + Low)/2) or the 20-day low - 1 ATR? Same for top touches (top - 1 ATR... mirror:
   mid first vs High + 1 ATR first). Baseline: the same start price run along 20 random 10-bar OHLC paths of the SAME stock
   (bootstrap, own history); same-bar double hits count as the adverse level first in both. Excess = actual - bootstrap,
   with a t from per-day means (Newey-West lag 10).
3. Trade: bottom touch -> buy next Open, exit at the mid (limit), stop Close < low - 1 ATR (next Open), time stop 10 bars;
   gross / net B per trade and NW t by class.
A class counts as "range-respecting" only if the bottom-touch excess P(mid first) >= +5 pp with t >= 3 and the trade is
net positive after cost B with t >= 3, positive in >= 3 of 4 subperiods.
