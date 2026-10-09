# ER-based automatic entry switching

Three controls at threshold0.30/0.40/0.50/0.60: stock_ER_only raises individual-stock ER requirement only; trend_gate_only additionally permits primary entry only when previous market-proxy ER>=threshold; switch enables secondary only when previous market ER<threshold. Unknown warmup allows neither gate. Higher threshold classifies MORE days as choppy; it does not make a choppy entry intrinsically better.

Primary unchanged: breakout priorHHV20, stockER>=threshold, no holding cap, exitSMA30 or fade2 priorATR from current Open, next tradable Open. Secondary fixed diagnostic prototype: previousClose<=previous lowerBollinger20(2std), currentClose reenters above band and rises, stockER<threshold; recoverySMA20/entryATR2stop/age20, next tradable Open. Previously this secondary did not pass standalone tests. This run tests the switching proposal, not an assertion it now has positive edge.

Entry gates complementary at market level, main and secondary entries never enabled on same market date. Existing holdings retain their own exits when gate changes; positions from both modules can overlap. This is entry switching, not forced-liquidation or separate fixed budgets. Same sharedRp1billion/10slots/10%prior-equity size/cashcap compounding, one holding per ticker, no leverage. New main gate signals only on tradable bars so stale queued entry cannot cross regime.

Saham2000-2025Aug15. Fee0.15%buy/0.25%sell. Spread stress uses modern grid/100share lots and1tick per side counterfactually, not actual historical quotes. Same universe/adjustment/market-impact limits. Market proxy is equal-weight supplied stocks, not IHSG. ER magnitude does not distinguish up/down; primary remains long-only breakout. Evaluation regimes remain ORIGINAL0.30 for every threshold, avoiding changing the yardstick. Sideways/uptrend annual equivalent attributes disjoint days, not standalone CAGR.

All tests in-sample, chronological slices descriptive only. Baseline exact equity regression, complementary gates, actual entry date eligibility, accounting/attribution checks passed. No active AFL change, no adoption of unproven secondary.

| Costs | Mode | ER | CAGR | Record months /308 | MDD | Sideways equivalent | Sideways cash | Trend trades | Choppy trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fees | stock_ER_only | 0.3 | 33.65% | 108 | -34.90% | 20.10% | 27.97% | 2392 | 0 |
| spread | stock_ER_only | 0.3 | 13.37% | 52 | -52.64% | 0.51% | 28.22% | 2396 | 0 |
| fees | trend_gate_only | 0.3 | 27.90% | 91 | -39.43% | 15.43% | 66.45% | 1528 | 0 |
| spread | trend_gate_only | 0.3 | 15.96% | 65 | -49.74% | 14.82% | 66.75% | 1528 | 0 |
| fees | switch | 0.3 | 16.11% | 66 | -56.20% | -1.89% | 32.36% | 1417 | 2276 |
| spread | switch | 0.3 | -10.00% | 0 | -94.26% | -27.43% | 33.72% | 1422 | 2340 |
| fees | stock_ER_only | 0.4 | 37.64% | 111 | -25.42% | 24.31% | 37.47% | 2110 | 0 |
| spread | stock_ER_only | 0.4 | 17.71% | 66 | -50.04% | 6.75% | 37.81% | 2114 | 0 |
| fees | trend_gate_only | 0.4 | 22.53% | 76 | -32.01% | 9.79% | 80.50% | 1056 | 0 |
| spread | trend_gate_only | 0.4 | 13.84% | 60 | -38.27% | 9.27% | 80.72% | 1054 | 0 |
| fees | switch | 0.4 | 7.10% | 41 | -59.16% | -7.29% | 32.05% | 981 | 3268 |
| spread | switch | 0.4 | -19.57% | 0 | -99.67% | -32.81% | 36.55% | 985 | 3333 |
| fees | stock_ER_only | 0.5 | 34.39% | 110 | -36.39% | 21.69% | 49.57% | 1772 | 0 |
| spread | stock_ER_only | 0.5 | 16.90% | 65 | -55.83% | 8.45% | 49.84% | 1773 | 0 |
| fees | trend_gate_only | 0.5 | 16.96% | 64 | -27.18% | 7.29% | 87.08% | 754 | 0 |
| spread | trend_gate_only | 0.5 | 11.10% | 44 | -32.80% | 7.28% | 87.11% | 754 | 0 |
| fees | switch | 0.5 | 2.48% | 21 | -61.93% | -7.60% | 31.24% | 695 | 3880 |
| spread | switch | 0.5 | -24.06% | 0 | -99.92% | -34.14% | 41.35% | 671 | 3678 |
| fees | stock_ER_only | 0.6 | 30.41% | 102 | -22.31% | 21.12% | 65.38% | 1294 | 0 |
| spread | stock_ER_only | 0.6 | 16.22% | 55 | -52.01% | 12.39% | 65.61% | 1296 | 0 |
| fees | trend_gate_only | 0.6 | 9.16% | 44 | -23.48% | 2.83% | 93.10% | 443 | 0 |
| spread | trend_gate_only | 0.6 | 5.12% | 27 | -40.75% | 2.74% | 93.14% | 443 | 0 |
| fees | switch | 0.6 | -5.26% | 1 | -82.20% | -11.60% | 32.18% | 425 | 4351 |
| spread | switch | 0.6 | -27.91% | 1 | -99.98% | -33.24% | 62.00% | 334 | 2829 |