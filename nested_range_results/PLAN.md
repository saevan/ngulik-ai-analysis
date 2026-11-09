# Two nested ranges: trade the small bounces inside a medium range, repeatedly (9 Nov 2026, written before results)
User: build two ranges. Range 1 holds the medium bounces, range 2 the smaller ones inside it, so we profit from the
repeated bounces. Resting limit orders are used, so no confirmation is needed (confirmation ate the bounce in
`sideways_swings_results`). The risk moves to range breaks.

At the Close of day t, with the market sideways on day t+1 (`regime_proxy`) and the stock eligible on day t+1:
- medium range: Hm/Lm = highest High / lowest Low of the last Nm bars up to t, with width Hm/Lm − 1 of 10–40%;
- small range: Hs/Ls = the same over the last Ns bars, with Hs > Ls x 1.02 (room for at least 2%);
- confluence (cell option): the small-range low sits in the lower half of the medium range, (Ls − Lm)/(Hm − Lm) <= 0.5.
Entry: buy limit at Ls on day t+1, filled if Low < Ls, at min(Open, Ls).
Exits:
- target = sell limit at Hs, or the medium-range mid (Hm + Lm)/2, from the day after entry, filled if High > target at
  max(Open, target);
- stop = Close < Lm x (1 − s), sold next Open, with s = 0 / 3%;
- time stop at the Close of bar T.
Repetition comes from new signals after each exit (one position per stock at a time).

Grid:
- Nm = 20 / 40;
- Ns = 5 / 10;
- target = small-range high / medium mid;
- s = 0 / 3%;
- T = 10 / 20;
- confluence = on / off.
That is 64 cells.

Setup: realistic universe, cost B 0.90% round trip (net with the user's fee 0.60% and no slippage also reported, since
both sides are limit orders), trade level, 2000-01-01..2025-08-15.
Control per cell: random eligible sideways-market days of the same stock with the same order mechanics (orders at that
day's ranges), same count per stock (5 seeds).
Selection on 2000–2015 only (highest training net among cells with >= 10 trades per year in training). The pick passes
only if, in 2016–2025.08:
- net > 0 with NW t >= 2 (lag T);
- net above its control;
- >= 3 of 4 subperiods net > 0.
Also reported: win rate vs break-even win rate, shares of exits by target / stop / time, and how many cells pass by
the test rule (chance about 2–3%).
