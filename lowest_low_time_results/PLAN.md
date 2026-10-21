# Second logic: "lowest low held for x bars" entry, "no new trade high for x bars" exit (21 Oct 2026, before results)

User idea (price + time). Definitions, fixed before any result:
- Lowest low: bar s is an N-bar low if Low[s] <= min(Low[s-N..s-1]) (touching counts).
- Entry signal at the Close of bar t when the most recent N-bar low was exactly x bars earlier (t - s = x), i.e. the
  low was touched and not touched again for x bars. Buy at the next Open (primary) or at the Close of t (closing
  auction, sensitivity).
- Exit: trade high = highest High since the entry bar (Close of t for a Close entry). When x bars pass without a new
  trade high, sell at the next Open. Same x for entry and exit. No other stop (the time rule bounds each trade).
- One position per stock; a new entry needs a new N-bar low after the exit.
- Grid (all reported): N {10, 20, 60} x x {3, 5, 10} x filter {market sideways at the signal, none} x entry {next Open,
  Close} = 36 cells. Market sideways = analyze_portfolio_regimes label (previous Close).
- Universe: realistic (liquid at the time, not stale), 2000-01-01..2025-08-15. Costs B 0.90% round trip (A 0.40%).
- Control: random entries on the same stocks and regime days, same count, same exit rule (does the entry add anything?).
Statistic: mean net return per trade, averaged per entry day, Newey-West t (lags 20); per subperiod 2000-07, 2008-15,
2016-20, 2021-25. Pass (standalone): net B > 0, t >= 3, positive in >= 3 of 4 subperiods, and above the random control.
Only a passing cell goes to a portfolio test. AFL unchanged.
