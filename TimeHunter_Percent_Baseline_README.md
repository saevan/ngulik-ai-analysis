# TimeHunter AFL — gross, current-bar Open fading

File: `TimeHunter_Fading_Gross.afl`. Default diperbarui 6 Oktober 2026: SMA30, hold=200, jendela High=20, pullback=2%, fading=30%, rebound satu bar. Atur SMA period=100 untuk mereproduksi baseline lama. Backtest versi aktif: `python backtest_timehunter_sma30.py`.

## Cara menjalankan

1. Buka file AFL di Formula Editor AmiBroker, lalu Send to Analysis.
2. Pilih Periodicity **Daily**, watchlist 100 saham yang sama, dan From–To **12 Juli 1994 sampai 15 Agustus 2025**. Gunakan riwayat lengkap untuk pemanasan indikator (minimal 100 bar jika membandingkan kedua versi).
3. Nonaktifkan **Pad and align** agar hitungan bar tetap mengikuti bar asli masing-masing saham. Gunakan data OHLCV dan penyesuaian corporate action yang sama; keluarkan bar intrahari TLKM yang tidak lengkap seperti pada data Python.
4. Parameter default: SMA period=30, Hold bars=200, Fading percent=30, Fading=On, Require positive volume=Yes. Pastikan parameter tersimpan di Analysis tidak mengganti default tersebut.
5. Nonaktifkan seluruh built-in stops (maximum loss, profit target, trailing, N-bar), biaya tambahan, early-exit fees, dan slippage di pengaturan eksternal. Formula menetapkan komisi dan bunga nol, tanpa slippage harga.
6. Klik **Explore**, ekspor CSV: setiap baris adalah satu transaksi selesai atau valuasi akhir periode. Kolom Date/Time bawaan adalah tanggal exit. Ini pembanding utama terhadap ledger Python.
7. Klik **Backtest** untuk laporan AmiBroker. Modal awal 1 miliar dan ukuran tetap 100 ribu per posisi hanya untuk menjalankan pengujian; Python sebelumnya tidak memodelkan alokasi modal. Jika order ditolak karena dana/aturan akun, laporan portofolio dapat berbeda dari Exploration. Jangan menafsirkan equity curve ini sebagai hasil portofolio yang sudah dirancang.

## Aturan tepat

- Close bar sinyal > SMA sesuai parameter (default SMA30), `1 - Close / HHV(High,20) >= 0.02`, dan Close > Close sebelumnya. High dinormalkan ke maksimum OHLC seperti Python.
- Beli Open berikutnya yang volumenya positif. Sinyal entry yang tertunda tetap antre meskipun kondisi entry kemudian berubah.
- Satu posisi long per saham. Tidak menambah posisi. Entry ulang paling cepat satu bar setelah penjualan, dengan filter entry kembali.
- Fading: `Low[t] <= Open[t] * 0.70`. Low dinormalkan ke minimum OHLC. Acuan berubah setiap bar dan tidak memakai harga entry/PnL.
- Sinyal fading dari bar yang sudah selesai dijual pada Open berikutnya dengan volume positif, bukan pada harga ambang fading.
- Exit waktu pada Close bar ke-200, entry dihitung bar pertama. Bila volume nol, antre sampai Open yang dapat diperdagangkan. Sinyal fading hanya diambil sebelum deadline exit waktu; fading yang sudah antre mendapat prioritas pada Open.
- Posisi tersisa ditutup pada Close akhir periode. Jika volume akhir nol, kode exit 5 adalah **valuasi tanpa fill**, bukan transaksi nyata. Ini sengaja mengikuti pembukuan Python; laporan Backtest standar akan membukukannya sebagai sell sintetis, sehingga gunakan kolom penanda Exploration.
- Tidak memakai `ApplyStop` atau tambahan delay: tanggal dan harga eksekusi ditentukan langsung oleh loop. Data volume harian digunakan sebagai asumsi apakah fill dapat terjadi, sama seperti engine Python.

## Pembanding hasil

Baseline SMA100 pada data yang sama: 1.974 transaksi, WR 53,44%, mean gross 26,26%, median 3,92%, average win 69,45%, average loss magnitude 23,82%, payout 2,92. Ini statistik persentase **per transaksi**, bukan CAGR atau return portofolio.

Versi aktif SMA30: 2.181 transaksi, WR 52,59%, PF 3,107, mean gross 24,07%, median 2,20%, average win 67,49%, average loss magnitude 24,67%, payout 2,736. Lima kriteria numerik lolos pada periode gabungan; belum validasi independen. Transaksi terburuk -96,92%. Ledger hasil ulang cocok dengan sweep sebelumnya. Hasil: `timehunter_sma30_results/`.

Hitung WR sebagai jumlah return > 0 dibagi semua transaksi, termasuk breakeven pada denominator. Average loss memakai hanya return < 0. Payout = average positive return / absolute average negative return; **bukan profit factor**. Gunakan CSV Exploration untuk perbandingan tidak berbobot ukuran posisi.

AFL belum dikompilasi/dijalankan dalam AmiBroker di lingkungan ini. Jangan menganggap hasil Python sudah direproduksi oleh AmiBroker sebelum menjalankannya dengan data yang sama.

## Referensi API resmi

- https://www.amibroker.com/guide/afl/settradedelays.html
- https://www.amibroker.com/guide/afl/setoption.html
- https://www.amibroker.com/guide/afl/status.html
