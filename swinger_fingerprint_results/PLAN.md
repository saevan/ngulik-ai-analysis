# Swinger ideal fingerprint per market condition (9 Nov 2026, written before results)
User direction: forget the current system and start from scratch. The goal is one trading system that performs in
uptrend, downtrend and sideways markets. The reference is Prototype Swinger ideal: find other logic with its
characteristics. Step 1 measures those characteristics per market condition. This step is descriptive only: no
selection, no new rules.

Benchmark: Prototype Swinger ideal (`backtest_prototype_swinger.run_portfolio(fr, 'afl_ideal', slip=.0025)`), cost
scenario B (fee 0.15/0.25% + 0.25% slippage per side), 10 positions of 10%, 2000-01-01..2025-08-15, current 100-stock
universe. Market condition at entry: `regime_proxy` (EW proxy ER20 >= 0.3 up/down, else sideways; known before the Open).

A. Trade character per condition: trades per year, win rate, average win/loss, expectancy, median bars held.
B. Where each trade's return comes from (log, additive): entry fill leg ln(entry-bar Close / fill), movement leg
   ln(exit-bar Close / entry-bar Close), exit fill leg ln(exit fill / exit-bar Close), costs. Also the
   Close-to-Close version (movement leg − 0.9%): win rate and expectancy per condition, and the share of the movement leg
   earned by the top 5% of trades.
C. What Swinger buys: features at the entry signal Close, medians vs all tradable stock-days in the same condition (base
   rate):
   - stock ER20;
   - 5/20/60-day return;
   - Close vs SMA30 and SMA120;
   - position in the 20-day range;
   - ATR14 / Close;
   - Close at a new 20-day closing high (share).
D. Movement leg by two pre-declared splits within each condition: stock ER20 < 0.2 vs >= 0.2, and Close above vs below
   SMA30.
Interpretation rule: the movement leg is the part another executable logic could capture. The fill legs come from the
benchmark's fill and are only noted.

## Addendum (9 Nov, written before results): user claim "WR around 50% is fine as long as average win > average loss"
From the same Swinger ideal trades, per condition and overall, for both the as-traded (ideal fill) and the Close-to-Close
basis: win rate, average net win, average net loss, payoff (avg win / |avg loss|), break-even win rate = 1 / (1 + payoff),
expectancy, median trade. Plus the arithmetic: needed payoff at win rates 30/40/45/50/55%.
