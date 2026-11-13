# Logic 2 candidate: relative-momentum rotation for idle cash in sideways markets (12 Nov 2026, written before results)
User: "coba cari logic kedua yang bisa kamu dapatkan" / "coba uji". Every daily mean-reversion family has failed
(10 forms, 2026-10..11). The only market property in `market_properties_v2` that is significant and has not been built
into a standalone module is cross-sectional momentum (MOM12-1 top minus bottom +1.44%/month, t 2.75; top quintile
exploratory +0.86%/month). Calendar effects were not significant there, and "buy the dip of a strong stock" failed
(`sideways_dip_property_results`), so those families are skipped.

Logic 2 = hold the N strongest stocks (relative momentum) while the market is sideways, so idle cash is used by stocks
that trend on their own (the fingerprint showed that in sideways markets only stocks with ER20 >= 0.2 carry positive
price movement). Not mean reversion.

Rules, decided at the Close of a rebalance day t, orders at the Open of t+1:
- Pool: realistic universe on t+1 (point-in-time top-half liquidity + stale filter).
- Score (3): MOM12-1 = C[t-20]/C[t-250] - 1; mom120 = C[t]/C[t-120] - 1; mom60 = C[t]/C[t-60] - 1. Only score > 0 is
  a candidate (buy positive momentum only).
- Filter (2): none / stock ER20 >= 0.2 at t.
- Gate for NEW buys (3), market label for t+1 (`regime_proxy`, known before the Open): sideways only / not downtrend /
  always (context: this is Logic 1 territory).
- N (2): 5 / 10 positions, target size = equity at the previous Close / N, cash-limited, buy <= 25% of ADV20.
- Rebalance (2): last trading day of the month / of the week.
- Exit (2): at rebalance only (sell when the stock is no longer a candidate or its rank > 2N) / the same plus
  Close < SMA30 at any Close, sold next Open.
- A stock's last bar closes the position at that Close. Buys that cannot be executed on t+1 are dropped; sells stay
  pending until executable.
3 x 2 x 3 x 2 x 2 x 2 = 144 cells. Cost B (fee 0.15/0.25% + 0.25% slippage per side). Rp1bn compounding,
2000-01-01..2025-08-15, current 100-stock universe (survivor-only data flatters momentum; stated in the conclusion).

Control per cell: identical mechanics with the momentum score replaced by a random number per stock per rebalance
(same pool and filter, no "score > 0" condition), 5 seeds averaged. Context benchmarks: equal-weight all eligible
stocks rebalanced monthly; money-market parking at 4%/year as the hurdle for idle cash.

Metrics per cell: CAGR and MDD 2000-25; annual return on sideways / uptrend / downtrend days (daily attribution) with
capital invested; trades per year, win rate, average win / loss, payoff, median bars; NW t (lag 20) of the daily return
on sideways days, and of the daily difference vs the control.
Selection on 2000-2015 only, among the sideways-only and not-downtrend cells: the highest sideways-day annual return.
The pick passes only if, in 2016-2025.08: sideways-day annual return >= 4% (the parking hurdle) with NW t >= 2; above
its control; and >= 3 of the 4 subperiods (2000-07, 2008-15, 2016-20, 2021-25) have a sideways-day annual return > 0.
Also reported: how many of the 96 gated cells pass the test rule (chance about 2-3).
Step 2 (only if the pick passes): run it as an extra module inside V2 realistic with shared cash (V2 first; Logic 2 buys
only with idle cash when the market is sideways; Logic 2 sold when V2 needs cash) and compare with V2 + 4% parking.

## Addendum (13 Nov, written after a one-cell smoke test, before the full run)
The pre-registered control redraws the random score at every rebalance, so it churns about 3x more than the momentum
cell (smoke test: 639 vs 189 trades) and pays more cost. A second control is added: a static random ranking drawn
once per seed (5 seeds), which has low turnover. The pass rule keeps the pre-registered control; the number of cells
that also beat the static control is reported.
