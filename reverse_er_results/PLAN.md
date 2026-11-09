# "Reverse ER" for a sideways Logic 2 (9 Nov 2026, written before results)
User: can a reverse ER build a second logic that exploits sideways markets?
Note: 1 − ER or 1/ER carries the same information as ER. "Low ER → switch to an inverted logic" was tested on 8–9 Oct:
- `choppy_inverted_signal_results`;
- `primary_inverse_switch_results`;
- `optimized_inverse_regime_results`;
- `choppy_exit_lever_grid_results`;
- `choppy_er_exit_results`.
All failed. One version not yet tested under the current standard is the mirror of V2's entry with SIGNED ER: V2 buys an
efficient UP move breaking the 20-day high; the mirror buys an efficient DOWN move at a new 20-day low, only when the
market is sideways, betting on reversion.

Signal at the Close of day t:
- market sideways on day t+1 (`regime_proxy`, known before the Open);
- stock signed ER20 = (C_t − C_{t−20}) / sum |dC| <= −0.3 / −0.4 / −0.5;
- Close at a new 20-day closing low (C_t <= min of the previous 20 Closes).
Buy at the next Open. One position per stock at a time.

Exits:
- (a) Close > SMA10 (sold next Open);
- (b) time stop at the Close of bar 10;
- (c) (a) or time stop at bar 20.
Stop: none / Close < entry x 0.90 (sold next Open). 3 x 3 x 2 = 18 cells.

Setup: realistic universe (point-in-time liquidity + stale filter), cost B 0.90% round trip, 2000-01-01..2025-08-15,
trade level.
Control per cell: random days of the same stock with the market sideways, same exits, same count per stock (5 seeds).
Selection on 2000–2015 only (highest training net). The pick passes only if, in 2016–2025.08:
- net > 0 with NW t >= 2 (daily by entry date, lag 10);
- net above its control;
- >= 3 of 4 subperiods net > 0.
Win rate and break-even win rate are reported.
