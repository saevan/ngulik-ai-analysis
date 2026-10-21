# Sideways mid-point + ATR logic by range width, with a 'last low' entry (21 Oct 2026)

Plan first (`PLAN.md`); code `mid_atr_sideways.py`; independent re-derivation `verify_mid_atr.py` (trade-by-trade identical).
Realistic universe, 2000-2025. Range = 20-bar High/Low, mid = (High+Low)/2, width W in ATR14, entry when Close is k ATR below
the mid (k 1/1.5/2) or within 0.5 ATR of the range low ('last low'); buy at the Close; exit at the mid (limit), stop
Close < low - 1 ATR, time stop 10 bars. Sideways = stock ER20 < 0.3 or market ER20 < 0.3. Cost B 0.90%.

- No cell passes. Narrow (W < 4) and medium (4-7) ranges: gross -0.6% to +0.03% per trade before costs, net -0.9% to -1.5%,
  not better than random below-mid entries of the same stock and width class (narrow slightly worse).
- The mid does not pull price back: in narrow ranges the opposite holds (lower in the range -> lower 10-day return,
  +0.22% per ATR of position, t 2.5; +0.33%, t 3.7 from the next Open); medium about 0. Both tails |z| > 1.5 are negative.
- 'Last low' is not a separate behaviour: in narrow ranges it overlaps 88% with 'below mid by 1 ATR', and it is the worst cell.
- Only wide ranges (W >= 7) with the stock's own ER < 0.3 are positive: 7-11 trades a year, gross +1.2..+1.8%, net t <= 1.04.
  It is not a sideways range: 92% are declines after a spike (median 25% below the 20-day high). Knife-edge (W >= 6: -0.23%
  gross), concentrated (without INCO, BRPT, TPIA gross 0.7-0.8% < cost), negative after cost in 2021-25 in every variant.
Caveats: buy at the Close of the signal bar is only approximately executable (next-Open entry is 0.07-0.19 pp worse for
narrow/medium); the random control is not distance-matched (favours the signal). AFL unchanged.
