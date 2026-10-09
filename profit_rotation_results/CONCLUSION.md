# Kesimpulan

24 simulasi selesai: sembilan kombinasi aktivasi/trailing dan baseline pada dua skenario biaya, ditambah baseline serta kandidat CAGR spread tertinggi dengan prioritas ticker dibalik. Semua sembilan kombinasi kalah terhadap baseline pada CAGR dan jumlah bulan rekor, baik fee-only maupun stress spread. Hasil ini menolak penerapan langsung keluarga exit yang diuji; bukan bukti semua bentuk rotasi tidak mungkin berhasil.

Kandidat CAGR tertinggi di kedua skenario utama: aktivasi4 ATR, retracement4 ATR. Fee-only: transaksi573 vs340, CAGR23.85% vs33.43%, bulan rekor99/308 vs127/308, MDD-60.47% vs-56.33%. Stress spread: transaksi553 vs340, CAGR16.62% vs29.92%, bulan rekor70/308 vs117/308, MDD-64.27% vs-59.70%. Dengan prioritas terbalik kandidat juga tertinggal: spread14.99% vsbaseline24.16%.

Fee-only WR naik65.79% dari62.65%, tetapi payout turun1.49 dari3.16. Jadi keberhasilan menambah transaksi atau persentase menang tidak cukup untuk mengganti keuntungan per pemenang yang berkurang. Pengujian portofolio sudah memasukkan reinvestasi setelah keluar; tidak menjumlahkan CAGR strategi terpisah. Identitas transaksi berbeda sehingga ini bukan dekomposisi kausal matched-trade.

Eleven unit tests passed, including activation, next-Open gap execution and suspension queue. Baseline curves reproduce saved outputs. Active AFL unchanged; experimental option is off by default. No cross-market or independent out-of-sample validation. Swinger ideal remains an aspirational target with its documented noncausal fill limitations.
