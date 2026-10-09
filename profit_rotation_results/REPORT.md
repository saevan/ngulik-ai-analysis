# Profit rotation experiment

Existing Breakout+ER, hold200, fade5 ATR unchanged. Added exit: fix ATR14 from prior completed bar at entry; arm once highest subsequent closing price minus actual entry fill >= activation*entryATR; when completed Close <= highest Close - retracement*entryATR, sell next tradable Open. Full exit; next entries still require original breakout/ER signals, cash and free slots. No same-bar reentry. Existing fade/time exits retain priority. Gaps and costs can turn a profit-trail exit into a loss. No same-bar ideal level fills.

Stocks 2000-01-04 to 2025-08-15; Rp1 billion, ten slots, prior-close equity sizing/compounding. Buy0.15% sell0.25%. Fees scenario no spread/fractional units; spread scenario modern IDX ticks plus100-share lots and one tick per side counterfactually applied to history. Not observed historical bid/ask. Original universe/corporate-action/market-impact limitations remain.

Grid activation2/4/8 and retracement1/2/4 ATR. Selected spread-CAGR winner tested with reverse ticker priority. Entire history is searched in-sample; time slices and reverse priority are sensitivities, not independent holdout validation. Not a claim of seven-criteria or cross-market success. Baseline exact equity regression checked; every run has engine cash/slot/PnL assertions. No active AFL change.

| Costs | Reverse | Activate ATR | Retrace ATR | CAGR | Record months | MDD | Trades | WR | Payout |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fees | False | 0 | 0 | 33.43% | 127/308 (41.23%) | -56.33% | 340 | 62.65% | 3.16 |
| fees | False | 2 | 1 | 18.72% | 96/308 (31.17%) | -55.93% | 1023 | 77.13% | 0.61 |
| fees | False | 2 | 2 | 22.58% | 103/308 (33.44%) | -52.58% | 925 | 70.05% | 0.97 |
| fees | False | 2 | 4 | 20.26% | 86/308 (27.92%) | -55.19% | 703 | 56.47% | 1.83 |
| fees | False | 4 | 1 | 17.91% | 90/308 (29.22%) | -60.89% | 744 | 72.85% | 0.78 |
| fees | False | 4 | 2 | 22.07% | 100/308 (32.47%) | -56.91% | 694 | 72.19% | 0.88 |
| fees | False | 4 | 4 | 23.85% | 99/308 (32.14%) | -60.47% | 573 | 65.79% | 1.49 |
| fees | False | 8 | 1 | 15.18% | 78/308 (25.32%) | -59.83% | 527 | 62.24% | 1.21 |
| fees | False | 8 | 2 | 21.26% | 101/308 (32.79%) | -50.21% | 516 | 62.98% | 1.43 |
| fees | False | 8 | 4 | 22.65% | 99/308 (32.14%) | -51.72% | 473 | 63.21% | 1.55 |
| spread | False | 0 | 0 | 29.92% | 117/308 (37.99%) | -59.70% | 340 | 59.71% | 3.06 |
| spread | False | 2 | 1 | 7.18% | 45/308 (14.61%) | -57.82% | 916 | 71.62% | 0.58 |
| spread | False | 2 | 2 | 11.79% | 68/308 (22.08%) | -60.54% | 863 | 66.63% | 0.86 |
| spread | False | 2 | 4 | 11.94% | 56/308 (18.18%) | -60.69% | 683 | 52.42% | 1.68 |
| spread | False | 4 | 1 | 12.97% | 71/308 (23.05%) | -62.13% | 746 | 71.05% | 0.72 |
| spread | False | 4 | 2 | 13.20% | 64/308 (20.78%) | -61.19% | 671 | 68.26% | 0.86 |
| spread | False | 4 | 4 | 16.62% | 70/308 (22.73%) | -64.27% | 553 | 64.20% | 1.24 |
| spread | False | 8 | 1 | 15.04% | 78/308 (25.32%) | -56.14% | 530 | 62.83% | 1.20 |
| spread | False | 8 | 2 | 13.95% | 70/308 (22.73%) | -54.47% | 509 | 59.92% | 1.30 |
| spread | False | 8 | 4 | 16.36% | 71/308 (23.05%) | -54.81% | 458 | 59.39% | 1.54 |
| fees | True | 0 | 0 | 27.73% | 93/308 (30.19%) | -55.43% | 345 | 58.55% | 2.87 |
| fees | True | 4 | 4 | 21.69% | 83/308 (26.95%) | -60.47% | 584 | 64.04% | 1.42 |
| spread | True | 0 | 0 | 24.16% | 82/308 (26.62%) | -57.84% | 345 | 56.23% | 2.74 |
| spread | True | 4 | 4 | 14.99% | 63/308 (20.45%) | -64.27% | 558 | 58.24% | 1.48 |