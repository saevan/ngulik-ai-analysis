# Time exit that resets on every new trade high (user idea, 26 Oct 2026, written before results)
Exit rule for V1's breakout trades: track the highest High since entry (entry bar included); each new high resets the
bar count to 0; if x bars pass without a new high (checked at the Close), sell at the next Open (gapdown_close rule
applies). Monthly module unchanged. x = 5, 10, 15, 20, 30.
Variants: R_only = this exit replaces fade / SMA30 / failed breakout; R_plus = added to the original exits;
R_failed = failed-breakout exit kept + this exit. 15 cells, B, 2000-2025.08, unrestricted and realistic, train 2000-15 /
test 2016-25 slices. Improvement over V1 only if: realistic CAGR >= V1 in train AND test, unrestricted CAGR >= V1 - 5 pp,
MDD not more than 5 pp deeper in either version. WR reported (goal ~50%). AFL unchanged.
