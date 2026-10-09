# TimeHunter ATR normalization

Defaults declared before testing: ATR14 Wilder, pullback1 ATR, fading2 ATR; SMA30, High20, rebound1, hold200 and all execution rules unchanged. All costs zero. These defaults are not optimized winners. Grid is sensitivity only.

ATR seeding: TR[0]=High[0]-Low[0]; first ATR at index13 is mean of first14 TRs; subsequent Wilder recurrence. Both pullback and fading use ATR from previous completed bar. Entry condition evaluated at completed Close, entry next tradable Open. Fading anchor is each current Open, exit next tradable Open, regardless of position PnL. Invalid/zero ATR blocks both price-threshold signals.

Same selected surviving crypto samples and forex-session limitations as timehunter_cross_market_results. Full histories differ; common period2023-07-01 through2025-08-15. No fee, leverage or portfolio sizing in return metrics. Mean is per trade. Normalization does not prove universal performance or seven criteria.
| Market | Period | N | WR | PF | Payout | Mean | Median | Numerical |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| stocks | since_start | 4560 | 48.03% | 2.20 | 2.28 | 7.67% | 0.00% | 4/5 |
| forex04 | since_start | 96 | 53.12% | 1.31 | 1.15 | 0.33% | 0.17% | 4/5 |
| crypto | since_start | 334 | 49.10% | 3.14 | 3.23 | 19.77% | -0.56% | 4/5 |
| forex00_sensitivity | since_start | 108 | 54.63% | 1.33 | 1.11 | 0.31% | 0.19% | 4/5 |

Requested entry start: 2000-01-01. Positions start flat. Prior data only warms indicators. Missing historical data are not fabricated. No common-period run in this invocation.
{
  "stocks": {
    "data_start": "2000-01-04 00:00:00",
    "data_end": "2025-08-15 00:00:00",
    "symbols": 100
  },
  "forex04": {
    "data_start": "2023-05-02 00:00:00",
    "data_end": "2026-05-21 00:00:00",
    "symbols": 9
  },
  "crypto": {
    "data_start": "2017-08-17 00:00:00",
    "data_end": "2025-08-15 00:00:00",
    "symbols": 8
  },
  "forex00_sensitivity": {
    "data_start": "2023-05-02 00:00:00",
    "data_end": "2026-05-22 00:00:00",
    "symbols": 9
  }
}