# Established ranges in sideways: buy the bottom, take profit at the top (21 Oct 2026, before results)

New angle vs earlier failures: only trade ranges whose price has ALREADY gone back and forth ("bolak balik"), and test
whether that history makes the next bounce more reliable than in other ranges. Fixed before any result:
- Range at bar t from the previous M bars (t-M..t-1): U = highest High, D = lowest Low, R = U - D.
  Bottom zone = Low <= D + z*R; top zone = High >= U - z*R.
- Established: in those M bars the compressed sequence of zone visits has >= n bottom visits and >= n top visits
  (alternating back and forth). Comparison group 'not established': same entry rule, fewer visits.
- Sideways: the stock's own ER20 < 0.3 at t-1 (primary); market sideways label reported as a variant.
- Profit room: target (top-zone edge U - z*R) at least 3% above the entry, so a full swing can cover the 0.90% cost.
- Entry at bar t: Low[t] enters the bottom zone while Close[t] >= D - 0.5 ATR14. Variant 'close': buy at the Close of t.
  Variant 'limit': buy limit at the bottom-zone edge D + z*R, filled at min(Open, edge) when Low < edge.
- Exit: take-profit limit at U - z*R (High >= level, filled at max(Open, level)); stop Close < D - 0.5 ATR -> next Open;
  time stop at the Close of bar 20. One position per stock.
- Grid: M {40, 60} x z {0.2, 0.25} x n {2, 3} x entry {close, limit} = 16 cells, each also run for 'not established'.
- Random control: same stock, sideways days, inside the range's lower half, same exit levels (20 seeds).
- Persistence: does a stock's range success rate (target before stop) in year Y predict year Y+1? (rank correlation)
Universe realistic (liquid at the time, not stale), 2000-01-01..2025-08-15, cost B 0.90% round trip.
Pass: net B > 0, t >= 3, positive in >= 3 of 4 subperiods, above 'not established' and above the random control.
AFL unchanged.
