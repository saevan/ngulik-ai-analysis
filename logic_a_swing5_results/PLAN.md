# New system from scratch, step 2: Logic A = 5-day swing breakout, executed realistically (9 Nov 2026, before results)
User rule (9 Nov): "acuan kita pakai yang ideal saja, tetapi logic yang kita bangun harus pakai yang realistis". The only
reference is Prototype Swinger ideal; every logic we build must be executable and is judged in the realistic version.

Logic, built from the step-1 fingerprint (Swinger buys 5-day swing breakouts; its price movement is positive in uptrends,
positive in sideways only for stocks with ER20 >= 0.2, negative in downtrends):
- Signal at the Close of day t: Close crosses above the 5-bar trailing line (Close > prior 5-day high after a down
  state). Exit signal: Close crosses below it (Close < prior 5-day low after an up state). Uses
  `backtest_prototype_swinger.signals(frame, 5)`.
- Execution: buy at the next Open. Sell at the first tradable Open after the exit signal (a pending exit is kept until it
  can be executed).
- Positions: 10% of equity per order (budget from the previous Close), max 10 positions, cash constrained, ticker order
  when slots run out. Positions still open at a stock's last bar are closed at that Close.
- Costs B: fee 0.15/0.25% + 0.25% slippage per side.
- Realistic: the stock must be point-in-time eligible (top-half liquidity + stale filter) on the entry day, and the buy
  must be <= 25% of ADV20.
- Period: 2000-01-01..2025-08-15. Market condition: `regime_proxy`, known before the Open.

Variants (all reported, none selected):
- A0: no filter.
- A1: uptrend = all stocks; sideways = only stocks with ER20 >= 0.2 at the signal Close; downtrend = no new entries.
- A2: uptrend = all stocks; sideways and downtrend = only stocks with ER20 >= 0.2.

Reported vs Swinger ideal (same costs):
- per condition: annual return on that condition's days, capital invested, trades per year, win rate, average win/loss,
  payoff, expectancy per trade;
- overall: CAGR, MDD;
- CAGR in 2000-07, 2008-15, 2016-20, 2021-25.08.
A variant counts as promising only if its realistic CAGR is > 0 in all 4 subperiods and its annual return is > 0 in each
of the three conditions. The unrestricted version (all stocks, no ADV cap) is saved for context only.

## Addendum (9 Nov, written before results): the previous system V2 in the same report
User asks how our previous logic does under the same rule. V2 (breakout HHV20 + 0.5%, ER20 >= 0.2, exits fade 2 ATR /
Close < SMA30, plus the monthly module; `wr_gap_v1.kw('realistic', True, None)` with `failed_exit=None`) is run in the
realistic version and reported with the same `report()` as Logic A (same conditions, subperiods, trade metrics) next to
Swinger ideal and Logic A1. Descriptive only; the same "promising" criterion is applied.
