# Sistem baru dengan karakter Swinger ideal (16 Okt 2026)

Kode: `search_swinger_like_system.py` (grid 360 + base, PLAN/FROZEN di-commit sebelum window evaluasi dibuka), `evaluate_swinger_like_finalists.py`,
`walkforward_swinger_like.py`, `capacity_swinger_like.py`, `swinger_fill_ladder.py`. Engine `backtest_stop_execution.py` (opsi baru default mati;
`test_stop_execution_new_options.py` mereproduksi kurva audit persis). Semua order kausal: level dan urutan diketahui sebelum Open.
Format: CAGR / bulan rekor (definisi Swinger: ada ekuitas harian tertinggi baru) / MDD. Rp1 miliar, maks 10 posisi, compounding.

## Benchmark dan sumber keunggulannya (fee 0,15/0,25%, 2000–2025)
| Swinger, sinyal sama, asumsi fill | Hasil |
|---|---|
| Ideal (level sinyal, boleh di luar range bar) | 114,8 / 249 / −19 |
| Ideal di-clamp ke [Low, High] bar | 88,2 / 224 / −26 |
| Beli/jual di Close bar konfirmasi | 13,7 / 64 / −56 |
| Stop order kausal | 30,2 / 102 / −50 |
| Next Open kausal | 21,5 / 83 / −56 |
Sekitar 27 pp berasal dari harga yang tidak mungkin, sisanya dari membeli di level breakout pada bar yang sudah diketahui ditutup di atas level.

## Sistem baru (keluarga "Swinger kausal")
Buy stop di HHV-N (N 5/10/20, High N bar sebelumnya), ER20 ≥ θ, order pra-Open hanya untuk K saham teratas momentum 120/20 (K = slot kosong, ukuran order dikunci sebelum Open), lewati bila Open > level+2%, exit fading 2 ATR dari Open berjalan atau Close<SMA30 (Open berikutnya; dijual di Close bila Open gap turun >2%), exit breakout palsu (Close bar entry < level → jual Open berikutnya), 20% ekuitas per posisi.

| Sistem | Train 2000–15 | Validasi 2016–20 | Tes 2021–25 | Full |
|---|---|---|---|---|
| Swinger ideal (fee) | 128,9/155/−14 | 101,0/48/−19 | 85,1/46/−16 | 114,8/249/−19 |
| Base: buy stop ketat HHV20 | 48,8/88/−17 | 39,3/28/−18 | 31,9/20/−18 | 44,4/137/−18 |
| Pilihan terdaftar (HHV10, ER .3, failed, 20%) | 62,1/91/−19 | 61,2/25/−18 | 40,2/17/−26 | 58,0/131/−28 |
| Train terbaik fee (HHV5, ER .3, failed, 20%) | 71,3/100/−18 | 70,1/25/−18 | 47,4/23/−25 | 66,4/145/−25 |
| Terbaik full sesudah melihat semua window (plafon, bukan OOS) | 70,7/114/−21 | 75,1/34/−19 | 101,7/38/−14 | 76,2/185/−21 |

Walk-forward prosedur pencarian (pilih dari masa lalu, uji di periode berikutnya, 2008–2025): aturan fee 54,7/91 dari 212 bulan/−23 (fee), 42,5/69/−36 (slippage 0,25%); Swinger ideal di tahun yang sama 95,9/173/−19. Keempat fold memilih HHV5 + exit breakout palsu + 20%.

Karakter (full, fee) — train terbaik vs Swinger ideal: avg loss 3,5% vs 3,2%; rugi >10% 3,4% vs 1,5%; payout 3,9 vs 5,2; WR 43,9% vs 51,9%; hold 10,4 vs 19,0 bar; modal terpakai 62% vs 93%; 2.286 vs 3.241 trade. Rugi kecil dan payout tinggi tercapai; WR, modal terpakai, dan kehalusan kurva tidak.

## Biaya dan kapasitas
- Slippage 0,25%/sisi: train terbaik 54,3/119/−32, pilihan terdaftar 49,8/117/−32, Swinger ideal 102,0/232/−21, Swinger kausal 13,8–14,9%.
- 1 tick di harga ter-adjust (pesimistis sebelum 2008: rata-rata 1,7%/sisi di 2000–07): 25–38%.
- Tanpa batas likuiditas semua sistem (termasuk Swinger ideal) tumbuh sampai order 16–41× nilai transaksi harian rata-rata — tidak bisa dieksekusi. Dengan batas order ≤25% ADV20: kita 23–28%, Swinger ideal 29,8%/186/−13; ≤5%: 17–21% vs 22,5%/177/−13. Selisih CAGR hampir hilang; selisih bulan rekor dan MDD tetap.

## Cek
- Uji pemotongan data (2008-06-30, 2016-01-15, 2021-03-31): identik untuk tiga finalis.
- Crypto 8 koin 2017–25, parameter sama: 84–102% vs Swinger ideal 158%, Swinger kausal 34–46%. Forex: semua ≈0 (tanpa leverage, tidak bermakna).

## Kesimpulan
Kinerja Swinger ideal tidak bisa disamai secara kausal: separuhnya bergantung pada informasi Close yang belum ada saat order. Sistem baru melampaui semua versi Swinger yang bisa dieksekusi (≈2× CAGR), mencapai rugi rata-rata dan payout yang mirip, tetapi CAGR sekitar separuh dan bulan rekor sekitar 55–60% dari ideal. Dengan batas likuiditas realistis selisih CAGR menyempit menjadi 1–2 pp, tetapi kehalusan kurva Swinger ideal tetap tidak tercapai.
Batasan: universe survivor, harga ter-adjust, ~6.000 run pada data yang sama (pilihan terbaik full adalah snooping), likuiditas dan slippage breakout belum dari data order book. AFL tidak diubah. Butuh forward test.
