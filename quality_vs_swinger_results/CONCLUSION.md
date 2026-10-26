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

## Tambahan: kualitas trade diukur dengan expectancy (permintaan pengguna, 26 Okt 2026)
Kode: `expectancy_vs_swinger.py` (ledger trade yang sama, `winrate_diagnosis_results/trades_*.csv`).

Definisi:
- E = WR × rata-rata menang − (1 − WR) × rata-rata kalah. Ini sama dengan rata-rata return bersih per trade.
- E_R = E / rata-rata kalah, yaitu expectancy per 1R dengan R = trade kalah rata-rata. Ini mengukur imbalan per unit
  risiko.
- CI 95%: bootstrap per bulan entry, 2.000 kali.
- "E × trade/th × ukuran posisi" adalah jembatan kasar ke return portofolio (kita 25% ekuitas per order, Swinger 10%;
  aritmetik, tanpa compounding).

| Kondisi | Sistem | Trade/th | E per trade (CI 95%) | E_R | E per bar | E × trade/th × ukuran |
|---|---|---|---|---|---|---|
| Semua | Kita | 31 | +7,0% (4,7…9,4) | 1,32R | 0,40% | ≈54%/th |
| | Kita realistis | 34 | +2,5% (1,3…3,8) | 0,52R | 0,15% | ≈21%/th |
| | Swinger ideal | 126 | +6,5% (5,5…7,6) | 1,88R | 0,34% | ≈82%/th |
| Uptrend | Kita | 11,6 | +8,5% (4,6…12,9) | 1,50R | 0,44% | ≈25%/th |
| | Kita realistis | 12,4 | +3,0% (1,1…5,1) | 0,65R | 0,18% | ≈9%/th |
| | Swinger ideal | 33 | +10,0% (7,7…12,2) | 3,32R | 0,47% | ≈33%/th |
| Sideways | Kita | 18,3 | +6,4% (3,8…9,5) | 1,29R | 0,38% | ≈29%/th |
| | Kita realistis | 20,3 | +2,1% (0,8…3,6) | 0,43R | 0,13% | ≈11%/th |
| | Swinger ideal | 72 | +5,3% (4,3…6,5) | 1,51R | 0,29% | ≈38%/th |
| Downtrend | Kita | 1,2 | +1,3% (−5,2…11,5) | 0,18R | 0,10% | ≈0,4%/th |
| | Kita realistis | 0,9 | +4,5% (−3,7…16,6) | 0,73R | 0,32% | ≈1%/th |
| | Swinger ideal | 22 | +5,2% (3,2…7,6) | 1,29R | 0,28% | ≈11%/th |
| Breakdown | Kita | 0,7 | +4,2% (−3,0…14,4) | 0,72R | 0,26% | ≈0,8%/th |
| | Kita realistis | 0,9 | +3,9% (−2,4…11,4) | 0,80R | 0,25% | ≈0,9%/th |
| | Swinger ideal | 15 | +5,0% (3,0…7,7) | 1,30R | 0,28% | ≈8%/th |

Expectancy per periode (E per trade; kita / kita realistis / Swinger ideal):

| Periode | Kita | Kita realistis | Swinger ideal |
|---|---|---|---|
| 2000-07 | 8,5% | 4,9% | 10,9% |
| 2008-15 | 3,4% | 0,4% | 5,9% |
| 2016-20 | 10,3% | 3,5% | 5,4% |
| 2021-25 | 6,6% | 1,6% | 3,4% |

Interpretasi:
1. Dalam persen per trade, expectancy kita (+7,0%) tidak berbeda nyata dari Swinger ideal (+6,5%); CI-nya tumpang
   tindih. Di 2016–25 expectancy kita malah lebih tinggi, tapi 71% P&L kita dari saham listing setelah 2018.
2. Per unit risiko, Swinger ideal lebih baik: 1,88R vs 1,32R. Trade kalahnya lebih kecil (3,5% vs 5,3%), terutama karena
   tidak ada trade breakout gagal (fill ideal).
3. Saat downtrend dan breakdown, expectancy kita tidak bisa dibedakan dari nol (CI melewati 0). Kita juga hampir tidak
   trade di kondisi itu (kurang dari 1–2 trade per tahun vs 15–22 trade untuk Swinger).
4. Celah return paling besar datang dari frekuensi, bukan dari expectancy per trade. E × frekuensi × ukuran ≈ 54%/th
   (kita) vs ≈ 82%/th (Swinger ideal), karena kita 31 trade per tahun vs 126.
5. Versi realistis: expectancy turun ke +2,5% per trade (0,52R). Di 2008–15 dan 2021–25 CI-nya menyentuh 0. Ini
   kelemahan terbesar kita.

## Tambahan: rincian selisih return per tahun (permintaan pengguna, 26 Okt 2026)
Kode: `yearly_gap_breakdown.py`. Hasil: `yearly_breakdown.csv`. Return tahunannya sama dengan tabel di atas.
- **Selisih kumulatif.** Rp1 M menjadi Rp28,9 T (kita) vs Rp66.500 T (Swinger ideal; angka teoretis karena fill tidak
  bisa dieksekusi dan tidak ada batas likuiditas). Ekuitas Swinger ideal sebesar 1,4× ekuitas kita di akhir 2000, 44×
  di 2007, 1.323× di 2016, 3.459× di 2023 (puncak), lalu 2.300× di Agustus 2025.
- **Pertumbuhan per tahun.** (1 + return kita) / (1 + return Swinger) median 0,75. Artinya di tahun biasa modal kita
  tumbuh sekitar 25% lebih sedikit daripada Swinger ideal.
- **Di kondisi apa selisih terjadi** (selisih log return 2000–25 dibagi per kondisi hari):
  - uptrend 31% (33% hari);
  - sideways 53% (56% hari);
  - downtrend 16% (11% hari).

  Per hari, selisih terbesar ada di downtrend. Selisih total paling banyak terjadi di sideways karena hari sideways
  paling banyak. Di tahun dengan selisih kecil, pembagian per kondisi tidak stabil (bisa negatif atau lebih dari 100%).

## Update V2 (26 Okt 2026) – `v2_quality_by_regime.py`, `v2_trade_quality.csv`, `v2_portfolio_by_condition.csv`
Ringkas (realistis | tanpa batasan | Swinger ideal):
| Kondisi | WR | Expectancy/trade | E_R | Trade/th | Return tahunan di hari itu |
|---|---|---|---|---|---|
| Uptrend | 43,5% \| 45,6% \| 52,1% | +8,1% \| +17,8% \| +10,0% | 0,90 \| 1,78 \| 3,32 | 10 \| 10 \| 33 | 48% \| 107% \| 186% |
| Sideways | 40,0% \| 48,9% \| 47,4% | +6,8% \| +13,9% \| +5,3% | 0,81 \| 1,52 \| 1,51 | 17 \| 16 \| 72 | 10% \| 33% \| 79% |
| Downtrend | 33,3% \| 34,1% \| 48,0% | +6,8% \| +3,6% \| +5,2% | 0,72 \| 0,32 \| 1,29 | 1,4 \| 1,7 \| 22 | 13% \| 24% \| 66% |

- Expectancy per trade kita lebih tinggi atau setara, tapi rugi per trade kita 2,5× lebih besar (−8,7% vs −3,5%), jadi
  E_R lebih rendah.
- Jumlah trade kita 4–15× lebih sedikit. Saat downtrend trade breakout realistis hampir nol dan expectancy-nya negatif.
- Celah return terutama dari frekuensi trade dan modal terpakai.

## Kenapa expectancy V2 lebih tinggi untuk trade yang dimulai saat sideways? (`v2_sideways_why.py`, `v2_sideways_why.csv`)
Trade yang entry-nya di hari berlabel sideways (realistis | Swinger ideal):

| | V2 realistis | Swinger ideal |
|---|---|---|
| Expectancy (rata-rata) | +6,8% | +5,3% |
| Median trade | −2,9% | −0,4% |
| Rata-rata tanpa 10% trade terbaik | −2,1% | +0,6% |
| Lama pegang | 48,5 bar | 18,3 bar |
| Expectancy per bar dipegang | 0,14% | 0,29% |

Expectancy per jenis trade V2: breakout +3,4% (12,7 trade/th) vs bulanan +17,5% (4,0 trade/th, sekitar 128 bar).

Di mana kenaikannya terjadi selama dipegang (rata-rata jumlah log return Close-ke-Close per trade, menurut kondisi tiap
hari):
- hari uptrend: +1,8% (32% hari);
- hari sideways: +0,7% (59% hari);
- hari downtrend: +0,4% (8% hari).

Per hari, hari uptrend memberi sekitar 5× lebih banyak.

Interpretasi:
- Keunggulan per trade itu bukan karena kita jago saat sideways. Rata-ratanya diangkat oleh segelintir pemenang besar,
  terutama dari modul bulanan yang dipegang berbulan-bulan sampai pasar berubah naik.
- Trade biasa yang dimulai saat sideways justru rugi (median −2,9%). Trade breakout di sideways (+3,4%) lebih rendah dari
  Swinger.
- Per hari dipegang, Swinger ideal menghasilkan dua kali lipat. Expectancy-nya hampir seluruhnya dari fill idealnya
  (log return Close-ke-Close-nya ≈ 0).
