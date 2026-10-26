# Struktur dasar market IDX (Kompas100, 1994–2025.08) – `market_structure_check.py`
Bar dengan volume 0 dikeluarkan. Candle hijau = Close > Open bar itu; merah = Close < Open; datar = sama.

## Klaim pengguna: jumlah candle merah dan hijau seimbang
| Timeframe (per saham) | Hijau | Merah | Datar | Rata-rata badan hijau / merah |
|---|---|---|---|---|
| Harian | 37,3% | 42,4% | 20,3% | +2,7% / −2,2% |
| Mingguan | 44,4% | 45,1% | 10,5% | +5,7% / −4,4% |
| Bulanan | 48,3% | 47,0% | 4,7% | +12,8% / −8,8% |

Harian per periode (hijau / merah): 1994–99 32 / 30; 2000–07 35 / 31; 2008–15 40 / 41; 2016–20 38 / 48; 2021–25 38 / 51.

- Bulanan: hampir seimbang. Mingguan: hampir seimbang.
- Harian: tidak seimbang. Sejak 2016 candle merah jauh lebih banyak, karena harga cenderung turun dari Open ke Close.
- Ukuran tidak seimbang: candle hijau rata-rata lebih besar.
- Indeks equal-weight survivor tidak seimbang (hari naik 57%, bulan naik 66%) karena bias survivor dan rata-rata
  aritmetik.
- Kesimpulan: benar sebagian. Jumlah merah/hijau per saham mendekati 50/50 makin besar timeframe-nya, tapi tidak di
  harian, dan besar candle tidak seimbang.

## Struktur dasar lain yang terukur
| Struktur | Hasil |
|---|---|
| Ekor gemuk | Kurtosis harian median 9,7; gerakan > 3 sd terjadi 1,8% hari (distribusi normal: 0,27%, jadi 6,5× lebih sering) |
| Volatilitas berkelompok | Autokorelasi \|return\| lag 1 = 0,28, lag 10 = 0,12. Hari bergejolak diikuti hari bergejolak. |
| Arah harian saham tak punya ingatan | Autokorelasi return harian per saham −0,01 |
| Indeks pasar punya ingatan positif | Autokorelasi return harian indeks EW +0,14 (sebagian karena saham yang jarang ditransaksikan) |
| Hari naik vs turun | Naik 38,9% (rata-rata +2,7%), turun 42,1% (−2,5%), datar sisanya |
| Gap | Gap naik 34% hari, gap turun 23%. Gap naik > 0,5% tertutup di hari yang sama 69%; gap turun 58%. |
