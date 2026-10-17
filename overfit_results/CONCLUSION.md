# Uji overfitting SK-5 — vonis sesudah verifikasi independen (17 Okt 2026)

Kode `overfit_tests_sk5.py`, `overfit_noise_calibration.py`, `touch_fill_check.py`; engine `backtest_stop_execution.py` (opsi baru `entry_mode='random'`
dan `touch_fill`, default tidak berubah, regresi lulus). Periode 2000-01..2025-08, Rp1 miliar, fee 0,15/0,25% kecuali disebut.
Verifikasi 3 pemeriksa independen: PBO dan Deflated Sharpe dihitung ulang identik; audit kode dan kritik tafsir menemukan masalah di bawah.
Catatan: SK-5 adalah peringkat 1 CAGR train (fee) dari 360 konfigurasi, BUKAN pilihan terdaftar (FROZEN.json memilih HHV10).

## Vonis: tidak lulus secara meyakinkan
1. **Asumsi fill terlalu optimistis (temuan terbesar).** Engine hanya mengisi buy stop bila High > level. Pada 11,3% hari saham High tepat sama
   dengan level HHV5; stop broker terpicu saat harga menyentuh level. Hari "sentuh lalu berbalik" rata-rata −1,1…−1,7% per trade dan dihindari diam-diam.
   | Sistem (full) | High > level | Sentuh = terisi | Sentuh + slippage 0,25% | Sentuh + batas 25% ADV |
   |---|---|---|---|---|
   | SK-5 | 63,2 / 139 / −27 | 44,6 / 107 / −35 | 31,7 / 75 / −44 | 24,7 / 72 / −40 |
   | ER 0,2 + trailing | 66,5 / 172 / −21 | 45,3 / 131 / −36 | 29,7 / 91 / −44 | 25,1 / 81 / −40 |
   | HHV10 (pilihan terdaftar) | 53,4 / 125 / −29 | 41,9 / 100 / −36 | 33,2 / 81 / −47 | 23,4 / 81 / −37 |
   | HHV20 lama (base) | 43,3 / 138 / −18 | 37,1 / 119 / −27 | 32,4 / 105 / −33 | 20,7 / 83 / −27 |
   Dengan fill sentuh, keunggulan channel pendek hampir hilang (median grid ch5/10/20: 39,0/38,5/38,3% vs 55,2/49,2/45,3%), PBO grid naik 0,045 → 0,19,
   dan SK-5 turun dari peringkat 1 ke 5 di train (45,1%). Semua hasil buy stop sebelumnya (kandidat HHV20, Swinger stop order, engine UTS) memakai aturan yang sama.
2. **Parameter spesifik SK-5 tidak lulus.** PBO di pojok HHV5 & 20% = 0,73 (fee) / 0,53; dimensi ER saja 0,69 / 0,79. Peringkat SK-5: train 1, validasi 87,
   tes 2021–25 257/360 (spread1 326/360); korelasi peringkat train→tes 0,11. ER 0,3 terbaik di train tetapi peringkat 7–8 dari 8 di 2016–25 (pergantian rezim).
3. **Uji yang "lulus" hanya bicara tentang keluarga sistem dan memakai null lemah:** PBO grid rendah karena ukuran 20% dan channel 5 mendominasi grid
   (dan karena aturan fill); DSR ≈1 juga untuk konfigurasi terburuk; entry acak (median 15%) bahkan di bawah indeks equal-weight universe yang sama (23,6%).
   Kontrol acak yang memakai filter ER + urutan momentum memberi 35,6% (maks 47%): sekitar separuh selisih berasal dari filter/urutan, bukan pemicu breakout.
4. **Ada alpha terhadap indeks equal-weight universe yang sama:** 3,26%/bulan (t 6,9), beta 0,63 (aturan fill lama). Tetapi semua pembanding berbagi universe survivor.
5. **Survivorship:** universe dibekukan pada saham listing sebelum 2015 → SK-5 2016–25 31,8% (indeks 13,8%, acak −2,8%); listing sebelum 2010 → 2021–25 10,4%
   (indeks 7,3%). Tanpa 20 saham listing ≥2018, SK-5 rugi di 2019 (−10,7%) dan 2023 (−8,5%). Bootstrap p5: full 50,8%, 2016–25 39,0%, 2021–25 23,6%.
6. **Noise harga** (−18%) sebagian besar menguji aturan seri/tie dan biaya perputaran, bukan overfitting.

## Yang masih berdiri
Keluarga breakout + filter ER + urutan momentum mengalahkan entry acak dan indeks equal-weight universe yang sama. Tetapi dengan fill realistis, biaya, dan
batas likuiditas, SK-5 setara/lebih buruk dari HHV20 lama (slippage: 31,7% vs 32,4%; batas 25% ADV: 24,7% vs 20,7% dengan MDD −40% vs −27%).

## Langkah berikut yang paling penting
Uji ulang semua sistem buy stop dengan fill sentuh (+1 tick) sebagai default; universe point-in-time (anggota Kompas100/LQ45 historis termasuk yang delisting);
atau forward test tertutup pada data sesudah 2025-08-15. AFL tidak diubah.
