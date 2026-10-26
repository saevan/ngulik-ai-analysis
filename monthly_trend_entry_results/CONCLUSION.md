# Unsur waktu: beli saham yang sedang trending di awal bulan (26 Okt 2026)

Rencana dikunci di `PLAN.md` sebelum hasil, untuk langkah 1 dan langkah 2.
- Kode: `monthly_trend_entry.py` (langkah 1), `monthly_watchlist_gate.py` (langkah 2), `monthly_watchlist_robustness.py`
  (cek tetangga, post hoc).
- Mesin dapat opsi baru `entry_mode='signal'` / `signal_fn` / `exit_signal_fn` (default mati; uji regresi lulus).
- Cek mekanisme: di versi realistis 100% entry jatuh di hari bursa pertama bulan itu dan 99–100% exit bulanan di hari
  pertama bulan berikutnya. Di versi tanpa batasan 7–12% entry tertunda karena saham tidak ditransaksikan hari itu.
- Biaya B, 2000-01-01..2025-08-15.
- Pembanding: Swinger ideal (WR 48,8%, expectancy +6,5%, 1,88R, 126 trade/th, 102,0%, 232 bulan rekor, MDD −21%).
  Sistem kita V0 sebagai acuan.

Filter "sedang trending" dicek di Close akhir bulan:

| Filter | Syarat |
|---|---|
| F_sma30 | Close > SMA30 |
| F_sma120 | Close > SMA120 |
| F_er | ER20 ≥ 0,3 dan naik 20 bar |
| F_high | Close ≥ 95% dari Close tertinggi 120 bar |
| F_mom | Close > Close 120 bar lalu |

## Langkah 1: sistem bulanan berdiri sendiri (beli di Open hari pertama bulan, urutan mom120)
Angka dalam versi realistis; tanpa batasan dalam kurung.

| Sel | WR | E/trade | E_R | Trade/th | CAGR | Bulan rekor | MDD |
|---|---|---|---|---|---|---|---|
| V0 (sistem kita) | 33,8% | +2,5% | 0,52R | 34 | 16,2% (49,3%) | 52 (119) | −44% (−24%) |
| F_mom, keluar saat filter gagal di akhir bulan, 25% | 41,1% | +21,1% | 1,31R | 9 | 16,7% (40,1%) | 62 (82) | −56% (−70%) |
| F_mom, keluar saat filter gagal, 10% | 42,6% | +18,3% | 1,18R | 15 | 17,3% (35,1%) | 66 (96) | −53% (−50%) |
| F_sma120, keluar saat filter gagal, 10% | 38,2% | +12,0% | 0,92R | 21 | 16,1% (40,6%) | 54 (109) | −57% (−52%) |
| F_er, keluar saat filter gagal, 10% | 46,6% | +1,3% | 0,17R | 44 | 4,6% (20,1%) | 40 (81) | −41% (−41%) |
| F_high, keluar saat filter gagal, 10% | 44,0% | +2,6% | 0,31R | 34 | 8,0% (24,6%) | 44 (94) | −35% (−43%) |
| Filter apa pun + exit sistem kita | 31–36% | +0,5…1,6% | – | 24–85 | 3,5–7,9% | 26–36 | −35…−55% |
| Kontrol: pilih acak, pegang 1 bulan | 46–49% | ≈0% | – | 49 | −4,8…+3,3% | 17–21 | −72…−93% |
| Kontrol: tanpa filter, urutan mom120, exit sistem | 32,1% | +1,0% | – | 40 | 7,1% | 27 | −49% |

Hasil (kriteria PLAN): tidak ada sel yang lolos. Sel F_mom gagal karena MDD −53…−56%, hanya 2 dari 4 subperiode lebih
baik dari V0, dan WR < 45%.

Observasi:
1. Membeli tiap awal bulan tidak membawa WR ke 50%.
   - WR tertinggi ada di F_er (46–47%), tapi expectancy-nya hanya +1,3…1,8%.
   - Pegang 1 bulan dengan pilihan acak juga memberi WR 46–49% dengan expectancy ≈ 0.
   - Jadi WR ~50% dari pegang berbasis waktu adalah tingkat lempar koin, bukan tanda edge.
2. Filter trending penting.
   - Dengan waktu entry yang sama, F_mom/F_sma120 + exit bulanan memberi 15–17%/th di versi realistis.
   - Tanpa filter: 7,1% (urutan mom120) dan ≤ 3,3% (pilih acak).
3. Hasil terbaik (F_mom bulanan) karakternya lain dari sistem kita:
   - sedikit trade (9–15/th), pegang sekitar 5 bulan (median 100 bar);
   - expectancy besar (+18…21%/trade, 1,2–1,3R);
   - modal terpakai 88–94%;
   - CAGR realistis setara V0, bulan rekor lebih banyak, tapi MDD jauh lebih dalam.
4. Entry bulanan + exit sistem kita buruk. Exit SMA30 menjual posisi bulanan rata-rata setelah 9–10 bar.

## Langkah 2: filter awal bulan sebagai daftar pantau untuk buy stop sistem kita
Sepanjang bulan m, buy stop hanya aktif di saham yang lolos filter pada Close terakhir bulan m−1.

| Daftar pantau | Lolos filter | WR (tanpa batasan / realistis) | CAGR realistis | Rekor | MDD realistis | Subperiode ≥ V0 | CAGR tanpa batasan |
|---|---|---|---|---|---|---|---|
| V0 (semua saham) | 100% | 38,3% / 33,8% | 16,2% | 52 | −44% | – | 49,3% |
| F_mom (Close > Close 120 bar lalu) | 48% | 38,6% / 34,3% | 17,5% | 57 | −44% | 3 dari 4 | 49,3% |
| F_sma120 | 48% | 38,8% / 34,0% | 18,1% | 52 | −38% | 1 dari 4 | 52,9% |
| F_sma30 | 48% | 36,7% / 33,5% | 10,4% | 34 | −61% | – | 45,8% |
| F_er | 17% | 37,9% / 32,8% | 10,8% | 36 | −41% | – | 37,7% |
| F_high | 19% | 35,9% / 31,3% | 9,1% | 35 | −51% | – | 32,6% |
| Acak 50% (3 seed) | 50% | – | 8,3–12,9% | 37–48 | −42…−50% | – | 31,9–45,0% |
| Acak 70% (3 seed) | 70% | – | 14,9–15,6% | 49–55 | −39…−44% | – | 44,8–46,4% |

F_mom lolos semua kriteria langkah 2, tapi tipis: +1,3 pp CAGR realistis dan +5 bulan rekor. WR hampir tidak berubah
(+0,3…0,5 pp).

Cek tetangga (post hoc):
- Versi realistis, lookback trend lain:

  | Filter | Close > Close 60 | 90 | 120 | 180 | 250 bar lalu | SMA60 | SMA120 | SMA200 |
  |---|---|---|---|---|---|---|---|---|
  | CAGR realistis | 16,8% | 19,1% | 17,5% | 14,6% | 17,1% | 15,6% | 18,1% | 17,4% |

  6 dari 8 di atas V0, dan MDD umumnya sama atau lebih baik (kecuali SMA60).
- Tanpa batasan: lookback pendek naik (60/90 bar: 55%; SMA60/120: 53%), lookback panjang turun (180/250 bar: 43–44%).
- Holdout 1995–99 (tanpa batasan): tanpa daftar pantau 55,7%; 120 bar 51,4%; 90 bar 77,3%; 180 bar 49,0%; SMA120
  56,1%. Hasilnya campur.
- WR di semua varian tetap 33–35% (realistis) dan 37–39% (tanpa batasan).

## Kesimpulan
- Unsur waktu (beli di awal bulan) + filter trending tidak menyelesaikan masalah win rate. WR sistem bulanan 38–47%; yang
  mendekati 50% expectancy-nya kecil, dan pegang 1 bulan acak pun sudah ~47%.
- Sebagai daftar pantau untuk sistem kita, filter trend jangka menengah (Close > Close 90–120 bar lalu atau > SMA120)
  memberi perbaikan kecil yang cukup konsisten di versi realistis: CAGR +1…3 pp, MDD sama atau lebih baik. Tapi WR tidak
  naik, karena trade kalah kita datang dari breakout yang gagal di hari pertama, dan filter bulanan tidak menyaring itu.
- Kandidat ini belum diadopsi. Kalau mau dikejar: uji pra-registrasi gabungan daftar pantau trend + tanpa aturan breakout
  gagal di versi realistis.
- AFL tidak diubah.

## Batasan
- Universe survivor.
- 30 + 5 + 8 varian di satu data set.
- Cek tetangga dan holdout dilakukan setelah melihat hasil langkah 2.
