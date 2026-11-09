# Grid search for a sideways Logic 2: what predicts a bounce? (9 Nov 2026, written before results)
User: grid search for signals that really predict the bounce, so that we get a Logic 2 for sideways markets.
Earlier: low ER alone does not predict bounces (`er_regime_check_results`). Here the search uses daily OHLCV
predictors not tested before: RSI2, consecutive down closes, volume, candle wick, market breadth, long-term trend.

Trades only when the market is sideways on the entry day (`regime_proxy`, known before the Open). Long only.

Signal at the Close of day t: one trigger AND at most one filter.
Triggers (4):
- T1: RSI(2) < 10;
- T2: 3 consecutive lower Closes;
- T3: Close in the bottom 20% of the 20-day High-Low range;
- T4: Close < SMA20 − 1.5 x ATR14.
Filters (7):
- F0: none;
- F1: Close > SMA200;
- F2: volume dry-up (avg volume 5 days / 60 days < 0.7);
- F3: Close in the upper half of the day's range (lower wick);
- F4: market breadth oversold (< 30% of stocks above their SMA20);
- F5: stock ER20 < 0.2;
- F6: volume spike (volume / avg 20 days > 2).
Entry (2):
- next Open;
- buy limit at Close − 0.5 x ATR14, valid on the next day only, filled if Low < limit at min(Open, limit).
Exit (3), each with a max hold of 10 bars (sold at the Close of bar 10):
- Close > SMA5, sold next Open;
- Close > previous day's High, sold next Open;
- time stop at the Close of bar 5.
4 x 7 x 2 x 3 = 168 cells.

Setup: realistic universe (point-in-time liquidity + stale filter on the entry day), one position per stock at a time,
cost B 0.90% round trip, trade level, 2000-01-01..2025-08-15.
Control per cell: random eligible sideways-market days of the same stock, same entry method and exits, same count per
stock (5 seeds).

Selection on 2000–2015 only: among cells with >= 10 trades per year in training, the highest training net. The pick
passes only if, in 2016–2025.08:
- net > 0 with NW t >= 2 (daily by entry date, lag 10);
- net above its control;
- >= 3 of 4 subperiods (2000-07, 2008-15, 2016-20, 2021-25) net > 0.
Also reported:
- the number of the 168 cells with test net > 0 and t >= 2 (by chance about 4 would);
- win rate and break-even win rate;
- net at the user's broker fee 0.60% without slippage (information only).

## Addendum (9 Nov, written after the main results, before this check)
Observation from the main run: the "F4 breadth < 30% + limit entry" family lost in 2000–2015 but won in 2016–2025.
Because it was noticed in the test period, it is a new hypothesis, not a result. Frozen check on data not used so far,
the 1996-01-01..1999-12-31 holdout. Two configs, Close > SMA5 exit:
- T1 RSI2 < 10 + F4 + limit Close − 0.5 ATR;
- T2 3 lower closes + F4 + limit Close − 0.5 ATR.
Same rules, realistic universe, cost B, with a control. Reported: trades, win rate, net, NW t, control. It supports the
hypothesis only if both configs have net > 0 there.
