# Remove H200 time exit

Existing Breakout+ER module, not the pullback AFL currently open. Only change: hold=None disables time exits; fading remains current Open-Low>=5*prior ATR14 then exit next tradable Open. No trailing or secondary module. All remaining positions closed/marked at end of their data series for terminal valuation; those closures are not recurring strategy exit signals.

Stocks2000-01-04 to2025-08-15, initialRp1billion, ten slots, prior-close equity allocation, compounding, one position per ticker. Buy0.15%,sell0.25%. Fees scenario fractional units/no spread. Spread stress uses modern grid/100share lots and1tick per side throughout history counterfactually, not observed historical bid/ask. Reverse ticker priority sensitivity included. Data/universe/liquidity limitations unchanged.

No hold cap can lengthen positions and increase terminal dependence; it does not mean selling earlier. Baseline equity regression matches saved results. All simulations run cash/slot/PnL assertions. No time exits allowed in no-cap ledger. Regime attribution reconciles to portfolio CAGR; sideways annual equivalent concatenates disjoint days, not a standalone strategy CAGR. In-sample research, no claim of seven criteria or independent validation. Active AFL unchanged.

| Variant | CAGR | Record months | MDD | Trades | Mean holding bars | Fade exits | Terminal exits | Sideways annual equivalent |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fees_h200_reverseFalse | 33.43% | 127/308 | -56.33% | 340 | 180.7 | 48 | 10 | 18.97% |
| fees_hNone_reverseFalse | 9.06% | 48/308 | -72.50% | 25 | 2460.8 | 15 | 10 | -1.09% |
| fees_h200_reverseTrue | 27.73% | 93/308 | -55.43% | 345 | 178.0 | 56 | 10 | 10.05% |
| fees_hNone_reverseTrue | 9.57% | 49/308 | -69.76% | 25 | 2484.6 | 15 | 10 | -1.88% |
| spread_h200_reverseFalse | 29.92% | 117/308 | -59.70% | 340 | 180.7 | 48 | 10 | 15.25% |
| spread_hNone_reverseFalse | 8.43% | 52/308 | -71.41% | 25 | 2485.3 | 15 | 10 | -0.66% |
| spread_h200_reverseTrue | 24.16% | 82/308 | -57.84% | 345 | 178.0 | 56 | 10 | 6.44% |
| spread_hNone_reverseTrue | 9.41% | 49/308 | -69.97% | 25 | 2484.6 | 15 | 10 | -1.83% |