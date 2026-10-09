# TimeHunter right-tail experiment

File AFL: `TimeHunter_RightTail_Gross.afl`. Versi eksperimen terpisah dari `TimeHunter_Fading_Gross.afl` (SMA30, hold200, fading30% tanpa gate rugi).

## Aturan default

- Entry sederhana: Close bar sebelumnya > SMA30, beli next tradable Open. Tidak perlu pullback atau rebound. Parameter Entry dapat diubah ke Always (tanpa filter).
- Hold terjadwal 400 bar, termasuk bar entry. Tidak ada profit target. Posisi untung tidak keluar lewat fading; tetap bisa keluar pada Close bar ke-400 atau batas akhir backtest.
- Sebelum deadline, jual bila **Low <= Open bar berjalan * 0.95 DAN Close < harga entry**. Keduanya diperiksa setelah bar selesai. Jual next Open dengan volume positif. Gap harga tetap berlaku; 5% bukan stop loss terhadap entry.
- Gate rugi memakai Close, bukan Low. Bila sempat rugi intrabar tetapi pulih di Close, tidak ada sinyal fading. Order yang sudah antre tidak dibatalkan bila Open berikutnya pulih.
- Posisi rugi yang turun perlahan tanpa menyentuh fading bisa tetap bertahan lama. Default tidak memakai loss timeout. Grid juga menguji opsi loss timeout 20 bar, tetapi opsi itu tidak diaktifkan dalam AFL contoh ini.
- Satu posisi per saham; tanpa averaging down; reentry paling cepat bar setelah exit. Sinyal entry yang tertunda tetap antre selama volume nol.

## Pengujian AmiBroker

Gunakan Daily, watchlist dan OHLCV sama, 12 Juli 1994–15 Agustus 2025; Pad and align Off. Matikan stop bawaan dan biaya tambahan. Parameter default: Hold bars=400, SMA period=30, Fading percent=5, Entry=Above SMA, Fading=On, Require positive volume=Yes. Explore untuk ledger per transaksi, Backtest untuk laporan dengan ukuran posisi uji. Modal awal dan ukuran posisi hanyalah test harness, bukan rancangan portofolio.

Biaya, komisi, bunga dan slippage harga nol. Posisi akhir periode ditutup/ditandai seperti engine sebelumnya; exit code 5 adalah valuasi tanpa fill pada volume nol. Statistik Python tidak berbobot ukuran posisi; PF berbasis jumlah return positif/absolut jumlah return negatif, bukan laba rupiah portofolio dengan alokasi berubah.

## Hasil Python contoh default

3.818 transaksi; WR18,78%; PF5,46; payout22,67; mean30,06%; median-4,88%; avg win195,97%; avg loss magnitude8,64%. Win holding318,3 bar; loss holding57,0 bar. P95 return148,34%; P99 return536,72%; skewness55,52. Transaksi terburuk-60,53%. Mean adalah return per transaksi, bukan CAGR.

Sebanyak1.115 transaksi sempat mencapai minimal+10% intratrade lalu berakhir negatif. Rata-rata selisih peak intratrade ke hasil akhir35,50 poin persentase; peak tidak dianggap harga exit yang dapat diketahui sebelumnya. Top1% transaksi menyumbang54,07% total keuntungan positif. Setelah membuang ceil(1%) return tertinggi, mean tersisa10,27%.

Kontrol dengan entry/hold/fading sama tetapi fading juga aktif saat untung:15.411 transaksi, WR40,77%, PF1,58, payout2,07. Kontrol tanpa fading:1.173 transaksi, WR54,73%, PF7,31, payout5,90, avg loss30,29%. Jadi loss gate meningkatkan payout dan memangkas avg loss dibanding tanpa fading, tetapi tidak unggul pada semua metrik.

Seluruh36 konfigurasi loss-only pada grid ini gagal WR>50% (WR tertinggi43,36%). Jangan menyatakan lolos tujuh kriteria. Data/periode sama dengan pencarian sebelumnya; belum validasi independen. Corporate action dan survivorship belum diverifikasi, relevan khususnya bagi ekor return sangat besar.

## Reproduksi dan status verifikasi

`python backtest_timehunter_right_tail.py`

`python -m unittest test_timehunter_right_tail.py`

Lima tes lolos: fade saat untung diabaikan, rugi+fade dijual next Open, gap rugi tanpa fading tidak memicu, pemulihan di Close tidak memicu, loss timeout dieksekusi next Open. Semua konfigurasi kontrol tanpa loss gate juga cocok persis dengan return engine lama per ticker. AFL belum dikompilasi/dijalankan langsung dalam AmiBroker.

Hasil lengkap: `timehunter_right_tail_results/REPORT.md` dan `grid.csv`. Contoh default dipilih sebelum hasil sweep, bukan pemenang ranking.
