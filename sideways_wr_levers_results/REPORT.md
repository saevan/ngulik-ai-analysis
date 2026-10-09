# Sideways WR levers: one factor at a time

User clarified acak means identify indicator levers, NOT random entry. The interrupted random-entry diagnostic is not used to select this experiment. All variants are standalone sideways systems, no main-module merge.

Baseline: market proxy prior-bar sideways; individual stock ER20<0.30, Close>SMA200, Low touches/breaches previous20bar low and Close recovers above it, Close>previousClose. Entry next tradable Open, no stale untradable queue. Exit Close>=SMA10 recovery, currentOpen-Low>=1priorATR fading or age20, all next tradable Open. Terminal valuation retained.

One factor changed at a time: stock ERthreshold0.1/0.2/0.4; supportlookback10/40; no extra rebound confirmation or Close>previousHigh; recovery SMA5/20; fade0.5/2ATR; age5/10. Market ER gate remains0.30 in all cases. Thresholds dimensionless or bars. Strict stock+market choppy entry, existing positions may exit after regime change.

2000-2025Aug15 stocks, initialRp1billion, max10slots,10%prior-equity/cashcap compounding, deterministic alphabetical priority. Fee0.15%buy/0.25%sell. Spread stress counterfactual modern grid/100shares and1tick each side, not observed historical bid/ask. All results in-sample. Entry-date subgroup stats include whole trade lifespan; they are not independent reset validation. No claim of sevencriteria or performance across all regimes.

WR changes describe the whole policy including changed trade composition and capacity; not matched-trade causal attribution. Higher WR may come with smaller wins/larger losses. Assess expectancy, payout and net CAGR jointly. Signal-prefix, market eligibility, cash/slot/PnL assertions checked. Active AFL unchanged.

| Costs | Lever | Trades | WR | Delta WR pp | Avg win | Avg loss | Mean return | CAGR |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| fees | baseline | 1188 | 45.37% | +0.00 | 3.14% | 3.87% | -0.69% | -3.24% |
| spread | baseline | 1188 | 33.33% | +0.00 | 2.67% | 4.69% | -2.23% | -9.90% |
| fees | er_0.1 | 549 | 45.72% | +0.35 | 3.34% | 3.59% | -0.42% | -0.94% |
| spread | er_0.1 | 549 | 33.15% | -0.18 | 2.94% | 4.60% | -2.10% | -4.45% |
| fees | er_0.2 | 907 | 46.31% | +0.94 | 3.22% | 3.74% | -0.52% | -1.90% |
| spread | er_0.2 | 907 | 33.85% | +0.51 | 2.77% | 4.60% | -2.10% | -7.24% |
| fees | er_0.4 | 1362 | 46.55% | +1.18 | 3.20% | 4.00% | -0.65% | -3.53% |
| spread | er_0.4 | 1362 | 34.36% | +1.03 | 2.77% | 4.72% | -2.15% | -10.87% |
| fees | support_10 | 2334 | 47.86% | +2.49 | 3.02% | 3.73% | -0.50% | -4.65% |
| spread | support_10 | 2315 | 33.74% | +0.40 | 2.69% | 4.41% | -2.02% | -16.60% |
| fees | support_40 | 464 | 43.53% | -1.84 | 3.04% | 4.13% | -1.01% | -1.84% |
| spread | support_40 | 464 | 30.82% | -2.51 | 2.53% | 5.06% | -2.72% | -4.84% |
| fees | confirm_none | 2392 | 44.86% | -0.51 | 3.50% | 3.89% | -0.58% | -5.55% |
| spread | confirm_none | 2359 | 33.70% | +0.37 | 3.06% | 4.78% | -2.14% | -17.81% |
| fees | confirm_above_high | 363 | 42.98% | -2.40 | 2.76% | 3.19% | -0.63% | -0.90% |
| spread | confirm_above_high | 363 | 29.48% | -3.86 | 2.33% | 4.39% | -2.41% | -3.38% |
| fees | target_5 | 1219 | 45.78% | +0.40 | 2.42% | 3.10% | -0.57% | -2.78% |
| spread | target_5 | 1219 | 28.22% | -5.11 | 2.28% | 3.84% | -2.11% | -9.62% |
| fees | target_20 | 1172 | 44.71% | -0.66 | 3.89% | 4.59% | -0.80% | -3.72% |
| spread | target_20 | 1172 | 36.01% | +2.67 | 3.36% | 5.56% | -2.35% | -10.30% |
| fees | fade_0.5 | 1251 | 37.65% | -7.72 | 2.92% | 2.54% | -0.48% | -2.37% |
| spread | fade_0.5 | 1251 | 26.22% | -7.11 | 2.58% | 3.63% | -2.00% | -9.36% |
| fees | fade_2 | 1127 | 50.22% | +4.85 | 3.01% | 4.22% | -0.59% | -2.67% |
| spread | fade_2 | 1127 | 36.91% | +3.58 | 2.53% | 4.85% | -2.13% | -8.99% |
| fees | age_5 | 1210 | 42.15% | -3.22 | 3.16% | 3.53% | -0.71% | -3.41% |
| spread | age_5 | 1210 | 30.66% | -2.67 | 2.76% | 4.45% | -2.24% | -10.10% |
| fees | age_10 | 1188 | 45.37% | +0.00 | 3.14% | 3.89% | -0.70% | -3.30% |
| spread | age_10 | 1188 | 33.33% | +0.00 | 2.67% | 4.71% | -2.25% | -9.96% |