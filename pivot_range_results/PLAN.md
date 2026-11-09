# Two ranges built from the bounce prices (zigzag pivots) (9 Nov 2026, written before results)
User clarification: the two ranges should come from the bounce prices found in `sideways_swings_results`, not from
N-day High/Low. Range 1 = the last medium swing (larger zigzag); range 2 = the last small swing (smaller zigzag) inside
it. Buy at the small bounce low, sell at the small bounce high, repeatedly.

Zigzag on Close (`sideways_swings.zigzag`); a pivot is used only after it is confirmed (confirmation bar <= t).
At the Close of day t:
- medium range = last confirmed medium swing low Lm and high Hm;
- small range = last confirmed small swing low Ls and high Hs;
- require: market sideways on t+1 (`regime_proxy`); stock eligible on t+1; Lm <= C_t <= Hm (still inside the medium
  range); Ls in the lower half of the medium range ((Ls − Lm)/(Hm − Lm) <= 0.5); C_t > Ls; Hs > Ls x 1.02.
Entry: buy limit at Ls on day t+1 (re-placed each day while the conditions hold), filled if Low < Ls at min(Open, Ls).
Exits:
- target = sell limit at Hs or at the medium mid (Hm + Lm)/2, from the day after entry, filled if High > target at
  max(Open, target), and only if target > entry;
- stop = Close < Lm x (1 − s), sold next Open, with s = 0 / 3%;
- time stop at the Close of bar T = 10 / 20.
Zigzag pairs (medium, small) = (10%, 3%) / (10%, 5%) / (5%, 3%). 3 x 2 x 2 x 2 = 24 cells.

Setup: realistic universe, one position per stock at a time, cost B 0.90% (user fee 0.60% without slippage also
reported), trade level, 2000-01-01..2025-08-15.
Control: random eligible sideways days of the same stock with valid pivots and C_t > Ls, same mechanics, same count per
stock (5 seeds).
Selection on 2000–2015 only (highest training net, >= 10 trades per year in training). The pick passes only if, in
2016–2025.08:
- net > 0 with NW t >= 2 (lag T);
- net above its control;
- >= 3 of 4 subperiods net > 0.
Exit shares and returns by exit type are reported.
