# Checkpoint 15 Oktober 2026

Kandidat terbaik: buy stop HHV20 + ER20 sebelumnya ≥0,3, lewati gap up >2%, jual di Close saat Open gap down >2% untuk exit tertunda, urutan momentum 120 hari, fade2 ATR dari Open bar berjalan, exit Close < SMA30, tanpa gate pasar, tanpa inverse. Full 2000–2025: fee 48,5%/136 bulan rekor, spread 1 tick 28,1%/100, spread 2 tick 13,6%/58. Mesin: `backtest_stop_execution.py`.

Urutan riset hari ini (baca CONCLUSION.md tiap folder):
1. `cagr_records_results/`: inverse merugikan CAGR/rekor; gate ER pasar membantu train tapi gagal 2021–25.
2. `swinger_gap_results/`: keunggulan Swinger ideal kebanyakan dari fill tidak kausal; buy stop di HHV20 lebih baik dari next Open.
3. `market_condition_results/`: kita kalah di breadth sempit/bear; filter kondisi gagal di luar train.
4. `market_property_results/`: sifat stabil (gap up memudar, gap down memantul, volume breakout, momentum); gapdown_close dan mom120 konsisten.
5. `robustness_results/`, `cost_lever_results/`, `gapup_exit_results/`: stress biaya, tuas biaya, gap-up exit (ditolak).

AFL aktif tidak diubah. Hasil bukan holdout independen.
