# Breakout + ER: ten-slot compounding portfolio

Initial capital1,000,000,000; maximum10 positions, one per instrument. Target new entry=10% of previous daily closing portfolio equity, capped by available cash. Initial target100,000,000. No leverage/fees/cash yield. Units fractional: lot means capital allocation, not exchange round lot. No periodic rebalance, existing quantities unchanged; winners may grow above10% equity. No forced investment without signals.

Entry Close>High20 of preceding bars, ER20>=0.30 optional. Same exits: hold200th Close or current Open-Low>=5*prior ATR14 then next tradable Open. Entries use only completed signal bars. Process pending Open sells, then Open buys in ticker alphabetical order, then Close exits and pending fade orders. Close-sale proceeds cannot fund earlier same-day Open buys. Insufficient-slot/cash entries rejected, fresh signals required; suspended-volume entry queues retained. No same-bar reentry.

Reverse-alphabetical priority sensitivity provided for stocks. All portfolio runs start flat on first available observation>=2000, earlier indicators warmed. Source session timezone forex uncertain;04 and00 tested independently. Daily bars across instruments treated as synchronized opens/closes (no intraday timing or FX currency-conversion model). Local quote-price percentage return applied to common account notional for forex/crypto; no leveraged FX margin model.

CAGR from actual first-last observation dates. A record month contains at least one daily closing equity above all prior daily closes and initial capital. Includes unrealized PnL and partial edge months. Terminal closes/marks, missing-close carry-forward follow earlier assumptions. Crypto only8 instruments and forex9, so maximum10 allocations cannot always be used. Unequal listing dates and absent signals leave cash idle.

Historical observed universe, stock corporate actions/survivorship unverified, selected surviving crypto, shared/correlated samples. Not independent validation, no guaranteed expected returns. No changes to main AFL: portfolio allocation tests are Python implementations, not AmiBroker validation.
| Market | Variant | Trades | Final equity | CAGR | MDD | Record months | Mean invested |
|---|---|---:|---:|---:|---:|---:|---:|
| stocks | no_filter | 338 | 80,183,564,805 | 18.67% | -56.37% | 80/308 (25.97%) | 95.07% |
| stocks | no_filter_reverse_priority | 346 | 1,108,138,692,764 | 31.48% | -55.70% | 111/308 (36.04%) | 94.34% |
| stocks | er_0.3 | 340 | 1,848,706,038,001 | 34.14% | -56.07% | 128/308 (41.56%) | 93.63% |
| stocks | er_0.3_reverse_priority | 345 | 604,803,336,846 | 28.41% | -55.17% | 96/308 (31.17%) | 93.84% |
| forex04 | no_filter | 41 | 1,023,012,750 | 0.75% | -5.13% | 7/37 (18.92%) | 78.26% |
| forex04 | er_0.3 | 38 | 1,022,729,580 | 0.74% | -5.50% | 5/37 (13.51%) | 72.28% |
| forex00 | no_filter | 42 | 1,044,596,432 | 1.44% | -4.35% | 11/37 (29.73%) | 76.34% |
| forex00 | er_0.3 | 40 | 1,024,496,494 | 0.80% | -4.20% | 6/37 (16.22%) | 73.17% |
| crypto | no_filter | 94 | 88,903,173,886 | 75.30% | -74.00% | 15/97 (15.46%) | 62.45% |
| crypto | er_0.3 | 89 | 123,694,166,893 | 82.69% | -70.42% | 17/97 (17.53%) | 59.72% |