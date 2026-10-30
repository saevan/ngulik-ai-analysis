# Buy-below-range module aiming at a ~70% win rate (30 Oct 2026, written before results)
User: can a buy-below-range module reach a ~70% win rate as Logic 2? The real requirement is a win rate ABOVE the
break-even win rate (net of cost B 0.90%), so both are reported.
Condition at the Close of day t: stock's own ER20 < 0.2 (choppy); 20-bar range width (H/L - 1) 10-40%; Close in the bottom
20% of the range. Realistic universe, 2000-01-01..2025-08-15. Entry at the next Open. One position per stock at a time.
Exits: target = +2% / +3% / +5% above the entry or the range mid (limit, filled at max(Open, target)); stop = none /
Close below the range low x 0.95 / Close below the entry x 0.90 (sold next Open); time stop at the Close of bar 5 / 10 / 20.
4 x 3 x 3 = 36 cells. Control per cell: random days with the same choppy + width condition and Close in the lower half,
same exits, same count per stock (5 seeds).
Selection on the training period 2000-2015 only: among cells with a training win rate >= 65%, the highest training net.
The pick passes only if, in 2016-2025.08: net > 0 with NW t >= 2 (daily by entry date, lag = time stop), win rate >= 65%,
net above its control; and over 2000-2025: >= 3 of 4 subperiods net > 0.

## Addendum (30 Oct, written before results): were the stocks choppy enough?
User asks whether these were already choppy stocks. Yes: own ER20 < 0.2 at the signal Close. Diagnostic on two cells
(the pick: +3%, no stop, 10 bars; the highest win rate: +2%, no stop, 20 bars), 2000-2025, no new selection:
1. By market regime at the entry date (regime_proxy: up / sideways / down).
2. By how choppy: ER20 < 0.1 vs 0.1-0.2; ER20 < 0.2 on all of the previous 20 days (established) vs not; ER60 < 0.2 vs not.
3. After entry (look-ahead, description only): share of trades whose Close falls below the range low during the trade;
   share whose ER20 at exit is >= 0.3 (the stock started trending).
Reported per group: trades, win rate, breakeven win rate, average win/loss, net B per trade with NW t, control net in the
same group. A group counts only as a lead (needing its own pre-registered test) if net > 0 with NW t >= 2.
