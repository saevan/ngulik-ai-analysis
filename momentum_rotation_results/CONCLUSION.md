# Rotasi momentum sebagai Logic 2 untuk dana idle saat sideways (13 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil (addendum kontrol kedua ditambahkan sesudah uji satu sel, sebelum grid).
Kode: `momentum_rotation.py`. Hasil: `results.csv` (144 sel), `ew_benchmark.csv`, `run.log`.

Setup:
- Setiap akhir bulan / minggu, pegang N saham dengan momentum tertinggi di universe realistis (likuid point-in-time +
  filter data basi, order ≤ 25% ADV20). Hanya momentum positif.
- Skor: MOM12-1 / mom120 / mom60. Filter: tanpa / ER20 ≥ 0,2. Gate beli: pasar sideways saja / bukan turun / selalu
  (konteks). N = 5 / 10. Exit: hanya saat rebalance (keluar dari peringkat 2N) / ditambah Close < SMA30.
- 144 sel, 96 di antaranya ber-gate (kandidat Logic 2). Biaya B, Rp1 M, 2000–2025.08.
- Kontrol: peringkat acak diundi ulang tiap rebalance (pra-registrasi) dan peringkat acak tetap per seed (addendum),
  5 seed masing-masing. Pembanding konteks: equal-weight semua saham eligible (rebalance bulanan) dan parkir 4%/th.

## Hasil (return per tahun pada hari pasar sideways)
| | Sel ber-gate (96) |
|---|---|
| Return sideways > 0 | 21 |
| Return sideways ≥ 4% (hurdle parkir) | 9 |
| Median return sideways | −4,5%/th |
| Di atas kontrol acak (keduanya) | 96 / 96 |
| t selisih vs kontrol ≥ 2 (uji 2016–25) | 35 |
| Negatif di 2008–15 | 96 / 96 |
| Negatif di 2016–20 | 75 / 96 |
| Lolos aturan uji | **0** |

Faktor (rata-rata return sideways sel ber-gate): bulanan −1,5% vs mingguan −13,1%; exit rebalance saja −2,3% vs
+ SMA30 −12,3%; tanpa filter −4,5% vs ER20 ≥ 0,2 −10,1%; N 5 −7,1% vs 10 −7,5%; gate bukan-turun −5,7% vs sideways
saja −8,9%. Perbedaan skor kecil (−6,7…−7,8%).

Keluarga terbaik (bulanan, exit rebalance saja, tanpa filter, N 5):

| Skor | Gate | CAGR | MDD | Sideways/th (t) | Naik/th | Turun/th | Latih sideways | Uji sideways (t) | t vs kontrol | Sub-periode + | Trade/th | WR | Menang / kalah |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MOM12-1 | sideways (pilihan latih) | 15,5% | −62% | +6,2% (1,2) | +35,8% | +13,4% | +4,1% | +9,2% (1,0) | 1,3 | 3/4 | 7,4 | 54% | +41% / −17% |
| MOM12-1 | bukan turun | 15,0% | −65% | +5,5% (1,1) | +34,2% | +17,1% | +0,6% | +13,0% (1,3) | 1,6 | 3/4 | 8,0 | 55% | +39% / −17% |
| mom120 | sideways | 14,4% | −65% | +5,2% (1,1) | +31,7% | +19,3% | −4,0% | +20,0% (1,7) | 2,6 | 2/4 | 10,5 | 49% | +40% / −16% |
| mom120 | bukan turun | 19,2% | −59% | +8,4% (1,5) | +42,0% | +20,2% | +2,1% | +18,3% (1,7) | 2,2 | 3/4 | 12,3 | 49% | +42% / −15% |
| mom60 | sideways | 10,4% | −55% | +1,5% (0,6) | +20,0% | +35,0% | −7,5% | +15,9% (1,5) | 2,3 | 2/4 | 16,2 | 43% | +27% / −12% |
| mom60 | bukan turun | 19,2% | −55% | +7,6% (1,4) | +36,8% | +38,9% | +1,0% | +18,1% (1,7) | 2,2 | 3/4 | 20,1 | 45% | +29% / −12% |

Pilihan latih (MOM12-1, tanpa filter, sideways saja, N 5, bulanan, exit rebalance saja):
- uji 2016–25: sideways +9,2%/th, t 0,99 (syarat ≥ 2) → GAGAL;
- kontrol −4,4% / −1,7%; 3/4 sub-periode positif; modal terpakai saat sideways 88%;
- sub-periode sideways: +14,6% / −3,5% / +3,4% / +14,8%.

Konteks:
- Equal-weight semua saham eligible (bulanan): sideways −0,1%/th, CAGR 4,1%, MDD −43%. Pasar sideways memang datar
  rata-rata; semua return rotasi di atas itu berasal dari pemilihan saham.
- Sel tanpa gate (selalu beli, wilayah Logic 1): CAGR terbaik 18,5% (mom120, N 5, bulanan), MDD −62%; median CAGR
  2,8%. Jauh di bawah V2 realistis (20,7%, MDD −46%).
- V2 realistis pada hari sideways: +9,7%/th dengan modal terpakai 62% (`logic_a_swing5_results/v2_compare.csv`).

## Kesimpulan
- Sifat momentum relatifnya nyata: peringkat momentum mengalahkan pemilihan acak di 96/96 sel, dan di 35 sel t selisihnya
  ≥ 2. Ini konsisten dengan `market_properties_v2` (MOM12-1 top–bottom +1,44%/bulan).
- Tetapi sebagai Logic 2 sideways, ukurannya terlalu kecil dan tidak stabil: median sel −4,5%/th, semua sel negatif di
  2008–15, sel terbaik pun +6…8%/th dengan t 1,1…1,5 dan MDD −55…−65%. Parkir 4%/th mengalahkan sebagian besar sel
  tanpa risiko.
- Rebalance mingguan, exit SMA30, dan filter ER memperburuk: keuntungan momentum datang dari memegang lama (median
  81–120 bar); setiap tambahan churn dimakan biaya 0,9%.
- Tidak ada sel yang lolos aturan uji. Langkah 2 (integrasi dengan V2) tidak dijalankan.
- Catatan: data hanya 100 saham Kompas100 saat ini (survivor), yang membuat momentum terlihat lebih baik dari aslinya.
  Hasil nyata kemungkinan lebih rendah lagi.
- Status: momentum relatif bukan Logic 2 yang berdiri sendiri. Nilainya hanya sebagai urutan prioritas pemilihan saham,
  yang sudah dipakai V2 (mom120).
