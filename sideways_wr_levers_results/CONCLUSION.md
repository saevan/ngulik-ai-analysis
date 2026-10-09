# Tuas yang memengaruhi WR

28simulasi selesai:14konfigurasi (baseline+13perubahan satu faktor) x2biaya. Ini pengujian standalone keluarga support-rebound, bukan perubahan main strategy. Market sideways selalu ERproxy<0.3 pada bar sebelumnya; ambang ER saham sendiri divariasikan. Histori2000-2025, seluruhnya in-sample; WR bukan jaminan expectancy/CAGR positif.

Baseline fee-only WR45.37%,avgwin3.14%,avgloss3.87%,CAGR-3.24%. Pengaruh WR terbesar dalam rentang yang diuji adalah fading:0.5ATR=>37.65%,1ATR=>45.37%,2ATR=>50.22%. Melonggarkan fading memberi peluang posisi pulih, tetapi avgloss naik dari2.54% (0.5ATR) menjadi4.22% (2ATR). Pada2ATR avgwin3.01%,mean return-0.59%,CAGR-2.67%; WRimpas sekitar58.36% jika distribusi besaran keuntungan/kerugian dianggap tetap. Ini perhitungan deskriptif, bukan asumsi bahwa WR bisa dinaikkan tanpa tradeoff.

Supportlookback10/20/40 memberi WR47.86/45.37/43.53%; memilih10menaikkanWR tetapiCAGR turun ke-4.65%. ERthreshold0.1/0.2/0.3/0.4 memberi45.72/46.31/45.37/46.55%, efek kecil dan tidak monoton. Konfirmasi tambahan Close>Highsebelumnya menurunkanWR42.98%, bukan menaikkan. RecoverytargetSMA5/10/20 memberi45.78/45.37/44.71%; target lebihdekat memangkasavgwin2.42%, targetlebihjauh menaikkanavgwin3.89% sekaligusavgloss4.59%. Age5bar menurunkanWR42.15%;10dan20hampirsama45.37%.

Seluruh varian masih CAGRnegatif setelahfee, dan makin buruk pada stressspread. Tuas WR teridentifikasi tetapi belum ditemukan sistem sideways yangworks. Tidak gabung ke utama atau ubahAFL. Hasil tidak boleh digeneralisasi sebagai hukum universal; perubahan komposisi transaksi,slot dan timing turut berpengaruh. Kasus fading2WR50.22%namunrugi membuktikan masalah bukan WR saja.
