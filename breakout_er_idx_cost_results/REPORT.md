# IDX fee and spread sensitivity — not executable historical quotes

User-approved all-in buy fee0.15%, sell fee0.25%. No extra tax/levy added on top. Portfolio remains initialRp1billion,10slots, target10% prior-close equity per buy including fee, cash-constrained, no leverage. Quantity and fees sized together, profits/losses compounded through actual cash. ER20>=0.30 breakoutHigh20, hold200/fade5 ATR14 unchanged.

Gross reproduces previous exact curve. Fee-only uses original OHLC prices and fractional units. Net scenarios mark open holdings at modeled sell price minus hypothetical liquidation fee; daily estimate is not repeatedly charged to cash. Actual fees charged once on each buy/sell. End-of-period nontradable marks remain synthetic valuations, not proven fills.

Tick scenarios use five bands from official IDX current table: previousClose<200=>1;200–<500=>2;500–<2000=>5;2000–<5000=>10;>=5000=>25. Tick fixed within the day from prior Close. Offer proxy=ceil(reference/tick+s)*tick; bid proxy=max(tick,floor(reference/tick-s)*tick). One tick EACH SIDE implies about2ticks total modeled spread, not1tick total. Grid-only scenario adds rounding but no extra tick. Reference is strategy execution Open or scheduled Close. Round quantity down to100 shares; this exchange lot is separate from10 capital slots.

CRITICAL DATA LIMITATION: 129734 stock Opens are noninteger. Raw unadjusted price/adjustment factors and historical bid/ask/depth are unavailable. Treat grid/round-lot scenarios as stress assumptions on the supplied series, NOT an accurate historical fill model. Current tick and100-share lot rules are applied counterfactually over2000–2025; historical tick/lot regimes, corporate-action prices, minimum prices, auction/special-board rules and price limits are not reconstructed. Tick ladder changed historically. Source: https://www.idx.id/id/produk-layanan/jam-dan-mekanisme-perdagangan/

No order-book depth, queue, spread observations, market impact, fill-capacity or settlement-credit model. Buying at modeled offer/selling at modeled bid does not prove full quantity can match. Synthetic quotes may lie outside recorded OHLC. Do not clamp to observed day High/Low using future information. Results are provisional estimates; accurate reconstruction needs raw OHLC plus actions and bid/ask/depth history.

CAGR uses2000-01-04–2025-08-15. Record months count at least one daily net equity above all prior daily equity and initial capital; partial edge months included. Source universe and priority selection limitations remain. Reverse ticker priority sensitivity included for1tick-side scenario.
| Scenario | Trades | Final equity | CAGR | Record months | MDD |
|---|---:|---:|---:|---:|---:|
| gross | 340 | 1,848,706,038,001 | 34.14% | 128/308 (41.56%) | -56.07% |
| fees_only | 340 | 1,615,571,952,233 | 33.43% | 127/308 (41.23%) | -56.33% |
| fees_grid_roundlot | 340 | 1,428,139,660,994 | 32.79% | 126/308 (40.91%) | -56.73% |
| fees_1tick_each_side | 340 | 815,313,142,578 | 29.92% | 117/308 (37.99%) | -59.70% |
| fees_1tick_each_side_reverse_priority | 345 | 255,376,322,299 | 24.16% | 82/308 (26.62%) | -57.84% |
| fees_2ticks_each_side | 340 | 464,939,948,074 | 27.10% | 109/308 (35.39%) | -66.45% |
| fees_3ticks_each_side | 340 | 269,830,453,228 | 24.43% | 99/308 (32.14%) | -71.21% |