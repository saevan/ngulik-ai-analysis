# WR entry levers after fixed 0.5 ATR stop

Secondary Choppy Range Escape10 only; market proxy ER20<0.30. Primary/AFL unchanged. One entry lever at a time; original LLV10/fade2 exits plus fixed entry0.5ATR Close stop, next tradable Open. Stock ER minimum does not change market choppy eligibility. Filters use completed signal bar, one bar lag. Prefix checks and original full baseline equity regression passed.

Rp1bn, ten slots,10%prior closing equity per new position cash capped, compounding. Buy0.15%/sell0.25%. Spread stress1tick eachside with modern IDX grid and100share lots; counterfactual, not historical quotes. Same selected universe/data limitations as original research.

Ten training configurations2000-2015; frozen selection and baseline tested2016-2020,2021-2025 and full. Selection and pass status in PLAN/FROZEN.json. Adaptive research on previously seen history, not independent validation. Monthly record = any day with closing equity above all previous history/initial capital within each fresh-start test window. Sideways equivalent annualizes attributed returns on disjoint sideways dates; not a standalone portfolio CAGR.

| Period | Cost | Lever | Value | Trades | WR | Avg loss | Avg win | CAGR | PF money | Records | Sideways equivalent |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|train|fees|baseline|0.0|1608|24.13%|4.15%|19.24%|12.05%|1.25|43/192|0.92%|
|train|fees|sma|30.0|1549|24.02%|4.17%|19.14%|11.42%|1.23|41/192|1.55%|
|train|fees|sma|100.0|1364|23.39%|4.03%|18.98%|9.36%|1.20|37/192|1.35%|
|train|fees|stock_er|0.3|975|25.13%|4.16%|19.20%|9.62%|1.35|35/192|7.66%|
|train|fees|stock_er|0.5|419|27.68%|4.26%|20.87%|6.55%|1.66|26/192|8.15%|
|train|fees|close_location|0.75|1417|24.63%|4.11%|19.18%|11.67%|1.26|42/192|3.17%|
|train|fees|close_location|0.9|1179|23.92%|4.19%|20.36%|11.07%|1.31|39/192|4.96%|
|train|fees|extension|0.5|1043|23.59%|3.75%|20.32%|11.21%|1.38|35/192|7.76%|
|train|fees|extension|1.0|1348|23.81%|3.86%|19.34%|12.25%|1.32|41/192|7.56%|
|train|fees|cost|16.0|729|19.20%|4.45%|19.92%|0.16%|1.01|13/192|-3.14%|
|validation|fees|baseline|0.0|822|20.80%|3.93%|16.93%|3.73%|1.07|10/60|-7.08%|
|validation|fees|stock_er|0.5|224|22.32%|4.29%|22.67%|6.76%|1.45|15/60|10.09%|
|validation|spread|baseline|0.0|907|17.31%|4.39%|17.72%|-10.73%|0.83|6/60|-32.37%|
|validation|spread|stock_er|0.5|227|17.62%|4.72%|25.38%|1.55%|1.09|8/60|0.60%|
|test|fees|baseline|0.0|970|17.63%|3.94%|16.81%|-6.07%|0.91|4/56|-7.07%|
|test|fees|stock_er|0.5|322|22.98%|4.61%|21.80%|9.62%|1.39|12/56|14.64%|
|test|spread|baseline|0.0|1048|15.55%|4.43%|17.58%|-21.31%|0.73|3/56|-30.91%|
|test|spread|stock_er|0.5|334|19.76%|5.13%|21.60%|0.33%|1.01|2/56|-0.28%|
|full|fees|baseline|0.0|3385|21.45%|4.04%|18.13%|6.84%|1.08|45/308|-2.79%|
|full|fees|stock_er|0.5|965|24.87%|4.39%|21.36%|6.97%|1.47|48/308|9.60%|
|full|spread|baseline|0.0|3657|17.86%|4.54%|18.52%|-8.02%|0.90|10/308|-26.62%|
|full|spread|stock_er|0.5|994|20.72%|5.01%|22.29%|1.77%|1.10|12/308|-0.13%|