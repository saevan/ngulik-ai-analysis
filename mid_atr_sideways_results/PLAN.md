# Sideways mid-point + ATR logic, by range width, with a separate 'last low' entry (21 Oct 2026, before results)

User idea: in sideways, find the middle of the range, use ATR to profit, treat narrow and wide ranges differently, and
use a different logic near the last low. Reading tested (fixed before results):
- Range at the Close of t: H = highest High and L = lowest Low of the last 20 bars (t-19..t); mid = (H+L)/2;
  ATR = ATR14 through t; width W = (H-L)/ATR; z = (Close - mid)/ATR.
- Width classes (fixed a priori): narrow W < 4, medium 4 <= W < 7, wide W >= 7.
- Sideways: stock's own ER20 < 0.3 at t (primary) or market sideways label (EW proxy ER20 < 0.3, previous Close).
- Entry 'below_mid_k': z <= -k, k in {1, 1.5, 2}. Entry 'last_low': Close - L <= 0.5 ATR (close to the range's last low).
  Buy at the Close of t (closing auction).
- Exit: sell at the mid when High reaches it (at max(Open, mid)); stop if Close < L - 1 ATR (sell next Open); time stop at
  the Close of bar t+10. One position per stock.
- Control: random eligible sideways stock-days of the same stock and the same width class, same exit rule (does being
  below the mid / near the last low add anything?). 20 seeds.
- Cells: 3 widths x (3 k + last_low) x 2 sideways definitions = 24.
- Property check: within sideways stock-days, slope of the abnormal 10-day forward return (Close t -> Close t+10, minus
  the EW mean of eligible stocks) on z, by width class (Newey-West, lags 10). Mean reversion around the mid = negative slope.
Universe realistic (liquid at the time, not stale), 2000-01-01..2025-08-15. Cost B 0.90% round trip.
Pass: net B > 0, t >= 3, positive in >= 3 of 4 subperiods, and gross above the random control. AFL unchanged.
