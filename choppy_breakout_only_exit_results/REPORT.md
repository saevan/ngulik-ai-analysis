# Exit on breakout without ER

Entry identical to inverse market-only: previous completed original sell(Close<SMA30 OR fade2ATR), marketproxy laggedER20<.30, tradable nextOpen. No stop/time cap. Baseline exit breakout20+stockER>=.30; market_er replaces it with current completed MARKET ER>=.30; breakout_only exits on Close>priorHHVHigh20 without stock or market ER requirement. Exit signals at Close fill next tradable Open. ER is unsigned, so either up or down directional movement can trigger. State condition >=.30, not one-day cross; pending exits survive suspensions.

Three fixed exit interpretations x two costs x three windows, no optimization. Full2000-2025 and fresh-start2016-2020/2021-2025. Same Rp1bn/10slots/compounding, buy.15%sell.25%. Spread stress modern IDX grid/100shares/1tick per side. Primary/AFL unchanged. Prefix causal entry/exit and original baseline equity regression checked. Market ER at signal Close is not lagged a second time; market regime entry label already lagged. Available stock observations determine when engine evaluates exits. Sideways equivalent is daily-regime attribution not standalone CAGR. Historical research, not independent validation.

| Period | Cost | Lever | Value | Trades | WR | Avg loss | Avg win | CAGR | PF money | Records | Sideways equivalent |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|full|fees|baseline|0|744|66.13%|19.99%|14.20%|4.79%|1.23|63/308|-1.66%|
|full|fees|market_er|0|3738|41.36%|5.18%|6.21%|-8.75%|0.68|0/308|-11.66%|
|full|fees|breakout_only|0|1234|66.69%|15.58%|9.88%|3.64%|1.18|34/308|-2.86%|
|full|spread|baseline|0|744|62.10%|19.38%|12.94%|-0.81%|0.96|2/308|-10.92%|
|full|spread|market_er|0|2894|28.02%|7.49%|8.48%|-29.50%|0.12|0/308|-44.10%|
|full|spread|breakout_only|0|1234|61.02%|14.90%|8.64%|-5.50%|0.68|1/308|-17.70%|
|validation|fees|baseline|0|150|72.67%|14.63%|11.91%|13.62%|1.97|27/60|12.80%|
|validation|fees|market_er|0|719|43.81%|4.25%|5.28%|-1.99%|0.95|13/60|-6.43%|
|validation|fees|breakout_only|0|254|73.23%|11.67%|9.98%|21.24%|2.11|29/60|19.64%|
|validation|spread|baseline|0|150|68.67%|14.17%|10.79%|8.28%|1.56|17/60|4.28%|
|validation|spread|market_er|0|719|31.99%|5.10%|5.58%|-22.40%|0.55|2/60|-38.16%|
|validation|spread|breakout_only|0|254|70.08%|11.58%|8.50%|11.61%|1.59|20/60|4.14%|
|test|fees|baseline|0|129|59.69%|17.36%|11.92%|-0.74%|0.97|8/56|-6.63%|
|test|fees|market_er|0|790|42.91%|4.67%|5.80%|-4.38%|0.92|11/56|-12.74%|
|test|fees|breakout_only|0|232|62.07%|12.92%|8.89%|1.73%|1.06|8/56|-4.07%|
|test|spread|baseline|0|129|55.81%|16.55%|11.65%|-3.22%|0.86|8/56|-10.20%|
|test|spread|market_er|0|790|34.43%|4.90%|6.15%|-18.32%|0.69|6/56|-31.38%|
|test|spread|breakout_only|0|232|58.62%|12.61%|8.39%|-2.78%|0.90|8/56|-10.45%|