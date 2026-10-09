# TimeHunter ATR normalization

Defaults declared before testing: ATR14 Wilder, pullback1 ATR, fading2 ATR; SMA30, High20, rebound1, hold200 and all execution rules unchanged. All costs zero. These defaults are not optimized winners. Grid is sensitivity only.

ATR seeding: TR[0]=High[0]-Low[0]; first ATR at index13 is mean of first14 TRs; subsequent Wilder recurrence. Both pullback and fading use ATR from previous completed bar. Entry condition evaluated at completed Close, entry next tradable Open. Fading anchor is each current Open, exit next tradable Open, regardless of position PnL. Invalid/zero ATR blocks both price-threshold signals.

Same selected surviving crypto samples and forex-session limitations as timehunter_cross_market_results. Full histories differ; common period2023-07-01 through2025-08-15. No fee, leverage or portfolio sizing in return metrics. Mean is per trade. Normalization does not prove universal performance or seven criteria.
| Market | Period | N | WR | PF | Payout | Mean | Median | Numerical |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| stocks | full | 5162 | 47.71% | 2.13 | 2.22 | 7.60% | 0.00% | 4/5 |
| stocks | common | 585 | 41.20% | 1.25 | 1.74 | 1.85% | -3.14% | 3/5 |
| forex04 | full | 96 | 53.12% | 1.31 | 1.15 | 0.33% | 0.17% | 4/5 |
| forex04 | common | 72 | 47.22% | 1.25 | 1.40 | 0.28% | -0.27% | 3/5 |
| crypto | full | 334 | 49.10% | 3.14 | 3.23 | 19.77% | -0.56% | 4/5 |
| crypto | common | 104 | 46.15% | 2.96 | 3.39 | 14.30% | -1.64% | 4/5 |
| forex00_sensitivity | full | 108 | 54.63% | 1.33 | 1.11 | 0.31% | 0.19% | 4/5 |
| forex00_sensitivity | common | 80 | 52.50% | 1.26 | 1.14 | 0.27% | 0.30% | 3/5 |