# Separate logics for small (narrowing) and large sideways ranges (21 Oct 2026)

Plan first (`PLAN.md`); code `range_size_modules.py`; independent re-derivation `verify_range_size.py` (trade-by-trade identical,
no look-ahead). Realistic universe, 2000-2025, cost B 0.90%. Range = 20 bars, width in ATR; small = W < 4 (optionally
narrowing >= 30% vs the previous 20 bars), large = W >= 6; sideways = stock or market ER20 < 0.3.

- Fade (buy the bottom 25%, take profit at the top-25% edge or mid): all 6 cells lose before costs (gross -0.45..-0.87%,
  net -1.35..-1.60%), no better than random entries.
- Narrowing adds nothing: small-range breakout 1.17% gross with narrowing vs 1.19% without (fails its own pre-registered rule).
- Breakouts beat fades in every size. Best: small-range breakout in choppy stocks, +1.17% gross, +0.24% net (t 0.8). But:
  * it is not a small-range effect: the same buy stop above the 20-bar high with the same exit on ALL eligible days gives
    1.19% gross; it is the main system's HHV20 breakout taken mostly in low-ER stocks;
  * with the fill rounded to the price grid (as the main system does) net is -0.02% (t -0.06);
  * without the top 5 tickers net -0.26%; without the top 3 years -0.11%; 2021-25 net -0.34%; since Dec 2024 gross -0.48%.
  * The original breakout control was degenerate (it bought at the Close of every condition day); a fair control (random
    buy stops at the same ATR distance) earns 0.42-0.51% gross, so the breakout trigger adds ~0.7 pp (t 2.1-2.5) gross,
    not enough after cost.
- Large-range breakout: 0.4-0.9% gross, about 0 after cost, not distinguishable from random buy stops.
No usable small- or large-range module. AFL unchanged.
