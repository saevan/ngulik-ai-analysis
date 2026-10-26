# Kualitas per trade dan return per tahun: sistem kita vs Prototype Swinger ideal (26 Okt 2026)

Kode: `quality_vs_swinger_by_regime.py`. Skenario B (fee 0,15/0,25% + slippage 0,25%/sisi), Rp1 M, compounding,
2000-01-01..2025-08-15. Sistem: pilihan utama v2 (tanpa batasan dan realistis = likuid point-in-time + filter data basi +
order ≤ 25% ADV20) vs Swinger ideal (pembanding tetap; fill-nya di level TSL bar sinyal tidak bisa dieksekusi).

Definisi kondisi market (diketahui sebelum Open hari itu):
- Uptrend / sideways / downtrend: proxy pasar equal-weight dengan ER20 ≥ 0,3 dan arah 20 hari naik / turun, selain itu
  sideways.
- Breakdown (irisan tambahan, tumpang tindih): Close proxy kemarin adalah low 20 hari baru. 60% hari breakdown juga
  berlabel downtrend.
Per trade dikelompokkan menurut kondisi saat entry. Portofolio dikelompokkan menurut kondisi tiap hari.
Pengecekan: hasil kali return tahunan sama dengan CAGR (49,3% / 16,2% / 102,0%).

## Kualitas per trade (return bersih per trade)
| Kondisi | Sistem | Trade | WR | Rata-rata | Median | Payout | Rata-rata per bar |
|---|---|---|---|---|---|---|---|
| Uptrend | Kita | 297 | 37,4% | +8,5% | −2,3% | 5,7 | 0,44% |
| | Kita realistis | 318 | 34,9% | +3,0% | −2,1% | 3,7 | 0,18% |
| | Swinger ideal | 852 | 52,1% | +10,0% | +0,4% | 7,3 | 0,47% |
| Sideways | Kita | 470 | 39,6% | +6,4% | −1,7% | 4,8 | 0,38% |
| | Kita realistis | 521 | 33,4% | +2,1% | −2,3% | 3,3 | 0,13% |
| | Swinger ideal | 1.833 | 47,4% | +5,3% | −0,4% | 4,3 | 0,29% |
| Downtrend | Kita | 30 | 26,7% | +1,3% | −4,8% | 3,4 | 0,10% |
| | Kita realistis | 22 | 27,3% | +4,5% | −4,7% | 5,3 | 0,32% |
| | Swinger ideal | 556 | 48,0% | +5,2% | −0,2% | 3,8 | 0,28% |
| Breakdown | Kita | 19 | 36,8% | +4,2% | −3,0% | 3,7 | 0,26% |
| | Kita realistis | 23 | 30,4% | +3,9% | −4,5% | 4,9 | 0,25% |
| | Swinger ideal | 396 | 48,0% | +5,1% | −0,3% | 3,8 | 0,28% |
| Semua | Kita | 797 | 38,3% | +7,0% | −2,0% | 5,1 | 0,40% |
| | Kita realistis | 861 | 33,8% | +2,5% | −2,3% | 3,5 | 0,15% |
| | Swinger ideal | 3.241 | 48,8% | +6,5% | −0,2% | 4,9 | 0,34% |

## Portofolio per kondisi (return tahunan pada hari berkondisi itu; modal terpakai)
| Kondisi (porsi hari) | Kita | Kita realistis | Swinger ideal |
|---|---|---|---|
| Uptrend (33%) | 113% (70%) | 34% (72%) | 186% (96%) |
| Sideways (56%) | 33% (43%) | 10% (41%) | 79% (93%) |
| Downtrend (11%) | 7% (14%) | 5% (13%) | 66% (82%) |
| Breakdown (8%) | 5% (22%) | −10% (20%) | 31% (73%) |

## Return per tahun (%; 2025 sampai 15 Agustus)
| Tahun | Kita | Kita realistis | Swinger ideal | Selisih kita (pp) | Selisih realistis (pp) |
|---|---|---|---|---|---|
| 2000 | −1,4 | −22,1 | 37,1 | −38,5 | −59,3 |
| 2001 | 25,3 | 8,8 | 163,3 | −138,1 | −154,5 |
| 2002 | 37,5 | 28,2 | 152,8 | −115,3 | −124,6 |
| 2003 | 162,1 | 87,6 | 378,4 | −216,3 | −290,7 |
| 2004 | 12,3 | 13,1 | 108,1 | −95,8 | −94,9 |
| 2005 | 55,9 | 40,5 | 129,4 | −73,5 | −88,9 |
| 2006 | 23,4 | 9,0 | 88,3 | −64,8 | −79,3 |
| 2007 | 258,4 | 112,3 | 287,8 | −29,4 | −175,6 |
| 2008 | 11,1 | −8,4 | 88,7 | −77,6 | −97,1 |
| 2009 | 28,8 | −8,6 | 252,7 | −224,0 | −261,3 |
| 2010 | 39,3 | 23,4 | 197,3 | −158,0 | −173,9 |
| 2011 | 3,0 | −2,4 | 32,5 | −29,5 | −34,9 |
| 2012 | 55,5 | 15,3 | 61,3 | −5,8 | −46,0 |
| 2013 | 33,2 | −9,3 | 50,6 | −17,4 | −59,9 |
| 2014 | 13,9 | 6,0 | 62,4 | −48,5 | −56,4 |
| 2015 | 30,8 | −12,4 | 49,6 | −18,8 | −62,0 |
| 2016 | 65,4 | 9,1 | 102,9 | −37,5 | −93,8 |
| 2017 | 95,9 | 60,7 | 80,2 | +15,7 | −19,6 |
| 2018 | 56,4 | 21,3 | 43,2 | +13,2 | −22,0 |
| 2019 | 57,0 | 2,1 | 89,2 | −32,2 | −87,1 |
| 2020 | 100,6 | 43,3 | 136,1 | −35,5 | −92,8 |
| 2021 | 278,3 | 36,2 | 177,9 | +100,5 | −141,7 |
| 2022 | −7,6 | −0,8 | 81,5 | −89,2 | −82,4 |
| 2023 | 9,7 | −23,7 | 66,4 | −56,6 | −90,1 |
| 2024 | 66,5 | 30,3 | 33,1 | +33,5 | −2,8 |
| 2025* | 30,0 | 54,2 | 8,2 | +21,8 | +46,0 |

Ringkasan tahunan:
- Median tahunan: kita 35%, kita realistis 11%, Swinger ideal 89%.
- Median selisih: −38 pp (realistis −88 pp). Rata-rata selisih: −55 pp (realistis −94 pp).
- Kita mengalahkan Swinger ideal di 5 dari 26 tahun (2017, 2018, 2021, 2024, 2025*). Versi realistis hanya di 2025*.
- CAGR 2000–25: kita 49,3%, realistis 16,2%, Swinger ideal 102,0%.

## Interpretasi
1. Per trade, versi tanpa batasan setara dengan Swinger ideal saat uptrend dan sideways:
   - Rata-rata per trade dan per bar sama atau lebih tinggi (sideways +6,4% vs +5,3%; per bar 0,38% vs 0,29%).
   - Tapi WR dan median trade jauh lebih rendah (lihat `winrate_diagnosis_results/`).
2. Saat downtrend dan breakdown kita kalah per trade (+1,3% vs +5,2%), dan hampir tidak trade: 30 vs 556 trade, modal
   terpakai 14% vs 82%.
3. Selisih return terutama dari jumlah trade dan modal terpakai, bukan dari mutu trade rata-rata:
   - Swinger ideal 4× lebih banyak trade dengan modal terpakai 93% (kita 49%).
   - Sebagian keunggulan Swinger berasal dari fill idealnya, yang tidak bisa dieksekusi (catatan singkat).
4. Versi realistis turun ke +2–3% per trade di uptrend/sideways. Batasan likuiditas yang paling memotong hasil.
5. Selisih tahunan tidak konstan:
   - Paling besar di 2001–2010 (sering −100 pp lebih).
   - Mengecil sejak 2012.
   - Versi tanpa batasan unggul di 4 dari 9 tahun terakhir. Versi realistis tidak.

## Batasan
- Universe survivor (Kompas100 2025). Saham listing setelah 2018 menyumbang 71% P&L kita.
- Label kondisi berasal dari proxy equal-weight universe ini.
- Trade downtrend/breakdown kita sedikit (19–30), jadi angkanya kasar.
