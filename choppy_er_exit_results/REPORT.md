# Exit when ER no longer choppy

Entry identical to inverse market-only: previous completed original sell(Close<SMA30 OR fade2ATR), marketproxy laggedER20<.30, tradable nextOpen. No stop/time cap. Baseline exit breakout20+stockER>=.30; market_er replaces it with current completed MARKET ER>=.30; stock_er uses current completed STOCK ER>=.30; market_or_original retains old exit plus market exit. Exit signals at Close fill next tradable Open. ER is unsigned, so either up or down directional movement can trigger. State condition >=.30, not one-day cross; pending exits survive suspensions.

Four fixed exit interpretations x two costs x three windows, no optimization. Full2000-2025 and fresh-start2016-2020/2021-2025. Same Rp1bn/10slots/compounding, buy.15%sell.25%. Spread stress modern IDX grid/100shares/1tick per side. Primary/AFL unchanged. Prefix causal entry/exit and original baseline equity regression checked. Market ER at signal Close is not lagged a second time; market regime entry label already lagged. Available stock observations determine when engine evaluates exits. Sideways equivalent is daily-regime attribution not standalone CAGR. Historical research, not independent validation.

| Period | Cost | Lever | Value | Trades | WR | Avg loss | Avg win | CAGR | PF money | Records | Sideways equivalent |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|full|fees|baseline|0|744|66.13%|19.99%|14.20%|4.79%|1.23|63/308|-1.66%|
|full|fees|market_er|0|3738|41.36%|5.18%|6.21%|-8.75%|0.68|0/308|-11.66%|
|full|fees|stock_er|0|5415|35.68%|4.41%|7.34%|-6.49%|0.85|0/308|-12.03%|
|full|fees|market_or_original|0|3939|42.02%|5.21%|6.03%|-9.36%|0.67|0/308|-12.73%|
|full|spread|baseline|0|744|62.10%|19.38%|12.94%|-0.81%|0.96|2/308|-10.92%|
|full|spread|market_er|0|2894|28.02%|7.49%|8.48%|-29.50%|0.12|0/308|-44.10%|
|full|spread|stock_er|0|3332|22.39%|7.07%|8.36%|-35.28%|0.13|0/308|-55.16%|
|full|spread|market_or_original|0|2735|27.86%|7.70%|7.06%|-31.90%|0.12|0/308|-47.15%|
|validation|fees|baseline|0|150|72.67%|14.63%|11.91%|13.62%|1.97|27/60|12.80%|
|validation|fees|market_er|0|719|43.81%|4.25%|5.28%|-1.99%|0.95|13/60|-6.43%|
|validation|fees|stock_er|0|954|35.85%|4.13%|7.76%|0.81%|1.02|8/60|3.41%|
|validation|fees|market_or_original|0|758|44.33%|4.16%|5.20%|-1.00%|0.97|12/60|-5.34%|
|validation|spread|baseline|0|150|68.67%|14.17%|10.79%|8.28%|1.56|17/60|4.28%|
|validation|spread|market_er|0|719|31.99%|5.10%|5.58%|-22.40%|0.55|2/60|-38.16%|
|validation|spread|stock_er|0|954|26.73%|5.14%|8.59%|-25.38%|0.60|1/60|-38.93%|
|validation|spread|market_or_original|0|758|32.19%|5.07%|5.46%|-23.29%|0.54|2/60|-39.88%|
|test|fees|baseline|0|129|59.69%|17.36%|11.92%|-0.74%|0.97|8/56|-6.63%|
|test|fees|market_er|0|790|42.91%|4.67%|5.80%|-4.38%|0.92|11/56|-12.74%|
|test|fees|stock_er|0|1129|37.56%|4.23%|6.01%|-9.81%|0.86|7/56|-15.39%|
|test|fees|market_or_original|0|827|43.17%|4.88%|5.68%|-6.97%|0.87|9/56|-15.98%|
|test|spread|baseline|0|129|55.81%|16.55%|11.65%|-3.22%|0.86|8/56|-10.20%|
|test|spread|market_er|0|790|34.43%|4.90%|6.15%|-18.32%|0.69|6/56|-31.38%|
|test|spread|stock_er|0|1129|29.14%|4.55%|6.79%|-27.34%|0.63|1/56|-38.79%|
|test|spread|market_or_original|0|827|34.46%|5.07%|6.03%|-21.16%|0.65|5/56|-34.68%|