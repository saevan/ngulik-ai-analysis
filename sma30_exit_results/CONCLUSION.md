# Kesimpulan SMA30 sebagai exit pengganti H200

16 simulasi selesai, dua entry berbeda, dua biaya dan dua prioritas saham. Exit baru adalah Close<SMA30 pada bar selesai lalu next tradable Open, tanpa batas hold200, fading5ATR dari Open bar berjalan tetap aktif. Tidak menggunakan fill pada nilai SMA atau Close sinyal.

Breakout+ER fee-only: CAGR33.43% menjadi35.24%, MDD-56.33% menjadi-39.47%, tetapi bulanrekor127/308 menjadi89/308 dan WR62.65% menjadi40.77%. Transaksi340 menjadi1989, meanholding180.66 menjadi25.33bar. Saat sideways return tahunan ekuivalen18.97% menjadi18.58%, sehingga tidak ada peningkatan pada ukuran tersebut. Stress spread: CAGR29.92% menjadi17.87%, bulanrekor117/308 menjadi57/308, sideways15.25% menjadi1.68%.

Entry AFL pullback fee-only: CAGR17.40% menjadi20.30%, tetapi MDD-57.53% menjadi-63.03%, bulanrekor91/308 menjadi74/308, WR53.75% menjadi26.71%. Transaksi333 menjadi4451, meanholding186.78 menjadi14.05bar. Stress spread: CAGR14.70% menjadi-10.07%, MDD-97.37%, bulanrekor8/308. Entry SMA bukan sinyal cross sekali; setup dapat berulang setelah exit sehingga transaksi bertambah banyak.

Reverse priority memberikan pola biaya sama: Breakout fee-only27.73% menjadi32.06%, spread24.16% menjadi15.47%; pullback fee-only20.00% menjadi30.39%, spread16.99% menjadi-2.99%. Sensitivitas ini bukan validasi out-of-sample. Spread memakai grid modern/lot100 dan1tick per sisi pada data yang mungkin adjusted; bukan quote historis aktual. Kesimpulan biaya berlaku pada asumsi stress tersebut.

SMA30 membantu perputaran dan beberapa ukuran fee-only, tetapi belum merupakan pengganti baseline yang unggul secara menyeluruh atau mendekati benchmark Swinger ideal. Tidak memenuhi WR>50% pada seluruh hasil SMA30, tidak membuktikan tujuh kriteria, dan belum diuji lintas pasar.16unit test lulus, baseline Breakout direproduksi, kausalitas prefix entry pullback diperiksa, dan seluruh ledger/atribusi direkonsiliasi. AFL aktif tidak diubah; ini replikasi sinyal Python dalam model alokasi10slot, bukan hasil native AmiBroker dengan fixed-notional harness AFL.
