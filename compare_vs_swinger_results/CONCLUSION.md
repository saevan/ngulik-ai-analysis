# Our system vs Prototype Swinger: strengths and weaknesses (26 Oct 2026)

Code `compare_vs_swinger.py` (+ `compare_vs_swinger_realistic_swinger.py`); numbers `summary.csv`, `regimes.csv`, `periods.csv`,
`swinger_ideal_realistic_B.csv`. Same data and engine conventions, Rp1bn, compounding, 2000-01-01..2025-08-15, scenario B
(fee 0.15/0.25% + 0.25%/side) unless stated. Ours = v2 main pick (buy stop 0.5% above HHV20, ER20 >= 0.2, mom120 order,
gap rules, exits fade 2 ATR / Close < SMA30 / failed breakout, 25% per order). 'Realistic' = point-in-time liquidity +
stale filter on new entries + buys <= 25% ADV20. Swinger ideal fills at the prior TSL on the signal bar (aspirational,
not executable); its causal versions are the stop order (touch fills) and signal -> next Open.

| B, 2000-25 | Ours | Ours realistic | Swinger ideal | Swinger ideal realistic | Swinger next Open | Swinger stop order |
|---|---|---|---|---|---|---|
| CAGR | 49.3% | 16.2% | 102.0% | 31.9% | 14.9% | -44.4% |
| Record months /308 | 119 | 52 | 232 | 179 | 67 | 1 |
| MDD | -24% | -44% | -21% | -17% | -64% | -100% |
| Trades/yr | 31 | 34 | 127 | 122 | 120 | 514 |
| Win rate | 38% | 34% | 49% | 48% | 33% | 14% |
| Avg win / avg loss | 26.8% / 5.3% | 17.0% / 4.9% | 17.0% / 3.5% | 12.6% / 3.5% | 17.8% / 6.3% | |
| Payout | 5.1 | 3.5 | 4.9 | 3.7 | 2.8 | 3.6 |
| Median trade | -2.0% | -2.3% | -0.2% | | -3.2% | |
| Bars win / loss | 31.5 / 8.9 | 31.5 / 9.0 | 27.3 / 11.1 | | 33.7 / 13.1 | |
| Capital invested | 49% | 48% | 93% | 48% | 93% | 75% |
| Positive months | 56% | 49% | 83% | | 55% | |
| Losing years | 1 | 7 | 0 | 0 | 10 | 21 |
| Longest under water (days) | 419 | 928 | 133 | | 2,949 | |
| P&L from post-2018 listings | 71% | 26% | 52% | 13% | 72% | |
| Uptrend / sideways / downtrend (ann.) | 113% / 33% / 7% | 34% / 10% / 5% | 186% / 79% / 66% | 53% / 22% / 37% | 75% / -1% / -25% | |
| CAGR A -> D (cost sensitivity) | 55.3 -> 44.7 | 19.6 -> 12.8 | 114.8 -> 90.1 | | | |

Strengths of ours: executable and causal (Swinger's executable versions: next Open 14.9% with -64% MDD, stop order
collapses); larger winners (26.8% vs 17.0%) with similar payout; losers cut faster (8.9 vs 11.1 bars) while winners run
longer; 4x fewer trades, so costs take less in absolute terms (A->D -10.6 pp vs -24.7 pp); stays out of downtrends
(7%/yr while the EW market made 0% with a -52% drawdown).
Weaknesses: low win rate (38% vs 49%) and a negative median trade; profit rests on a few big winners (top 10% of trades
= 127% of P&L); half the capital idle (49% vs 93% invested); far fewer record months (119 vs 232) and long flat stretches
(419 days vs 133); weak in sideways (33% vs 79%) and downtrends (7% vs 66%); depends on stocks that later became index
members (71% of P&L from post-2018 listings) and loses most of its return under realistic liquidity limits
(49% -> 16%; Swinger ideal under the same limits 32%, still with its non-executable fill). Weak 2008-15 (realistic ~0%).
AFL unchanged.
