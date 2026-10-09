# Independent choppy channel system

Market-only control=True. When True, ONLY market proxy must be choppy; individual-stock ER gate removed. This control asks whether stocks need to be individually choppy during a choppy market. Definitions below that mention stock ER apply only to strict mode. Candidate count=8. This extra control is adaptive research after inspecting earlier strict-mode failures; not a pristine holdout.

Purpose: imitate outcome characteristics of the user-selected Swinger ideal benchmark, not identical transactions. Three new candidate entries with ER stock20<0.30 AND prior-completed-bar equal-weight market proxy ER<0.30: channel state flip (same completed-close Cross definition as Swinger, nextOpen fill); range escape above priorHigh5/10; or failed breakdown below priorLow5/10 with Close recovery at least0.5priorATR and risingClose. No main-system merge.

New cost-aware selection: preceding completed20bar High-Low width must exceed8/16times estimated roundtrip fee+1tick each side at signalClose. Estimate uses modern IDX grid/0.15%buy/0.25%sell; dimensionless range/cost multiple, no future entry quote. This filter is explicitly based on a synthetic modern-grid cost assumption, not universally valid historical prices. Units in bars and ratios, but cross-market applicability untested.

Exit: channel-flip opposite Close crossing for that family; other families Close below previousLow5/10. All retain currentOpen-Low>=2previousATR fade. Completed signals execute next tradable Open; no time cap, no early fixed take-profit. Entry only on positive-volume observations, no stale entry queue. Existing positions can persist after regime changes. Terminal closures/marks remain. No lookahead clamps or ideal signal-bar fills.

Independent portfolio initialRp1billion, ten slots,10%prior-equity sizing/cashcap/compounding, one ticker position. Fees0.15%buy/0.25%sell. Spread stress modern grid/100shares plus1tick each side applied counterfactually across history, not observed bid/ask. Selected universe, adjusted-looking quotes, actions, survivorship and liquidity/capacity limits remain.

Twelve parameter sets selected using2000-2015 only, frozen candidate then2016-2020 and2021-2025; fee-only/full-period/reverse-order checks. Earlier projects already examined these historical years, so this is chronological validation within adaptive research, not pristine independent holdout. PLAN.json and FROZEN.json define selection; if no training pass, subsequent runs diagnostic only. No claim of seven-criteria/benchmark success merely from positive CAGR.

Prefix causality for entries/exits, market eligibility, cash/slot/PnL and attribution reconciliation checked. Sideways annual equivalent is daily attribution over disjoint dates, not standalone CAGR. Report both equity metrics and trade win/loss shape. Main AFL unchanged.

| Window | Costs | Family | Length | Cost multiple | Reverse | CAGR | PF money | WR | Avg win | Avg loss | Mean bars | Record months | Sideways equivalent |
|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | spread | channel_flip | 5 | 8 | False | -3.41% | 0.93 | 33.33% | 14.38% | 7.35% | 17.3 | 11/192 | -17.03% |
| train | spread | channel_flip | 5 | 16 | False | -1.90% | 0.93 | 32.59% | 15.47% | 7.83% | 15.8 | 18/192 | -9.58% |
| train | spread | channel_flip | 10 | 8 | False | 3.56% | 1.09 | 36.46% | 18.92% | 8.96% | 25.9 | 35/192 | -12.42% |
| train | spread | channel_flip | 10 | 16 | False | 0.46% | 1.03 | 36.00% | 18.67% | 9.58% | 24.2 | 20/192 | -5.10% |
| train | spread | range_escape | 5 | 8 | False | -1.35% | 0.98 | 33.51% | 15.18% | 7.36% | 16.6 | 17/192 | -18.48% |
| train | spread | range_escape | 5 | 16 | False | -3.98% | 0.90 | 32.46% | 14.60% | 7.61% | 15.7 | 12/192 | -13.52% |
| train | spread | range_escape | 10 | 8 | False | 6.28% | 1.13 | 37.56% | 18.69% | 8.82% | 25.4 | 34/192 | -11.17% |
| train | spread | range_escape | 10 | 16 | False | 2.19% | 1.07 | 35.77% | 19.66% | 9.22% | 24.4 | 20/192 | -9.19% |
| validation | spread | range_escape | 10 | 8 | False | -1.92% | 0.96 | 31.19% | 17.87% | 7.93% | 23.3 | 4/60 | -12.02% |
| test | spread | range_escape | 10 | 8 | False | -7.43% | 0.89 | 30.04% | 19.78% | 8.83% | 22.6 | 6/56 | -15.19% |
| train | fees | range_escape | 10 | 8 | False | 14.71% | 1.30 | 40.28% | 18.92% | 8.04% | 25.4 | 50/192 | 2.94% |
| validation | fees | range_escape | 10 | 8 | False | 6.08% | 1.15 | 33.81% | 17.61% | 7.35% | 23.3 | 10/60 | 1.01% |
| test | fees | range_escape | 10 | 8 | False | 0.55% | 1.01 | 32.68% | 19.25% | 8.38% | 22.6 | 9/56 | -4.08% |
| full | fees | range_escape | 10 | 8 | False | 10.20% | 1.13 | 36.92% | 18.72% | 7.96% | 24.3 | 55/308 | 0.83% |
| test | spread | range_escape | 10 | 8 | True | -4.76% | 0.91 | 31.61% | 17.64% | 8.69% | 22.0 | 3/56 | -13.20% |
| full | spread | range_escape | 10 | 8 | False | 1.98% | 1.03 | 34.23% | 18.76% | 8.61% | 24.3 | 34/308 | -12.32% |