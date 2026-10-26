# Grid search: monthly-module filter to catch moves BEFORE the breakout (26 Oct 2026, written before results)

User goal: the monthly module should capture profit earlier instead of always waiting for the breakout (idle cash /
choppy markets are a later topic). Base: V1 (V0 breakout unchanged + monthly entry, 10% orders, monthly first at the Open,
allowance 35%). Only the monthly filter changes. Costs B, 2000-01-01..2025-08-15.

Grid (filter at the month-end Close; exit when the trend condition fails at a month-end Close, sold next Open):
- trend lookback n: Close > Close n bars ago, n = 60, 120, 250;
- stock ER20 >= 0 (off), 0.2, 0.3, 0.4;
- pre-breakout proximity: off / Close within 5% / within 10% below the highest High of the last 60 bars AND Close
  not above the HHV20 breakout level (not broken out yet).
3 x 4 x 3 = 36 cells, unrestricted and realistic. V1 = (120, 0.3, off).

Selection (train 2000-2015 only): highest realistic train CAGR among cells keeping >= 70% of V0's breakout trades
(unrestricted, full period - a mechanical capacity check, not a performance one). Test 2016-2025.08 untouched by the
choice. The selected cell is an improvement over V1 only if, in the test period, realistic CAGR >= V1 and unrestricted
CAGR >= V1 - 5 pp, and realistic MDD (test) not more than 5 pp deeper than V1's.
Diagnostic "early capture": for monthly trades, share that later hit the HHV20 breakout level while held, and the
average gain from the monthly entry to that level (profit taken before the breakout system would have bought).
Nothing adopted automatically; AFL unchanged.
