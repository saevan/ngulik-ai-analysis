# Why our win rate is below 50%, and does "price + time" bring it to ~50%? (26 Oct 2026)

User claim to check: combining price and time exits gives a win rate of about 50%; find what keeps our WR below 50%.
Benchmark (user rule, permanent): Prototype Swinger IDEAL only (B: WR 48.8%, payout 4.90, 102.0% CAGR, 232 record
months, MDD -21%). System: v2 main pick F1_ch20_er0.2_cand_f0.0_s4_b0.005 (buy stop 0.5% above HHV20 on the price grid,
ER20 >= 0.2, mom120 order, gap 2%, gapdown_close 2%, exits fade 2 ATR / Close < SMA30 / failed breakout, 25% equity per
order, max 10). Cost B (fees 0.15/0.25% + 0.25%/side slippage). 2000-01-01..2025-08-15. AFL unchanged.

## Step 1 - trade-level diagnosis (exploratory, already run: diagnose_winrate.py)
Run first, before this plan was written, so it is descriptive only: WR by exit reason, regime, period; entry-day Close vs
fill; cost flips; loser paths (MFE/MAE, best Close); counterfactual exits on the same entries.

## Step 2 - portfolio test of price/time exits (fixed BEFORE results)
New engine option `max_hold=n` in backtest_stop_execution.run: at the Close of the n-th bar held (entry bar = bar 1), a
pending 'time_exit' is set if no other exit is pending; sold at the next tradable Open (gapdown_close rule applies as for
other Close-signal exits). Default None = old behaviour (regression tests must still pass).
Same entries, sizing, order book and costs as the main pick; only the exits change. Cells (15):
- V0: original exits.
- TIME_n (time only, no fade / SMA / failed exit): n = 10, 20, 40.
- V0+CAP_n (original exits plus a time cap): n = 20, 40, 60.
- FAIL+TIME_n (failed-breakout exit kept, then time only): n = 20, 40.
- TP_k+TIME_n (take profit at entry + k x entry ATR, plus time; no other exits): k = 3, 6; n = 10, 20, 40.
Runs: B unrestricted (main), B realistic (point-in-time top-half liquidity + stale filter + buys <= 25% ADV20),
subperiod CAGR slices 2000-07 / 08-15 / 16-20 / 21-25 (B unrestricted), holdout 1995-03-01..1999-12-31 (B unrestricted,
descriptive only).
A cell counts as "WR ~50% without paying for it" only if ALL hold:
(a) WR >= 45%; (b) B unrestricted CAGR >= V0 and MDD not deeper than V0 - 5 pp; (c) realistic CAGR >= V0 realistic;
(d) CAGR slice >= V0 in >= 3 of 4 subperiods; (e) record months >= V0.
15 cells on one data set: a single passing cell with failing neighbours is treated as noise, not adopted. Nothing is
adopted into the active system from this test.
