# Acuan lintas pasar — riset 6 Oktober 2026

Status: riset definisi, belum penggantian AFL atau backtest normalisasi. Tidak ada indikator yang otomatis menjamin WR/PF atau distribusi sinyal sama di semua pasar.

## Tiga pengertian yang perlu dipisahkan

1. Bisa dihitung dari data yang sama: OHLC tersedia pada saham/forex/crypto.
2. Ukuran dapat dibandingkan: bebas nominal harga, dan bila perlu relatif terhadap volatilitas/distribusi historis.
3. Kinerja transferable: parameter dan aturan sama tetap memenuhi kriteria pada data baru dari berbagai pasar. Ini harus diuji, bukan disimpulkan dari normalisasi.

Bar adalah satuan observasi lintas pasar, bukan satuan risiko/waktu kalender yang setara. Timeframe, zona waktu, sesi, hari kosong dan definisi bar harus ditentukan. Crypto punya bar akhir pekan; hasil agregasi forex lokal sudah sensitif terhadap batas hari.

## Audit baseline

| Komponen | Sifat | Status |
|---|---|---|
| Hold200/SMA30/High20 | Hitungan bar | Portable, tergantung pembentukan bar |
| Close > SMA30 | Perbandingan relatif | Bebas pengalian skala harga positif, bukan jaminan distribusi sinyal sama |
| Close > Close sebelumnya | Arah rebound | Bebas nominal harga, tidak mengukur kekuatan gerakan |
| Pullback2% | Rasio harga | Bebas nominal, belum relatif volatilitas |
| Fading30% dari Open bar berjalan | Rasio harga | Bebas nominal, belum relatif volatilitas; tidak terpicu di sampel forex |
| Volume > 0 | Asumsi fill | Memerlukan metadata pasar/vendor; forex lokal mencatat semua volume nol |

## Kandidat ukuran yang lebih sebanding

- Gerakan/ATR: (Open-Low)/ATR sebelumnya untuk fading; (High tertinggi20-Close)/ATR sebelumnya untuk kedalaman pullback. ATR mentah masih satuan harga; rasionya bebas satuan dan relatif volatilitas. ATR sebelumnya membuat ambang tersedia sejak Open. N dan koefisien k harus dibekukan lintas pasar; ATR nol/tidak tersedia tidak menghasilkan sinyal.
- Z-score rolling: (nilai-rata-rata)/simpangan baku pada riwayat. Terstandardisasi tetapi tidak mengasumsikan data normal atau peluang ekor sama. Hindari full-sample mean/std.
- Persentil rolling: posisi ukuran saat ini dalam distribusi ukuran yang sama pada bar-bar sebelumnya. Dapat membandingkan kelangkaan historis; bukan jaminan frekuensi masa depan sama. Wajib window mundur, penanganan ties dan warmup konsisten.
- RSI/ADX/Stochastic/%B: rasio atau posisi relatif, bukan angka harga mentah. Skala seragam tidak menjamin level ambang mempunyai makna prediktif/frekuensi sama. %B dapat di luar rentang band.
- PPO/ROC/ATRP: menghilangkan pengaruh nominal harga, tetapi angka tetap masih bisa berbeda jauh karena volatilitas pasar.

Kurang sebanding langsung: nominal harga/points/pips tetap, ATR mentah dengan ambang absolut, nilai MACD mentah dengan ambang absolut, volume nominal, jam bursa spesifik. MACD crossover atau tanda MACD tidak sama dengan ambang MACD absolut; jangan menyebut seluruh keluarga MACD tidak transferable.

Usulan minimal untuk riset berikutnya: pertahankan logika trend/pullback/rebound/time/fading, bandingkan ambang pullback dan fading dalam satuan ATR atau persentil. Ini perubahan ukuran/ambang yang tetap harus dibacktest terhadap baseline; jangan mengklaim ekuivalen dengan aturan persentase lama. Acuan fading tetap Open BAR TERBARU, bukan harga entry/high/peak posisi. Tidak otomatis menambah oscillator baru.

## Sumber primer

- ATR, True Range, Wilder smoothing dan adaptasi volatilitas: https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr
- RSI dan ketergantungan ambang pada karakter harga/tren: https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/RSI
- PPO versus level harga: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/percentage-price-oscillator-ppo
- %B, posisi terhadap band dan nilai di luar band: https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/percent-b
- Struktur OTC forex: https://www.bis.org/publications/qr-201912/sizing-global-foreign-exchange-markets

Klasifikasi dan usulan rumus di atas adalah analisis riset, bukan bukti dari sumber bahwa strategi akan profitable secara universal.
