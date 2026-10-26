# Time exit that resets on every new trade high (user idea, 26 Oct 2026, written before results)
Exit rule for V1's breakout trades: track the highest High since entry (entry bar included); each new high resets the
bar count to 0; if x bars pass without a new high (checked at the Close), sell at the next Open (gapdown_close rule
applies). Monthly module unchanged. x = 5, 10, 15, 20, 30.
Variants: R_only = this exit replaces fade / SMA30 / failed breakout; R_plus = added to the original exits;
R_failed = failed-breakout exit kept + this exit. 15 cells, B, 2000-2025.08, unrestricted and realistic, train 2000-15 /
test 2016-25 slices. Improvement over V1 only if: realistic CAGR >= V1 in train AND test, unrestricted CAGR >= V1 - 5 pp,
MDD not more than 5 pp deeper in either version. WR reported (goal ~50%). AFL unchanged.

## Confirmation test (26 Oct 2026, after the exploratory no-SMA30 run, written before these results)
Candidate: V1 with the SMA30 exit replaced by the high-reset exit (x bars without a new trade high), fade 2 ATR and failed
breakout kept, monthly module unchanged. Main test = REALISTIC version. Neighbours x = 16, 18, 20, 22, 25.
Accepted as an improvement in the realistic version only if ALL: (a) >= 4 of 5 x beat V1 realistic on full-period CAGR
with MDD not deeper; (b) x = 20 beats V1 realistic in the holdout 1996-01-01..1999-12-31 (realistic, data from 1994-07);
(c) x = 20 vs V1 realistic paired monthly log-return difference: Newey-West t >= 1.5 (lag 6). Unrestricted reported.

## V2 + high-reset exit as an ADDITIONAL exit (26 Oct 2026, written before these results)
V2 (no failed-breakout exit; fade 2 ATR + SMA30 kept) plus the high-reset exit, x = 10, 15, 20, 25, 30. Checks as before:
(a) >= 4 of 5 x beat V2 realistic full-period CAGR with MDD not more than 2 pp deeper; (b) x = 20 beats V2 realistic in the
holdout 1996-1999; (c) x = 20 vs V2 realistic monthly log-return difference, Newey-West t >= 1.5. Unrestricted reported.
