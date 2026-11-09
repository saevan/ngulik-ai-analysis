# Grid search Logic 2 sideways: apa yang meramalkan pantulan? (9 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `sideways_bounce_grid.py`, `sideways_bounce_holdout.py`. Hasil:
- `results_all.csv`;
- `summary.csv`;
- `holdout_1996_99.csv`.

Setup:
- Hanya hari pasar sideways, long saja, versi realistis, biaya B 0,9%, 2000–2025.08.
- 4 pemicu (RSI2 < 10, 3 Close turun, 20% bawah range, Close < SMA20 − 1,5 ATR) × 7 filter (tanpa, > SMA200, volume
  kering, ekor bawah, breadth < 30%, ER20 < 0,2, lonjakan volume) × 2 entry (Open besok, limit Close − 0,5 ATR) × 3 exit
  (Close > SMA5, Close > High kemarin, 5 bar) = 168 sel.

## Hasil
- Hanya 1 dari 168 sel yang bersih > 0 di 2000–25, dan itu pun +0,01%. Di periode latih hanya 3 sel yang positif.
- Rata-rata sinyal vs kontrol acak: +0,06 poin. 87/168 sel di atas kontrolnya, sama dengan lempar koin.
- Pilihan latih: 3 Close turun + lonjakan volume + limit + exit Close > High kemarin.
  - latih +0,50% (t 1,0);
  - uji 2016–25: −0,62% (t −0,95), 2/4 subperiode positif;
  - GAGAL.
- WR 44–62%; WR impas 54–65%.
- Filter yang paling memperbaiki kotor (rata-rata semua sel): breadth < 30% (+0,34%), lonjakan volume (+0,34%),
  > SMA200 (+0,20%). Semuanya jauh di bawah biaya 0,9%.
- Dengan fee pengguna 0,6% tanpa slippage, sebagian sel kecil positif (sampai +0,64%). Tapi ini hanya informasi, karena
  slippage nyata tidak nol.

## Temuan yang tidak lolos: breadth < 30% + limit entry
4 sel uji dengan bersih > 0 dan t ≥ 2 semuanya dari keluarga ini (sekitar 4 sel memang diharapkan lolos karena kebetulan).

| T1/T2 + breadth < 30% + limit, exit Close > SMA5 | 1996–99 (holdout) | 2000–07 | 2008–15 | 2016–20 | 2021–25 |
|---|---|---|---|---|---|
| RSI2 < 10 | −1,65% | −0,95% | −1,05% | +0,89% | +1,42% |
| 3 Close turun | −0,99% | −1,68% | −0,31% | +1,18% | +1,12% |

Positif hanya sejak 2016, dan rugi di 1996–2015. Holdout 1996–99 tidak mendukung (sampelnya kecil, 66–100 trade). Ini
bukan bukti; paling jauh hipotesis untuk forward test sesudah 2025-08 (data belum bisa diunduh).

## Kesimpulan
- Grid search 168 kombinasi dengan data harian (harga, volume, candle, breadth) tidak menemukan Logic 2 sideways yang
  lolos.
- Indikator yang diuji hanya membawa informasi pantulan sekitar 0,2–0,3% per trade. Biaya 0,9% terlalu besar.
