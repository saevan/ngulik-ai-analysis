# Standalone sideways research

16 predefined training combinations: RSI2<5/15 aboveSMA200; 20bar support rejection with risingClose aboveSMA200; or5bar breakout aboveSMA50. All require prior-completed-bar equal-weight market proxy sideways. Individual stocks need not themselves be choppy: breakout family searches relative strength within a sideways market. Independent entry, no main strategy positions.

Exits Close<SMA5/10 or currentOpen-Low>=1/2priorATR, next tradable Open. No hold200. RSI uses explicitly implemented ewm(alpha0.5,adjustFalse) with2observations; no claim of exact AmiBroker RSI initialization. Entry only on tradable bars, expired setup not queued. Terminal closures for each separate period remain.

Train2000-2015, validation2016-2020, finaltest2021-2025Aug15. Frozen single candidate chosen only from train, no retuning on validation/test. Entire historical dataset was already examined in earlier research: these are chronological non-selection periods for this run, NOT genuinely untouched external data. Same survivorship/corporateaction/universe and capacity limitations.

InitialRp1billion for each period, max10positions/10%previous-equity sizing, cash-constrained compounding. Feesbuy0.15%sell0.25%. Selection uses modern-grid/100share-lot plus1tick each side stress, not historical observed bid/ask; fee-only sensitivity also shown. SMA/fade nextOpen executions; signal built with full earlier warmup. No merging or active AFL changes.

Success requires positive CAGR,PF>1.1,positive sideways attribution and>=40trades in train and both later windows; reverse test must remain positive. This is a research gate, not seven universal criteria. Sideways annual equivalent concatenates disjoint marked-equity days, not standalone CAGR. All actual entries checked against causal regime eligibility; accounting and return attribution reconciled.

| Period | Costs | Family | SMA | Fade | Reverse | CAGR | PF | Trades | Sideways equivalent |
|---|---|---|---:|---:|---|---:|---:|---:|---:|
| train | spread | rsi5 | 5 | 1 | False | -29.87% | 0.15 | 2632 | -50.41% |
| train | spread | rsi5 | 5 | 2 | False | -29.64% | 0.14 | 2630 | -50.57% |
| train | spread | rsi5 | 10 | 1 | False | -29.89% | 0.14 | 2654 | -50.43% |
| train | spread | rsi5 | 10 | 2 | False | -29.27% | 0.15 | 2664 | -50.40% |
| train | spread | rsi15 | 5 | 1 | False | -40.31% | 0.09 | 3110 | -63.39% |
| train | spread | rsi15 | 5 | 2 | False | -40.29% | 0.09 | 3085 | -63.89% |
| train | spread | rsi15 | 10 | 1 | False | -40.37% | 0.09 | 3110 | -63.39% |
| train | spread | rsi15 | 10 | 2 | False | -40.61% | 0.08 | 2994 | -63.78% |
| train | spread | channel_rebound | 5 | 1 | False | -8.79% | 0.30 | 729 | -15.57% |
| train | spread | channel_rebound | 5 | 2 | False | -9.02% | 0.31 | 728 | -15.28% |
| train | spread | channel_rebound | 10 | 1 | False | -9.46% | 0.21 | 730 | -16.95% |
| train | spread | channel_rebound | 10 | 2 | False | -9.53% | 0.23 | 729 | -16.90% |
| train | spread | breakout5 | 5 | 1 | False | -30.49% | 0.31 | 3411 | -51.84% |
| train | spread | breakout5 | 5 | 2 | False | -26.95% | 0.42 | 3155 | -49.59% |
| train | spread | breakout5 | 10 | 1 | False | -26.39% | 0.41 | 3010 | -47.62% |
| train | spread | breakout5 | 10 | 2 | False | -20.16% | 0.56 | 2460 | -41.79% |
| validation | spread | channel_rebound | 5 | 1 | False | -11.47% | 0.40 | 410 | -21.26% |
| test | spread | channel_rebound | 5 | 1 | False | -21.21% | 0.20 | 473 | -30.18% |
| train | fees | channel_rebound | 5 | 1 | False | -0.95% | 0.87 | 729 | -0.98% |
| validation | fees | channel_rebound | 5 | 1 | False | -1.73% | 0.86 | 410 | -5.34% |
| test | fees | channel_rebound | 5 | 1 | False | -9.98% | 0.46 | 473 | -14.54% |
| test | spread | channel_rebound | 5 | 1 | True | -21.34% | 0.20 | 472 | -30.36% |