# Standalone sideways research

16 predefined training combinations: RSI2<5/15 aboveSMA200; 20bar support rejection with risingClose aboveSMA200; or5bar breakout aboveSMA50. All require prior-completed-bar equal-weight market proxy sideways. Individual stocks need not themselves be choppy: breakout family searches relative strength within a sideways market. Independent entry, no main strategy positions.

For RSI/support-rebound, exit Close>=SMA5/10 (recovery) or age20 signals nextOpen. For breakout, exit Close<SMA5/10 without age cap. All retain currentOpen-Low>=1/2priorATR fading next tradable Open. No hold200. Initial control experiment with below-SMA exits on all families is archived in standalone_sideways_results; this recovery version corrects exit direction for mean-reversion families after observing that control. Thus this entire research is adaptive, despite freezing this version before its validation/test. RSI uses explicitly implemented ewm(alpha0.5,adjustFalse) with2observations; no claim of exact AmiBroker RSI initialization. Entry only on tradable bars, expired setup not queued. Terminal closures for each separate period remain.

Train2000-2015, validation2016-2020, finaltest2021-2025Aug15. Frozen single candidate chosen only from train, no retuning on validation/test. Entire historical dataset was already examined in earlier research: these are chronological non-selection periods for this run, NOT genuinely untouched external data. Same survivorship/corporateaction/universe and capacity limitations.

InitialRp1billion for each period, max10positions/10%previous-equity sizing, cash-constrained compounding. Feesbuy0.15%sell0.25%. Selection uses modern-grid/100share-lot plus1tick each side stress, not historical observed bid/ask; fee-only sensitivity also shown. SMA/fade nextOpen executions; signal built with full earlier warmup. No merging or active AFL changes.

Success requires positive CAGR,PF>1.1,positive sideways attribution and>=40trades in train and both later windows; reverse test must remain positive. This is a research gate, not seven universal criteria. Sideways annual equivalent concatenates disjoint marked-equity days, not standalone CAGR. All actual entries checked against causal regime eligibility; accounting and return attribution reconciled.

| Period | Costs | Family | SMA | Fade | Reverse | CAGR | PF | Trades | Sideways equivalent |
|---|---|---|---:|---:|---|---:|---:|---:|---:|
| train | spread | rsi5 | 5 | 1 | False | -25.88% | 0.19 | 2179 | -43.40% |
| train | spread | rsi5 | 5 | 2 | False | -23.19% | 0.19 | 1951 | -41.15% |
| train | spread | rsi5 | 10 | 1 | False | -24.41% | 0.26 | 2072 | -41.39% |
| train | spread | rsi5 | 10 | 2 | False | -20.79% | 0.27 | 1754 | -37.61% |
| train | spread | rsi15 | 5 | 1 | False | -37.49% | 0.12 | 3012 | -59.59% |
| train | spread | rsi15 | 5 | 2 | False | -35.24% | 0.12 | 3014 | -57.48% |
| train | spread | rsi15 | 10 | 1 | False | -36.26% | 0.15 | 3052 | -58.24% |
| train | spread | rsi15 | 10 | 2 | False | -30.74% | 0.18 | 2759 | -52.19% |
| train | spread | channel_rebound | 5 | 1 | False | -10.56% | 0.16 | 687 | -18.85% |
| train | spread | channel_rebound | 5 | 2 | False | -10.78% | 0.16 | 671 | -19.89% |
| train | spread | channel_rebound | 10 | 1 | False | -9.96% | 0.25 | 677 | -18.31% |
| train | spread | channel_rebound | 10 | 2 | False | -10.20% | 0.24 | 649 | -19.74% |
| train | spread | breakout5 | 5 | 1 | False | -30.49% | 0.31 | 3411 | -51.84% |
| train | spread | breakout5 | 5 | 2 | False | -26.95% | 0.42 | 3155 | -49.59% |
| train | spread | breakout5 | 10 | 1 | False | -26.39% | 0.41 | 3010 | -47.62% |
| train | spread | breakout5 | 10 | 2 | False | -20.16% | 0.56 | 2460 | -41.79% |
| validation | spread | channel_rebound | 10 | 1 | False | -11.03% | 0.40 | 381 | -19.64% |
| test | spread | channel_rebound | 10 | 1 | False | -16.66% | 0.35 | 423 | -23.45% |
| train | fees | channel_rebound | 10 | 1 | False | -2.74% | 0.71 | 677 | -5.12% |
| validation | fees | channel_rebound | 10 | 1 | False | -1.79% | 0.87 | 381 | -4.18% |
| test | fees | channel_rebound | 10 | 1 | False | -5.47% | 0.73 | 423 | -7.55% |
| test | spread | channel_rebound | 10 | 1 | True | -17.17% | 0.33 | 418 | -24.17% |