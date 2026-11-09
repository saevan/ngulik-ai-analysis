# Does ER tell us what the market will do next? (9 Nov 2026, written before results)
User claim: ER identifies the market condition (straight = trend, choppy = sideways), so high ER → trend logic, low ER →
a second logic that exploits the back-and-forth bounces.
ER20 at day t is a description of days t-20..t. For a two-logic switch to work, ER at t must describe days t+1..t+20.
Descriptive test, no trading rules.

Stocks: realistic universe (point-in-time liquidity + stale filter), 2000-01-01..2025-08-15 (future windows end by
2025-08-15). Buckets of stock ER20 at Close t: < 0.1, 0.1-0.2, 0.2-0.3, 0.3-0.5, >= 0.5, plus all days (base rate).
Per bucket, over t+1..t+20:
1. Persistence:
   - median future ER20 (at t+20);
   - P(future ER20 < 0.2);
   - P(future ER20 >= 0.3).
2. Bounces:
   - mean lag-1 autocorrelation of daily log returns (negative = back-and-forth);
   - variance ratio VR(5) = var(5-day returns) / (5 x var(1-day returns)), where < 1 means mean reversion.
3. Continuation: mean of sign(past 20-day return) x future 20-day return. Positive means the past direction continues;
   negative means it reverses.
4. Range: vs the past 20-day High/Low range, the share of windows that stay inside, break only up, break only down, or
   break both; median future 20-day range width.
Market level (EW proxy of `regime_proxy`): the same persistence and continuation for market ER20 buckets, and the
regime label 20 trading days later (transition shares from uptrend / sideways / downtrend).
