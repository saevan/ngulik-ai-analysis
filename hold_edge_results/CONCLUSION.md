# Apakah "memegang untung lebih lama" keunggulan kita, dan bisakah dipakai mengejar Swinger ideal? (17 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `hold_edge.py`. Hasil: `return_by_hold.csv`,
`max_hold_counterfactual.csv`, `swinger_after_exit.csv`, `rule_test.csv`, `trades_H1.csv`, `trades_H2.csv`.
Versi realistis, biaya B, 2000-01-01..2025-08-15.

## 1. Dari mana uang V2 (jumlah return per trade, bobot sama)
| Lama pegang | V2: porsi trade / WR / rata-rata / porsi total | Swinger ideal: porsi trade / WR / rata-rata / porsi total |
|---|---|---|
| ≤ 10 bar | 19% / 7% / −6,5% / −17% | 40% / 17% / −2,0% / −13% |
| 11–30 | 41% / 29% / −1,5% / −9% | 43% / 63% / +5,8% / +38% |
| 31–60 | 19% / 76% / +11,9% / +31% | 12% / 88% / +23,6% / +45% |
| 61–120 | 10% / 45% / +4,1% / +6% | 4% / 91% / +48,2% / +27% |
| > 120 | 11% / 79% / +57,1% / **+89%** | 0,2% / 75% / +52% / +2% |
Semua trade > 120 bar adalah modul bulanan (82 trade, jumlah +46,8 dari total sekitar +52,7). Trade breakout paling
lama 116 bar dan untungnya di 31–120 bar (+29,8). Trade ≤ 30 bar (60% trade) rugi.

## 2. Batas waktu pegang (counterfactual)
Catatan penyimpangan dari PLAN: `max_hold` hanya berlaku untuk posisi breakout (posisi bulanan memakai exit sendiri;
opsi `extra_main_exits` akan mengganti seluruh exit bulanan, jadi tidak dipakai). Hasil: tanpa batas 20,7% / MDD −46%;
120 bar sama; 60 bar 22,5% / −43%; 40 bar 21,4% / −42%; 20 bar 20,8% / −45%, WR 47%. Memotong breakout tidak merugikan;
yang dipegang sangat lama dan bernilai adalah modul bulanan.

## 3. Apa yang ditinggalkan Swinger sesudah exit
Close 20 / 60 hari sesudah exit Swinger: rata-rata +1,8% / +5,2%, median 60 hari +0,7%. Hanya 18% trade yang sahamnya
≥ 20% lebih tinggi 60 hari kemudian (29% sempat ≥ 20% di dalam 60 hari). Sebagian besar ayunan Swinger memang selesai.

## 4. Uji aturan: entry ala Swinger (A1, dieksekusi nyata) + exit pegang lama
| | CAGR | MDD | 2000–07 | 2008–15 | 2016–20 | 2021–25 | Trade/th | WR | Payoff | Median bar |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 + exit swing (lama) | 4,9% | −69% | +20,2% | −3,6% | −1,8% | +2,7% | 86 | 34% | 2,4 | 13 |
| A1 + exit Close < SMA30 (H1) | 0,6% | −81% | +14,1% | +2,2% | +0,3% | −21,2% | 100 | 28% | 2,8 | 5 |
| A1 + SMA30 atau trail 15% (H2) | 0,8% | −78% | +15,9% | 0,0% | +1,1% | −19,6% | 100 | 28% | 2,8 | 5 |
| V2 realistis | 20,7% | −46% | +41,6% | +1,8% | +15,4% | +27,1% | 28 | 41% | 3,5 | 25 |
| Swinger ideal | 102,0% | −21% | +150% | +88% | +90% | +70% | 126 | 49% | 4,9 | 13 |
Tidak ada varian yang menjanjikan. 39% entry A1 terjadi saat Close masih di bawah SMA30 dan langsung terjual ≤ 2 bar
(−1,7% rata-rata); entry di atas SMA30 hanya +1,5% per trade (median 13 bar, WR 33%).

## Kesimpulan
- Benar, kita punya keunggulan memegang lama, tetapi sempit: 11% trade (modul bulanan, > 120 bar) membuat sekitar 89%
  dari jumlah return trade V2, sekitar 3 trade per tahun, dan sangat bergantung pada beberapa tren raksasa (mis. WIFI
  2025) di data survivor.
- Keunggulan ini berbeda jenis dengan Swinger: Swinger untung dari banyak ayunan 11–120 bar plus bonus fill; kita dari
  sedikit tren panjang. Ayunan Swinger kebanyakan sudah selesai saat ia keluar (median +0,7% 60 hari sesudahnya).
- Memasang exit pegang lama pada entry ala Swinger justru memperburuk (CAGR 0,6–0,8% vs 4,9%). Jadi keunggulan ini tidak
  bisa dipakai untuk menutup celah frekuensi Swinger. Paling jauh ia bisa diperbesar di tempatnya sendiri (modul
  bulanan), yang sebelumnya diuji dengan hasil campuran (lookback 81 kombinasi: noisy; jatah 35% sudah dipilih).
