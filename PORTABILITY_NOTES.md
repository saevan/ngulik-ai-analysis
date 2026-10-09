# Portabilitas

Runner optimasi terbaru dan loader grid_search_timehunter memakai Path(__file__), sehingga dapat bekerja dari root hasil ekstrak. Python3.11.15, NumPy2.4.6, pandas3.0.3 di sumber.20tests smoke lulus Windows; Linux/web dan AmiBroker native belum diuji. Semua modul pihak ketiga yang diimpor skrip penelitian adalah numpy/pandas. Tidak perlu mengunduh data untuk mengulangi riset saham.

Skrip historis berikut masih memuat path Windows; periksa dan ubah DATA_DIR/output path menjadi relatif sebelum menjalankan skrip historis tersebut. Snapshot sengaja mempertahankan aslinya, bukan mengubah hasil lama diam-diam:

- backtest_data_size_test.py
- backtest_diluc.py
- backtest_diluc_sweep.py
- backtest_exit_breakdown.py
- backtest_exit_final.py
- backtest_exit_variants.py
- backtest_fading_hybrid.py
- backtest_fading_move.py
- backtest_lomba.py
- backtest_prototype_swinger.py
- backtest_pullback_recovery.py
- backtest_robustness_test.py
- backtest_root_cause.py
- backtest_shrink_indicator.py
- backtest_test1.py
- backtest_test3.py
- backtest_test3_sweep.py
- backtest_test3_sweep2.py
- backtest_test3_sweep_all_small.py
- backtest_test4.py
- backtest_test5.py
- backtest_test6.py
- backtest_test6_v2.py
- backtest_test7.py
- backtest_test7_batch1.py
- backtest_test7_robust.py
- backtest_test7_robust2.py
- backtest_test7_scale.py
- backtest_test7_self.py
- backtest_time_vs_price.py
