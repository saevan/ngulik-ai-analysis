# In sideways: how deep are declines and how big are the bounces? (30 Oct 2026, written before results)
User: find, inside ranges, how far a decline goes and how big the bounce is.
Realistic universe (point-in-time liquidity + stale filter), 2000-01-01..2025-08-15. Sideways stock = own ER20 < 0.2 at
the start of the decline; also reported for ER >= 0.2 and by market label.
Part 1 (swing anatomy, descriptive): pivots = bar whose High/Low is the extreme of +-3 bars, alternated. Decline = swing
high -> next swing low; bounce = that low -> next swing high. By decline bucket (0-5, 5-10, 10-15, 15-20, 20-30, >30%):
count, median decline length, median bounce %, bounce/decline ratio (median), P(ratio >= 0.5), P(ratio >= 1 = new high).
Baseline: the same statistics on each stock's random-walk twin (its own daily bars in shuffled order: close-to-close
return and High/Low offsets kept per bar), 3 shuffles.
Part 2 (real time): first Close at least X% below the 20-day high (X = 5, 10, 15, 20%) while the stock is sideways.
From the next Open over 10 and 20 bars: max rise (MFE), max further fall (MAE), return at the Close of bar 10/20.
Compared with random days of the same stock and condition (sideways, eligible), 5 seeds. Excess = event - random.
Descriptive; any trading use needs its own pre-registered test.
