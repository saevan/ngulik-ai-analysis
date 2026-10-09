# Selective early-breakout-failure exit

Second system only: ChoppyRangeEscape10/cost8/marketER<0.30, no time cap, fade2ATR and original priorLLV10 exit retained. Additional exit: during first3/5/10holdingbars, Close below both actual entry price and ORIGINAL breakout level for1/2consecutivebars -> next tradable Open. Original level = HHV10 before entry signal bar, fixed at entry. Recovery resets consecutive count. Window expiry disables new early-failure signals but preserves already queued exits. No forced exit at window end. Long winners untouched by this additional rule unless they retrace below entry during probation.

Same2000-2025 stocks, Rp1billion/10slots/prior-equity10%cashcap compounding. Fees0.15%buy/0.25%sell. Spread stress modern grid/100shares/1tick eachside counterfactual, not observed bidask. Active AFL and primary unchanged. Entries are unchanged setups but cash/slot path can alter realized trades. Market-onlychoppy gate, stock ER unrestricted as existing secondary.

14runs baseline plus6variants under2costs. In-sample exploratory exit-only test, not independent validation. Same-entry diagnostics use ticker/date matches and final returns, for retrospective audit only; not a rule using future outcome. Do not equate matched-trade return differences to whole-portfolio CAGR attribution. Sideways annual equivalent is disjoint-day attribution, not standalone CAGR. No guarantee of loss ceiling at nextOpen. Baseline exact regression, eligibility, accounting and attribution checked.

| Costs | Window | Consecutive closes | Avg loss | WR | CAGR | MDD | Records /308 | Sideways equivalent |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fees | 0 | 0 | 7.96% | 36.92% | 10.20% | -45.69% | 55 | 0.83% |
| spread | 0 | 0 | 8.61% | 34.23% | 1.98% | -72.29% | 34 | -12.32% |
| fees | 3 | 1 | 5.50% | 28.34% | 8.73% | -51.69% | 59 | -1.39% |
| spread | 3 | 1 | 6.23% | 25.81% | -1.40% | -85.54% | 31 | -17.62% |
| fees | 3 | 2 | 6.68% | 32.51% | 9.69% | -48.16% | 57 | -0.10% |
| spread | 3 | 2 | 7.43% | 29.89% | 0.12% | -74.79% | 27 | -15.03% |
| fees | 5 | 1 | 5.10% | 26.69% | 9.36% | -55.23% | 57 | -1.09% |
| spread | 5 | 1 | 5.84% | 24.08% | -1.28% | -85.86% | 33 | -18.35% |
| fees | 5 | 2 | 6.14% | 30.35% | 8.99% | -49.45% | 55 | -1.05% |
| spread | 5 | 2 | 6.88% | 28.02% | -0.90% | -80.73% | 25 | -16.58% |
| fees | 10 | 1 | 4.68% | 25.22% | 8.80% | -52.05% | 57 | -0.54% |
| spread | 10 | 1 | 5.46% | 22.71% | -2.16% | -88.74% | 29 | -18.99% |
| fees | 10 | 2 | 5.68% | 28.75% | 9.07% | -50.04% | 52 | 0.57% |
| spread | 10 | 2 | 6.42% | 26.33% | -1.17% | -83.98% | 26 | -16.21% |