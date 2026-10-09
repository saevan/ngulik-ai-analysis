# Two independent systems, one cash-constrained portfolio

Primary: existing High20 breakout + ER20>=0.30, entry next tradable Open, hold200 Close or fade5 previous ATR14 then next tradable Open. No profit-trail extension.

Secondary: individual-stock ER20<0.30 and Close <= SMA20 - dip*previous ATR14, dip0.5 or1.5. Entry next tradable Open. Independent exits: Close>=current SMA20; or Close<=actual entry price -2*ATR known before entry; or age>=5/15 bars. All secondary exit signals execute next tradable Open. Terminal Close/mark is the documented exception. Stop does not guarantee its price, suspension/gaps delay execution. No rebound requirement and no shorting.

Reserved configurations cap primary/secondary positions at7/3 or5/5. Shared variant uses all ten slots with secondary cap retained; alphabetical cross-module ticker priority. One ticker can belong to only one module at a time; no same-bar reentry. Same account, no leverage, ten total positions, initialRp1billion, each new entry10% prior-close total equity capped by cash. Slot reservation is not a fixed capital split: existing winners drift and modules share available cash. No forced liquidation when regimes switch. Range-only has primary cap0 and ten range slots.

Stocks2000-01-04 to2025-08-15. Buy0.15%,sell0.25%. Fees scenario no spread/fractional units. Spread stress uses current grid and100-share lots plus1tick per side counterfactually across history, not reconstructed historical bid/ask. Data universe, adjustments, survivorship, liquidity and fill-capacity limitations remain. Original AFL unchanged.

Eight reserved configurations under both cost models; best selected by full-sample spread CAGR then tested shared, standalone and reverse-priority. These are in-sample sensitivity checks, not independent validation. Market sideways attribution uses prior-bar ER of equal-weight proxy, different from individual-stock entry gate; conditional annualized return concatenates disjoint days, not a separately executable CAGR. Records preserve whole-portfolio ATH. Do not sum module CAGRs. Module PnL is realized currency contribution in the shared account, not isolated strategy performance.

Baseline regression reproduces saved curves; portfolio cash/slots/PnL checked on every run. Tests cover reservation and independent mean exit at next Open, plus previous portfolio/fee/trailing regressions.

| Variant | CAGR | Record months | MDD | Trades | WR | Sideways annual equivalent |
|---|---:|---:|---:|---:|---:|---:|
| fees_baseline_reverseFalse | 33.43% | 127/308 | -56.33% | 340 | 62.65% | 18.97% |
| fees_d0.5_h5_slots3_reverseFalse | 13.74% | 68/308 | -66.17% | 4762 | 47.59% | 0.02% |
| fees_d0.5_h5_slots5_reverseFalse | 4.80% | 24/308 | -72.70% | 7519 | 47.13% | -5.87% |
| fees_d0.5_h15_slots3_reverseFalse | 13.73% | 68/308 | -65.44% | 2947 | 55.96% | 0.63% |
| fees_d0.5_h15_slots5_reverseFalse | 6.42% | 44/308 | -73.42% | 4579 | 55.30% | -4.52% |
| fees_d1.5_h5_slots3_reverseFalse | 20.34% | 82/308 | -64.77% | 3594 | 45.16% | 3.15% |
| fees_d1.5_h5_slots5_reverseFalse | 7.79% | 43/308 | -71.94% | 5172 | 45.28% | -2.51% |
| fees_d1.5_h15_slots3_reverseFalse | 18.35% | 85/308 | -68.32% | 2212 | 52.26% | 4.10% |
| fees_d1.5_h15_slots5_reverseFalse | 9.92% | 60/308 | -72.07% | 3287 | 52.18% | -0.76% |
| spread_baseline_reverseFalse | 29.92% | 117/308 | -59.70% | 340 | 59.71% | 15.25% |
| spread_d0.5_h5_slots3_reverseFalse | -19.59% | 1/308 | -99.73% | 4859 | 34.84% | -28.63% |
| spread_d0.5_h5_slots5_reverseFalse | -26.36% | 1/308 | -99.99% | 5301 | 30.03% | -38.55% |
| spread_d0.5_h15_slots3_reverseFalse | -7.42% | 1/308 | -94.94% | 3066 | 44.62% | -16.22% |
| spread_d0.5_h15_slots5_reverseFalse | -20.89% | 1/308 | -99.86% | 4820 | 43.44% | -30.86% |
| spread_d1.5_h5_slots3_reverseFalse | -7.02% | 1/308 | -98.05% | 3663 | 35.41% | -20.08% |
| spread_d1.5_h5_slots5_reverseFalse | -24.10% | 1/308 | -99.94% | 4522 | 33.17% | -34.76% |
| spread_d1.5_h15_slots3_reverseFalse | 0.29% | 10/308 | -91.50% | 2358 | 44.49% | -10.83% |
| spread_d1.5_h15_slots5_reverseFalse | -14.90% | 1/308 | -99.18% | 3473 | 42.93% | -23.59% |
| fees_shared_slots_reverseFalse | 21.84% | 84/308 | -57.64% | 775 | 51.23% | 11.43% |
| fees_range_only_reverseFalse | -7.66% | 1/308 | -90.74% | 5398 | 52.45% | -13.06% |
| fees_baseline_reverseTrue | 27.73% | 93/308 | -55.43% | 345 | 58.55% | 10.05% |
| fees_selected_reverseTrue | 11.69% | 58/308 | -66.96% | 2242 | 52.32% | 2.04% |
| spread_shared_slots_reverseFalse | 15.52% | 65/308 | -79.09% | 853 | 45.13% | 2.36% |
| spread_range_only_reverseFalse | -30.87% | 1/308 | -99.99% | 1997 | 31.40% | -31.06% |
| spread_baseline_reverseTrue | 24.16% | 82/308 | -57.84% | 345 | 56.23% | 6.44% |
| spread_selected_reverseTrue | -0.54% | 1/308 | -90.38% | 2334 | 43.74% | -13.16% |