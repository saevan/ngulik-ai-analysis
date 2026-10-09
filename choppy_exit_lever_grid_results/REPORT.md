# Crossed breakout and ER exit lever experiment

Entry fixed inverse market-only choppy: Close<SMA30 OR fade2, nextOpen, marketER20<.30. Exit Close>priorHHVHigh(N), N5/20/40, optionally stockER20>=0.30/0.50. ER0 means no exit ER filter, not an optimized value. Holding unrestricted, no new stop. All exits next tradable Open. Market entry ER stays unchanged; only STOCK exit ER threshold varied.

Nine configurations x two costs, full2000-2025, no selection or parameter adoption. Rp1bn/10slots/compounding/buy.15%sell.25%;spreadmodernIDX1tickeachside100shares counterfactual. Descriptive within-dataset effects and interactions, not independent validation. Prefix checks and original HHV20/ER.3 baseline equity regression. Primary/AFL unchanged. Sideways equivalent = attributed daily return annualization, not standalone CAGR.

| Period | Cost | Lever | Value | Trades | WR | Avg loss | Avg win | CAGR | PF money | Records | Sideways equivalent |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|full|fees|5|0.0|3284|62.12%|8.47%|5.30%|-1.32%|0.96|3/308|-6.04%|
|full|fees|5|0.3|953|62.85%|17.14%|13.68%|5.32%|1.21|59/308|-0.51%|
|full|fees|5|0.5|410|66.34%|22.43%|22.15%|9.18%|1.65|80/308|-2.64%|
|full|fees|20|0.0|1234|66.69%|15.58%|9.88%|3.64%|1.18|34/308|-2.86%|
|full|fees|20|0.3|744|66.13%|19.99%|14.20%|4.79%|1.23|63/308|-1.66%|
|full|fees|20|0.5|392|66.58%|23.52%|23.12%|9.09%|1.65|76/308|-2.50%|
|full|fees|40|0.0|721|66.71%|20.31%|13.80%|4.25%|1.23|38/308|-2.74%|
|full|fees|40|0.3|610|65.90%|21.13%|15.53%|4.89%|1.29|52/308|-0.49%|
|full|fees|40|0.5|377|68.17%|23.66%|23.81%|10.48%|1.75|82/308|-1.68%|
|full|spread|5|0.0|3237|50.97%|8.43%|4.68%|-21.10%|0.22|0/308|-37.47%|
|full|spread|5|0.3|953|58.97%|17.20%|12.26%|-2.28%|0.88|0/308|-13.12%|
|full|spread|5|0.5|410|63.41%|22.30%|20.41%|5.45%|1.42|57/308|-8.75%|
|full|spread|20|0.0|1234|61.02%|14.90%|8.64%|-5.50%|0.68|1/308|-17.70%|
|full|spread|20|0.3|744|62.10%|19.38%|12.94%|-0.81%|0.96|2/308|-10.92%|
|full|spread|20|0.5|392|63.52%|23.06%|21.58%|5.68%|1.43|50/308|-8.06%|
|full|spread|40|0.0|721|63.80%|20.08%|12.16%|-1.25%|0.93|1/308|-11.69%|
|full|spread|40|0.3|610|63.93%|21.48%|13.85%|0.29%|1.02|12/308|-8.15%|
|full|spread|40|0.5|377|65.52%|23.16%|22.00%|7.13%|1.55|60/308|-7.12%|