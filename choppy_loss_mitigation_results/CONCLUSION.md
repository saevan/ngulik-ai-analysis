# Mitigasi berhasil mengecilkan rata-rata rugi, belum memperbaiki sistem

20simulasi selesai:8konfigurasi x2biaya, lalu baseline dan kandidatloss-reduction/CAGRspreadterbaik diuji prioritas terbalik. Entry ChoppyRangeEscape10/cost8/marketER<0.3 tetap; perubahan hanya exit sistemkedua. Main dan AFL aktif tidakdiubah.24unit test lulus termasuk fixedentryATR/nextOpen/suspension.

Fee-only baselineavg loss7.96%,WR36.92%,CAGR10.20%. Stopentry0.5ATR:loss4.04%,WR21.45%,CAGR6.84%;stop1ATR:loss5.40%,WR27.28%,CAGR7.76%;stop1.5ATR:loss6.55%,WR32.09%,CAGR9.32%;stop2ATR:loss7.20%,WR34.67%,CAGR8.67%. ExitLLV5tanpastop:loss6.54%,WR36.55%,CAGR7.95%;LLV3:loss5.51%,WR33.81%,CAGR3.65%;LLV5+stop1:loss5.11%,WR29.09%,CAGR4.91%. Semua CAGRfee lebih rendah dari baseline.

SpreadbaselineCAGR1.98%. Stop0.5/1/1.5/2 =>-8.02/-4.09/-2.55/-0.42%;LLV5/3=>-2.53/-8.53%;combo-7.96%. Seluruh kandidat tetap negatif pada return tahunan ekuivalen sidewaysspread. Reversepriority baseline2.17%vsstop2 0.31%, pola ketertinggalan bertahan.

Matched-entry diagnosis (ticker+tanggalentry sama, bukan seluruhportofolio): stop0.5 memotong747dari1028lossesmenjadi losslebihkecil/hasillebihbaik, tetapi266dari596baselinewinners berubahmenjadiloss. Stop1:640dari1018losses membaik,160dari590winners menjadiloss. LLV5:648dari1035losses membaik,90dari588winners menjadiloss. Ini menggunakan hasilakhir untuk diagnosis, bukan rulemasa depan; sampel hanyaentryberpasangan, ukuranposisi/cashpathdanentrytambahan tetapberbeda. Menjelaskan tradeoff nyata tanpa mengklaim dekomposisiCAGR kausal lengkap.

Stop berdasarkan Close lalu next tradableOpen bukan stopmarketintraday dan tidak menjamin bataskerugian; gap/fee/suspensibisamelebihiambang. AngkaATR tetapdarisebelumentry agar stop tidakmelebar saatvolatilitasnaik. Tidak otomatismengadopsivariankarena avg lossmengecil; belum ditemukan dominasi netprofit/sideways. In-sample, stressspreadcounterfactual, datalimits tetap.
