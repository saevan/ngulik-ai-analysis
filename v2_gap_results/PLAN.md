# Why is V2 not as strong as Swinger ideal? (9 Nov 2026, written before results)
Descriptive gap analysis, no new rules. Systems: V2 realistic and V2 unrestricted (`wr_gap_v1.kw(v, True, None)`,
`failed_exit=None`), Swinger ideal (`run_portfolio(fr, 'afl_ideal', slip=.0025)`). Cost B, 2000-01-01..2025-08-15.

A. Bridge: CAGR and annual return per condition for V2 realistic → V2 unrestricted → Swinger ideal. The realistic
   constraints (point-in-time liquidity, stale filter, 25% ADV20 cap) apply to V2 only; the benchmark has none.
B. Money x opportunities x quality: per system, trades per year N, average weight at entry w (entry amount / equity at
   the previous Close), weighted net return per trade E (sum w*r / sum w). Contribution per year = N x w x E. Gap in
   logs: ln(C_swinger / C_v2) = ln N ratio + ln w ratio + ln E ratio. Also capital invested by condition.
C. Missed big moves: Swinger ideal's top 5% trades by net return. Share of their holding days on which V2 held the same
   stock, and share of those trades V2 overlapped at all. The same for V2's top 5% trades vs Swinger.
D. Loss size: V2 losers by exit reason (share of losers, average loss, average bars). Swinger losers for reference: as
   traded and on the Close-to-Close basis (from the step-1 fingerprint; the fill note stays brief).
E. Where V2 idles: invested share and number of positions by condition; share of days with at least one free slot.
