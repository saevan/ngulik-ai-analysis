# Calibration v3: is there a better module to chase Swinger ideal, using what we learned? (26 Oct 2026, before results)
Reference: V2 now (breakout buy stop HHV20 +0.5%, ER20 >= 0.2, mom120 order, exits fade 2 ATR / Close < SMA30, no failed
exit, 25% orders; monthly module: Close > Close 120 and ER20 >= 0.3, own exit, 10% orders, max 35%). Also "breakout only".
Benchmark: Swinger ideal only (B: 102.0% CAGR, 232 record months, MDD -21%, WR 48.8%). Costs B, 2000-01-01..2025-08-15.

Levers (each motivated by a finding):
- swing filter (structure S2): off / skip entries when the swing structure (pivot +-3, known at the previous Close) is
  down (LH+LL) / require up (HH+HL);
- ER threshold of the breakout (v2 W1.7: effect concentrated at high ER): 0.2 / 0.3 / 0.5;
- ranking of orders: mom120 / ER20 of the previous bar (v2: mom120 ranking not significant);
- crash guard (S8, correlation 0.43 in sell-offs; breadth result): off / no new entries while the equal-weight market's
  60-day return at the previous Close is below -10%;
- monthly module: off / on (as in V2);
- order size: 25% / 33% of equity (size = largest CAGR lever in v2).
3 x 3 x 2 x 2 x 2 x 2 = 144 configurations, unrestricted and realistic (point-in-time liquidity + stale filter + 25% ADV cap).
Filters apply to all entries (breakout and monthly) through the entry gate.

Selection (train 2000-2015 only): highest realistic train CAGR among configurations with unrestricted full-period CAGR >=
V2 now - 5 pp and MDD not more than 5 pp deeper than V2 now in both versions.
The pick is "better than V2 now" only if ALL: realistic test (2016-2025.08) CAGR >= V2 now; realistic holdout 1996-1999
CAGR >= V2 now; paired monthly log-return difference vs V2 now (realistic, full period) Newey-West t >= 1.5.
Reported: the pick, the top 10 by train, lever marginal effects (median over the other levers), gap to Swinger ideal.
AFL unchanged.
