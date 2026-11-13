# Do higher-ER stocks give bigger bounces we can use? (13 Nov 2026, written before results)
User: "apakah bila ER-nya lebih besar akan ada pantulan yang lebih besar yang bisa kita manfaatkan?"
`choppy_bounces_results` showed bounces in ER >= 0.3 stocks are rarer but bigger (median 8.7% vs 7.4%, p90 24% vs 19%).
ER is unsigned, so the direction of the stock's trend is tested separately.

Part 1 (descriptive): bounce size and real-time catch by finer ER20 bucket at the low's confirmation bar
(< 0.2, 0.2-0.3, 0.3-0.4, 0.4-0.5, >= 0.5) and by the stock's 20-day direction (C_k > C_{k-20} = up, else down),
zigzag threshold 3% / 5% / 10%. Same construction as `choppy_bounces.py`.

Part 2 (rule test): buy the confirmed bounce in a trending stock.
- Signal at the Close of bar k: a swing low L is confirmed (Close >= L x (1 + X), zigzag threshold X); stock ER20 at k
  satisfies the cell's condition; direction = up (C_k > C_{k-20}) or any; stock eligible on k+1 (realistic universe).
  All market conditions are allowed (the market label at entry is recorded and reported for the pick).
- Entry at the Open of k+1. Exit: Close <= running highest Close since entry x (1 - X) (the same reversal size as the
  bounce definition) or Close < L, both sold at the next Open; safety time stop at the Close of bar 60.
- One position per stock at a time. Cost B 0.90% round trip. 2000-01-01..2025-08-15.
Grid: X = 3% / 5% / 10%; ER condition = ER20 >= 0.2 / >= 0.3 / >= 0.5 / < 0.2 (reference, choppy); direction = up / any.
3 x 4 x 2 = 24 cells.
Control per cell: random eligible days of the same stock in the same ER and direction state (same count per stock,
5 seeds), buy next Open, the same trailing exit, with the stop level at Close_k x (1 - X). It separates the bounce
timing from the state "trending stock".
Reported per cell: trades per year, win rate and break-even win rate, average win / loss, payoff, gross, net with NW t
(lag 20), control net, exit shares, average bars; for the training pick also the split by market condition at entry.
Selection on 2000-2015 only among cells with >= 10 trades per year (excluding the ER < 0.2 reference cells): the highest
training net. The pick passes only if, in 2016-2025.08: net > 0 with NW t >= 2; net above its control; and >= 3 of the
4 subperiods have net > 0.
Note: buying a confirmed bounce in a trending stock is trend following (Logic 1 territory, a pullback entry), not a
sideways-specific logic; it is judged on the same rule anyway, and its sideways-market slice is reported.
