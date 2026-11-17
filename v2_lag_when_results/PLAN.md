# When does V2 lag Swinger ideal on stocks? (17 Nov 2026, written before results)
User: "pada saat apa di saham logic kita ketinggalan dari swinger ideal". Descriptive only.
Systems: V2 realistic (as in `v2_gap_vs_swinger.py`) and Swinger ideal (`run_portfolio(fr, 'afl_ideal', slip=.0025)`),
cost B, 2000-01-01..2025-08-15.
1. Per calendar year: return of each system, gap in percentage points, and the year's market condition mix
   (share of uptrend / sideways / downtrend days, `regime_proxy`) and equal-weight proxy return.
2. Per market condition: annual return on that condition's days, invested share, and the share of the total log-growth
   gap that comes from each condition (sum of daily log-return differences on those days / total).
3. Per market speed: daily log-return gap grouped by quintile of the proxy's 20-day return known before the Open
   (fast fall ... fast rise), annualised.
4. Per V2 state: days when V2 holds 0-2 / 3-6 / 7+ positions; share of days and share of the gap.
