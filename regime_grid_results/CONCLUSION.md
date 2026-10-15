# Grid per rezim (naik / turun / choppy) untuk mendekati Swinger ideal (15 Oktober 2026)

Kode `regime_grid_search.py`. Sinyal Close i, fill Open(i+1); statistik per trade, satu posisi per saham, fee 0,15/0,25%. Rezim di bar sinyal dari `regime_proxy` (ER20 proxy equal-weight, lag satu bar; uptrend/downtrend = ER ≥0,3 dengan arah 20 bar naik/turun; choppy = ER <0,3). 270 konfigurasi: channel 20/55 × filter kejar (skip bila Close sinyal > level + 0,5/1 ATR) × stop (Close ≤ entry − 1,5/2/3 ATR, atau Close < LLV5/LLV10 Low sebelum entry) × aktivasi trailing (+0,5/1/2 ATR) × lebar trailing (1,5/2/2,5 ATR). Pilih per rezim di saham 2000–2015 (jumlah kriteria 1–5, lalu mean). Saham 2016–2025 dan crypto = hold-out.

Pilihan beku: semua rezim channel 55 + stop LLV10 + trailing 2,5 ATR; aktivasi +1 ATR (naik), +2 ATR dan filter kejar 1 ATR (turun), +0,5 ATR (choppy).

## Hasil (2016–2025 hold-out, saham)

| Rezim | Sistem | Trade | Mean | WR | Avg win | Avg loss | Payout | Bar menang/kalah | Lolos 1–5 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| naik | Regime-switch | 683 | 4.39% | 50.5% | 17.6% | 9.1% | 1.94 | 35 / 27 | 4 |
| naik | Base HHV55 | 673 | 3.86% | 49.3% | 17.9% | 9.8% | 1.83 | 33 / 24 | 3 |
| naik | Swinger ideal | 392 | 6.77% | 48.5% | 16.8% | 2.6% | 6.38 | 25 / 10 | 4 |
| turun | Regime-switch | 47 | 8.03% | 38.3% | 35.6% | 9.1% | 3.91 | 46 / 33 | 4 |
| turun | Base HHV55 | 60 | 1.31% | 33.3% | 22.2% | 9.1% | 2.43 | 39 / 21 | 4 |
| turun | Swinger ideal | 186 | 3.57% | 45.2% | 12.0% | 3.4% | 3.55 | 23 / 9 | 4 |
| choppy | Regime-switch | 852 | 2.32% | 43.1% | 16.6% | 8.5% | 1.96 | 36 / 23 | 3 |
| choppy | Base HHV55 | 855 | 2.64% | 46.8% | 16.6% | 9.6% | 1.72 | 38 / 24 | 3 |
| choppy | Swinger ideal | 874 | 4.35% | 46.9% | 12.9% | 3.2% | 4.02 | 23 / 9 | 4 |
| semua | Regime-switch | 1582 | 3.39% | 46.1% | 17.5% | 8.7% | 2.01 | 36 / 25 | 4 |
| semua | Base HHV55 | 1588 | 3.10% | 47.4% | 17.3% | 9.7% | 1.79 | 36 / 24 | 3 |

Train 2000–2015 (semua rezim): regime-switch mean 5,82%, WR 53,8%, payout 2,17, 5/5; base 5,73%, 53,9%, 2,04, 5/5. Crypto 2017–2025: regime-switch 4/5 (bar kalah > bar menang), base 5/5.

## Batas yang terlihat di grid (frontier)
- Stop lebih ketat → avg loss turun, tetapi WR dan mean juga turun di semua rezim dan kedua periode. Contoh choppy 2016–25 rata-rata grid: stop 1,5 ATR → loss 6,2%, WR 34,6%, mean 0,98%; stop LLV10 → loss 9,3%, WR 46,8%, mean 2,09%.
- Avg loss terkecil yang tercapai 4,9–5,6% (Swinger ideal 2,6–4,0%).
- Mean terbaik di grid (dilihat pasca-freeze) di 2016–25: choppy 3,38%, naik 4,66% — di bawah Swinger ideal (4,35%, 6,77%). Turun 8,0% dengan 47 trade saja.
- Swinger ideal sendiri WR <50% di ketiga rezim pada 2016–2025.

## Kesimpulan
- Regime-switch sedikit memperbaiki base di hold-out saham (mean 3,10% → 3,39%, payout 1,79 → 2,01, 3/5 → 4/5), kecuali di choppy (mean turun 2,64% → 2,32%). Di crypto lebih buruk dari base.
- Tidak ada kombinasi stop/trailing/entry dengan eksekusi Open(i+1) yang mendekati karakter Swinger ideal (rugi ±3% dengan WR ±50%) di rezim mana pun. Pola ini konsisten dengan dekomposisi sebelumnya: rugi kecil Swinger berasal dari fill di level stop pada bar sinyal.
- Rezim downtrend sampelnya kecil (46–63 trade per periode); angkanya tidak stabil.
