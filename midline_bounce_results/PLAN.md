# The midline as the reference for bounces in sideways markets (13 Nov 2026, written before results)
User: "ketika dia memberikan pantulan kita cari garis tengah dulu gimana sebagai acuan kita gitu". The reading
"buy below, sell at the range midline" was already tested (target = range mid in `high_wr_range_results` and
`nested_range_results`: all cells lost). Two readings not yet tested:

B. Pullback to the middle of the bounce. Zigzag on Close with threshold X (`sideways_swings.zigzag`). A swing low L is
   confirmed on the bar where Close >= L x (1 + X). From then on, H = the running highest Close since the low. Setup on
   day t (within 30 bars of the low): H >= L x (1 + 2X) (the bounce is at least twice the threshold), mid < C_t < H
   (price has pulled back below H but is still above mid), market sideways on t+1 (`regime_proxy`, known before the
   Open), stock eligible on t+1 (realistic universe). Order: buy limit at mid = (L + H) / 2 on day t+1, filled if Low <
   mid at min(Open, mid). Exits: target = sell limit at H from the day after entry (filled at max(Open, H) if High > H);
   stop = Close < L x (1 - s), sold next Open; time stop at the Close of bar T. Grid: X = 3% / 5%; T = 10 / 20;
   s = 0 / 3%. 8 cells.
   Control: random eligible sideways days of the same stock (same count per stock, 5 seeds) with a generic dip limit
   at Close x (1 - X), target Close x (1 + X), stop Close x (1 - 2X), same T. It shows whether the bounce structure adds
   anything to a generic limit order below the price.

C. Reclaim of the range midline. Range = highest High / lowest Low of the last N bars; mid = (H + L) / 2. Signal at the
   Close of day t: C_{t-1} < mid_{t-1} and C_t > mid_t (the bounce crosses back above the midline), stock ER20 < 0.2
   (choppy stock), market sideways on t+1, eligible on t+1. Buy at the next Open. Exits: target = sell limit at H (the
   range high at the signal); stop = Close < L (range low) or Close back below mid (both sold next Open); time stop at
   the Close of bar T. Grid: N = 20 / 40; stop = range low / back below mid; T = 10 / 20. 8 cells.
   Control: random eligible sideways days of the same stock with ER20 < 0.2, same mechanics (buy next Open, target the
   day's range high, same stop and T), 5 seeds.

Common: one position per stock at a time, cost B 0.90% round trip (the user's fee 0.60% without slippage also reported),
trade level, 2000-01-01..2025-08-15. Reported per cell: trades per year, win rate and break-even win rate, average
win / loss, gross, net with NW t (daily by entry date, lag T), control net, exit shares (target / stop / time), and for
B the split by stock ER20 < 0.2 vs >= 0.2 at the setup.
Selection on 2000-2015 only, per family, among cells with >= 10 trades per year in training: the highest training
net. The pick passes only if, in 2016-2025.08: net > 0 with NW t >= 2; net above its control; and >= 3 of the 4
subperiods (2000-07, 2008-15, 2016-20, 2021-25) have net > 0.
