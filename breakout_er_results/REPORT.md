# Breakout + Kaufman ER module

Long-only module tested separately: completed Close > highest High of the preceding20 bars (exclude signal bar), and ER20>=threshold. Default0.30 declared before results; no-filter control and0.20/0.40/0.50 sensitivities. ER=abs(Close-Close20barsAgo)/sum(abs(one-bar Close changes),20). Flat denominator =>0, warmup unavailable =>no filtered signal. ER measured per instrument, not an aggregate market index. No SMA/pullback entry filter added to this breakout module.

Entry next tradable Open; original exit machinery unchanged: scheduled200th Close or Low<=current Open-5*previous ATR14, next tradable Open. No ER-based exit. Same hold/ATR/execution across variants. Prior history warms indicators; initial flat positions, entries>=2000 where data available. Gap/volume handling and period-end forced closure follow existing engine.

Equity: initial1billion, fixed100thousand each buy, fractional units, no fees/slippage/leverage/cash yield. Most funds idle; this is previous AFL test-harness sizing, not a fully allocated portfolio. Daily marked-to-market equity; missing asset close carried forward. CAGR uses actual first-last data dates. Monthly record fraction means at least one daily closing equity record during the month; includes partial first/last months. End-record fraction also saved.

Sample histories differ: stocks2000–2025, forex2023–2026, crypto2017–2025. Forex source timezone unknown;04:00 primary/00:00 sensitivity. Selected surviving crypto and unaudited stock corporate actions/survivorship remain limitations. This retrospective module test does not prove future chop avoidance or seven-criteria universality.
| Market | Variant | N | WR | PF | CAGR | Record months | MDD |
|---|---|---:|---:|---:|---:|---:|---:|
| stocks | no_filter | 1900 | 54.42% | 3.34 | 0.165646% | 108/308 (35.06%) | -0.2864% |
| stocks | er_0.2 | 1815 | 54.82% | 3.45 | 0.165773% | 108/308 (35.06%) | -0.2743% |
| stocks | er_0.3 | 1704 | 53.76% | 3.51 | 0.158339% | 103/308 (33.44%) | -0.2355% |
| stocks | er_0.4 | 1534 | 54.11% | 3.59 | 0.147324% | 97/308 (31.49%) | -0.2097% |
| stocks | er_0.5 | 1297 | 54.82% | 3.67 | 0.130376% | 103/308 (33.44%) | -0.1633% |
| forex04 | no_filter | 41 | 53.66% | 1.41 | 0.000751% | 7/37 (18.92%) | -0.0053% |
| forex04 | er_0.2 | 41 | 43.90% | 1.15 | 0.000312% | 6/37 (16.22%) | -0.0055% |
| forex04 | er_0.3 | 38 | 44.74% | 1.54 | 0.000752% | 5/37 (13.51%) | -0.0057% |
| forex04 | er_0.4 | 31 | 54.84% | 1.65 | 0.000581% | 9/37 (24.32%) | -0.0057% |
| forex04 | er_0.5 | 24 | 33.33% | 0.95 | -0.000044% | 5/37 (13.51%) | -0.0039% |
| forex00 | no_filter | 42 | 50.00% | 1.90 | 0.001442% | 11/37 (29.73%) | -0.0045% |
| forex00 | er_0.2 | 41 | 48.78% | 1.66 | 0.001116% | 9/37 (24.32%) | -0.0044% |
| forex00 | er_0.3 | 40 | 45.00% | 1.41 | 0.000809% | 7/37 (18.92%) | -0.0043% |
| forex00 | er_0.4 | 31 | 58.06% | 2.50 | 0.001577% | 13/37 (35.14%) | -0.0037% |
| forex00 | er_0.5 | 24 | 58.33% | 1.19 | 0.000204% | 10/37 (27.03%) | -0.0039% |
| crypto | no_filter | 95 | 55.79% | 12.62 | 0.206443% | 11/97 (11.34%) | -1.2714% |
| crypto | er_0.2 | 90 | 61.11% | 13.86 | 0.210107% | 13/97 (13.40%) | -1.2588% |
| crypto | er_0.3 | 89 | 60.67% | 14.46 | 0.206144% | 13/97 (13.40%) | -1.2399% |
| crypto | er_0.4 | 81 | 62.96% | 15.73 | 0.202907% | 13/97 (13.40%) | -1.2084% |
| crypto | er_0.5 | 71 | 61.97% | 20.26 | 0.201912% | 12/97 (12.37%) | -1.1773% |

ER reference: https://doc.stocksharp.com/en/topics/api/indicators/list_of_indicators/kaufman_efficiency_ratio

Reproduce: python backtest_breakout_er.py. No main AFL modifications.