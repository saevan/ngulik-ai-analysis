# Entry baru: peluang terjaga, keunggulan setelah spread belum terbukti

23 simulasi selesai:11 konfigurasi training2000–2015 dengan spread, lalu satu kandidat diagnostik dibekukan dan dibanding baseline pada2016–2020,2021–2025,full2000–15Agustus2025, dua skenario biaya. Seluruh10 alternatif gagal minimal satu syarat training. Kandidat diagnostik bukan kandidat lolos. Ini riset adaptif pada data yang pernah diperiksa, bukan holdout independen.

Batas frekuensi ditetapkan sebelum hasil: minimal80% jumlah transaksi baseline pada periode/biaya sama. Baseline=entry RangeEscape10/cost8 tanpa filter ERsaham, dengan stop0.5entryATR; bukan versi ERsaham>=0.5 yang hanya965trade. Exit sama untuk semua: stop0.5ATR tetap dari entry, priorLLV10, fading2ATR dari Open bar berjalan; sinyal Close dijual next tradable Open, tanpa H200. Primary dan AFL aktif tidak berubah.

Entry diuji: HHV3/5 breakout, cross kembali di atas SMA5/10, tembus priorLLV5/10 intraday lalu Close pulih di atas support/Open, pullback ke SMA5 di atas SMA20/50, serta channel flip Swinger5/10 dengan nextOpen. Seluruhnya marketproxyER20<0.3 dan range20/cost>=8; tidak mensyaratkan sahamERtinggi. Filter umum dipertahankan agar perbedaan utama berasal dari entry. Kelayakan tidak mengandalkan raw bidask historis.

## Kandidat diagnostik pullback20

Pada bar sinyal: Close>SMA20, Low<=SMA5, Close>Close sebelumnya, Close>Open. Range20 >=8kali estimasi biaya pulangpergi dari Close yang diketahui. Entry Open berikutnya jika pasar berlabel choppy dan bar dapat diperdagangkan. Ini entry pantulan di atas SMA20, bukan pullback AFL aktif; tanpa limit-fill ideal.

Dipilih berdasarkan mean return training tertinggi di antara konfigurasi yang menjaga frekuensi, karena tidak ada yang lolos seluruh gate. Bukan dipilih berdasarkan hasil validasi atau full. Pada training spread kandidat2126tradevsbaseline1726,WR20.18vs19.52%,CAGR-0.68vs-3.42%; sideways-22.27vs-23.34%. Masih negatif.

Fullfee beli0.15%jual0.25%, Rp1miliar/10slot/compounding:

| Metrik | Baseline stop ketat | Entry pullback20 |
|---|---:|---:|
| Transaksi |3385|3812|
| WR |21.45%|22.46%|
| Rata-rata rugi |4.04%|3.95%|
| Rata-rata untung |18.13%|18.72%|
| Rata-rata return trade |0.72%|1.14%|
| CAGR |6.84%|12.13%|
| Max drawdown |-50.86%|-56.12%|
| Bulan rekor |45/308|62/308|
| Cash sideways |31.32%|15.01%|
| Slot sideways |6.70|8.44|
| Annual equivalent sideways |-2.79%|-0.42%|

Jumlah transaksi naik12.61%, WRnaik1.01poinpersentase, rata-rata rugi turun0.09poinpersentase. Jadi perbaikan kualitas fee-only tidak dibayar pemangkasan frekuensi, tetapi perbaikannya kecil dan drawdown memburuk. CAGR positif full tidak membuktikan kemampuan khusus sideways.

Dengan spread1tickmasing-masing sisi, fraksi modern BEI dan100shares sebagai stresscounterfactual: baseline3657trade,CAGR-8.02%,sideways-26.62%; kandidat4257trade,CAGR-6.36%,sideways-27.57%,MDD-94.95%. Efek jumlah trade berbeda karena kas/slot/rounding ikut berubah, bukan entryrules berubah. Validasi2016–2020 spreadCAGR-8.08%,test2021–2025-22.75%vsbaseline-21.31%; WRtest14.97%vsbaseline15.55%. Perbaikan WR tidak bertahan di semua periode/biaya.

Swinger ideal targetchoppyWR50.46%/loss3.21%/1833entries tetap jauh; angkaSwingertradeentrychoppy menggunakan fullumurtrade. Sideways annual equivalent memakai equity pada harisideways, bukan CAGR portofolio mandiri. Posisi boleh bertahan lintasregime; cash berarti kas portofolio pada hari tersebut.

Kesimpulan: pola pantulan ini memberi arah entry yang menjaga peluang, tetapi BELUM layak diadopsi sebagai sistem sideways setelah biaya. Tidak digabung ke sistem utama. Tidak menyimpulkan semua strategi pantulan gagal atau hanya stop yang salah. Stop0.5ATR masih asumsi eksperimen, bukan batas loss terjamin.13unit test engine/stop/biaya lulus; prefixcausality entry seluruhframe, eligibility danfullbaselineequity regression lulus. Reproduksi search_choppy_new_entries.py, seluruhledger/comparison/PLAN/FROZEN/REPORT tersimpan. Utilization.csv dihitung dari hari marketproxy sideways.
