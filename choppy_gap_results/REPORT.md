# Diagnosis: apakah sideways menyebabkan tertinggal dari Swinger?

Hipotesis tidak didukung sebagai penjelasan utama. Modul Breakout + ER tetap berinvestasi saat sideways; filter ER berlaku per saham untuk entry baru, bukan perintah keluar ketika pasar sideways. Ini mengaudit modul Breakout + ER yang digunakan pada perbandingan terakhir, bukan mengganti AFL ATR Shared Candidate yang sedang terbuka.

Periode saham 4 Januari 2000 sampai 15 Agustus 2025. Modal awal Rp1 miliar, maksimum 10 posisi, compounding, fee beli 0,15% dan jual 0,25%. Tabel utama tanpa spread/fraksi agar sebanding dengan target Swinger ideal.

| Sistem | CAGR | Bulan rekor | Maximum drawdown | Transaksi |
|---|---:|---:|---:|---:|
| Swinger fill ideal AFL | 114,77% | 249/308 (80,84%) | -18,81% | 3.241 |
| Breakout + ER | 33,43% | 127/308 (41,23%) | -56,33% | 340 |
| Breakout tanpa ER | 18,07% | 78/308 (25,32%) | -56,60% | 338 |
| Swinger stop-order | 30,25% | 102/308 (33,12%) | -49,67% | 7.266 |
| Swinger sinyal asli, next Open | 21,51% | 83/308 (26,95%) | -55,52% | 3.086 |

Saat proxy pasar sideways, Breakout + ER mempunyai rata-rata 93,77% equity dalam posisi, rata-rata 9,83 dari 10 slot terisi, dan tidak ada hari penutupan tanpa posisi. Ada 193 entry aktual pada hari sideways. Return tahunan ekuivalen dari gabungan hari sideways adalah +18,97%; ini bukan CAGR strategi sideways yang berdiri sendiri.

Swinger ideal pada hari sideways memiliki eksposur hampir sama, 93,50%. Jadi perbedaan hasil bukan karena modal kita diam sedangkan modal Swinger bekerja. Rata-rata holding Breakout + ER 180,66 bar versus Swinger ideal 19,04 bar: posisi lama memenuhi slot dan memperlambat perputaran. Menghapus ER memperbanyak peluang sinyal, tetapi tidak otomatis menambah transaksi portofolio; kontrol tanpa ER menghasilkan 338 transaksi dan 16.527 penolakan entry karena slot penuh. Angka penolakan menghitung kejadian sinyal, bukan peluang unik yang pasti untung.

Dengan stress fraksi modern BEI, lot 100 saham dan satu tick pada masing-masing sisi, ER menghasilkan CAGR 29,92% dan 117/308 bulan rekor; tanpa ER menjadi 15,03% dan 65/308. Ini asumsi stress, bukan bid/offer historis yang diamati.

Swinger ideal juga mengungguli pada uptrend dan downtrend, bukan hanya sideways. Benchmark ideal tetap target aspiratif pilihan pengguna, tetapi 964 fill berada di luar rentang harian dan sinyal Close digunakan untuk fill pada level yang lebih awal. Selisih terhadap benchmark tidak bisa dianggap bukti keunggulan sideways yang dapat dieksekusi. Swinger stop-order mengubah pemicu sinyal; next Open lebih dekat dengan sinyal Close asli. Keduanya comparator, bukan reproduksi ideal AFL.

Kesimpulan: modul sideways layak menjadi hipotesis penelitian, belum terbukti diperlukan atau meningkatkan hasil. Modul kedua memerlukan aturan pembagian slot/modal karena portofolio hampir penuh; menambahkan sinyal saja tidak menyelesaikan hal tersebut. Uji tambahan harus mempertahankan mesin exit awal pada kontrol, memakai harga fill kausal serta biaya yang sama, dan membandingkan hasil gabungan, bukan menjumlahkan CAGR dua modul. Tidak ada perubahan AFL atau klaim tujuh kriteria terpenuhi.

Detail metode, batasan proxy, dan pengujian rekonsiliasi ada di METHODOLOGY.md. Angka dapat direproduksi dengan `python analyze_choppy_gap.py`.
