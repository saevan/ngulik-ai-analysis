# Independent choppy channel system

Purpose: imitate outcome characteristics of the user-selected Swinger ideal benchmark, not identical transactions. Three new candidate entries with ER stock20<0.30 AND prior-completed-bar equal-weight market proxy ER<0.30: channel state flip (same completed-close Cross definition as Swinger, nextOpen fill); range escape above priorHigh5/10; or failed breakdown below priorLow5/10 with Close recovery at least0.5priorATR and risingClose. No main-system merge.

New cost-aware selection: preceding completed20bar High-Low width must exceed8/16times estimated roundtrip fee+1tick each side at signalClose. Estimate uses modern IDX grid/0.15%buy/0.25%sell; dimensionless range/cost multiple, no future entry quote. This filter is explicitly based on a synthetic modern-grid cost assumption, not universally valid historical prices. Units in bars and ratios, but cross-market applicability untested.

Exit: channel-flip opposite Close crossing for that family; other families Close below previousLow5/10. All retain currentOpen-Low>=2previousATR fade. Completed signals execute next tradable Open; no time cap, no early fixed take-profit. Entry only on positive-volume observations, no stale entry queue. Existing positions can persist after regime changes. Terminal closures/marks remain. No lookahead clamps or ideal signal-bar fills.

Independent portfolio initialRp1billion, ten slots,10%prior-equity sizing/cashcap/compounding, one ticker position. Fees0.15%buy/0.25%sell. Spread stress modern grid/100shares plus1tick each side applied counterfactually across history, not observed bid/ask. Selected universe, adjusted-looking quotes, actions, survivorship and liquidity/capacity limits remain.

Twelve parameter sets selected using2000-2015 only, frozen candidate then2016-2020 and2021-2025; fee-only/full-period/reverse-order checks. Earlier projects already examined these historical years, so this is chronological validation within adaptive research, not pristine independent holdout. PLAN.json and FROZEN.json define selection; if no training pass, subsequent runs diagnostic only. No claim of seven-criteria/benchmark success merely from positive CAGR.

Prefix causality for entries/exits, market eligibility, cash/slot/PnL and attribution reconciliation checked. Sideways annual equivalent is daily attribution over disjoint dates, not standalone CAGR. Report both equity metrics and trade win/loss shape. Main AFL unchanged.

| Window | Costs | Family | Length | Cost multiple | Reverse | CAGR | PF money | WR | Avg win | Avg loss | Mean bars | Record months | Sideways equivalent |
|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | spread | channel_flip | 5 | 8 | False | -3.14% | 0.93 | 32.80% | 14.38% | 7.26% | 17.1 | 9/192 | -16.39% |
| train | spread | channel_flip | 5 | 16 | False | 0.49% | 1.02 | 32.40% | 17.34% | 7.64% | 16.4 | 22/192 | -7.12% |
| train | spread | channel_flip | 10 | 8 | False | 2.87% | 1.09 | 36.84% | 17.81% | 8.75% | 25.7 | 29/192 | -11.48% |
| train | spread | channel_flip | 10 | 16 | False | 0.53% | 1.05 | 36.57% | 17.99% | 9.35% | 24.5 | 19/192 | -3.42% |
| train | spread | range_escape | 5 | 8 | False | -6.69% | 0.84 | 32.06% | 13.29% | 7.18% | 16.8 | 5/192 | -18.52% |
| train | spread | range_escape | 5 | 16 | False | -4.52% | 0.81 | 30.08% | 14.50% | 7.59% | 15.5 | 8/192 | -11.75% |
| train | spread | range_escape | 10 | 8 | False | 3.56% | 1.11 | 37.45% | 17.52% | 8.61% | 26.1 | 28/192 | -10.35% |
| train | spread | range_escape | 10 | 16 | False | -2.55% | 0.84 | 31.92% | 16.98% | 9.25% | 23.8 | 13/192 | -8.55% |
| train | spread | failed_breakdown | 5 | 8 | False | -7.24% | 0.53 | 27.90% | 10.90% | 7.16% | 16.0 | 1/192 | -13.86% |
| train | spread | failed_breakdown | 5 | 16 | False | -4.00% | 0.34 | 26.55% | 8.65% | 8.00% | 14.3 | 1/192 | -6.07% |
| train | spread | failed_breakdown | 10 | 8 | False | -5.19% | 0.58 | 28.49% | 13.30% | 8.42% | 20.8 | 1/192 | -9.87% |
| train | spread | failed_breakdown | 10 | 16 | False | -3.23% | 0.31 | 27.27% | 8.62% | 9.64% | 19.6 | 1/192 | -4.23% |
| validation | spread | range_escape | 10 | 8 | False | -11.88% | 0.71 | 30.24% | 13.15% | 7.81% | 23.8 | 4/60 | -19.02% |
| test | spread | range_escape | 10 | 8 | False | -15.23% | 0.70 | 28.71% | 15.32% | 8.49% | 23.6 | 0/56 | -24.67% |
| train | fees | range_escape | 10 | 8 | False | 9.80% | 1.30 | 40.36% | 17.64% | 7.97% | 26.1 | 40/192 | 0.23% |
| validation | fees | range_escape | 10 | 8 | False | -6.13% | 0.84 | 32.63% | 13.18% | 7.30% | 23.8 | 6/60 | -9.49% |
| test | fees | range_escape | 10 | 8 | False | -8.79% | 0.82 | 30.38% | 15.41% | 7.90% | 23.6 | 3/56 | -15.96% |
| full | fees | range_escape | 10 | 8 | False | 2.69% | 1.04 | 35.64% | 16.27% | 7.76% | 25.0 | 40/308 | -5.91% |
| test | spread | range_escape | 10 | 8 | True | -11.81% | 0.77 | 31.62% | 14.96% | 8.56% | 22.8 | 1/56 | -19.84% |
| full | spread | range_escape | 10 | 8 | False | -3.45% | 0.95 | 33.23% | 16.16% | 8.37% | 25.0 | 28/308 | -15.74% |