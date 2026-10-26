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
