# Second-system loss mitigation

Entry unchanged: Choppy RangeEscape10, completed marketER<0.3, cost/range filter8, next tradable Open, only positive-volume entry bars. No changes to primary system or active AFL. Exit baseline priorLLV10 or fading2 priorATR, no hold200. Compare fixed-entry-ATR Close stop0.5/1/1.5/2; channelLLV5/3; and channel5+stop1.

Stop uses ATR14 from immediately before entry, fixed for trade lifetime, actual entry fill price. Close<=entry-k*ATR triggers next tradable Open, including suspension delay. This is a completed-bar stop SIGNAL, not an intraday resting stop or guaranteed maximum percentage loss; gaps/fees can exceed threshold. It does not use future High/Low to assign an ideal fill. First pending exit preserved; stop gets reason priority on simultaneous new signals. Existing fading still referenced to each current bar Open.

Stocks2000-2025Aug15, initialRp1billion, ten slots,10%prior-equity sizing/cashcap compounding. Buy0.15%sell0.25%. Spread stress currentgrid/100shares and1tick each side counterfactually across history, not observed historicalbidask. Earlier dataset/action/liquidity/survivorship limits unchanged. Main entry same but realized trades may differ because exits free cash/slots.

8configurations x2costs plus reversed-priority baseline/selected sensitivity. Selection highest full-sample spreadCAGR among avg-loss-improving variants, so exploratory in-sample, not independent validation or seven-criteria pass. Time slices are continuous-portfolio descriptive returns, not reset holdouts. Sideways equivalent attributes disjoint dailyreturns, not standalone CAGR. No automatic adoption.

Baseline curves exact regression; cash/slot/PnL, marketeligibility and regime attribution checked. Unit tests cover fixedentryATR, gap nextOpen, intradaytouch not Close signal, and suspended exit surviving recovery.

| Costs | LLV | Stop ATR | Reverse | Avg loss | Avg win | WR | CAGR | MDD | Records /308 | Sideways equivalent |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| fees | 10 | nan | False | 7.96% | 18.72% | 36.92% | 10.20% | -45.69% | 55 | 0.83% |
| spread | 10 | nan | False | 8.61% | 18.76% | 34.23% | 1.98% | -72.29% | 34 | -12.32% |
| fees | 10 | 0.5 | False | 4.04% | 18.13% | 21.45% | 6.84% | -50.86% | 45 | -2.79% |
| spread | 10 | 0.5 | False | 4.54% | 18.52% | 17.86% | -8.02% | -93.66% | 10 | -26.62% |
| fees | 10 | 1.0 | False | 5.40% | 18.26% | 27.28% | 7.76% | -54.40% | 51 | -2.27% |
| spread | 10 | 1.0 | False | 5.86% | 18.25% | 23.78% | -4.09% | -88.00% | 15 | -18.92% |
| fees | 10 | 1.5 | False | 6.55% | 18.44% | 32.09% | 9.32% | -52.28% | 53 | 0.41% |
| spread | 10 | 1.5 | False | 7.07% | 17.89% | 28.57% | -2.55% | -87.72% | 26 | -17.16% |
| fees | 10 | 2.0 | False | 7.20% | 17.61% | 34.67% | 8.67% | -53.89% | 57 | -0.11% |
| spread | 10 | 2.0 | False | 7.76% | 18.00% | 31.22% | -0.42% | -85.64% | 36 | -14.79% |
| fees | 5 | nan | False | 6.54% | 14.30% | 36.55% | 7.95% | -48.46% | 54 | -0.20% |
| spread | 5 | nan | False | 7.21% | 14.19% | 33.61% | -2.53% | -83.02% | 25 | -17.01% |
| fees | 3 | nan | False | 5.51% | 12.25% | 33.81% | 3.65% | -63.24% | 38 | -4.78% |
| spread | 3 | nan | False | 6.19% | 12.40% | 30.18% | -8.53% | -96.24% | 16 | -24.07% |
| fees | 5 | 1.0 | False | 5.11% | 14.63% | 29.09% | 4.91% | -51.15% | 39 | -3.59% |
| spread | 5 | 1.0 | False | 5.59% | 14.40% | 25.31% | -7.96% | -93.07% | 9 | -22.80% |
| fees | 10 | nan | True | 7.99% | 18.35% | 37.22% | 10.43% | -48.53% | 50 | 0.98% |
| fees | 10 | 2.0 | True | 7.32% | 17.92% | 34.51% | 8.65% | -53.18% | 54 | -1.04% |
| spread | 10 | nan | True | 8.67% | 18.30% | 34.72% | 2.17% | -75.03% | 33 | -12.30% |
| spread | 10 | 2.0 | True | 7.88% | 18.40% | 31.51% | 0.31% | -84.40% | 38 | -15.17% |