# Separate logics for small (narrowing) and large sideways ranges (21 Oct 2026, before results)

User idea: sideways ranges narrow; use one logic for small ranges and another for large ranges.
Earlier tests already covered fading ranges by width (mid_atr_sideways, established_range: all lose) and found that
volatility squeezes do not predict larger moves in sideways (sideways_properties S8). New here: the NARROWING condition,
and testing BOTH a fade and a breakout logic for each range size. Fixed before results:
- Range at the Close of t: H, L = highest High / lowest Low of t-19..t; W = (H - L) / ATR14; sideways = stock ER20 < 0.3
  (variant: market sideways label).
- Narrowing: W[t] <= 0.7 x W[t-20] (the current 20-bar range is at least 30% narrower than the previous one).
- Small range: W < 4 and narrowing. Large range: W >= 6.
- Fade logic (both sizes): buy at the Close when Close is in the bottom 25% of the range; take-profit limit at the
  top-25% edge (small) or at the mid (large); stop Close < L - 0.5 ATR (sell next Open); time stop Close of bar 10 (small)
  or 20 (large).
- Breakout logic (both sizes): buy stop for the next bar at H + 0.1 ATR (filled at max(Open, level) when High reaches it);
  exit when 5 bars pass without a new trade high or Close < the range mid (sell next Open); time stop 40 bars.
- Comparisons: small-range logics also run WITHOUT the narrowing condition (does narrowing add anything?); every cell has a
  20-seed random control (same stock, same sideways and size condition, same exit rule; entry at the Close).
- Cells: {small, large} x {fade, breakout} x {stock_er, market} = 8, plus 4 'small without narrowing' cells.
Realistic universe, 2000-01-01..2025-08-15, cost B 0.90%. Pass: net B > 0, t >= 3, positive in >= 3 of 4 subperiods,
above the random control (and, for small ranges, above the no-narrowing version). AFL unchanged.
