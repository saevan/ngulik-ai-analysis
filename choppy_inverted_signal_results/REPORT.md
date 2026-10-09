# Inverting primary raw signals during choppy regime

Source: research Breakout20+stockER20>=.30, exits Close<SMA30 or Open-Low>=2priorATR14. Not active pullback AFL. Invert underlying signal conditions, not historical executed trades. Long only: sell becomes buy, buy becomes sell. No additional range/cost or high-stockER entry selection. Entry on next tradable Open eligible market choppy dates. Market variant uses market proxy gate only; market_stock additionally requires stockER<.30 at signal. Both pure variants have no extra stop/hold/fading sell. market_stock_stop adds separately labeled .5entryATR Close stop. Exits are NOT gated by choppy; queues survive suspensions; entry requires a tradable execution bar; no stale entry queues.

Three interpretations fixed before results; no optimized parameters. Full2000-2025 and fresh-start2016-2020/2021-2025. Earlier data examined, not independent validation. Rp1bn/10slots/compounding/buy.15%sell.25%; spread stress modern IDX grid/100shares/1tick eachside, not actual historical bidask. Prefix entry/exit and eligibility/accounting checks. Main unchanged. Sideways annual equivalent is daily regime attribution, not standalone CAGR. Monthly records use closing all-time equity peak since window start.

| Period | Cost | Lever | Value | Trades | WR | Avg loss | Avg win | CAGR | PF money | Records | Sideways equivalent |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|full|fees|market|0.0|744|66.13%|19.99%|14.20%|4.79%|1.23|63/308|-1.66%|
|full|fees|market_stock|0.0|753|66.80%|19.63%|13.75%|4.77%|1.25|61/308|-2.68%|
|full|fees|market_stock_stop|0.5|4432|19.52%|3.99%|16.68%|-2.21%|0.95|4/308|-11.38%|
|full|spread|market|0.0|744|62.10%|19.38%|12.94%|-0.81%|0.96|2/308|-10.92%|
|full|spread|market_stock|0.0|753|62.42%|18.74%|12.66%|-0.60%|0.96|3/308|-11.43%|
|full|spread|market_stock_stop|0.5|3451|13.76%|7.22%|16.59%|-37.69%|0.08|0/308|-60.38%|
|validation|fees|market|0.0|150|72.67%|14.63%|11.91%|13.62%|1.97|27/60|12.80%|
|validation|fees|market_stock|0.0|148|70.27%|13.48%|12.58%|13.86%|1.97|29/60|16.45%|
|validation|fees|market_stock_stop|0.5|846|20.45%|3.72%|15.75%|1.98%|1.04|7/60|-2.30%|
|validation|spread|market|0.0|150|68.67%|14.17%|10.79%|8.28%|1.56|17/60|4.28%|
|validation|spread|market_stock|0.0|148|66.22%|13.16%|11.55%|8.73%|1.58|20/60|8.06%|
|validation|spread|market_stock_stop|0.5|1087|15.36%|4.86%|15.32%|-31.87%|0.52|1/60|-50.59%|
|test|fees|market|0.0|129|59.69%|17.36%|11.92%|-0.74%|0.97|8/56|-6.63%|
|test|fees|market_stock|0.0|137|63.50%|18.51%|11.46%|0.85%|1.04|8/56|-5.48%|
|test|fees|market_stock_stop|0.5|914|16.52%|3.66%|18.34%|-3.24%|0.95|12/56|-9.39%|
|test|spread|market|0.0|129|55.81%|16.55%|11.65%|-3.22%|0.86|8/56|-10.20%|
|test|spread|market_stock|0.0|137|59.12%|17.22%|11.28%|-1.78%|0.92|7/56|-9.13%|
|test|spread|market_stock_stop|0.5|1034|13.54%|3.95%|17.14%|-22.45%|0.69|1/56|-34.95%|