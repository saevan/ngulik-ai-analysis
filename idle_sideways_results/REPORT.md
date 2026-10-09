# Idle cash sideways module experiment

Primary is Breakout+ER, fade2 priorATR and SMA30 exit, no time cap. Secondary is new confirmed band rebound: prior Close<=prior lower Bollinger band, current Close>current lower band and >previous Close; stock ER20<0.30. Band=SMA20-k*population std20, k1/1.5/2. Secondary entry only when market proxy prior-bar regime is sideways AND stock prior-bar ER<0.30, next tradable Open. Queued secondary orders are canceled outside eligibility. Exits next tradable Open after Close>=SMA20, Close<=entry-2entryATR, or age10/20bars. Terminal marks remain.

All eligible primary entries processed first in ticker order. Secondary fills residual slots/cash, max10 total positions, no reserved allocation, one position per ticker, no same-bar reentry or leverage. A secondary position already held can block future primary signals: primary-first is same-open priority, not a guarantee of zero opportunity cost. Standalone reserves all slots for secondary, disabling primary entries.

Stocks2000-2025, initialRp1billion, each new position10% previous close equity cash-capped, compounding. Fee0.15%buy/0.25%sell. Fees model no spread/fractional units. Spread is modern grid/100share lot plus1tick each side counterfactually across history, not actual historical bid/ask. Existing data selection/adjustment/liquidity limitations remain.

Six combinations per cost model plus baselines; best full-sample spread sideways annual equivalent selected for standalone/reverse sensitivity. In-sample selection, no untouched validation. Time slices are descriptive. Sideways annual equivalent attributes disjoint daily returns and is not independently executable CAGR. No automatic AFL adoption. Primary baseline exact equity regression, range entry regime eligibility, standalone module isolation, cash/slot/PnL and attribution checks passed.

| Variant | CAGR | Sideways annual equivalent | Sideways idle | Records /308 | MDD | Secondary trades |
|---|---:|---:|---:|---:|---:|---:|
| fees_combined_bNone_h10_reverseFalse | 33.65% | 20.10% | 27.97% | 108 | -34.90% | 0 |
| fees_combined_b1_h10_reverseFalse | 22.29% | 5.93% | 7.40% | 76 | -56.11% | 2454 |
| fees_combined_b1_h20_reverseFalse | 20.35% | 5.36% | 6.89% | 69 | -55.70% | 2345 |
| fees_combined_b1.5_h10_reverseFalse | 19.79% | 3.64% | 10.29% | 72 | -55.71% | 1883 |
| fees_combined_b1.5_h20_reverseFalse | 20.70% | 3.21% | 9.24% | 79 | -57.09% | 1822 |
| fees_combined_b2_h10_reverseFalse | 24.12% | 6.64% | 15.32% | 81 | -47.75% | 1276 |
| fees_combined_b2_h20_reverseFalse | 24.05% | 6.30% | 14.32% | 84 | -50.39% | 1252 |
| spread_combined_bNone_h10_reverseFalse | 13.37% | 0.51% | 28.22% | 52 | -52.64% | 0 |
| spread_combined_b1_h10_reverseFalse | -15.74% | -38.19% | 9.22% | 0 | -99.05% | 2524 |
| spread_combined_b1_h20_reverseFalse | -14.21% | -36.28% | 8.42% | 0 | -98.49% | 2436 |
| spread_combined_b1.5_h10_reverseFalse | -11.23% | -32.29% | 11.29% | 0 | -96.80% | 1936 |
| spread_combined_b1.5_h20_reverseFalse | -10.67% | -32.07% | 10.30% | 0 | -96.18% | 1883 |
| spread_combined_b2_h10_reverseFalse | -5.03% | -25.64% | 15.89% | 0 | -89.19% | 1310 |
| spread_combined_b2_h20_reverseFalse | -4.63% | -24.60% | 15.02% | 0 | -89.48% | 1284 |
| fees_standalone_b2_h20_reverseFalse | -10.51% | -16.27% | 53.53% | 0 | -94.59% | 2750 |
| fees_combined_bNone_h10_reverseTrue | 32.62% | 17.97% | 28.34% | 101 | -36.22% | 0 |
| fees_combined_b2_h20_reverseTrue | 23.38% | 7.20% | 14.26% | 86 | -52.05% | 1257 |
| spread_standalone_b2_h20_reverseFalse | -23.44% | -37.97% | 64.67% | 0 | -99.90% | 2410 |
| spread_combined_bNone_h10_reverseTrue | 11.97% | -1.19% | 28.62% | 53 | -54.87% | 0 |
| spread_combined_b2_h20_reverseTrue | -5.85% | -25.49% | 14.89% | 0 | -89.35% | 1295 |