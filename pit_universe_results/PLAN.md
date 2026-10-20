# Point-in-time eligibility test (20 Oct 2026, written before results)

Goal: remove the part of the survivorship bias that can be removed with the data we have. The file holds today's 100
Kompas100 members back to 1994; stocks that were delisted or dropped are missing and CANNOT be added (no data; the network
policy blocks finance data hosts). What can be removed is look-ahead selection: a stock that was small and illiquid years
ago is in the file only because it later became liquid enough for the 2025 list.

Rule (fixed now): a stock may receive a NEW entry on day t only if, using data up to t-1,
1. it has at least 250 trading bars, and
2. its 120-day mean traded value (Close x Volume) ranks in the top half of the file's stocks with a valid value that day
   (sensitivity: top third).
Open positions are never forced out. Everything else = v2 main pick (search_realistic_chase_v2.kw), scenarios A and B,
windows 2000-15 / 2016-20 / 2021-25 / 2000-25, universes all and pre2018. Compared with the unrestricted main pick.
Swinger ideal is not restricted (its engine has no gate), so it keeps the full bias; this is noted, not corrected.

## Addendum (20 Oct 2026, before running): stale data and liquid volume
User asked whether stale data and liquid volume are considered. Already in place: Volume-0 bars are not tradable (no fills,
no exits on them). Added now, fixed before results, scenario B unless stated:
- stale filter: new entry only if, over the previous 60 bars, >= 90% had Volume > 0 and <= 10% were one-price bars
  (Open = High = Low = Close);
- liquidity cap (scenario C): every buy <= 25% of the stock's 20-day average traded value (sells uncapped);
- variants: PIT top half; + stale; + cap; + stale + cap; and unrestricted + stale + cap. Same windows and universe 'all'.
