# "When the range breaks, ER turns straight, Logic 1 takes over and Logic 2 is sold automatically" (9 Nov 2026, before results)
User claim: a range break makes ER straight again, so an ER-based switch would sell the Logic 2 position. Tested on the
two Logic 2 range systems (`nested_range`: 64 cells, `pivot_range`: 24 cells), with entries restricted to the user's
framework (stock ER20 < 0.2 at the signal Close, market sideways). Note: Logic 1 (V2) buys only UPWARD breakouts, so a
downward break only triggers the sale.

Exit variants (target and time stop unchanged):
1. price stop (the original: Close < medium low x (1 − s));
2. stock ER20 >= 0.2 at Close, sold next Open;
3. stock ER20 >= 0.3;
4. market leaves sideways (label for the next day is not sideways), sold next Open;
5. price stop + stock ER20 >= 0.3.
Variants 2–4 replace the price stop.

Reported per system and variant, over all cells:
- mean gross / net / win rate / average win / average loss;
- cells with net > 0 (cost B 0.90%) over 2000–2025;
- for the variant's training pick (2000–2015), the test 2016–2025.08 result (net, NW t, subperiods).
Descriptive check on the trades that ended at the price stop (variant 1, the training-pick cell of each system):
- share that reached stock ER20 >= 0.3 before the stop;
- bars from entry to ER20 >= 0.3;
- return at that Close vs at the stop exit.
The claim is supported only if an ER exit makes cells profitable after cost B and the training pick passes in test
(net > 0, NW t >= 2, >= 3 of 4 subperiods net > 0).
