# Handoff TimeHunter / Swinger — 9 Oktober 2026

Ini ringkasan terstruktur untuk melanjutkan percakapan VS Code di web, bukan transkrip lengkap chat atau Claude. Semua kode, data lokal, catatan dan hasil penelitian ikut dalam ZIP. Baca dokumen ini dahulu, lalu AGENTS.md, STRATEGY_NOTES.md dan laporan yang dirujuk. Catatan lama merekam versi lama; jangan menjadikannya konfigurasi terbaru.

## Tujuan dan preferensi pengguna

Berkomunikasi dalam Bahasa Indonesia. Fokus sistem investasi, bukan RecoverHunter untuk lomba. Setiap dugaan pengguna tentang strategi harus dicek ke kode/data atau langsung diuji; pisahkan observasi, interpretasi, dan kausalitas yang belum terbukti. Jangan sekadar menyetujui atau menawarkan backtest.

Benchmark yang sengaja dipilih adalah Prototype Swinger dengan fill ideal sesuai AFL. Targetnya karakter hasil, bukan transaksi identik. Jangan berulang kali mengganti benchmark. Laporkan asumsi fill secara proporsional.

Tujuh kriteria historis: mean return > median, average win > magnitudo average loss, payout > 2, WR > 50%, expectancy positif, penerapan lintas pasar, dan kausalitas eksekusi. Lima angka lolos in-sample bukan tujuh kriteria terbukti. Belum ada kandidat terkini terbukti 7/7.

User pernah menyebut 'acak'; maksudnya mencari tuas parameter yang memengaruhi WR, bukan random entry. Random-entry experiment lama dihentikan; jangan laporkan sebagai selesai.

## Tiga versi yang wajib dibedakan

1. **AFL aktif: TimeHunter_ATR_Shared_Candidate.afl.** Entry pullback: Close > SMA30, Close > Close sebelumnya, HHV High10 termasuk bar berjalan minus Close >= 0.25 ATR sebelumnya. Exit Close < SMA30 atau fading 5 ATR, next tradable Open; tanpa H200. Masih harness gross fixed-notional, bukan portfolio compounding penelitian. Tidak diubah oleh eksperimen terbaru. H200_Archive hanya arsip.
2. **Utama penelitian:** Close > HHV High20 bar sebelumnya DAN ER saham20 >= 0.3; exit Close < SMA30 ATAU Open bar berjalan - Low >= 2 ATR14 sebelumnya. Sinyal Close, eksekusi next tradable Open. Long only, tanpa hold cap. Fading selalu dari Open BAR BERJALAN, bukan Open entry.
3. **Sistem kedua terbaru:** balik raw signal utama: sell utama menjadi buy kedua; buy utama menjadi sell kedua. Masih long only, bukan short. Gate ER PASAR20: >=0.3 entry utama; <0.3 entry kedua; unknown tidak entry. Exit posisi mengikuti modul pemilik, meski rezim berubah. Tidak otomatis forced sell saat ganti rezim pada baseline.

Arahan terakhir sebelum pindah: 'coba sesuaikan optimalisir agar kedua sistem perform saat mereka sedang bekerja'. Optimasi sudah selesai dan gagal syarat; lihat bagian berikut. Kandidat pullback low-ATR/LLV5 yang sempat disukai pengguna adalah penelitian sebelumnya, bukan arsitektur terbaru.

## Hasil paling baru: 48 simulasi optimasi selesai

Kode optimize_primary_inverse_regimes.py; output optimized_inverse_regime_results/. Baca CONCLUSION.md, comparison.csv, PLAN.json dan FROZEN.json.

Grid HHV10/20 x SMA20/30 x forced regime-end exit False/True: 8 konfigurasi. Hubungan sinyal utama/inverse dipertahankan. ER saham/pasar 20 dan threshold0.3, fading2 tetap. Train 2000–2015 memakai fee+spread, setiap konfigurasi diuji primary-only, inverse-only dan gabungan (24 run). Syarat: masing-masing standalone CAGR dan own-regime return positif, gabungan CAGR dan kedua regime return positif. SEMUA GAGAL.

Fallback diagnostik yang dibekukan: HHV20/SMA20/carry (rotate=False), passed=false. Ini bukan pemenang layak adopsi. Diuji dibanding baseline HHV20/SMA30/carry, standalone kedua modul, dua biaya, validation2016–2020/test2021–2025/full2000–2025 (24 run lagi). Data historis sebelumnya pernah dilihat, bukan holdout independen.

| Gabungan | Full fee CAGR | Full fee+spread CAGR | Test2021–25 fee+spread CAGR |
|---|---:|---:|---:|
| Baseline HHV20/SMA30 | 15.80% | 5.51% | 1.02% |
| Diagnostik HHV20/SMA20 | 15.54% | 3.65% | -1.11% |

Inverse HHV20/SMA20 full fee+spread CAGR -0.89%, atribusi choppy annual equivalent -9.12%; test CAGR -1.86%, choppy -8.05%. Tidak layak mengatakan kedua modul sudah perform di rezimnya. Tidak ada perubahan AFL/default yang diadopsi.

## Baseline switching dan benchmark

backtest_primary_inverse_switch.py / primary_inverse_switch_results/STRATEGY.md: utama+inverse shared cash/slots. Full baseline fee gabungan CAGR15.80%, WR55.11%, MDD-58.38%, rekor81/308bulan; fee+spread CAGR5.51%, WR50.49%, MDD-74.37%, rekor36/308. Main dengan market-trend gate standalone CAGR27.90% fee /15.96% spread. Inverse standalone fee CAGR4.79%, WR66.13%, average win14.20%, loss19.99%, holding74.63bar. WR tinggi tidak menjamin sistem sideways menguntungkan.

Prototype_Swinger_Source.afl dan backtest_prototype_swinger.py: HHV/LLV5 state channel, cross Close/TSL, ideal fill previous TSL di bar sinyal. Fill aspiratif ini bisa di luar OHLC dan bukan simulasi order kausal; sengaja tetap benchmark.

Perbandingan khusus choppy yang benar: backtest_choppy_head_to_head.py / choppy_head_to_head_results. ENTRY Swinger digate ER pasar<0.3 dan portofolio dihitung ulang. Swinger 2,575 transaksi, WR51.53%, avg win14.69%, avg loss3.14%, hold19.20bar, full CAGR71.13%; atribusi choppy annual equivalent99.26%, rekor195/280bulan choppy. Fee0.15/0.25%, ideal tanpa spread. Jangan campur dengan subset1,833 trade dari ledger benchmark lama atau full tanpa gate CAGR114.77%.

## Definisi data, biaya dan statistik

- Modal Rp1 miliar, 10 slot (istilah pengguna '10 lot x100jt' berarti alokasi), per entry10% equity Close sebelumnya dibatasi cash. Compounding, tanpa leverage, satu ticker satu posisi, prioritas alfabet ketika slot terbatas. Gabungan berbagi modal; jangan menjumlah CAGR standalone.
- Fee beli0.15%, jual0.25% all-in. Skenario fee-only fractional units; stress spread satu tick masing-masing sisi, round lot100 saham. Tick modern BEI1/2/5/10/25 berdasarkan prior Close, diterapkan counterfactually ke seluruh sejarah. Tidak punya historis orderbook/bid-offer.
- Saham Data/Data kompas 100.csv: periode laporan full 4Jan2000–15Agu2025, 100 saham; loader membuang satu TLKM intraday dan memperbaiki rentang31 OHLC inkonsisten. Corporate actions/survivorship dan kapasitas eksekusi belum tervalidasi. Forex dan crypto ikut paket, tetapi eksperimen terbaru khusus saham.
- Regime proxy adalah chain index equal-weight return saham tersedia, BUKAN IHSG. ER20 unsigned; 'lurus' bisa turun. Label rezim lag satu bar agar entry memakai informasi tersedia. analyze_portfolio_regimes.py sumber definisi.
- CAGR portfolio dihitung dari equity compounding menurut kalender. Return per rezim adalah atribusi log daily return atas tanggal rezim, dianualkan memakai durasi kalender terkait; bukan CAGR portofolio terpisah yang bisa langsung ditradingkan. 'Trend' optimasi menggabungkan naik dan turun.
- Bulan rekor: ada daily closing equity melebihi seluruh high historis termasuk modal awal; bukan sekadar month-end positif. Full308bulan, 280bulan memiliki hari choppy. Posisi boleh carry melintasi rezim; bedakan rezim entry dari atribusi harian.
- Semua tabel CSV metrik rasio memakai desimal (0.1554 =15.54%), kecuali kolom/dokumen menyatakan sebaliknya.

## Peta hasil terdahulu, agar tidak mengulang pencarian tanpa alasan

- choppy_inverted_signal_results: inverse murni WR tinggi tetapi loss besar; tambahan stop memperkecil loss dan menurunkan WR/profit.
- choppy_head_to_head_results/LOSS_DIAGNOSIS.md: inverse252 losers avg19.99%, holding126.87; loss sudah17.86% saat Close sinyal, fill berikutnya tambah1.82pp dan fee0.32pp. Exit breakout+ER bisa menunda pelepasan posisi rugi.
- choppy_er_exit_results: mengganti exit menjadi ER pasar>=0.3 memang hold turun74.63->10.28, tetapi WR66.13->41.36 dan fee CAGR4.79->-8.75. Rezim berubah tidak berarti harga sudah profit.
- choppy_fading_entry_test_results: fading dapat memajukan sinyal entry dalam subset episode, tetapi bukan penyebab universal profit atau banyak trade tambahan.
- choppy_breakout_only_exit_results dan choppy_exit_lever_grid_results: menghapus ER exit/mengecilkan HHV memengaruhi holding DAN WR/payout; tuas bukan independen. Semua9config grid negatif pada atribusi choppy di kedua biaya.
- choppy_swinger_profile_results/CONCLUSION.md:81run/52configtrain, tidak ada yang memenuhi seluruh target karakter. Holding mirip tidak cukup. choppy_holding_candidate_audit_results menjelaskan win kecil/loss dan profit yang dilepas kembali.
- STRATEGY_NOTES.md dan semua direktori *_results membawa rangkaian eksperimen terdahulu. Jangan mengambil hasil lama H200/gross sebagai hasil strategi terkini.

## Melanjutkan pekerjaan

Verifikasi manifest dan jalankan smoke tests sebelum mengubah kode. Ringkas kegagalan optimasi48run dengan angka, lalu uji hipotesis berikutnya secara terkontrol untuk meningkatkan expectancy sistem inverse pada choppy tanpa merusak utama. Jangan mengklaim kandidat lolos atau mengganti AFL aktif otomatis. Bekukan konfigurasi sebelum evaluasi periode lain, laporkan biaya/versi/periode/CAGR/rekor/WR/payout/MDD/holding/trade count dan keterbatasan sejarah yang sudah dilihat.

Tidak ada job backtest yang perlu diteruskan saat snapshot ini. 20 unit tests relevan lulus kembali saat handoff. Pengujian native AmiBroker dan Linux/web belum dilakukan; Python runner terbaru memakai path relatif lokasi skrip. Beberapa skrip lama masih hardcoded Windows, dicatat dalam PORTABILITY_NOTES.md.
