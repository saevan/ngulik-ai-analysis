# Frozen TimeHunter cross-market transfer

SMA30 / High20 / pullback2% / rebound1 / hold200 / fade30%. Long-only, all costs zero, same execution engine, no optimization by market. Fading from current-bar Open; sell next tradable Open. Same bar count does not mean same calendar duration (crypto trades weekends).

Forex source hourly CSV, source timezone unknown. Primary daily sessions start04:00 in source clock, based on observed Monday04:00–Saturday03:00 weekly coverage. Midnight-source-clock aggregation is included as sensitivity; do not label these UTC. Conservative first/last-session exclusion. No bars synthesized over missing sessions. Forex Volume=0 treated as unavailable metadata, not a trading halt. Crypto uses Binance spot daily UTC candles through2025-08-15.

Full history differs between markets. Common comparison is2023-07-01–2025-08-15, with prior bars for indicator warmup and flat initial positions. Common-period windows were chosen before inspecting performance. Per-period end closures are reported and sensitivity excluding them is in comparison.csv.

WR counts breakeven trades in denominator. Avg loss is positive magnitude. PF is sum positive returns / absolute sum negative returns, equal entry notional; mean is return per trade, not CAGR/portfolio. Universality is not established merely by implementing the same formula. Small cross-market samples, correlated assets, selected surviving crypto pairs, and unaudited stock corporate actions/survivorship limit inference.
| Market | Period | N | WR | Mean | Median | Avg win | Avg loss | Payout | PF | Numeric | Fade exits | End closures |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| stocks_daily | full | 2181 | 52.59% | 24.07% | 2.20% | 67.49% | 24.67% | 2.74 | 3.11 | 5/5 | 53 | 93 |
| stocks_daily | common | 298 | 42.95% | 7.76% | -2.66% | 42.93% | 19.06% | 2.25 | 1.73 | 4/5 | 2 | 97 |
| forex_daily_04 | full | 17 | 41.18% | -0.05% | -1.74% | 4.30% | 3.10% | 1.39 | 0.97 | 2/5 | 0 | 2 |
| forex_daily_04 | common | 15 | 46.67% | -0.30% | -1.57% | 2.73% | 2.96% | 0.92 | 0.81 | 1/5 | 0 | 5 |
| crypto_daily_UTC | full | 124 | 59.68% | 73.30% | 13.80% | 146.88% | 35.59% | 4.13 | 6.11 | 5/5 | 42 | 8 |
| crypto_daily_UTC | common | 33 | 78.79% | 48.52% | 31.71% | 70.00% | 31.28% | 2.24 | 8.31 | 5/5 | 3 | 8 |
| forex_daily_00_sensitivity | full | 15 | 53.33% | 1.52% | 0.37% | 4.80% | 2.24% | 2.15 | 2.45 | 5/5 | 0 | 2 |
| forex_daily_00_sensitivity | common | 13 | 53.85% | 0.77% | 1.57% | 3.51% | 2.42% | 1.45 | 1.69 | 3/5 | 0 | 6 |

## Data coverage
{
  "stocks_daily": {
    "rows": 464768,
    "symbols": 100,
    "start": "1994-07-12 00:00:00",
    "end": "2025-08-15 00:00:00"
  },
  "forex_daily_04": {
    "rows": 7841,
    "symbols": 9,
    "start": "2023-05-02 00:00:00",
    "end": "2026-05-21 00:00:00"
  },
  "crypto_daily_UTC": {
    "rows": 20889,
    "symbols": 8,
    "start": "2017-08-17 00:00:00",
    "end": "2025-08-15 00:00:00"
  },
  "forex_daily_00_sensitivity": {
    "rows": 8595,
    "symbols": 9,
    "start": "2023-05-02 00:00:00",
    "end": "2026-05-22 00:00:00"
  }
}

## Official crypto data reference
https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md

Reproduce: python download_crypto_daily.py (network), then python backtest_timehunter_cross_market.py (local). Raw responses and hashes saved under Data/crypto_binance_daily.