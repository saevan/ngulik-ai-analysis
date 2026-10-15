# Optimasi CAGR + bulan rekor equity, 15 Oktober 2026

Kode: `optimize_cagr_records.py`. Rencana dan aturan pemilihan dibekukan sebelum validasi (`PLAN.json`, `FROZEN.json`). Semua angka ada di `comparison.csv` (rasio dalam desimal).

Setup tetap sama: Rp1 miliar, 10 slot bersama, 10% equity Close sebelumnya per entry, compounding, long only. Fee beli 0,15% dan jual 0,25%. Stress spread memakai 1 tick per sisi dan lot 100. Entry Breakout HHV20 + ER saham20 ≥0,3. Exit Close < SMA30 atau fading k×ATR dari Open bar berjalan. Fill di next tradable Open, tanpa hold cap.

Tuas yang diuji (14 konfigurasi):
- gate pasar: none / ER pasar ≥0,3 / uptrend saja
- urutan entry saat slot penuh: alfabet / ER saham bar sinyal tertinggi
- fading: 2 / 5
- modul inverse choppy: on/off

Pemilihan dilakukan di train 2000–2015 dengan skenario spread. Syaratnya: CAGR > baseline gabungan DAN bulan rekor ≥ baseline. Dari yang memenuhi, dipilih CAGR tertinggi.

## Train (spread)

- Kedua konfigurasi dengan inverse paling buruk: alfabet 4,64% dengan 26 rekor, urutan ER −1,97% dengan 6 rekor.
- Semua konfigurasi tanpa inverse yang memakai gate pasar (ER atau uptrend) menghasilkan 20,6–25,5% dengan 47–53 rekor. Tanpa gate hasilnya 12,2–18,9%.
- Fade 5 selalu lebih baik daripada fade 2 di train.
- Urutan ER tidak konsisten lebih baik daripada alfabet.

Konfigurasi yang dibekukan: gate ER pasar, urutan alfabet, fade 5, tanpa inverse (train 25,54%, 53 rekor).

## Evaluasi

| Window | Biaya | Konfigurasi | CAGR | Rekor | MDD | WR | Payout | Hold | Trade |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| validation 2016–20 | fees | baseline gabungan | 23.16% | 22/60 | -37.06% | 60.64% | 1.46 | 49.4 | 249 |
| validation 2016–20 | fees | **frozen** | 21.59% | 24/60 | -27.42% | 40.36% | 3.11 | 25.9 | 280 |
| validation 2016–20 | fees | original tanpa gate f2 | 30.88% | 22/60 | -25.52% | 38.66% | 2.80 | 19.6 | 538 |
| validation 2016–20 | spread | baseline gabungan | 14.79% | 15/60 | -39.00% | 55.02% | 1.42 | 49.4 | 249 |
| validation 2016–20 | spread | **frozen** | 14.02% | 18/60 | -33.42% | 36.88% | 2.87 | 25.8 | 282 |
| validation 2016–20 | spread | original tanpa gate f2 | 15.51% | 13/60 | -31.86% | 35.25% | 2.54 | 19.5 | 539 |
| test 2021–25 | fees | baseline gabungan | 5.11% | 10/56 | -49.79% | 48.82% | 1.34 | 53.5 | 211 |
| test 2021–25 | fees | **frozen** | 6.95% | 5/56 | -24.90% | 37.69% | 2.19 | 22.7 | 268 |
| test 2021–25 | fees | original tanpa gate f2 | 19.79% | 12/56 | -27.47% | 36.31% | 2.45 | 19.7 | 504 |
| test 2021–25 | spread | baseline gabungan | 1.02% | 10/56 | -54.33% | 46.92% | 1.27 | 53.5 | 211 |
| test 2021–25 | spread | **frozen** | 1.57% | 4/56 | -27.82% | 35.07% | 2.03 | 22.7 | 268 |
| test 2021–25 | spread | original tanpa gate f2 | 7.63% | 8/56 | -42.32% | 33.13% | 2.35 | 19.7 | 504 |
| full 2000–25 | fees | baseline gabungan | 15.80% | 81/308 | -58.38% | 55.11% | 1.41 | 47.7 | 1321 |
| full 2000–25 | fees | **frozen** | 28.12% | 91/308 | -32.97% | 43.15% | 3.32 | 26.5 | 1284 |
| full 2000–25 | fees | original tanpa gate f2 | 33.65% | 108/308 | -34.90% | 40.84% | 2.82 | 20.4 | 2392 |
| full 2000–25 | spread | baseline gabungan | 5.51% | 36/308 | -74.37% | 50.49% | 1.29 | 47.7 | 1321 |
| full 2000–25 | spread | **frozen** | 18.90% | 70/308 | -46.43% | 40.25% | 2.87 | 26.5 | 1287 |
| full 2000–25 | spread | original tanpa gate f2 | 13.37% | 52/308 | -52.64% | 36.19% | 2.44 | 20.4 | 2396 |

## Kesimpulan

1. **Observasi yang konsisten:** mematikan modul inverse menaikkan CAGR, menambah bulan rekor, dan memangkas MDD dibanding baseline gabungan. Ini berlaku di train dan full untuk kedua biaya. Di validation hasilnya hampir sama. Di test, CAGR frozen sedikit lebih tinggi, tetapi bulan rekornya lebih sedikit (4–5 vs 10).
2. **Frozen belum terbukti lebih baik daripada original tanpa gate di periode sesudah train.** Di validation spread hasilnya kalah tipis dalam CAGR tetapi menang bulan rekor. Di test kalah di keduanya. Keunggulan full spread (18,90% vs 13,37%) sebagian besar berasal dari periode train yang dipakai untuk memilih.
3. Ini bukan holdout independen, karena data sudah pernah dieksplorasi dan ada 14 konfigurasi (risiko multiple testing). Tidak ada perubahan AFL/default yang diadopsi.
4. Periode 2021–2025 lemah untuk semua varian setelah spread. Jumlah rekornya rendah (4–10 dari 56 bulan) karena puncak equity sebelumnya belum terlampaui lama.

Regresi: baseline gabungan dan original fade2 untuk window full mereproduksi persis kurva yang sudah dipublikasikan sebelumnya (rtol 1e-10). Uji prefix causality untuk entry dan priority builder juga lulus. 20 unit tests lulus sesudah penambahan `priority_builder` (default None = perilaku lama).
