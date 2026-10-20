# Bounce after an x-ATR drop, bought with a buy limit (20 Oct 2026)

Plan first (`PLAN.md`), code `atr_dip_limit.py`, all numbers `events.csv`. Realistic universe (liquid at the time, not stale),
limit at previous Close - x ATR14, fill when Low trades through, 2000-2025.

- A bounce exists before costs: from the fill price to that day's Close +0.47% (1 ATR, t 18.7), +0.60% (1.5), +0.67% (2),
  +1.18% (3 ATR, t 4.4). The limit buys 2.9-7.3% cheaper than that day's Open.
- After cost B (0.90% round trip) it is negative for 1-2 ATR at every exit (Close t, Open t+1, t+1, t+5, t+20).
- 3 ATR: +0.28% (Close t) / +0.46% (Open t+1), t about 1, 565 fills in 25 years; event-weighted +0.13%/+0.27%.
  Negative in 2021-25 at every x and exit (-0.65% to -2.1%).
- By market regime: sideways is negative at every x and exit. Uptrend 3 ATR is +0.9..+1.4% net but only 158 fills, t <= 2.4,
  a subgroup picked after looking.
Pre-registered rule (net > 0 with t >= 3 and positive in 3 of 4 subperiods) is not met -> no portfolio test. AFL unchanged.
