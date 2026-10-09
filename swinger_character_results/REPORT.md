# Karakter hasil dibanding target Swinger ideal

Kandidat kita: Breakout+ER, exitSMA30, fading2ATR, tanpa hold200. Fee0.15%/0.25%, tanpa spread, portofolio Rp1miliar/10slot/compounding, saham2000-2025. Swinger ideal diterima sebagai target aspiratif pilihan pengguna; tidak perlu transaksi identik.

## Profil seluruh transaksi

| Karakter | Kita | Swinger |
|---|---:|---:|
| Mean hold |20.39bar|19.04bar|
| Jumlah transaksi |2392|3241|
| Win rate |40.84%|51.90%|
| Rata-rata menang |19.73%|16.51%|
| Rata-rata rugi |7.00%|3.19%|
| Payout |2.82|5.17|
| Profit factor return berbobot sama pertrade |1.95|5.58|
| Mean net return pertrade |3.92%|7.03%|
| Fraksi transaksi rugi lebih10% |12.79%|1.54%|
| Rata-rata holding transaksi rugi |13.05bar|10.95bar|
| Bulan berturut-turut terlama tanpa rekor |33|5|

Profit factor di tabel berbeda dari PF rupiah portofolio karena pembobotan compounding; jangan campur kedua definisi. Distribusi untung besar kita bukan kelemahan paling mencolok: rata-rata pemenang kita lebih besar, dan p99return101.45% vs109.92%. Perbedaan deskriptif terbesar ada pada tingkat keberhasilan, besar/ekor kerugian, dan eksposur setelah perubahan exit.

## Saat sideways

Untuk transaksi yang ENTRY pada hari sideways (return seluruh umur transaksi, bisa melewati rezim lain):1475vs1833entry; WR39.86%vs50.46%; avgwin18.91%vs14.67%; avgloss7.04%vs3.21%; meanreturn3.30%vs5.81%; transaksi rugi>10%13.69%vs1.47%.

Untuk equity PADA HARI sideways: kas idle27.97%vs6.50%, rata-rata7.10vs9.44slot terisi, hari equitypositif49.90%vs57.34%, return tahunan ekuivalen20.10%vs87.15%, bulanrekor57/280vs191/280. Penilaian idle6.23% dari diskusi sebelumnya berlaku untuk H200, bukan kandidatSMA30/fade2 sekarang. Kesimpulan harus mengikuti versi strategi. Angka ini membuktikan eksposur berbeda, bukan bukti memaksakan kas terinvestasi akan meningkatkan profit.

## Sasaran karakter untuk penelitian berikutnya

Pertahankan holding sekitar19-20bar dan kekuatan pemenang, sambil menguji peningkatan WR menuju50-52%, pengurangan avgloss menuju3-3.2%, fraksi rugi>10% mendekati1-2%, serta kas idle sideways mendekati6-7% HANYA jika tambahan entry punya expectancy bersih positif. Target ini profil benchmark, bukan kombinasi parameter yang sudah terbukti dapat dicapai sekaligus. Mengubah exit dapat menurunkan avgwin/WR, sehingga harus menguji tradeoff, bukan mengasumsikan ukuran lain tetap.

Tidak ada dekomposisi kausal yang membuktikan kontribusi tiap faktor ke selisih CAGR. Timing, overlap, ukuran posisi, korelasi dan urutan keuntungan memengaruhi hasil. Expectancy identity lolos dan atribusi daily return direkonsiliasi. Tidak ada perubahan AFL atau parameter pada analisis ini.
