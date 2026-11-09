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

## Addendum (9 Nov, written before results): in which market conditions does Swinger trade while V2 does not?
Same systems and period. Market condition per day: `regime_proxy` (uptrend / sideways / downtrend), plus the
overlapping breakdown slice (proxy Close at a new 20-day low, known before the Open).
1. Per condition: share of days, trades opened per year (Swinger vs V2), capital invested, and share of days with
   Swinger >= 75% invested while V2 < 25%.
2. Swinger trades not covered by V2 (V2 never held that stock during the trade), by entry condition: count per year,
   share of Swinger trades, win rate and average return as traded, and the price movement leg (Close-to-Close net, from
   `swinger_fingerprint_results/trades.csv.gz`). The covered trades are reported the same way.
3. The uncovered trades split by two pre-declared stock features at the signal Close: stock ER20 < 0.2 vs >= 0.2, and
   Close above vs below SMA30.
Main version: V2 realistic; V2 unrestricted saved in the CSVs.
