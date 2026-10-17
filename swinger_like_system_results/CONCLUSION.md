# Sistem baru dengan karakter Swinger ideal — "Swinger Kausal" (16 Okt 2026, v2)

> **Koreksi 17 Okt 2026:** semua angka buy stop di sini memakai aturan fill High > level. Bila buy stop juga terisi saat High tepat menyentuh level
> (realistis untuk stop broker), SK-5 full fee turun 63,2% → 44,6% (rekor 139 → 107, MDD −27% → −35%), ER 0,2 + trailing 66,5% → 45,3%, HHV20 lama 43,3% → 37,1%.
> Lihat `overfit_results/CONCLUSION.md` dan `overfit_results/touch_fill_check.csv`.

Kode: `search_swinger_like_system.py` (grid 360 + base; PLAN/FROZEN di-commit sebelum window evaluasi dibuka), `evaluate_swinger_like_finalists.py`,
`walkforward_swinger_like.py`, `capacity_swinger_like.py`, `swinger_fill_ladder.py`. Engine `backtest_stop_execution.py`; opsi baru default mati,
`test_stop_execution_new_options.py` mereproduksi kurva audit persis. Format: CAGR / bulan rekor (definisi Swinger: ada ekuitas harian
tertinggi baru dalam bulan itu) / MDD. Rp1 miliar, compounding, long only.

**v2:** audit independen menemukan look-ahead di order book v1 (volume hari itu dipakai memilih saham, slot saham yang gap >2% dialihkan ke
peringkat berikutnya memakai informasi Open) dan order "debu" <Rp1. v2 memakai order book murni pra-Open (`book_preopen`) dan order minimum
0,1% budget; efeknya −3…−5 pp. Hasil v1 disimpan di `v1_book_lookahead/`.

## Sistem: Swinger Kausal HHV5 (SK-5)
- Sebelum Open: untuk saham yang belum dipegang, level = High tertinggi 5 bar sebelumnya (level `res` Swinger); siap bila ER20 bar sebelumnya ≥ 0,3.
- Order buy stop hanya untuk K saham siap dengan momentum ln(C[t−21]/C[t−141]) tertinggi, K = slot kosong; ukuran tiap order dikunci sebelum
  Open = 20% ekuitas Close kemarin (dibatasi kas). Saat Open: order dibatalkan bila Open > level×1,02 (slotnya tidak dialihkan).
- Terisi bila High > level, harga max(Open, level).
- Exit (diputuskan di Close, dieksekusi Open berikutnya; bila Open itu gap turun >2% dijual di Close hari itu):
  breakout palsu (Close bar entry < level), fading (Open−Low ≥ 2 ATR14), atau Close < SMA30.
- Dipilih oleh aturan train-only (CAGR fee train tertinggi dari 360) dan oleh kedua aturan walk-forward di fold 2012, 2016, 2021.

## Hasil (fee 0,15/0,25%, tanpa batas likuiditas — basis yang sama dengan Swinger ideal)
| Sistem | Train 2000–15 | Validasi 2016–20 | Tes 2021–25 | Full |
|---|---|---|---|---|
| Swinger ideal | 128,9/155/−14 | 101,0/48/−19 | 85,1/46/−16 | 114,8/249/−19 |
| **SK-5** | 67,0/96/−18 | 69,7/25/−18 | 44,5/21/−27 | **63,2/139/−27** |
| Pilihan terdaftar (HHV10, syarat spread1) | 56,1/90/−20 | 58,3/25/−19 | 37,3/13/−29 | 53,4/125/−29 |
| Base: buy stop ketat HHV20 | 47,1/89/−18 | 40,2/29/−16 | 31,1/20/−18 | 43,3/138/−18 |
| Plafon post-hoc (terbaik full sesudah melihat semua window) | 59,9/103/−24 | 89,8/36/−23 | 93,8/33/−19 | 70,7/170/−24 |
| Swinger stop order kausal | | | | 30,2/102/−50 |
| Swinger next Open kausal | | | | 21,5/83/−56 |

Walk-forward prosedur (pilih dari masa lalu, uji ke depan, 2008–2025): 49,3/90 dari 212/−27 (fee), 37,9/69/−35 (slippage 0,25%);
Swinger ideal tahun yang sama 95,9/173/−19.

Karakter (full, fee) SK-5 vs Swinger ideal: avg loss 3,5% vs 3,2%; payout 4,1 vs 5,2; rugi >10% 3,2% vs 1,5%; WR 44,0% vs 51,9%;
hold 10,5 vs 19,0 bar (menang 16,4 / kalah 5,9); modal terpakai 59% vs 93%; 2.116 vs 3.241 trade.

## Kenapa kinerja Swinger ideal tidak bisa disamai (sinyal Swinger sama, fee sama)
Ideal 114,8/249 → di-clamp ke range bar 88,2/224 → isi di Close bar konfirmasi 13,7/64 → stop order kausal 30,2/102 → next Open 21,5/83.
Keunggulan ideal = membeli di level breakout pada bar yang sudah diketahui ditutup di atas level (dan ~27 pp dari harga di luar range bar).

## Biaya, kapasitas, pasar lain
- Slippage 0,25%/sisi: SK-5 51,8/117/−35; Swinger ideal 102,0/232/−21; Swinger kausal 13,8–14,9%. 1 tick di harga ter-adjust (pesimistis
  sebelum 2008): SK-5 27,9/69/−49 (lebih buruk dari base 28,8/104).
- Tanpa batas likuiditas order tumbuh puluhan kali nilai transaksi harian (semua sistem, termasuk Swinger ideal). Batas order ≤25% ADV20:
  SK-5 27,5/94/−28 vs Swinger ideal 29,8/186/−13; ≤5%: 20,2/86/−26 vs 22,5/177/−13. Selisih CAGR hampir hilang, selisih bulan rekor dan MDD tetap.
- Crypto 8 koin 2017–25 (parameter sama, fee 0,1%): SK-5 99,9/27/−36; Swinger ideal 157,7/53/−30; Swinger kausal 34–46%. Forex: semua ≈0.
- Uji pemotongan data (2008-06-30, 2016-01-15, 2021-03-31): identik.

## Kesimpulan
- Kinerja Swinger ideal tidak dapat disamai secara kausal. SK-5 kira-kira setengah CAGR-nya dan ~55% bulan rekornya, tetapi 2–3× semua versi
  Swinger yang bisa dieksekusi dengan MDD jauh lebih kecil.
- Karakter yang tercapai: rugi kecil dan payout tinggi. Tidak tercapai: WR >50%, hold panjang, modal terpakai ~93%.
- Dibanding kandidat lama (base): CAGR naik (fee +20 pp, slippage 0,25% +13 pp) tetapi bulan rekor tidak naik dan MDD lebih dalam (−27% vs −18%);
  dengan biaya 1 tick tidak lebih baik.
- Batasan: universe survivor, harga ter-adjust, ±6.000 run pada data yang sama, likuiditas dan slippage breakout belum dari order book riil.
  AFL tidak diubah. Langkah berikut: forward test (paper trade) SK-5 sebelum dipakai.
