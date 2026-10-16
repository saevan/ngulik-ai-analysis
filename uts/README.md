# UTS — Breakout Stop ER (backtest dan dashboard)

Kode sumber backtest untuk dashboard `output/UTS_NIM_Nama.html`. Python 3.11+ dengan numpy dan pandas.

## Menjalankan ulang
```sh
python -m uts.test_regression     # mesin UTS (mode kompatibel) = mesin riset yang sudah diaudit, identik
python -m uts.run_uts             # semua uji: grid in-sample, OOS, walk-forward, sensitivitas, biaya, delay, robust, look-ahead
python -m uts.build_dashboard     # menulis output/UTS_NIM_Nama.html (mandiri, tanpa internet)
python -m uts.forward_test --data <csv baru>   # forward test sesudah tanggal pembekuan (parameter & kode beku)
```
Data: `Data/Data kompas 100.csv` (Ticker, Date/Time, Open, High, Low, Close, Volume), harian 2000-01-04 s.d. 2025-08-15.

## Berkas
- `data.py` pemuat dan pembersihan data; `indicators.py` indikator kausal, fraksi harga, ARA/ARB.
- `engine.py` aturan strategi dan eksekusi (buy stop, fee, spread offer/bid, lot, ARA/ARB, likuiditas 5% ADV20, delay).
- `metrics.py` definisi metrik sesuai soal; `run_uts.py` seluruh pengujian; `build_dashboard.py` dashboard HTML.
- `test_regression.py` bukti mesin baru = mesin riset yang diaudit; `forward_test.py` forward test.
