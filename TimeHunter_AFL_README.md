# TimeHunter ATR ? versi aktif

AFL utama memakai SMA30, High20, rebound satu bar, hold200, **pullback1 ATR** dan **fading2 ATR**. ATR14 memakai Wilder smoothing dengan seed mean14 TR pertama. Kedua ambang memakai ATR dari bar sebelumnya. Acuan fading tetap Open bar terbaru; sinyal dieksekusi next tradable Open. Tidak ada syarat posisi rugi baru.

Baseline persentase diarsipkan di TimeHunter_Fading_Percent_Baseline.afl dan TimeHunter_Percent_Baseline_README.md. Default ATR ditentukan sebelum hasil, bukan pemenang tuning per pasar.

## Pengaturan AmiBroker

- Daily, Pad and align Off. Matikan built-in stops, early-exit fee dan seluruh biaya tambahan.
- Parameters: Hold bars200, SMA period30, ATR period14, Pullback ATR multiple1, Fading ATR multiple2, Fading On.
- Require positive volume=Yes untuk saham/crypto dengan volume riil. **No untuk data forex lokal yang volume-nya tidak tersedia/semua nol.**
- Gunakan riwayat lengkap yang sama untuk seed ATR. Batas hari forex mengikuti sesi sumber04:00; zona waktu sumber belum diketahui. Jumlah bar sama bukan durasi kalender sama.
- Explore untuk ledger sinyal independen alokasi modal. Backtest memakai modal1 miliar/posisi100 ribu sebagai test harness, bukan rancangan portofolio.
- Satu posisi per ticker, tanpa averaging down. ATR nol/tidak tersedia memblokir sinyal harga. Exit waktu tetap Close bar200; order menunggu saat volume nol. Exit code5 adalah valuasi akhir tanpa fill, bukan transaksi nyata.

## Hasil Python default, seluruh riwayat tersedia

| Pasar | N | WR | PF | Payout | Mean/trade | Numerik |
|---|---:|---:|---:|---:|---:|---:|
| Saham | 5162 | 47,71% | 2,13 | 2,22 | 7,60% | 4/5 |
| Forex04 | 96 | 53,13% | 1,31 | 1,15 | 0,33% | 4/5 |
| Crypto | 334 | 49,10% | 3,14 | 3,23 | 19,78% | 4/5 |

Ini perbaikan ukuran relatif volatilitas, belum peningkatan kinerja atau7/7. Saham/crypto gagal WR>50%, forex gagal payout>2. Dari12 pasangan koefisien, belum ada yang lolos5/5 di ketiga pasar sekaligus. Seluruhnya eksplorasi pada data yang sudah dilihat. Periode full berbeda; perbandingan tanggal bersama tersedia dalam laporan. Crypto dipilih dari pasangan yang masih ada; corporate action/survivorship saham serta sumber timezone forex belum tervalidasi sepenuhnya.

Mean adalah return per transaksi, bukan CAGR/portofolio. PF berbasis return dengan notional entry sama.

## Reproduksi

python backtest_timehunter_atr.py

python -m unittest test_timehunter_atr.py test_grid_timehunter.py

24 tes lolos, termasuk invariansi skala harga, prefix causality, ATR sebelumnya, seed/ATR nol dan eksekusi lama. AFL belum dikompilasi/dijalankan langsung dalam AmiBroker. Ledger, sensitivitas dan laporan: timehunter_atr_results/.
