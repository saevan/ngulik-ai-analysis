# Biaya broker pengguna dan dana menganggur V2 (30 Okt 2026) – `costs_idle_check.py`
**Biaya.**
- Skenario B kita = fee 0,15% beli + 0,25% jual (0,40%) ditambah perkiraan slippage 0,25% per sisi (0,50%) = 0,90%
  pulang-pergi.
- Fee broker pengguna (0,25% / 0,35% = 0,60%) lebih mahal dari asumsi fee kita. Selisih "0,9%" berasal dari slippage
  (spread/fraksi harga dan dampak order), bukan fee.

| Skenario (pulang-pergi) | V2 realistis | V2 tanpa batasan | Swinger ideal |
|---|---|---|---|
| B kita (0,90%) | 20,7% / 63 / −46% | 50,6% / 135 / −27% | 102,0% / 232 / −21% |
| Fee pengguna tanpa slippage (0,60%) | 23,6% / 70 / −46% | 50,3% / 138 / −28% | 109,6% / 238 / −20% |
| Fee pengguna + slippage 0,10%/sisi (0,80%) | 21,4% / 69 / −46% | 51,3% / 135 / −27% | 104,5% / 235 / −21% |
| Fee pengguna + slippage 0,25%/sisi (1,10%) | 19,2% / 56 / −47% | 48,3% / 131 / −31% | 97,2% / 228 / −22% |

Format: CAGR / bulan rekor / MDD.

**Dana menganggur V2 (skenario B).**

| | Uptrend | Sideways | Downtrend | Rata-rata |
|---|---|---|---|---|
| Realistis | 17% | 38% | 62% | 34% |
| Tanpa batasan | 20% | 37% | 59% | 34% |

Bila kas menganggur diparkir di pasar uang 3 / 4 / 5% per tahun:
- realistis 20,7% → 21,9 / 22,3 / 22,6%;
- tanpa batasan 50,6% → 52,2 / 52,7 / 53,2%;
- MDD sedikit membaik.
