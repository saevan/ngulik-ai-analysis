# Is "holding winners longer" our edge, and can it help chase Swinger ideal? (17 Nov 2026, written before results)
User: "apakah kita mempunyai 1 keunggulan yakni bisa memegang keuntungan lebih lama sehingga kita bisa memanfaatkannya
ke depan untuk mengejar hasil Swinger ideal?" Realistic version, cost B, 2000-01-01..2025-08-15.

1. Where V2's money comes from (descriptive): V2 realistic trades grouped by bars held (<= 10, 11-30, 31-60, 61-120,
   > 120): share of trades, win rate, mean return, and share of total P&L. The same table for Swinger ideal.
2. Does holding long matter (counterfactual): V2 realistic with a time exit (`max_hold`) of 20 / 40 / 60 / 120 bars,
   applied to both modules, vs V2 as is. Reported: CAGR, MDD, win rate.
3. What Swinger leaves on the table: for each Swinger ideal trade, the stock's Close-to-Close move from Swinger's exit
   bar to 20 / 60 bars later, and the share of trades where the stock rose >= 20% in the next 60 bars.
4. Rule test, "use our holding edge with more entries": Logic A entries (5-day swing breakout of Swinger, executed at
   the next Open, realistic universe, 10% orders, 10 slots, A1 market filter as in `logic_a_swing5`) but with V2's
   long-hold exit instead of the swing exit: sell at the next Open after Close < SMA30 (variant H1), or after Close <
   SMA30 or Close <= highest Close since entry x 0.85 (variant H2, a 15% trailing stop). Compared with Logic A1 (swing
   exit), V2 realistic and Swinger ideal: CAGR, MDD, the four subperiod CAGRs, annual return per market condition,
   trades per year, win rate, payoff.
   Promising only if a variant beats V2 realistic CAGR and is positive in all four subperiods. Nothing is adopted.
