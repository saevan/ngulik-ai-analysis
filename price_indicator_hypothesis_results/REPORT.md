# Does shortening price indicators preserve returns and increase trades?

393 configurations, 100 stocks, continuous 1994-07-12 to 2025-08-15, zero costs. Every execution uses the existing engine; fading references each current bar Open and executes next tradable Open.

Scope: every price component in the existing strategy family (SMA, rolling-high pullback window/depth, breakout, rebound lookback, fading threshold). Not every indicator ever invented. A rebound over N bars is an explicit variant of the original one-bar rebound. Hold is controlled at 50, 100 and 200, rather than shortened along with indicators.

The user clarified that 30% refers to WIN RATE. Check both trade frequency and changes in WR; mean return remains an additional metric only. PF uses equal entry notional. A signal bar is not an actual trade: only one position per symbol and entry cannot occur while holding. Comparisons are descriptive, in-sample, not tests of statistical equivalence or causality. Windows have their natural warmups. Corporate actions and survivorship remain unaudited.

Validation: prefix causality checked for all entry variants and tickers; original SMA100 entry signals and 1,974-trade baseline reproduced.

## SMA30 versus SMA100, other parameters fixed

| Indicator | Value | Hold | Fade | Signal bars | Trades | WR | PF | Mean | Median | Payout |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| sma_only | 30 | 50 | off | 226948 | 7842 | 50.64% | 1.927 | 5.88% | 0.55% | 1.804 |
| sma_only | 30 | 50 | 0.3 | 226948 | 7874 | 50.58% | 1.925 | 5.89% | 0.52% | 1.800 |
| sma_only | 30 | 100 | off | 226948 | 4245 | 52.34% | 2.316 | 11.08% | 1.79% | 2.057 |
| sma_only | 30 | 100 | 0.3 | 226948 | 4278 | 51.89% | 2.404 | 12.00% | 1.54% | 2.164 |
| sma_only | 30 | 200 | off | 226948 | 2246 | 51.91% | 3.377 | 27.39% | 2.05% | 3.058 |
| sma_only | 30 | 200 | 0.3 | 226948 | 2288 | 51.49% | 3.236 | 25.75% | 1.81% | 2.961 |
| sma_only | 100 | 50 | off | 232904 | 6553 | 50.60% | 2.003 | 6.16% | 0.57% | 1.876 |
| sma_only | 100 | 50 | 0.3 | 232904 | 6568 | 50.58% | 1.991 | 6.11% | 0.57% | 1.866 |
| sma_only | 100 | 100 | off | 232904 | 3672 | 52.59% | 2.484 | 12.20% | 1.68% | 2.161 |
| sma_only | 100 | 100 | 0.3 | 232904 | 3692 | 52.44% | 2.509 | 12.54% | 1.58% | 2.197 |
| sma_only | 100 | 200 | off | 232904 | 2063 | 54.05% | 3.492 | 26.15% | 4.33% | 2.913 |
| sma_only | 100 | 200 | 0.3 | 232904 | 2087 | 53.62% | 3.463 | 26.41% | 4.11% | 2.931 |
| sma_combined | 30 | 50 | off | 62398 | 7045 | 50.32% | 1.856 | 5.47% | 0.39% | 1.762 |
| sma_combined | 30 | 50 | 0.3 | 62398 | 7056 | 50.33% | 1.848 | 5.43% | 0.40% | 1.753 |
| sma_combined | 30 | 100 | off | 62398 | 3996 | 51.58% | 2.216 | 10.42% | 1.20% | 2.025 |
| sma_combined | 30 | 100 | 0.3 | 62398 | 4014 | 51.47% | 2.279 | 11.07% | 1.19% | 2.088 |
| sma_combined | 30 | 200 | off | 62398 | 2161 | 52.80% | 3.258 | 25.35% | 2.18% | 2.867 |
| sma_combined | 30 | 200 | 0.3 | 62398 | 2181 | 52.59% | 3.107 | 24.07% | 2.20% | 2.736 |
| sma_combined | 100 | 50 | off | 63585 | 5704 | 51.12% | 1.996 | 6.05% | 0.86% | 1.834 |
| sma_combined | 100 | 50 | 0.3 | 63585 | 5716 | 51.01% | 1.977 | 5.99% | 0.76% | 1.823 |
| sma_combined | 100 | 100 | off | 63585 | 3363 | 52.69% | 2.592 | 12.79% | 1.77% | 2.263 |
| sma_combined | 100 | 100 | 0.3 | 63585 | 3378 | 52.61% | 2.577 | 12.78% | 1.71% | 2.254 |
| sma_combined | 100 | 200 | off | 63585 | 1956 | 53.78% | 3.487 | 26.63% | 4.12% | 2.940 |
| sma_combined | 100 | 200 | 0.3 | 63585 | 1974 | 53.44% | 3.418 | 26.26% | 3.92% | 2.916 |

## All price components at hold=200 / fading=30%

| Indicator | Value | Hold | Fade | Signal bars | Trades | WR | PF | Mean | Median | Payout |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| sma_only | 5 | 200 | 0.3 | 211178 | 2371 | 52.93% | 3.301 | 25.76% | 2.78% | 2.830 |
| sma_only | 10 | 200 | 0.3 | 220493 | 2361 | 52.56% | 3.191 | 25.13% | 1.93% | 2.797 |
| sma_only | 20 | 200 | 0.3 | 225319 | 2321 | 52.52% | 3.280 | 25.83% | 2.74% | 2.887 |
| sma_only | 30 | 200 | 0.3 | 226948 | 2288 | 51.49% | 3.236 | 25.75% | 1.81% | 2.961 |
| sma_only | 50 | 200 | 0.3 | 229229 | 2230 | 52.29% | 3.223 | 25.32% | 2.96% | 2.875 |
| sma_only | 75 | 200 | 0.3 | 231406 | 2166 | 53.28% | 3.370 | 26.49% | 3.11% | 2.906 |
| sma_only | 100 | 200 | 0.3 | 232904 | 2087 | 53.62% | 3.463 | 26.41% | 4.11% | 2.931 |
| sma_only | 150 | 200 | 0.3 | 232291 | 1984 | 53.63% | 3.480 | 26.20% | 3.34% | 2.934 |
| sma_only | 200 | 200 | 0.3 | 232316 | 1881 | 53.06% | 3.532 | 26.72% | 2.34% | 3.068 |
| sma_combined | 5 | 200 | 0.3 | 89889 | 2305 | 51.80% | 3.098 | 23.86% | 1.61% | 2.834 |
| sma_combined | 10 | 200 | 0.3 | 75381 | 2278 | 52.63% | 3.139 | 24.25% | 2.41% | 2.773 |
| sma_combined | 20 | 200 | 0.3 | 66075 | 2238 | 53.08% | 3.033 | 23.53% | 3.00% | 2.624 |
| sma_combined | 30 | 200 | 0.3 | 62398 | 2181 | 52.59% | 3.107 | 24.07% | 2.20% | 2.736 |
| sma_combined | 50 | 200 | 0.3 | 61439 | 2102 | 53.00% | 3.263 | 24.98% | 2.54% | 2.829 |
| sma_combined | 75 | 200 | 0.3 | 62675 | 2035 | 53.56% | 3.511 | 27.01% | 3.49% | 2.989 |
| sma_combined | 100 | 200 | 0.3 | 63585 | 1974 | 53.44% | 3.418 | 26.26% | 3.92% | 2.916 |
| sma_combined | 150 | 200 | 0.3 | 63681 | 1874 | 53.36% | 3.436 | 25.85% | 3.30% | 2.938 |
| sma_combined | 200 | 200 | 0.3 | 63878 | 1773 | 53.36% | 3.514 | 26.20% | 3.19% | 3.035 |
| pullback_only | 5 | 200 | 0.3 | 299917 | 2381 | 52.50% | 3.338 | 26.47% | 2.20% | 2.943 |
| pullback_only | 10 | 200 | 0.3 | 352414 | 2385 | 52.87% | 3.360 | 26.61% | 2.75% | 2.891 |
| pullback_only | 20 | 200 | 0.3 | 389056 | 2386 | 52.81% | 3.327 | 26.13% | 2.81% | 2.867 |
| pullback_only | 30 | 200 | 0.3 | 403503 | 2387 | 52.79% | 3.297 | 26.03% | 2.63% | 2.839 |
| pullback_only | 50 | 200 | 0.3 | 416805 | 2385 | 52.91% | 3.295 | 26.18% | 2.99% | 2.838 |
| pullback_only | 75 | 200 | 0.3 | 423133 | 2373 | 52.97% | 3.307 | 26.41% | 3.38% | 2.833 |
| pullback_only | 100 | 200 | 0.3 | 425855 | 2361 | 52.90% | 3.355 | 26.41% | 2.63% | 2.880 |
| pullback_only | 150 | 200 | 0.3 | 426725 | 2338 | 53.25% | 3.298 | 25.56% | 3.11% | 2.781 |
| pullback_only | 200 | 200 | 0.3 | 425163 | 2308 | 52.56% | 3.398 | 26.68% | 2.45% | 2.961 |
| pullback_combined | 5 | 200 | 0.3 | 40330 | 1906 | 53.31% | 3.460 | 26.12% | 3.21% | 2.976 |
| pullback_combined | 10 | 200 | 0.3 | 53476 | 1943 | 53.17% | 3.355 | 25.50% | 3.31% | 2.894 |
| pullback_combined | 20 | 200 | 0.3 | 63585 | 1974 | 53.44% | 3.418 | 26.26% | 3.92% | 2.916 |
| pullback_combined | 30 | 200 | 0.3 | 68164 | 1992 | 53.26% | 3.436 | 26.35% | 3.27% | 2.950 |
| pullback_combined | 50 | 200 | 0.3 | 73406 | 2028 | 52.76% | 3.378 | 25.63% | 3.19% | 2.955 |
| pullback_combined | 75 | 200 | 0.3 | 77894 | 2054 | 52.82% | 3.384 | 26.01% | 3.37% | 2.953 |
| pullback_combined | 100 | 200 | 0.3 | 80890 | 2061 | 52.74% | 3.412 | 26.25% | 3.33% | 2.988 |
| pullback_combined | 150 | 200 | 0.3 | 83422 | 2049 | 52.56% | 3.439 | 26.41% | 3.03% | 3.030 |
| pullback_combined | 200 | 200 | 0.3 | 84654 | 2025 | 52.94% | 3.471 | 26.74% | 3.16% | 3.011 |
| breakout | 5 | 200 | 0.3 | 44144 | 2238 | 51.88% | 3.204 | 25.42% | 1.93% | 2.892 |
| breakout | 10 | 200 | 0.3 | 31496 | 2138 | 52.71% | 3.386 | 26.63% | 2.45% | 2.972 |
| breakout | 20 | 200 | 0.3 | 22446 | 2004 | 54.34% | 3.414 | 26.21% | 4.27% | 2.828 |
| breakout | 30 | 200 | 0.3 | 18593 | 1884 | 54.41% | 3.671 | 28.19% | 4.25% | 3.012 |
| breakout | 50 | 200 | 0.3 | 14494 | 1679 | 54.44% | 3.632 | 27.78% | 4.17% | 2.984 |
| breakout | 75 | 200 | 0.3 | 11982 | 1512 | 54.37% | 3.760 | 27.95% | 4.64% | 3.087 |
| breakout | 100 | 200 | 0.3 | 10406 | 1376 | 54.72% | 3.852 | 28.58% | 4.48% | 3.120 |
| breakout | 150 | 200 | 0.3 | 8531 | 1172 | 54.95% | 3.844 | 28.77% | 4.21% | 3.104 |
| breakout | 200 | 200 | 0.3 | 7407 | 1010 | 56.04% | 3.880 | 29.97% | 5.11% | 2.996 |
| rebound_combined | 1 | 200 | 0.3 | 63585 | 1974 | 53.44% | 3.418 | 26.26% | 3.92% | 2.916 |
| rebound_combined | 2 | 200 | 0.3 | 71157 | 1993 | 52.63% | 3.439 | 26.62% | 3.05% | 3.023 |
| rebound_combined | 3 | 200 | 0.3 | 76119 | 1986 | 52.11% | 3.452 | 26.54% | 2.47% | 3.098 |
| rebound_combined | 5 | 200 | 0.3 | 83048 | 2005 | 52.12% | 3.373 | 25.82% | 2.41% | 3.021 |
| rebound_combined | 10 | 200 | 0.3 | 96041 | 1996 | 52.71% | 3.363 | 25.85% | 2.90% | 2.951 |
| rebound_combined | 20 | 200 | 0.3 | 115496 | 1985 | 52.85% | 3.405 | 26.02% | 2.95% | 2.976 |
| rebound_combined | 30 | 200 | 0.3 | 132078 | 1987 | 53.15% | 3.435 | 26.76% | 3.12% | 2.954 |
| rebound_combined | 50 | 200 | 0.3 | 152518 | 1996 | 52.35% | 3.391 | 26.19% | 2.47% | 3.015 |
| rebound_combined | 100 | 200 | 0.3 | 151545 | 1897 | 53.35% | 3.521 | 26.74% | 2.45% | 3.013 |
| pullback_depth | 0.005 | 200 | 0.3 | 85504 | 2032 | 53.30% | 3.442 | 26.21% | 3.86% | 2.946 |
| pullback_depth | 0.01 | 200 | 0.3 | 77645 | 2024 | 52.87% | 3.399 | 26.00% | 3.24% | 2.963 |
| pullback_depth | 0.02 | 200 | 0.3 | 63585 | 1974 | 53.44% | 3.418 | 26.26% | 3.92% | 2.916 |
| pullback_depth | 0.03 | 200 | 0.3 | 51940 | 1927 | 53.30% | 3.424 | 26.45% | 3.21% | 2.937 |
| pullback_depth | 0.05 | 200 | 0.3 | 34708 | 1802 | 53.33% | 3.467 | 27.07% | 3.44% | 2.976 |
| pullback_depth | 0.075 | 200 | 0.3 | 20956 | 1583 | 53.51% | 3.546 | 28.20% | 3.28% | 3.023 |
| pullback_depth | 0.1 | 200 | 0.3 | 12593 | 1318 | 52.73% | 3.593 | 29.99% | 3.29% | 3.159 |
| pullback_depth | 0.15 | 200 | 0.3 | 4781 | 784 | 54.97% | 4.110 | 37.69% | 6.73% | 3.280 |

## Fading sensitivity at hold=200 (original entry)

| Indicator | Value | Hold | Fade | Signal bars | Trades | WR | PF | Mean | Median | Payout |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| fading | 0.02 | 200 | 0.02 | 63585 | 34169 | 36.48% | 1.318 | 0.54% | -0.77% | 1.992 |
| fading | 0.03 | 200 | 0.03 | 63585 | 24711 | 37.47% | 1.369 | 0.86% | -1.10% | 2.050 |
| fading | 0.05 | 200 | 0.05 | 63585 | 11584 | 40.15% | 1.545 | 2.31% | -1.81% | 2.134 |
| fading | 0.075 | 200 | 0.075 | 63585 | 4920 | 44.67% | 1.960 | 6.99% | -1.44% | 2.281 |
| fading | 0.1 | 200 | 0.1 | 63585 | 3119 | 47.74% | 2.352 | 12.56% | 0.00% | 2.434 |
| fading | 0.15 | 200 | 0.15 | 63585 | 2264 | 51.37% | 2.828 | 19.60% | 1.47% | 2.580 |
| fading | 0.2 | 200 | 0.2 | 63585 | 2076 | 52.22% | 3.159 | 23.86% | 2.51% | 2.801 |

## Matched adjacent-window comparisons

Every comparison changes only one lookback, with hold and fade unchanged. Fraction below counts configurations, NOT independent statistical observations.

                   pairs  fraction_short_more_trades  median_trade_ratio  mean_delta_min  mean_delta_max  wr_delta_min  wr_delta_max  median_abs_wr_delta
family                                                                                                                                                   
breakout              48                    1.000000            1.152274       -0.019708        0.004167     -0.016285      0.008199             0.004642
pullback_combined     48                    0.250000            0.985150       -0.011533        0.010912     -0.005466      0.005017             0.001358
pullback_only         48                    0.687500            1.003252       -0.011173        0.011855     -0.004575      0.007614             0.001444
rebound_combined      48                    0.458333            0.998791       -0.009242        0.007995     -0.009927      0.008106             0.002985
sma_combined          48                    1.000000            1.042110       -0.020293        0.008293     -0.008820      0.005879             0.003233
sma_only              48                    1.000000            1.042916       -0.011673        0.019299     -0.011799      0.010758             0.003269

Reproduce: python test_price_indicator_hypothesis.py
