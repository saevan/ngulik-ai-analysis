# Hasil mitigasi exit sistem kedua

Uji lanjutan selesai: 14 simulasi, melanjutkan 20 simulasi batas rugi/LLV. Sistem yang diuji hanya Choppy Range Escape10/cost8 dengan entry market ER20 < 0.30, exit dasar prior LLV10 atau fading2ATR, tanpa H200. Sistem utama dan AFL aktif tidak berubah.

Periode saham 4 Januari 2000–15 Agustus 2025; modal Rp1 miliar, maksimal 10 posisi, alokasi entry 10% equity penutupan sebelumnya dibatasi kas, compounding. Fee beli 0,15%, jual 0,25%. Skenario tambahan memakai fraksi modern BEI, lot100 saham, dan satu tick tiap sisi sebagai asumsi stres, bukan bid/offer historis teramati.

Exit tambahan memeriksa 3/5/10 bar pertama setelah entry, menghitung 1/2 penutupan berturut-turut di bawah harga entry sekaligus level breakout asli; eksekusi pada Open berikutnya yang dapat diperdagangkan. Level breakout tetap, tidak mengikuti HHV baru. Ini sinyal berbasis Close, bukan jaminan batas kerugian intraday.

Semua enam variasi menurunkan rata-rata rugi sekaligus WR, tetapi CAGR lebih rendah daripada baseline dalam kedua skenario biaya. Kandidat dengan CAGR tertinggi di antara exit tambahan: jendela3/konfirmasi2. Fee-only: rata-rata rugi 6,68% vs 7,96%; WR32,51% vs36,92%; CAGR9,69% vs10,20%; MDD-48,16% vs-45,69%; bulan rekor57/308 vs55/308. Dengan spread: CAGR0,12% vs1,98%; ekuivalen tahunan sideways-15,03% vs-12,32%.

Diagnosis entry berpasangan pada kandidat3/2: 490 dari1053 transaksi yang semula rugi membaik, tetapi62 dari607 transaksi yang semula untung berubah rugi. Diagnosis ini hanya pasangan ticker/tanggal entry sama dan memakai hasil akhir untuk audit; bukan aturan prediksi atau dekomposisi penuh CAGR. Perubahan kas/slot juga mengubah transaksi yang terealisasi.

Kesimpulan gabungan: memperketat stop, memperpendek LLV, dan exit kegagalan breakout awal berhasil memperkecil rata-rata rugi, tetapi belum memperbaiki profitabilitas sistem kedua. Tidak ada kandidat yang diadopsi atau digabungkan. Hasil ini tidak membuktikan semua bentuk mitigasi mustahil; hanya menolak variasi yang diuji sebagai peningkatan kinerja. Penelitian in-sample, bukan validasi independen. Return tahunan ekuivalen sideways berasal dari atribusi return harian pada tanggal sideways, bukan CAGR portofolio mandiri yang dapat diperdagangkan.

Reproduksi: mitigate_failed_breakout.py. Hasil lengkap: comparison.csv, matched_entries.csv, REPORT.md dan ledger/equity setiap varian. Pengujian unit memeriksa level asli, reset konfirmasi, masa evaluasi, serta regresi engine terkait; baseline equity juga dibandingkan dengan hasil asli.
