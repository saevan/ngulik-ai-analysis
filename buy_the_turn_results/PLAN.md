# Buy the turn after a decline (30 Oct 2026, written before results)
User: can we exploit the bounces? decline_bounce_results showed bounces measured from the (hindsight) low are large but
buying after an X% decline is no better than random. Here we wait for the turn: confirmation instead of guessing the low.
Setup (known at the Close of day t): within the last 10 bars the Close fell at least X% below the 20-bar high (X = 10, 15,
20%); still at least X/2 below that high at t (not already bounced).
Trigger: Close of t above the highest High of the 3 previous bars (a small swing up). Entry at the next Open (skip if it
gaps > 2% above the Close). Variant: stock sideways at t (own ER20 < 0.2) / any ER.
Exit: target = recover 50% or 100% of the decline (low of the decline up to the 20-bar high at trigger), limit fill at
max(Open, target); stop = Close below the lowest Low of the decline -> next Open; time stop 10 bars (Close).
Grid 3 X x 2 ER x 2 targets = 12 cells. Realistic universe, cost B 0.90%, 2000-01-01..2025-08-15.
Control per cell: random days with the same setup (and ER variant), bought at the next Open, same exits, same count per stock
(5 seeds) - tests whether the turn confirmation adds anything.
Pass only if ALL: net > 0 with NW t >= 3 (daily by entry date, lag 10); net > 0 in >= 3 of 4 subperiods; gross >= control
+ 0.5 pp; >= 2 of 3 X positive net for that ER/target. A pass would still need a portfolio test as Logic 2.
