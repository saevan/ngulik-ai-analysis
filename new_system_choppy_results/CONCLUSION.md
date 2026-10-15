# Sistem baru HHV55 vs Swinger ideal saat ER pasar choppy (15 Oktober 2026)

Sistem baru: Close > HHV55 sebelumnya; stop Close ≤ entry − 3 ATR14; trailing aktif sesudah peak Close ≥ entry + 2 ATR, keluar saat Close ≤ peak − 2,5 ATR; semua eksekusi Open(i+1); satu posisi per saham (statistik trade, belum portofolio); fee 0,15/0,25%. Swinger ideal: ledger `prototype_swinger_benchmark_results/afl_ideal_net_trades.csv` (fill ideal, fee yang sama). Choppy = ER20 proxy equal-weight 100 saham < 0,3 dengan label lag satu bar (`regime_proxy`), dilihat pada tanggal entry. Kode `new_system_choppy_vs_swinger.py`.

| Kondisi | Periode | Sistem | Trade | Mean | Median | WR | Avg win | Avg loss | Payout | Bar menang/kalah | Lolos 1–5 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| choppy | 2000–25 | Sistem baru | 1545 | 3.04% | −0.40% | 48.0% | 16.6% | 9.5% | 1.75 | 36.2 / 22.2 | 3 |
| choppy | 2000–25 | Swinger ideal | 1833 | 5.81% | 0.06% | 50.5% | 14.7% | 3.2% | 4.57 | 26.0 / 10.4 | 5 |
| choppy | 2000–15 | Sistem baru | 721 | 3.79% | 0.33% | 51.5% | 16.0% | 9.2% | 1.75 | 35.5 / 20.8 | 4 |
| choppy | 2000–15 | Swinger ideal | 959 | 7.15% | 0.60% | 53.7% | 16.1% | 3.2% | 5.00 | 28.2 / 11.7 | 5 |
| choppy | 2016–20 | Sistem baru | 370 | 4.19% | −0.80% | 46.2% | 19.7% | 9.1% | 2.16 | 40.6 / 23.4 | 4 |
| choppy | 2016–20 | Swinger ideal | 399 | 5.60% | −0.40% | 46.9% | 15.5% | 3.1% | 4.97 | 25.2 / 9.6 | 4 |
| choppy | 2021–25 | Sistem baru | 454 | 0.92% | −1.53% | 44.1% | 15.2% | 10.3% | 1.47 | 33.9 / 23.2 | 3 |
| choppy | 2021–25 | Swinger ideal | 475 | 3.30% | −0.40% | 47.0% | 10.8% | 3.3% | 3.27 | 21.4 / 9.0 | 4 |
| trend | 2000–25 | Sistem baru | 1919 | 5.66% | 0.84% | 53.1% | 18.8% | 9.2% | 2.05 | 33.1 / 23.0 | 5 |
| trend | 2000–25 | Swinger ideal | 1408 | 8.62% | 0.57% | 53.8% | 18.8% | 3.2% | 5.93 | 27.2 / 11.6 | 5 |

Kesimpulan:
- Saat choppy, sistem baru kalah dari Swinger ideal terutama di **rugi rata-rata (9,5% vs 3,2%)** dan durasi rugi (22 vs 10 bar). Avg win sistem baru justru lebih besar (16,6% vs 14,7%) dan WR hampir sama (48,0% vs 50,5%).
- Swinger ideal sendiri tidak memenuhi WR >50% saat choppy 2016–20 (46,9%) dan 2021–25 (47,0%); WR choppy-nya turun di periode yang sama dengan sistem baru.
- Saat trend, sistem baru lolos 5/5 (full 2000–25) dan WR menyamai Swinger ideal; selisihnya tetap rugi per trade.
- Stop 3 ATR dengan eksekusi Open berikutnya membuat rugi rata-rata ~9%; Swinger ideal ~3% karena fill di level stop pada bar sinyal. Uji sebelumnya (swinger_character_match_results) menunjukkan stop lebih ketat dengan eksekusi kausal menurunkan WR dan CAGR.
