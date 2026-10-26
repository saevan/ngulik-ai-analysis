# Monthly entry with the EXISTING exits (user clarification 26 Oct 2026, written before results)
User: the monthly module is only an extra entry ("at the start of the month some stocks are bought early, without a
breakout"); exits must be the existing ones. Check: the current V2 monthly positions use only their own month-end exit
(code line `if p.get('kind')=='extra': ... continue`), so V2 does NOT match the intent.
Test: V2 breakout unchanged (no failed exit; fade 2 ATR + Close < SMA30, next Open, gapdown_close) + monthly entry whose
positions use the same exits (engine option extra_main_exits=True, no own exit). Filters at the month-end Close:
F1 = Close > Close 120 bars ago and ER20 >= 0.3 (current); F2 = ER20 >= 0.4 and Close > Close 20 bars ago;
F3 = F1 and Close > SMA30 (not already below the exit line). Sizing: S1 = 10% orders, monthly positions <= 35% of
equity; S2 = 25% orders like the breakout, no separate cap. 6 cells, unrestricted and realistic, B, 2000-2025.08.
References: V2 as now; breakout only (V2 without monthly). Reported: CAGR (train 2000-15 / test 2016-25), records, MDD, WR,
monthly-trade WR / expectancy / bars / share exited within 2 bars.
Candidate to replace the current V2 monthly design if realistic CAGR >= V2 realistic in train AND test, unrestricted
CAGR >= V2 - 5 pp, MDD not more than 5 pp deeper in either version. AFL unchanged.

## Round 2: SMA filter for the monthly entry (user 26 Oct 2026, written before round-2 results)
Monthly positions use the existing exits (fade 2 ATR, Close < SMA30). Goal: avoid buying stocks that are already below /
right at the exit line.
Part 1 (diagnostic): monthly trades of F1|S1 and F2|S1 bucketed by the signal Close vs SMA n (n = 10, 20, 30, 50, 100,
200): above / below, and for SMA30 the distance 0-3%, 3-5%, 5-10%, >10% above. Expectancy, WR, bars per bucket.
Part 2 (grid): base filter {none, F1, F2} x SMA condition {C>SMA10, C>SMA20, C>SMA30, C>SMA50, C>SMA100, C>SMA200,
C>=1.03 SMA30, C>=1.05 SMA30, C>=1.10 SMA30, stack SMA20>SMA50>SMA100 and C>SMA20} = 30 cells, 10% orders, monthly
<= 35% of equity, unrestricted and realistic. Selection on realistic train CAGR (2000-2015). The pick counts as useful
only if it beats "breakout only" (V2 without the monthly module) in realistic train AND test, unrestricted full CAGR >=
breakout only - 5 pp, and MDD not more than 5 pp deeper in either version. Compared also with V2 now.
