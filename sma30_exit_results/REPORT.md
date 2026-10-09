# SMA30 exit backtest

Two separate entries: (1) prior-HHV20 breakout and ER20>=0.30, (2) active AFL default setup: Close>SMA30, Close>previousClose, HHV High10 including signal bar minus Close>=0.25 prior ATR14. Both entry signals use completed bars, next tradable Open execution. This is a Python portfolio replication of AFL default signals, not native AmiBroker execution or its fixed-notional test harness.

Exit comparison: original H200 Close plus fade5 previous ATR14 versus NO holding cap and completed Close<SMA30 followed by next tradable Open. Equality does not trigger. Uses level condition, not Cross, so already-below positions also exit. Fading measured from each current bar Open, next tradable Open fill, unchanged and reason priority before SMA if simultaneous. No secondary module/profit trail. Terminal closures/marks remain.

Stocks2000-01-04 through2025-08-15, Rp1billion, ten slots, entry10% prior-close equity capped cash, compounding. Buy0.15%,sell0.25%. Fee-only fractional units/no spread. Spread stress applies modern price grid/100share lot and1tick each side counterfactually over history; not observed historical bid/ask. Same universe/adjustment/market-impact limitations. Reverse ticker priority sensitivity. All in-sample, no universal or seven-criterion claim. Active AFL unchanged.

Sideways uses prior-bar market proxy ER, conditional annual equivalent concatenates disjoint days and is not independently executable CAGR. Baseline regression, entry-prefix causality, no-time-exit assertion, cash/slot/PnL and attribution reconciliation checked. Unit tests cover strict below/equality, gap execution next Open and suspension queue.

| Variant | CAGR | Records | MDD | Trades | WR | Mean bars | Sideways annual equivalent |
|---|---:|---:|---:|---:|---:|---:|---:|
| breakout_ER_fees_H200_reverseFalse | 33.43% | 127/308 | -56.33% | 340 | 62.65% | 180.7 | 18.97% |
| breakout_ER_fees_SMA30_reverseFalse | 35.24% | 89/308 | -39.47% | 1989 | 40.77% | 25.3 | 18.58% |
| breakout_ER_fees_H200_reverseTrue | 27.73% | 93/308 | -55.43% | 345 | 58.55% | 178.0 | 10.05% |
| breakout_ER_fees_SMA30_reverseTrue | 32.06% | 93/308 | -37.51% | 2007 | 40.56% | 25.1 | 15.03% |
| breakout_ER_spread_H200_reverseFalse | 29.92% | 117/308 | -59.70% | 340 | 59.71% | 180.7 | 15.25% |
| breakout_ER_spread_SMA30_reverseFalse | 17.87% | 57/308 | -50.16% | 1991 | 36.46% | 25.3 | 1.68% |
| breakout_ER_spread_H200_reverseTrue | 24.16% | 82/308 | -57.84% | 345 | 56.23% | 178.0 | 6.44% |
| breakout_ER_spread_SMA30_reverseTrue | 15.47% | 53/308 | -51.36% | 2012 | 36.53% | 25.1 | -1.62% |
| AFL_pullback_fees_H200_reverseFalse | 17.40% | 91/308 | -57.53% | 333 | 53.75% | 186.8 | 3.98% |
| AFL_pullback_fees_SMA30_reverseFalse | 20.30% | 74/308 | -63.03% | 4451 | 26.71% | 14.1 | 4.10% |
| AFL_pullback_fees_H200_reverseTrue | 20.00% | 101/308 | -52.86% | 338 | 54.73% | 184.0 | 8.36% |
| AFL_pullback_fees_SMA30_reverseTrue | 30.39% | 76/308 | -49.49% | 4442 | 27.42% | 14.0 | 10.80% |
| AFL_pullback_spread_H200_reverseFalse | 14.70% | 78/308 | -58.65% | 333 | 50.45% | 186.8 | 1.59% |
| AFL_pullback_spread_SMA30_reverseFalse | -10.07% | 8/308 | -97.37% | 4452 | 21.32% | 14.1 | -25.89% |
| AFL_pullback_spread_H200_reverseTrue | 16.99% | 92/308 | -55.88% | 338 | 52.96% | 184.0 | 6.07% |
| AFL_pullback_spread_SMA30_reverseTrue | -2.99% | 8/308 | -89.77% | 4461 | 21.81% | 14.0 | -21.38% |