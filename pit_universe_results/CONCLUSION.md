# Point-in-time eligibility: how much of our result is survivorship (20 Oct 2026)

Plan written first (`PLAN.md`); code `pit_universe.py`, control `pit_universe_control.py` (added after seeing results).
v2 main pick, scenario B, CAGR % / record months / MDD %:

| Universe rule | 2000-15 | 2016-20 | 2021-25 | 2000-25 |
|---|---|---|---|---|
| Unrestricted (today's 100 Kompas100 members) | 40.1/74/-23 | 79.2/29/-23 | 54.1/20/-24 | 49.3/119/-24 |
| Random half of the stocks each month (control, 3 seeds) | 29.3-35.6 | 18.8-88.7 | 16.0-43.8 | 31.0-38.5 / 87-103 |
| PIT: only stocks liquid at the time (top half by 120-day traded value, >= 250 bars) | 17.5/40/-33 | 22.2/12/-31 | 17.8/7/-44 | 19.0/54/-44 |
| PIT top third | 8.2/29/-48 | 12.3/14/-25 | -4.1/1/-60 | 7.1/32/-61 |
| PIT top half, without 2018+ listings | 17.5/40 | 11.8/11 | 12.9/8 | 16.2/51/-41 |

Reading: halving the candidate pool by itself costs about 11-18 pp (49.3 -> 31-38.5). Restricting to stocks that were
liquid at the time costs a further 12-20 pp (-> 19.0). Much of the main pick's return came from stocks that were small or
illiquid when bought and are in the file only because they later became Kompas100 members.

What this does NOT fix: stocks that were delisted or dropped from the index are absent from the data, so even the PIT
result is still optimistic. A full fix needs historical Kompas100 constituents (IDX publishes them each Feb/Aug) and price
history for removed/delisted stocks; the session's network policy blocks finance data hosts (www.idx.co.id returned 403).
Swinger ideal was not restricted and keeps the full bias. AFL unchanged.

## Addendum: stale data and liquid volume (`pit_stale_liquidity.py`, `stale_liquidity.csv`)
Already in every run: Volume-0 bars are not tradable. Added (rules fixed before results): stale filter (>= 90% traded days and
<= 10% one-price bars in the previous 60 bars) and a liquidity cap (each buy <= 25% of 20-day average traded value). Scenario B:

| Variant | 2000-15 | 2016-20 | 2021-25 | 2000-25 | median order / entry-day value | orders > entry-day value |
|---|---|---|---|---|---|---|
| Unrestricted | 40.1/74 | 79.2/29 | 54.1/20 | 49.3/119/-24 | 1.25x | 53% |
| Stale + cap only | 22.8/59 | 43.4/22 | 36.0/24 | 24.7/83/-31 | 0.08x | 0.7% |
| PIT top half | 17.5/40 | 22.2/12 | 17.8/7 | 19.0/54/-44 | 0.04x | 0.2% |
| PIT + stale + cap | 13.3/38 | 21.9/12 | 17.8/7 | 16.2/52/-44 | 0.02x | 0% |

The unrestricted main pick bought more than the whole day's traded value in half of its entries, mostly in stocks that were
illiquid at the time. With point-in-time liquidity, stale-data and volume limits the system earns about 16% a year with a
-44% drawdown, and delisted stocks are still missing (so even this is optimistic).
