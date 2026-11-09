# Indikator mean reversion klasik (RSI dan lainnya) sebagai Logic 2 (9 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `mr_indicator_grid.py`. Hasil: `results_all.csv`, `summary.csv`.

Setup:
- 12 indikator (RSI14 < 30, RSI14 kembali > 30, RSI2 < 5, RSI3 < 10, Stochastic, Bollinger bawah, kembali di atas
  Bollinger, Williams %R, CCI, IBS, z-score, MFI) × 2 entry × 3 exit × 2 cakupan (sideways / semua hari) = 144 sel.
- Universe realistis, biaya B, 2000–2025.08.

## Hasil
- Sideways: 0 dari 72 sel bersih > 0, baik di 2000–25, di periode latih, maupun di periode uji (t ≥ 2).
  - Bersih −0,67…−1,74% per trade (median −1,12%).
  - Rata-rata sinyal vs hari acak: −0,08 poin, artinya lebih buruk dari acak.
- Semua hari: juga 0 dari 72. Rata-rata sinyal vs acak +0,01 poin.
- Sel terbaik per indikator saat sideways (semuanya dengan buy limit):

| Indikator | WR | WR impas | Menang / kalah | Kotor | Bersih | Acak |
|---|---|---|---|---|---|---|
| IBS < 0,2 | 55% | 64% | +3,8% / −4,4% | +0,14% | −0,67% | −0,85% |
| Close < Bollinger bawah | 57% | 61% | +4,7% / −5,0% | +0,48% | −0,72% | −0,91% |
| RSI3 < 10 | 59% | 62% | +4,6% / −5,2% | +0,59% | −0,72% | −1,08% |
| RSI14 < 30 | 59% | 62% | +8,0% / −10,7% | +0,28% | −1,00% | −0,91% |
| RSI2 < 5 | 57% | 64% | +4,4% / −5,2% | +0,22% | −0,97% | −0,98% |

- Pilihan latih (IBS < 0,2 + limit + exit Close > SMA5): uji −0,40% (t −2,4), 0/4 subperiode. GAGAL.

## Kesimpulan
- RSI dan indikator mean reversion klasik lain tidak membawa keunggulan saat sideways: rata-ratanya tidak lebih baik
  dari beli di hari acak.
- Kotor terbaik hanya +0,6% per trade, di bawah biaya 0,9%.
- Ini bentuk ke-10 mean reversion long-only harian yang gagal.
