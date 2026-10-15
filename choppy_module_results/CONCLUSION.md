# Modul saat pasar choppy agar dana tidak idle (15 Oktober 2026)

Sistem 1 (tetap): beli Close > HHV20 dan ER20 saham ≥0,3, hanya bila ER20 pasar ≥0,3; jual Close < SMA30 atau fading 2 ATR; Open berikutnya. Modul choppy: entry hanya bila ER20 pasar <0,3 (Close sinyal), Open berikutnya, berbagi 10 slot, sistem 1 didahulukan. Rp1 miliar, 10% equity, compounding. Fee 0,15/0,25%; spread1 = fee + 1 tick per sisi + lot 100. Mesin `backtest_two_module.py` (sistem 1 saja mereproduksi persis kurva sebelumnya). Kode `search_choppy_parking_module.py` (putaran 1), `search_choppy_parking_round2.py` (putaran 2), definisi `choppy_modules.py`.

Keluarga yang dulu gagal tidak diulang (RSI2/support/Bollinger mean reversion, range escape, inverse, profil Swinger). Kandidat baru berbasis sifat stabil: breakout saham yang trending sendiri (ER saham tinggi), momentum 120 hari, uptrend volatilitas rendah; masing-masing dengan/tanpa "direbut" (posisi modul choppy terlemah dijual di Open berikut bila sistem 1 butuh slot).

Aturan pilih (train 2000–15, spread1): CAGR > sistem 1 saja DAN bulan rekor ≥ sistem 1 saja. **Tidak ada konfigurasi yang lolos di kedua putaran.**

## Putaran 1 (full 2000–25; CAGR / bulan rekor / MDD)

| Modul choppy | Fee | Spread1 | Modal terpakai hari choppy (fee) |
|---|---|---|---|
| Sistem 1 saja | 27.9% / 91 / −39% | 16.0% / 65 / −50% | 34% |
| Breakout ER saham ≥0,5 HHV20, tanpa direbut | 34.5% / 105 / −31% | 17.2% / 64 / −47% | 54% |
| Breakout ER saham ≥0,3 HHV20, tanpa direbut | 36.6% / 110 / −33% | 16.6% / 62 / −51% | 71% |
| Breakout ER saham ≥0,3 HHV55, tanpa direbut | 32.6% / 95 / −31% | 15.4% / 57 / −48% | 63% |
| Momentum top 10%, keluar < SMA50, tanpa direbut | 36.2% / 109 / −45% | 14.7% / 54 / −62% | 71% |
| Momentum top 10%, maks 20 bar, tanpa direbut | 31.9% / 101 / −46% | 7.3% / 37 / −65% | 69% |
| Uptrend volatilitas rendah, tanpa direbut | 25.2% / 85 / −51% | −12.1% / 0 / −97% | 81% |
| Varian "direbut" (semua keluarga) | 22.7–30.1% | −17.1–11.7% | — |

"Direbut" lebih buruk di semua keluarga: avg win modul choppy turun (mis. 20,0% → 12,0%) karena posisi yang dijual sering calon pemenang.

## Putaran 2 (ditetapkan sebelum dijalankan): mekanisme kapasitas untuk breakout ER saham ≥0,5

| Varian | Biaya | Train | Validation | Test | Full |
|---|---|---|---|---|---|
| Sistem 1 saja | fee | 35.5% / 67 | 23.6% / 22 | 8.1% / 5 | 27.9% / 91 / −39% |
| Maks 10 slot | fee | 39.3% / 71 | 32.6% / 24 | 19.4% / 12 | 34.5% / 105 / −31% |
| **Maks 5 slot** | fee | 39.7% / 71 | 36.2% / 28 | 13.2% / 10 | **34.1% / 105 / −32%** |
| Maks 10, rebut hanya posisi rugi | fee | 41.1% / 74 | 36.2% / 26 | 13.7% / 12 | 35.1% / 109 / −35% |
| Maks 5, rebut hanya posisi rugi | fee | 40.7% / 72 | 38.4% / 26 | 9.9% / 8 | 34.0% / 102 / −37% |
| Sistem 1 saja | spread1 | 20.6% / 51 | 14.5% / 21 | 2.0% / 3 | 16.0% / 65 / −50% |
| Maks 10 slot | spread1 | 18.8% / 50 | 18.3% / 15 | 8.9% / 5 | 17.2% / 64 / −47% |
| **Maks 5 slot** | spread1 | 19.5% / 50 | 21.9% / 21 | 4.0% / 4 | **17.2% / 67 / −47%** |
| Maks 10, rebut hanya posisi rugi | spread1 | 19.2% / 49 | 22.5% / 16 | 6.2% / 4 | 17.1% / 60 / −53% |
| Maks 5, rebut hanya posisi rugi | spread1 | 18.8% / 48 | 21.2% / 17 | 2.8% / 2 | 15.9% / 57 / −53% |

Karakter modul breakout ER ≥0,5 (maks 5 slot, full): 654 trade, WR 42,8% (fee) / 38,4% (spread), payout 2,44 / 2,10, mean +3,9% / +1,8% per trade, hold 19,6 bar. Modal terpakai pada hari choppy 34% → 51%.

## Kesimpulan
- Modul choppy terbaik: **breakout saham yang trending sendiri (Close > HHV20, ER20 saham ≥0,5) saat pasar choppy, tanpa direbut, maks 5 slot**. Ini satu-satunya keluarga dengan expectancy positif pada kedua biaya, dan memperbaiki CAGR di validation, test dan full (fee: semua window; spread: validation, test, full) dengan MDD lebih dangkal. Train dengan spread sedikit di bawah sistem 1 (19,5% vs 20,6%), sehingga tidak lolos aturan pilih; statusnya kandidat diagnostik.
- Keluarga yang membuat modal hampir selalu terpakai (momentum, volatilitas rendah: 70–81%) untung dengan fee tetapi rugi besar dengan spread. Dana idle lebih baik daripada trade berexpectancy negatif setelah biaya.
- Merebut slot dari modul choppy merugikan; membatasi modul choppy 5 slot lebih aman.
- Pemilihan keluarga putaran 2 memakai hasil putaran 1 semua window; data sudah pernah dilihat; AFL tidak diubah.
