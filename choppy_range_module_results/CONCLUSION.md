# Choppy-only range module (20 Oct 2026)

Plan first (`PLAN.md`), code `choppy_range_module.py`, numbers `variants.csv`, trades `trades.csv`.
Realistic universe, 2000-2025, 16 pre-registered variants (range 10/20 bars, target mid/top, ER20 < 0.3/0.2, stop 2 ATR/none).

All 16 lose money even BEFORE costs: gross -0.95% to -1.66% per trade, net of cost B -1.9% to -2.5% (t -5.8 to -11),
negative in every subperiod 2000-07, 2008-15, 2016-20, 2021-25. Win rate is high (55-62% for the mid target) but the
losers are large: e.g. N10/mid/ER<0.3/no stop: 3,780 target exits average +4.7%, 2,608 time exits average -9.1%.
Buying a break of the range bottom in a choppy stock mostly buys the start of a further drop. No variant passes; no
portfolio test. Consistent with the 8-9 Oct inverse/switch tests and the ATR-dip buy-limit test. AFL unchanged.
