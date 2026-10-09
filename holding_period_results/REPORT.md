# Holding period sweep

Existing Breakout+ER module, not the pullback AFL currently open. Only maximum holding bars vary; entry ER20>=0.30 and prior-HHV20 breakout, fade5 previous ATR14, next tradable Open entry/fade exit, scheduled hold-bar Close exit remain unchanged. Holding cap differs from observed mean duration.

Stocks 2000-01-04 through 2025-08-15; Rp1 billion, ten slots, compounding from prior-close equity. Buy fee0.15%, sell fee0.25%. Fees scenario has fractional units and no spread. Spread scenario applies modern grid/100-share lots and one tick each side counterfactually to history, not observed historical bid/ask. Reverse scenario changes only ticker priority.

New trades after early exits are included under the original entry rules. Portfolio CAGR therefore tests net replacement through reinvestment; this is not a matched-trade causal decomposition of foregone profit versus replacement profit. More trades need not mean better returns. Profit can also be saved by exiting losers earlier.

All holds and time slices use the same historical sample. No independent out-of-sample validation or universal seven-criterion pass. Original AFL untouched. H200 fee and spread curves reproduce saved baselines to numerical tolerance; engine cash/slot and terminal PnL reconciliation assertions run for every variant.

| Scenario | Hold cap | Actual mean bars | Trades | CAGR | Record months | MDD | WR | Payout |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fees | 10 | 10.12 | 4235 | 24.34% | 90/308 (29.22%) | -38.93% | 49.85% | 1.45 |
| fees | 20 | 20.16 | 2535 | 29.41% | 102/308 (33.12%) | -30.35% | 49.74% | 1.72 |
| fees | 30 | 29.69 | 1845 | 27.93% | 94/308 (30.52%) | -32.28% | 51.60% | 1.72 |
| fees | 50 | 48.64 | 1193 | 33.82% | 97/308 (31.49%) | -42.06% | 52.98% | 2.06 |
| fees | 75 | 72.26 | 825 | 26.86% | 93/308 (30.19%) | -46.02% | 55.52% | 1.90 |
| fees | 100 | 95.07 | 636 | 20.37% | 90/308 (29.22%) | -62.25% | 54.56% | 1.83 |
| fees | 150 | 137.46 | 445 | 22.71% | 96/308 (31.17%) | -55.56% | 53.93% | 2.45 |
| fees | 200 | 180.66 | 340 | 33.43% | 127/308 (41.23%) | -56.33% | 62.65% | 3.16 |
| spread | 10 | 10.12 | 4235 | -6.45% | 1/308 (0.32%) | -87.40% | 42.27% | 1.28 |
| spread | 20 | 20.16 | 2535 | 8.41% | 41/308 (13.31%) | -53.36% | 45.13% | 1.48 |
| spread | 30 | 29.69 | 1845 | 12.17% | 50/308 (16.23%) | -57.56% | 46.50% | 1.57 |
| spread | 50 | 48.64 | 1193 | 22.08% | 74/308 (24.03%) | -56.11% | 48.62% | 1.95 |
| spread | 75 | 72.35 | 825 | 19.31% | 75/308 (24.35%) | -49.59% | 51.64% | 1.84 |
| spread | 100 | 95.07 | 636 | 15.19% | 73/308 (23.70%) | -65.81% | 51.57% | 1.78 |
| spread | 150 | 137.46 | 445 | 18.88% | 83/308 (26.95%) | -56.18% | 52.36% | 2.26 |
| spread | 200 | 180.66 | 340 | 29.92% | 117/308 (37.99%) | -59.70% | 59.71% | 3.06 |
| fees_reverse | 10 | 10.12 | 4223 | 25.65% | 105/308 (34.09%) | -33.57% | 50.11% | 1.46 |
| fees_reverse | 20 | 20.15 | 2537 | 30.06% | 108/308 (35.06%) | -35.74% | 49.82% | 1.74 |
| fees_reverse | 30 | 29.69 | 1840 | 30.95% | 107/308 (34.74%) | -35.04% | 50.43% | 1.86 |
| fees_reverse | 50 | 48.56 | 1196 | 28.12% | 90/308 (29.22%) | -40.07% | 52.93% | 1.82 |
| fees_reverse | 75 | 72.45 | 825 | 30.66% | 107/308 (34.74%) | -45.22% | 54.06% | 2.09 |
| fees_reverse | 100 | 94.20 | 643 | 24.37% | 100/308 (32.47%) | -58.39% | 54.12% | 2.02 |
| fees_reverse | 150 | 139.13 | 440 | 27.13% | 98/308 (31.82%) | -52.08% | 51.36% | 2.97 |
| fees_reverse | 200 | 178.01 | 345 | 27.73% | 93/308 (30.19%) | -55.43% | 58.55% | 2.87 |