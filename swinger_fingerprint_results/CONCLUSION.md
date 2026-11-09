# Sidik jari Swinger ideal per kondisi pasar (9 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `swinger_fingerprint.py`. Hasil:
- `character_by_condition.csv`;
- `entry_features_vs_base.csv`;
- `move_by_split.csv`;
- `trades.csv.gz`.

Pembanding: Prototype Swinger ideal, biaya B, 10 posisi × 10%, 2000-01-01..2025-08-15, universe 100 saham saat ini. Kondisi
pasar saat entry dari `regime_proxy`.

## A + B. Karakter trade dan asal return per trade
| | Naik | Sideways | Turun |
|---|---|---|---|
| Trade per tahun | 33 | 72 | 22 |
| WR | 52% | 47% | 48% |
| Rata-rata menang / kalah | +21,9% / −3,0% | +15,0% / −3,5% | +15,1% / −4,0% |
| Expectancy per trade | +10,0% | +5,3% | +5,2% |
| Median bar dipegang | 14 | 13 | 12 |
| Kaki fill entry (log) | +3,1% | +2,4% | +2,8% |
| Kaki pergerakan harga, Close entry → Close exit (log) | **+2,1%** | **+0,1%** | **−0,95%** |
| Kaki fill exit (log) | +2,9% | +2,3% | +2,8% |
| Biaya | −0,9% | −0,9% | −0,9% |
| Basis Close-ke-Close (bersih): WR | 34% | 30% | 28% |
| Basis Close-ke-Close (bersih): expectancy | **+3,4%** | **+0,3%** | **−0,6%** |
| Pergerakan rata-rata 5% trade terbaik | +62,8% | +42,9% | +44,6% |
| Pergerakan rata-rata tanpa 5% trade terbaik | −1,1% | −2,1% | −3,4% |

Catatan: metrik "porsi pergerakan dari 5% trade terbaik" di PLAN tidak terdefinisi saat jumlahnya kecil atau negatif.
Karena itu metrik ini dilaporkan sebagai rata-rata dengan dan tanpa 5% trade terbaik.

## C. Apa yang dibeli Swinger (median saat sinyal vs semua hari saham di kondisi sama)
| | Naik: Swinger / dasar | Sideways: Swinger / dasar | Turun: Swinger / dasar |
|---|---|---|---|
| Return 5 hari | +3,5% / +0,6% | +3,6% / 0,0% | +4,2% / −1,9% |
| Posisi di range 20 hari | 0,75 / 0,63 | 0,65 / 0,45 | 0,57 / 0,26 |
| Di atas SMA30 | 83% / 69% | 67% / 45% | 46% / 20% |
| Close tertinggi 20 hari | 38% / 20% | 26% / 12% | 18% / 5% |
| ER20 saham < 0,2 | 54% / 44% | 66% / 53% | 59% / 38% |
| ATR14 / Close | 3,0% / 3,2% | 3,1% / 3,3% | 3,8% / 4,0% |

## D. Kaki pergerakan per kelompok (log; bersih Close-ke-Close di kurung)
| | Naik | Sideways | Turun |
|---|---|---|---|
| Saham ER20 < 0,2 | +2,1% (+2,9%) | −0,3% (−0,2%) | −0,6% (0,0%) |
| Saham ER20 ≥ 0,2 | +2,1% (+4,0%) | +0,9% (+1,5%) | −1,4% (−1,4%) |
| Di atas SMA30 | +2,3% (+3,6%) | +0,2% (+0,5%) | −0,6% (+0,2%) |
| Di bawah SMA30 | +1,3% (+2,6%) | 0,0% (0,0%) | −1,2% (−1,2%) |

## Observasi
- Karakter Swinger: trade sering (sekitar 126 per tahun), dipegang sekitar 13 bar, rugi kecil (−3…−4%), menang besar
  (+15…+22%), WR sekitar 50%, dan modal hampir selalu terpakai.
- Yang dibeli Swinger adalah breakout swing pendek: harga baru naik sekitar 4% dalam 5 hari, di separuh atas range, dan
  lebih sering di saham choppy daripada rata-rata.
- Untung di ketiga kondisi berasal dari fill-nya (+5,4% per trade, tidak bisa dieksekusi). Pergerakan harga yang
  ditangkapnya:
  - nyata saat naik: +3,4% bersih per trade;
  - hampir nol saat sideways;
  - negatif saat turun.
- Pergerakan itu seluruhnya datang dari 5% trade terbaik. Tanpa mereka, pergerakan negatif di semua kondisi.

## Interpretasi (belum diuji sebagai sistem)
Bagian karakter Swinger yang bisa ditiru logika lain yang bisa dieksekusi:
- banyak percobaan murah dengan rugi kecil, yang dibayar oleh sedikit trade raksasa;
- saat pasar naik: semua jenis saham;
- saat sideways: hanya saham yang sedang tren sendiri (ER20 ≥ 0,2, bersih +1,5%/trade);
- saat turun: tidak ada kelompok entry Swinger yang pergerakannya positif. Dengan saham long saja, target realistis saat
  turun adalah rugi sekecil mungkin, bukan untung seperti Swinger ideal. Uji pantulan dan mean reversion sebelumnya juga
  gagal.
