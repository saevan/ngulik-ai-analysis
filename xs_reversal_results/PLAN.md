# Mean reversion Logic 2, the one family not yet tested: cross-sectional short-term reversal (9 Nov 2026, before results)
User: should we try a mean-reversion Logic 2 for sideways markets? Almost all earlier sideways tests were absolute mean
reversion (range bottom, decline-bounce, buy-the-turn, inverted signals, RSI2/oversold grid, signed ER) and all failed.
The untested family is RELATIVE: buy the stocks that fell most versus the other stocks (short-term losers), betting
they catch up.

Each day t, with the market sideways on day t+1 (`regime_proxy`), rank the stocks eligible on day t+1 (realistic
universe: point-in-time liquidity + stale filter) by their return over the last L days (ranking by the stock's return
equals ranking by return relative to the market). Buy the bottom 5 at day t+1. One position per stock at a time; a
stock already held is skipped (no replacement).

Grid: L = 1 / 5 / 10 days × hold H = 5 / 10 bars (sold at the Close of bar H) × entry = next Open / limit at Close −
0.5 x ATR14 valid next day (filled if Low < limit at min(Open, limit)). 12 cells.

Cost B 0.90% round trip, trade level, 2000-01-01..2025-08-15.
Comparisons per cell, same dates, same count per date, same exits:
- control: 5 random eligible stocks (5 seeds);
- the top 5 (short-term winners).
Selection on 2000–2015 only (highest training net). The pick passes only if, in 2016–2025.08:
- net > 0 with NW t >= 2 (daily by entry date, lag H);
- net above its control;
- >= 3 of 4 subperiods net > 0.
