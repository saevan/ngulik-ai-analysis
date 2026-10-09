# New entries with opportunity floor and fixed exit

Secondary entry research; baseline Range Escape10; market proxy ER20<0.30. Primary/AFL unchanged. Entry family changes; common cost8 eligibility; original LLV10/fade2 exits plus fixed entry0.5ATR Close stop, next tradable Open. No stock ER filter. Filters use completed signal bar, one bar lag. Prefix checks and original full baseline equity regression passed.

Rp1bn, ten slots,10%prior closing equity per new position cash capped, compounding. Buy0.15%/sell0.25%. Spread stress1tick eachside with modern IDX grid and100share lots; counterfactual, not historical quotes. Same selected universe/data limitations as original research.

Eleven training configurations with spread2000-2015; frozen selection and baseline tested2016-2020,2021-2025 and full. Selection and pass status in PLAN/FROZEN.json. Adaptive research on previously seen history, not independent validation. Monthly record = any day with closing equity above all previous history/initial capital within each fresh-start test window. Sideways equivalent annualizes attributed returns on disjoint sideways dates; not a standalone portfolio CAGR.

| Period | Cost | Lever | Value | Trades | WR | Avg loss | Avg win | CAGR | PF money | Records | Sideways equivalent |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|train|spread|baseline|10|1726|19.52%|4.69%|19.24%|-3.42%|0.93|10/192|-23.34%|
|train|spread|short_breakout|3|2201|19.26%|4.77%|17.81%|-7.85%|0.84|2/192|-25.21%|
|train|spread|short_breakout|5|2052|18.18%|4.70%|19.11%|-6.74%|0.87|4/192|-23.65%|
|train|spread|reclaim_ma|5|2404|19.30%|4.90%|19.93%|-6.31%|0.88|3/192|-32.42%|
|train|spread|reclaim_ma|10|2242|17.84%|4.78%|19.64%|-9.69%|0.76|0/192|-30.97%|
|train|spread|failed_breakdown|5|1321|18.32%|4.85%|16.91%|-8.74%|0.75|1/192|-20.75%|
|train|spread|failed_breakdown|10|965|17.72%|5.02%|16.41%|-8.62%|0.67|1/192|-17.21%|
|train|spread|pullback|20|2126|20.18%|4.68%|19.99%|-0.68%|0.99|17/192|-22.27%|
|train|spread|pullback|50|2014|20.31%|4.58%|19.10%|-0.48%|0.99|19/192|-19.26%|
|train|spread|channel_flip|5|1719|18.85%|4.76%|18.35%|-5.85%|0.88|8/192|-23.71%|
|train|spread|channel_flip|10|1163|19.09%|4.85%|18.09%|-4.42%|0.85|2/192|-19.62%|
|validation|fees|baseline|10|822|20.80%|3.93%|16.93%|3.73%|1.07|10/60|-7.08%|
|validation|fees|pullback|20|871|22.62%|3.80%|17.26%|12.74%|1.24|16/60|-0.79%|
|validation|spread|baseline|10|907|17.31%|4.39%|17.72%|-10.73%|0.83|6/60|-32.37%|
|validation|spread|pullback|20|984|17.58%|4.21%|18.40%|-8.08%|0.88|8/60|-32.13%|
|test|fees|baseline|10|970|17.63%|3.94%|16.81%|-6.07%|0.91|4/56|-7.07%|
|test|fees|pullback|20|1006|19.09%|3.89%|18.05%|0.54%|1.01|6/56|-9.68%|
|test|spread|baseline|10|1048|15.55%|4.43%|17.58%|-21.31%|0.73|3/56|-30.91%|
|test|spread|pullback|20|1176|14.97%|4.32%|17.63%|-22.75%|0.72|3/56|-38.50%|
|full|fees|baseline|10|3385|21.45%|4.04%|18.13%|6.84%|1.08|45/308|-2.79%|
|full|fees|pullback|20|3812|22.46%|3.95%|18.72%|12.13%|1.13|62/308|-0.42%|
|full|spread|baseline|10|3657|17.86%|4.54%|18.52%|-8.02%|0.90|10/308|-26.62%|
|full|spread|pullback|20|4257|18.18%|4.47%|19.06%|-6.36%|0.94|17/308|-27.57%|