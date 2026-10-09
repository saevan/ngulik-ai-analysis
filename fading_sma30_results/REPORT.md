# Fading sweep with SMA30 exit

Two separate entries: Breakout+ER20 versus active AFL SMA30/High10 pullback0.25ATR/rebound. No holding cap, strict Close<SMA30 signals next tradable Open exit. Fading(current Open-Low>=k*previous ATR14) also exits next tradable Open; k5/3/2/1/0.5. Original signals, sizing and ranking unchanged. Simultaneous fade/SMA signals tagged fading. No additional modules.

Stocks2000-01-04 to2025-08-15, Rp1billion, ten slots,10% prior-close equity entries, cash-constrained compounding, alphabetical ranking. Fees buy0.15%sell0.25%; fee-only fractional units/no spread. Spread stress modern grid/100share lots plus1tick each side counterfactually applied to historical adjusted-looking data; not actual bid/ask. Universe/liquidity/corporate action limitations retained. Terminal closure included.

Swinger ideal reference mean holding19.035bars,3241trades,CAGR114.77%,249/308records; same-bar Close-conditioned earlier-level fills and964outside-bar fills make it aspirational, not executable proof. Matching duration/trades does not match edge. Pullback baseline already holds shorter than Swinger. Whole-history in-sample sensitivity only; no out-of-sample or cross-market validation. Default AFL is not automatically changed based on duration matching.

All four fade5 baseline curves reproduce prior results. Cash/slot/PnL and regime-attribution reconciliation checked. Sideways annual equivalent is attribution of disjoint days, not standalone CAGR.

| Entry | Costs | Fade ATR | Mean bars | Trades | CAGR | Records /308 | MDD | WR |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| breakout_ER | fees | 5.0 | 25.33 | 1989 | 35.24% | 89 | -39.47% | 40.77% |
| breakout_ER | fees | 3.0 | 24.17 | 2069 | 35.04% | 99 | -38.16% | 40.89% |
| breakout_ER | fees | 2.0 | 20.39 | 2392 | 33.65% | 108 | -34.90% | 40.84% |
| breakout_ER | fees | 1.0 | 6.93 | 5519 | 19.81% | 83 | -40.30% | 39.08% |
| breakout_ER | fees | 0.5 | 3.38 | 8411 | 9.87% | 62 | -58.57% | 36.57% |
| breakout_ER | spread | 5.0 | 25.34 | 1991 | 17.87% | 57 | -50.16% | 36.46% |
| breakout_ER | spread | 3.0 | 24.14 | 2073 | 17.42% | 63 | -52.32% | 36.52% |
| breakout_ER | spread | 2.0 | 20.36 | 2396 | 13.37% | 52 | -52.64% | 36.19% |
| breakout_ER | spread | 1.0 | 6.95 | 5488 | -15.39% | 0 | -98.91% | 32.43% |
| breakout_ER | spread | 0.5 | 3.62 | 5973 | -25.59% | 0 | -99.95% | 27.66% |
| AFL_pullback | fees | 5.0 | 14.05 | 4451 | 20.30% | 74 | -63.03% | 26.71% |
| AFL_pullback | fees | 3.0 | 13.86 | 4518 | 19.57% | 72 | -60.74% | 26.63% |
| AFL_pullback | fees | 2.0 | 12.75 | 4931 | 17.70% | 66 | -63.17% | 28.13% |
| AFL_pullback | fees | 1.0 | 6.77 | 9819 | 11.08% | 51 | -74.99% | 33.08% |
| AFL_pullback | fees | 0.5 | 3.51 | 21315 | -1.46% | 52 | -98.33% | 34.77% |
| AFL_pullback | spread | 5.0 | 14.07 | 4452 | -10.07% | 8 | -97.37% | 21.32% |
| AFL_pullback | spread | 3.0 | 13.86 | 4520 | -10.87% | 7 | -97.70% | 21.33% |
| AFL_pullback | spread | 2.0 | 12.73 | 4946 | -15.34% | 0 | -98.93% | 22.46% |
| AFL_pullback | spread | 1.0 | 7.09 | 6114 | -32.60% | 0 | -100.00% | 26.38% |
| AFL_pullback | spread | 0.5 | 4.11 | 3532 | -36.52% | 0 | -100.00% | 19.79% |