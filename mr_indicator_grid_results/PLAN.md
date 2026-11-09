# Classic mean-reversion indicators (RSI and others) as Logic 2 (9 Nov 2026, written before results)
User: what about RSI or other mean-reversion signals? RSI2 < 10 was in `sideways_bounce_grid` (failed). This grid covers
the classic indicators with their textbook settings, at the signal Close t.

Signals (12):
- S1: RSI14 < 30;
- S2: RSI14 crosses back above 30;
- S3: RSI2 < 5;
- S4: RSI3 < 10;
- S5: Stochastic %K14 < 20 and %K crosses above %D3;
- S6: Close < lower Bollinger band (SMA20 − 2 SD20);
- S7: Close crosses back above the lower band;
- S8: Williams %R14 < −90;
- S9: CCI20 crosses back above −100;
- S10: IBS = (C − L) / (H − L) < 0.2;
- S11: z-score (C − SMA10) / SD10 < −2;
- S12: MFI14 < 20.
Entry (2):
- next Open;
- buy limit at Close − 0.5 x ATR14, valid next day, filled if Low < limit at min(Open, limit).
Exit (3):
- Close > SMA5, sold next Open, max 10 bars;
- Close > SMA20, sold next Open, max 20 bars;
- time stop at the Close of bar 5.
Market scope (2): sideways only (`regime_proxy` on the entry day) / all days (context).
12 x 2 x 3 x 2 = 144 cells.

Setup: realistic universe on the entry day, one position per stock at a time, cost B 0.90% round trip, trade level,
2000-01-01..2025-08-15. Control per cell: random eligible days in the same scope, same entry and exit, same count per
stock (5 seeds).
Selection on 2000–2015 only, among the sideways cells with >= 10 trades per year in training: the highest training net.
The pick passes only if, in 2016–2025.08:
- net > 0 with NW t >= 2 (lag 10);
- net above its control;
- >= 3 of 4 subperiods net > 0.
Also reported: how many cells have test net > 0 and t >= 2 (about 2–3% would by chance), win rate and break-even win
rate, and net at the user's fee 0.60% without slippage (information only).
