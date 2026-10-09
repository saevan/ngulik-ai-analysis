# Breakout ER portfolio: regime attribution

Uses existing ten-slot compounding equity, initial1billion, new buy10% prior-close equity capped cash. No new trades, no exit/rule changes. Primary variant ER20>=0.30, plus no-filter control and reversed-stock-priority sensitivity.

Market proxy=equal-weight daily return of available instrument closes, chained into an index; forward-fill missing closes, first listing has no return until prior price exists. Retains historical universe selection/survivorship limitations. Not IHSG, a crypto market-cap index or a USD index. Forex is a basket of the provided pair orientations.

Regime uses ONLY prior completed close: ER20 of proxy>=0.30 and positive20-bar displacement =>uptrend; negative=>downtrend; lowerER=>sideways. Unknown warmup labeled separately. Lag one observation; present-day return cannot classify itself. Exposure attribution uses actual days between observations, including weekends in the interval that ends at next observation. Current er column is diagnostic only; regime column is lagged.

Conditional annualized return=exp(sum of portfolio log returns in regime / calendar days assigned to regime *365.25)-1. It concatenates disjoint regime intervals; NOT the actual CAGR of a separately tradable strategy nor an expectation of future return. Annualized contribution uses total whole-history days instead, and product(1+contribution)-1 exactly reconciles to total portfolio CAGR.

Record month fraction=months with a portfolio all-time daily-closing equity record ON a day labeled with this regime / months containing at least one day in the regime. Portfolio peak never resets. Months may occur in multiple regimes, so counts/fractions must not be added. First/last partial months included; regimes with few days have weak annualized estimates.
| Market | Variant | Regime | Time share | Equivalent annual return | Whole-history annualized contribution | Record months / months present |
|---|---|---|---:|---:|---:|---:|
| stocks | er_0.3 | downtrend | 11.22% | 14.65% | 1.55% | 6/106 (5.66%) |
| stocks | er_0.3 | sideways | 55.30% | 19.61% | 10.41% | 84/280 (30.00%) |
| stocks | er_0.3 | uptrend | 33.48% | 70.85% | 19.64% | 93/211 (44.08%) |
| stocks | no_filter | downtrend | 11.22% | -5.45% | -0.63% | 2/106 (1.89%) |
| stocks | no_filter | sideways | 55.30% | 8.33% | 4.52% | 44/280 (15.71%) |
| stocks | no_filter | uptrend | 33.48% | 48.88% | 14.25% | 61/211 (28.91%) |
| stocks | er_0.3_reverse_priority | downtrend | 11.22% | 13.18% | 1.40% | 5/106 (4.72%) |
| stocks | er_0.3_reverse_priority | sideways | 55.30% | 10.64% | 5.75% | 58/280 (20.71%) |
| stocks | er_0.3_reverse_priority | uptrend | 33.48% | 71.32% | 19.75% | 72/211 (34.12%) |
| forex04 | er_0.3 | downtrend | 6.28% | 5.62% | 0.34% | 0/9 (0.00%) |
| forex04 | er_0.3 | sideways | 69.87% | 1.87% | 1.30% | 4/37 (10.81%) |
| forex04 | er_0.3 | unknown | 2.51% | 0.00% | 0.00% | 0/1 (0.00%) |
| forex04 | er_0.3 | uptrend | 21.35% | -4.14% | -0.90% | 4/25 (16.00%) |
| forex04 | no_filter | downtrend | 6.28% | 5.81% | 0.36% | 0/9 (0.00%) |
| forex04 | no_filter | sideways | 69.87% | 1.64% | 1.14% | 4/37 (10.81%) |
| forex04 | no_filter | unknown | 2.51% | 0.00% | 0.00% | 0/1 (0.00%) |
| forex04 | no_filter | uptrend | 21.35% | -3.42% | -0.74% | 5/25 (20.00%) |
| forex00 | er_0.3 | downtrend | 6.09% | 7.88% | 0.46% | 0/9 (0.00%) |
| forex00 | er_0.3 | sideways | 70.79% | 1.32% | 0.93% | 5/37 (13.51%) |
| forex00 | er_0.3 | unknown | 2.06% | 0.00% | 0.00% | 0/1 (0.00%) |
| forex00 | er_0.3 | uptrend | 21.06% | -2.80% | -0.60% | 4/24 (16.67%) |
| forex00 | no_filter | downtrend | 6.09% | 6.89% | 0.41% | 0/9 (0.00%) |
| forex00 | no_filter | sideways | 70.79% | 2.18% | 1.54% | 8/37 (21.62%) |
| forex00 | no_filter | unknown | 2.06% | 0.00% | 0.00% | 0/1 (0.00%) |
| forex00 | no_filter | uptrend | 21.06% | -2.36% | -0.50% | 7/24 (29.17%) |
| crypto | er_0.3 | downtrend | 12.47% | 60.16% | 6.05% | 0/57 (0.00%) |
| crypto | er_0.3 | sideways | 63.25% | 12.84% | 7.94% | 9/95 (9.47%) |
| crypto | er_0.3 | unknown | 0.68% | 0.00% | 0.00% | 0/2 (0.00%) |
| crypto | er_0.3 | uptrend | 23.60% | 625.21% | 59.60% | 15/64 (23.44%) |
| crypto | no_filter | downtrend | 12.47% | 67.39% | 6.63% | 0/57 (0.00%) |
| crypto | no_filter | sideways | 63.25% | 10.03% | 6.24% | 7/95 (7.37%) |
| crypto | no_filter | unknown | 0.68% | 0.00% | 0.00% | 0/2 (0.00%) |
| crypto | no_filter | uptrend | 23.60% | 536.25% | 54.75% | 13/64 (20.31%) |

Checks passed: regime prefix causality on every market, exact log-return attribution/CAGR reconciliation, and no reset of all-time-high records. No claim of causal regime predictability or out-of-sample validation.