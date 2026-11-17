# V2 on forex (17 Nov 2026, written before results)
User: "gimana performa dia di forex?" V2 has never been run on forex. Earlier forex work (Oct 2026) used older systems
at zero cost: TimeHunter baseline 17 trades, WR 41%, PF 0.97; the first breakout+ER module CAGR ~0.00%.

Data: `Data/Data Forex.csv`: 9 pairs (AUDUSD, EURJPY, EURUSD, GBPJPY, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY), hourly
bars 2023-05-01..2026-05-23, volume unavailable (zero). Aggregated to daily sessions starting 04:00 source clock with
`backtest_timehunter_cross_market.forex_daily(fx, 4)` (source timezone unknown; edge sessions dropped), as in the
earlier cross-market work. Sensitivity: 00:00 sessions.
Both directions: each pair is also included as its inverse (Open = 1/Open, High = 1/Low, Low = 1/High, Close = 1/Close),
so the long-only V2 can take the short side. 18 instruments. A pair and its inverse can in principle be held at the same
time; the number of such days is reported.

System: V2 unrestricted (no liquidity gate, since volume is unavailable): buy stop at HHV20 + 0.5% on the instrument's
own price grid (data-derived), ER20 >= 0.2, mom120 priority, exits fade 2 ATR and Close < SMA30 (next Open), gap-down
close 2%, 25% orders, 10 slots, plus the monthly module (Close > Close 120 bars ago and ER20 >= 0.3 at the month-end
Close, 10% orders, max 35%); no failed-breakout exit. Month-ends from the forex session calendar.
Costs: three proportional scenarios, no commission: 0 (gross), 0.05% and 0.10% round trip (0.025% / 0.05% per side).
For scale, 1 pip on EURUSD is about 0.009%. The user's actual forex costs are unknown.
Benchmark: Prototype Swinger ideal on the same 18 instruments, same costs.
Accounting as before: percent return on the quote price applied to a common notional (Rp1bn), no leverage, no currency
conversion, daily bars treated as synchronized.

Period: all sessions (2023-05-02..2026-05-22); indicators warm up inside the data. CAGR over the actual span; also the
two halves 2023-05..2024-10 and 2024-11..2026-05.
Reported: CAGR, MDD, trades, win rate, average win / loss, payoff, expectancy per trade, capital invested; per
instrument (pair and direction) trades and expectancy; overlap days; the same for Swinger ideal.
Descriptive only: 3 years x 9 pairs is a small sample, so no selection and no pass rule. "Encouraging" would be V2
expectancy > 0 at 0.10% cost in both halves; anything less is "no evidence".
