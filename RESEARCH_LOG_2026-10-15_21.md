# Log riset 15–21 Oktober 2026 (ringkasan percakapan dan hasil)

Ringkasan permintaan pengguna dan jawabannya. Rincian, angka lengkap dan batasan ada di `CONCLUSION.md` tiap folder.
Semua uji: rencana dikunci (PLAN.md di-commit) sebelum hasil, angka dicek ulang pemeriksa independen. AFL aktif tidak
pernah diubah. Biaya B = fee 0,15%/0,25% + slippage 0,25% per sisi (round trip 0,90%), kecuali disebut lain.

## Mengejar Swinger ideal
- `swinger_like_system_results/`, `overfit_results/`, `lookahead_audit_results/`, `sk5_regime_results/`: SK-5 dan kandidat
  awal; aturan fill ketat (High > level) ternyata terlalu optimistis; parameter SK-5 tidak lolos uji overfitting.
- `realistic_chase_v2_results/`: uji ulang dengan eksekusi dikoreksi. Pilihan utama v2 = buy stop 0,5% di atas HHV20 (grid
  harga), ER20 ≥ 0,2, urutan mom120, gap 2%, exit fade 2 ATR / Close < SMA30 / breakout gagal, 25% ekuitas per order.
  B 2000–25: 49,3% CAGR / 119 bulan rekor / MDD −24% vs Swinger ideal 102,0% / 232. Tidak ada sistem kausal yang
  mendekati; fill Swinger ideal tidak bisa dieksekusi.

## Sifat pasar
- `market_properties_v2/`: 62 uji pra-registrasi. Yang bisa dipakai hanya sebagai aturan di dalam sistem: buy stop di atas
  level (W1.5), filter ER (W1.7), jual di Close saat Open gap down (melemah sejak call auction 9 Des 2024). Trend jangka
  pendek memudar sejak 2011 (≈0 di 2021–25); pola overnight/intraday berbalik sejak 2013; efek Senin hilang; premi
  ilikuiditas = artefak daftar Kompas100 2025.
- `property_levers_results/`: menerapkan sifat-sifat itu sebagai tuas portofolio tidak menaikkan hasil; hanya
  `gapdown_close` terkonfirmasi.

## Survivorship, data basi, likuiditas
- `pit_universe_results/`: hanya saham yang likuid saat itu + filter data basi + batas order 25% ADV20: CAGR 2000–25
  turun dari 49% ke sekitar 16% (MDD −44%). Separuh entry versi lama membeli lebih dari seluruh transaksi hari itu.
  Survivorship penuh belum bisa dihapus: data saham delisting tidak ada dan jaringan sesi memblokir sumber data.
- `regime_breakdown_results/`: versi realistis uptrend 34%/th, sideways 10%, downtrend 5%.

## Logika kedua untuk sideways (semua gagal setelah biaya)
- `sideways_swings_results/`: ayunan sideways banyak (±410/th ≥5%), sistem hanya ikut 5%.
- `atr_dip_limit_results/`: buy limit x ATR di bawah Close: pantulan ada, terlalu kecil.
- `choppy_range_module_results/`: beli di bawah range saat choppy: rugi sebelum biaya.
- `sideways_dip_property_results/`: beli koreksi saham kuat di Close, jual di Open: +0,34% kotor, di bawah biaya.
- `sideways_properties/`: saat sideways range tidak dihormati lebih dari kebetulan; arah keluar tidak bisa ditebak.
- `lowest_low_time_results/`: entry lowest low + x bar, exit tanpa puncak baru x bar: entry ≈ acak; ER saham/pasar tidak
  menolong.
- `mid_atr_sideways_results/`: titik tengah + ATR per lebar range: rugi; range lebar positif tapi rapuh.
- `established_range_results/`: range yang sudah bolak-balik: pantulan lebih sering tapi kecil, rugi sebelum biaya.
- `range_size_modules_results/`: range kecil/menyempit vs besar, fade vs breakout: fade rugi; breakout ≈ breakout HHV20
  sistem utama, ≈0 setelah biaya dengan fill di grid.
Kesimpulan: di data ini tidak ada logika sideways berbasis level harga yang menutup biaya. Arah yang tersisa: parkir dana
menganggur, data point-in-time (termasuk delisting), forward test sesudah 2025-08-15.

## Lain-lain
- Dashboard pemindai harian dengan data Yahoo Finance: belum ada; ditunda pengguna (Yahoo diblokir jaringan sesi).
- Repo: https://github.com/saevan/ngulik-ai-analysis (branch `claude/blissful-mccarthy-mufwoy`), private.

## 26 Oktober 2026 – Keunggulan dan kelemahan vs Prototype Swinger
- `compare_vs_swinger_results/`: perbandingan karakter lengkap (B 2000–25). Ringkasan di CONCLUSION.md folder itu:
  kita 49,3% (realistis 16,2%) vs Swinger ideal 102,0% (dengan batasan realistis yang sama 31,9%); versi Swinger yang
  bisa dieksekusi 14,9% (next Open, MDD −64%) atau runtuh (stop order). Kelemahan utama kita: win rate 38%, modal
  terpakai 49%, bulan rekor 119 vs 232, lemah saat sideways/downtrend, bergantung pada saham listing baru.

## 26 Oktober 2026 – Kenapa win rate < 50%; uji klaim "harga + waktu → WR ~50%"
- `winrate_diagnosis_results/`:
  - WR rendah terutama karena buy stop membeli sebelum breakout terkonfirmasi. Di 42% trade, Close hari entry sudah di
    bawah fill. Seperempat trade keluar sebagai breakout gagal dengan WR 1,5%. Tanpa trade itu WR 51,7%.
  - Biaya hanya membalik 2% trade.
  - Klaim benar: exit waktu atau harga + waktu menaikkan WR ke 53–71%. Tapi semua versi menurunkan CAGR (49% → 17–40%)
    dan bulan rekor. Tidak ada yang lolos, jadi tidak diadopsi.
  - Mesin dapat opsi `max_hold` (default mati).

## 26 Oktober 2026 – Kualitas per trade per kondisi market dan return per tahun vs Swinger ideal
- `quality_vs_swinger_results/`:
  - Per trade, saat uptrend/sideways kita setara Swinger ideal (rata-rata +6–9% per trade). Saat downtrend/breakdown
    kita jauh kalah dan hampir tidak trade.
  - Selisih utama ada di jumlah trade (797 vs 3.241) dan modal terpakai (49% vs 93%).
  - Median return tahunan: kita 35%, realistis 11%, Swinger ideal 89%. Kita unggul di 5 dari 26 tahun, versi realistis
    hanya di 2025.
  - Diukur dengan expectancy (`expectancy_vs_swinger.py`): per trade kita +7,0% vs Swinger ideal +6,5%, tidak berbeda
    nyata. Per unit risiko kita 1,32R vs 1,88R. Versi realistis +2,5% (0,52R). Saat downtrend/breakdown expectancy kita
    tidak berbeda dari nol. Celah return terutama dari frekuensi trade: 31 vs 126 trade per tahun.

## 26 Oktober 2026 – Bahas win rate lanjutan; unsur waktu (beli saham trending di awal bulan)
- `winrate_diagnosis_results/` (tambahan):
  - Breakout gagal makin sering: 20% (2000–07) → 34% (2016–25). WR trade yang tidak gagal stabil sekitar 50–55%.
  - Kegagalan bisa ditebak sebagian, tapi kelompok yang sering gagal tidak punya expectancy lebih rendah.
  - Koreksi: exit SMA30 adalah give-back (median puncak +12%, keluar −2%), bukan impas.
  - Di versi realistis, tanpa aturan breakout gagal lebih baik (19,4% vs 16,2%, MDD −37% vs −44%). Eksploratif.
- `monthly_trend_entry_results/`:
  - Sistem beli-awal-bulan dengan filter trending tidak membawa WR ke 50% (38–47%; pegang 1 bulan acak pun ~47%).
  - Sebagai daftar pantau untuk buy stop kita, trend jangka menengah memberi +1…3 pp CAGR realistis, tapi WR tetap.
  - Belum diadopsi.
  - Langkah 3–4 (entry bulanan ditambahkan, breakout tetap): tanpa jatah modal, entry bulanan menggusur breakout
    atau tidak kebagian kas. Dengan jatah 35%: realistis 18,6% (V0 16,2%), 64 bulan rekor, tapi MDD tanpa batasan −39% dan
    WR gabungan tetap 34%. Tidak ada yang lolos; WR tidak naik.
  - Dampak beli awal bulan (jatah 35%): manfaat saat downtrend datang dari pemilihan saham trend kuat yang sudah
    dipegang. Manfaat saat uptrend hanya dari modal tambahan (tambahan acak sama saja). Di versi tanpa batasan,
    breakout pemenang tergusur.
  - ER pada entry bulanan: ER market membuat tambahan lebih jinak (MDD turun, breakout tetap, WR realistis 37%), tapi
    CAGR realistis turun. ER saham lolos kriteria, tapi tidak konsisten antar periode dan holdout. Tidak diadopsi.

## 26 Oktober 2026 – V1 dipakai; kenapa WR belum seperti Swinger ideal
- Keputusan pengguna: V1 = V0 + entry bulanan (Close > Close 120 bar lalu & ER20 saham ≥ 0,3, order 10%, maksimal 35%)
  menjadi sistem riset acuan (STRATEGY_NOTES). AFL tidak diubah.
- `wr_gap_v1_results/`:
  - Fill ideal Swinger memberi +2,7% di entry dan +2,7% di exit per trade (tidak pernah negatif). Tanpa itu WR Swinger
    30,8% dan expectancy +1,0%.
  - Pada basis Close-ke-Close, WR V1 36,7% (realistis 30,9%) dengan expectancy jauh lebih tinggi.
  - Beli di Close yang terkonfirmasi tidak menolong: WR 38–40%, CAGR turun separuh.
  - Celah WR = fill yang tidak bisa dieksekusi.
- `monthly_filter_grid_results/`: grid 36 filter modul bulanan (latih 2000–15, uji 2016–25). Pilihan dari periode latih =
  filter V1 sendiri. Trade bulanan masuk rata-rata hanya sekitar 4% di bawah level breakout; labanya datang dari memegang
  lama.
- Putaran 2 (32 filter trend: SMA, MACD, ER saja, slope, dekat puncak 52 minggu): pilihan latih tetap filter V1; ER20 ≥ 0,4–0,5 saja adalah alternatif setara.
- `high_reset_exit_results/`: exit waktu reset di high baru. WR naik ke 45–47%; terbaik x = 15 (realistis 21,7%, MDD −37%) tapi versi tanpa batasan MDD −48%. Tidak lolos.
- Uji konfirmasi 'tanpa SMA30 + reset x20': tetangga 4/5 menang tipis, tapi holdout 1996–99 kalah (9,1% vs 12,0%) dan t = 1,42. Tidak diterima; SMA30 tetap.
- V1 tanpa aturan breakout gagal: WR +6 poin, return setara (t = 0,63, holdout kalah tipis). Tidak diterima; netral.
- Keputusan pengguna: aturan breakout gagal dibuang → V2 (STRATEGY_NOTES).
- V2 + exit reset tambahan: tidak memperbaiki (2/5 tetangga, t = −0,19); WR +0,5…2 poin.
- `monthly_entry_main_exits_results/`: V2 ternyata belum sesuai maksud (posisi bulanan tidak pakai exit lama). Versi sesuai maksud tidak menambah apa-apa (trade bulanan kena SMA30/fade, expectancy ≈ 0–2%).
- Filter SMA untuk entry bulanan (exit lama): saham di bawah SMA30 langsung kena exit (98% ≤ 2 bar). Dengan filter, trade bulanan hanya +2…3%/trade. Pilihan grid (ER ≥ 0,4 + Close ≥ 1,03 × SMA30) tidak lolos (MDD +9 pp vs breakout saja).
- Aturan sesuai maksud (tiap awal bulan beli saham di atas SMA30, exit lama): trade bulanan WR 28–32%, expectancy ≈ 0; semua varian di bawah 'breakout saja'.
- Exit x bar sebagai exit modul bulanan (F1/SMA30, x 10–60): tidak ada yang mengalahkan V2 atau breakout saja; trade bulanan makin baik makin lama dipegang.
- Lookback modul bulanan, 81 kombinasi: pilihan latih = 120/120 (V2); median sel di bawah 'breakout saja'; tidak ada sel yang mengalahkan breakout saja di kedua versi. Breakout saja = pilihan paling kokoh.
- `market_structure_results/`: candle merah/hijau seimbang hanya di mingguan/bulanan. Baterai v3: struktur swing turun −0,65%/20 hari (filter), koreksi > 61,8% melemahkan trend, high 60 hari cenderung tembus, korelasi 0,43 saat crash. Squeeze, angka bulat, S/R, umur trend: tidak terbukti. Data harga sebelum 2021 sudah adjusted.
- `calibrate_v3_results/`: 144 konfigurasi tuas berbasis temuan (swing, ER, ranking, crash guard, modul bulanan, ukuran). Pilihan latih = V2 sendiri; tidak ada modul lebih baik. 'Lewati swing turun' sedikit positif; crash guard, ER ketat, ranking ER negatif.
- `wide_range_results/`: range lebih lebar/panjang (N 20–250 hari, lebar 10–80%+). 64 sel tidak lolos. Kandidat N=20/lebar 40–80% gagal konfirmasi (tetangga 2/9). Range lebar = saham habis jatuh, rawan bias survivor.
- `stock_er_range_results/`: dengan ER per saham, bawah range tetap tidak memantul (excess ≈ 0) dan trade beli bawah range rugi di semua kelas. Resistance atas range nyata di saham choppy (+6,3 pp, t 5,0); hanya berguna untuk short/hindari/aturan jual.
- `sideways_size_results/`: sideways kecil/besar = satu sebaran menerus (median lebar 14%, 4 ATR). Swinger ideal untung di sideways 10–40% (sampai 36 bps/hari), V2 hampir tidak masuk saham choppy. Sideways kecil tidak layak (expectancy Swinger +2,4% < bonus fill).
- `swing_in_range_results/`: swing 5 bar yang bisa dieksekusi di saham choppy dengan range 10–40%: 12 sel rugi (kotor ≈ entry acak, bersih −1,0…−1,5%). Laba Swinger di sana berasal dari fill ideal.

## 26–30 Oktober 2026 – catatan pelengkap (jawaban yang belum tercatat di log)
- V2 vs Swinger ideal per kondisi market (`quality_vs_swinger_results/`):
  - `v2_trade_quality.csv`: expectancy per trade kita setara atau lebih tinggi, tapi rugi per trade 2,5× lebih besar dan
    jumlah trade 4–15× lebih sedikit.
  - `v2_similarity.csv`: kemiripan return realistis 26% (naik) / 12% (sideways) / 20% (turun).
  - Kemiripan expectancy: per trade 112%, per unit risiko 45%, per hari dipegang 41%. Dihitung dari `v2_trade_quality.csv`,
    tanpa file baru.
  - `v2_sideways_why.csv` dan `v2_sideways_yearly.csv`: keunggulan entry-sideways datang dari beberapa trade raksasa
    modul bulanan. V2 unggul hanya 10/26 tahun, dan 3/26 tanpa trade terbaik.
  - `v1_v2_holding.csv`: membuang aturan breakout gagal memperpanjang holding breakout sekitar 6 bar.
  - `v2_by_stock_er_*.csv`: Swinger ideal mendapat 55% labanya di saham choppy. V2 hampir tidak masuk saham choppy, dan
    41% hari pegangnya ada di saham yang sudah choppy dengan hasil ≈ 0.
- `sideways_entry_block_results/`: saat sideways, breakout hanya 7% hari dan 45% diblokir ER; sinyal 3,9% vs 10,3% saat
  uptrend.
- Diskusi tanpa uji baru:
  - logika "trade kecil menang rutin" tidak direkomendasikan, karena win rate impas 59–73% untuk target 2–5% dengan biaya
    0,9%;
  - "menutup biaya" adalah syarat perlu, bukan cukup (ada 8 syarat);
  - kerangka Logic 2 dari nol menunggu keputusan pengguna soal instrumen, biaya nyata, dan data tambahan.
- `costs_idle_results/`: fee broker pengguna 0,25/0,35% (0,60%) lebih mahal dari asumsi fee kita. Selisih 0,9% berasal
  dari slippage. Dana menganggur V2 realistis 17% / 38% / 62% (naik / sideways / turun). Parkir 4%/th: CAGR realistis
  20,7% → 22,3%.
- 30 Okt (tanpa uji baru): penjelasan kenapa range sideways kecil dan besar tidak bisa dimanfaatkan.
  - Range kecil: potensi untung kecil vs biaya, 74% jebol dalam 20 bar dengan arah tak tertebak, dan Swinger ideal pun
    hanya +2,4%/trade.
  - Range besar: risiko per trade ikut membesar (dalam ATR sama dengan range kecil), batas tidak dihormati lebih dari
    acak, sering saham habis jatuh (rawan bias survivor).
  - Akar bersama: di data harian, timing masuk di dalam range tidak lebih baik dari acak (kontrol). Satu-satunya sifat
    nyata (resistance atas range saham choppy) hanya bisa dipakai dengan short.
  - Sumber: `range_size_modules_results`, `mid_atr_sideways_results`, `wide_range_results`, `stock_er_range_results`,
    `sideways_size_results`, `swing_in_range_results`, `sideways_properties`.
- `decline_bounce_results/`: anatomi penurunan → pantulan di saham sideways (pantulan median 5% sampai 30%, sebanding dengan penurunan; dari titik terendah yang hanya diketahui setelahnya). Real time setelah turun 5–20% dari high 20 hari: naik dan turun maksimum sama-sama membesar, return tidak beda dari hari acak (t −1,6…1,4).
- `buy_the_turn_results/`: beli saat pantulan mulai (Close > high 3 bar) setelah turun 10–20%: 12 sel rugi, lebih buruk dari entry acak (bersih −1,3…−2,1%). Pantulan tidak bisa dimanfaatkan dengan data harian.
- `buy_the_turn_results/` addendum: tanpa target (stop/waktu saja) di saham choppy tetap rugi (WR 38–43% vs WR impas 47–52%). Mean reversion kita: WR 49–62% tapi butuh 65–72% karena menang kecil/kalah besar + biaya.
- `high_wr_range_results/` (30 Okt): beli di 20% bawah range saham choppy untuk mengejar WR ~70%, dengan 36 sel
  target/stop/waktu. WR 70–83% tercapai (target +2–3%, waktu lama), tetapi WR impas 85–92%. Semua sel rugi bersih
  −1,4…−1,9%, bahkan kotor sebelum biaya pun rugi, dan sama dengan kontrol acak. Pilihan latih (+3%, tanpa stop, 10 bar):
  uji WR 66%, bersih −1,6% (t −8,4) → gagal. Bukan kandidat Logic 2.
- `high_wr_range_results/` addendum: apakah kurang choppy? Tidak. Rugi di semua rezim pasar (−1,1…−1,6%), di ER20 < 0,1,
  di choppy 21 hari berturut-turut, dan di ER60 < 0,2. Sesudah entry, 39–46% trade Close jebol di bawah low range
  (bersih −5%). Trade yang tetap di range menang 96–99,7%. Choppy di masa lalu tidak meramalkan range bertahan.
- 30 Okt (tanpa uji baru): penjelasan ER (Kaufman efficiency ratio) untuk pengguna.
  - Rumus: |Close hari ini − Close n hari lalu| / jumlah |perubahan Close harian| selama n hari. Lihat
    `uts/indicators.py` `efficiency_ratio`.
  - Rentang 0–1, tanpa arah.
  - Pemakaian:
    - V2 breakout: ER20 bar sebelumnya ≥ 0,2;
    - modul bulanan: ER20 ≥ 0,3;
    - rezim pasar: ER20 proxy ≥ 0,3 + arah 20 hari;
    - saham choppy: ER20 < 0,2.
  - Batasnya: hanya menggambarkan 20 hari ke belakang, tidak meramalkan.
- 9 Nov: arah baru pengguna, yaitu mulai dari awal dengan satu sistem untuk naik/sideways/turun dan acuan Swinger ideal.
  - `swinger_fingerprint_results/`: per trade, Swinger ideal = fill entry +2,4…3,1% + pergerakan + fill exit
    +2,3…2,9% − biaya 0,9%.
  - Pergerakan (Close-ke-Close bersih): naik +3,4%, sideways +0,3% (+1,5% di saham ER ≥ 0,2), turun −0,6%. Semuanya
    dari 5% trade terbaik.
  - Yang dibeli: breakout swing pendek (+4%/5 hari, separuh atas range, sering saham choppy).
  - Untung di semua kondisi berasal dari fill.
- 9 Nov: cek klaim "WR ~50% tidak masalah asal menang rata-rata > kalah rata-rata". Hasil: benar secara hitungan hanya
  di WR tepat 50% dengan angka bersih.
  - Swinger ideal: WR 49%, payoff 4,9 (WR impas 17%). Basis Close-ke-Close: WR 31%, payoff 2,7, WR impas 27%. Median
    trade negatif.
  - Karakter yang ditiru seharusnya payoff besar/rugi kecil, bukan WR 50%. WR dan payoff saling tukar lewat exit.
  - Sumber: `swinger_fingerprint_results/wr_payoff_check.csv`.
- 9 Nov: aturan pengguna "acuan ideal, logika realistis" dicatat di STRATEGY_NOTES.
  - `logic_a_swing5_results/`: sinyal swing 5 hari ala Swinger dengan eksekusi Open berikutnya, versi realistis.
  - CAGR A0 / A1 / A2: −2,8% / +4,9% / +3,0%; MDD −93% / −69% / −71%.
  - Per kondisi, A1: naik +19,9%, sideways −1,6%, turun −1,2%. WR 33,5%, payoff 2,4.
  - Gagal. Rugi lebih besar karena eksekusi sesudah candle sinyal, dan biaya sekitar 8–11% modal per tahun.
- 9 Nov: "kalau pakai logika sebelumnya?" → V2 realistis dalam laporan Logic A (`logic_a_swing5_results/v2_compare.csv`).
  - CAGR 20,7%, MDD −46%. Subperiode +41,6 / +1,8 / +15,4 / +27,1%.
  - Per kondisi: naik +47,8%, sideways +9,7%, turun +13,1% (26% / 12% / 20% dari Swinger ideal).
  - Lolos syarat dan unggul atas Logic A di semua kondisi.
  - Expectancy per trade +7,3% ≈ Swinger ideal (+6,5%); selisih utama ada di jumlah trade (28 vs 126 per tahun) dan
    modal terpakai (66% vs 93%).
  - 5/26 tahun negatif.
- 9 Nov: "apa yang membuat V2 belum seoptimal Swinger?" → `v2_gap_results/`.
  - Jembatan CAGR: V2 realistis 20,7% → tanpa batasan 50,7% → Swinger 102%.
  - Identitas trade × bobot × kualitas: jumlah trade (28 vs 126/th) = 124% dari celah, kualitas hanya 13%.
  - V2 melewatkan 76% dari 5% trade terbaik Swinger.
  - Modal: kas ≥ 25% di 56% hari.
  - Rugi rata-rata −8,7% (modul bulanan −14,8%) vs Swinger −3,5%.
- 9 Nov: "di kondisi apa Swinger trading tapi V2 tidak?" → `v2_gap_results/by_condition_*.csv`.
  - Trade per tahun Swinger / V2: naik 33/10, sideways 72/17, turun 22/1,4. 88% trade Swinger tidak tersentuh V2.
  - Pergerakan bersih trade yang terlewat: naik +2,7% (ER ≥ 0,2: +4,7%, sekitar 13/th), sideways −0,8%, turun −2,2%,
    breakdown −1,8%.
  - Hanya celah saat pasar naik yang bernilai nyata.
- 9 Nov: "ER kebalikan untuk Logic 2 sideways?" → `reverse_er_results/`.
  - 1 − ER = informasi sama. Saklar logika terbalik sudah gagal di 5 studi 8–9 Okt.
  - Cermin V2 dengan ER bertanda (turun efisien + low 20 hari, pasar sideways, beli Open besok): 18 sel semua rugi
    −0,6…−1,8%. Terbaik WR 61% vs WR impas 65%.
  - Sedikit lebih baik dari acak (+0,45 poin) tapi di bawah biaya. Pilihan latih gagal di uji (−0,43%, t −1,0).
- 9 Nov: cek klaim "ER lurus = tren → logic tren; ER choppy = sideways → logic pantulan" → `er_regime_check_results/`.
  - ER saham hari ini tidak meramalkan ER 20 hari lagi (median 0,20 dan P(ER < 0,2) 50% di semua kelompok).
  - Saham ER < 0,1 hanya 16% tetap di range 20 hari ke depan.
  - ER tinggi meramalkan kelanjutan arah (saham +1,2%, pasar +3,6% per 20 hari).
  - Kesimpulan: benar untuk logika tren, salah untuk logika pantulan. ER rendah = tidak ada informasi tren.
- 9 Nov: grid search Logic 2 sideways, 168 sel (`sideways_bounce_grid_results/`).
  - Kombinasi: 4 pemicu × 7 filter (RSI2, volume, ekor bawah, breadth, SMA200, ER, lonjakan volume) × 2 entry × 3 exit.
  - Hasil: hanya 1 sel bersih > 0 (+0,01%); sinyal vs acak +0,06 poin.
  - Pilihan latih gagal di uji (−0,62%, t −0,95).
  - Keluarga breadth < 30% + limit untung hanya 2016–25, rugi 1996–2015 termasuk holdout 1996–99. Statusnya hipotesis
    forward test, bukan hasil.
- 9 Nov: "perlu coba Logic 2 mean reversion?" → hampir semua uji sideways sudah mean reversion (9 bentuk).
  - Bentuk yang belum pernah diuji, pembalikan relatif (beli 5 saham paling tertinggal saat sideways), dijalankan di
    `xs_reversal_results/`: 12/12 rugi −0,9…−1,4%, dan saham tertinggal tidak lebih baik dari acak.
  - Ringkasan semua uji mean reversion ada di CONCLUSION.
- 9 Nov: "pakai RSI atau sinyal mean reversion lain?" → `mr_indicator_grid_results/`.
  - 12 indikator klasik × 2 entry × 3 exit × 2 cakupan = 144 sel.
  - Hasil: 0/144 bersih > 0; saat sideways sinyal rata-rata −0,08 poin vs acak.
  - Terbaik: IBS/Bollinger/RSI3 + limit, kotor ≤ +0,6% vs biaya 0,9%.
  - Pilihan latih gagal di uji (−0,40%, t −2,4).
- 9 Nov: "berikan pantulan range saat sideways" → `sideways_swings_results/`, zigzag 3/5/10%.
  - Pantulan setelah kejadian: +7,5% / +11,2% / +21,6% (median), dalam 4 / 7 / 17 bar, sebesar penurunan sebelumnya.
  - Real time (konfirmasi X% di kedua ujung): tertangkap +0,2% / +0,4% / +1,5%; sesudah biaya −0,7% / −0,5% / +0,6%
    (median −5,3%).
  - Lebar range 20 hari saat sideways 16,7%.
- 9 Nov: "2 range (sedang + kecil) untuk pantulan berulang" → `nested_range_results/`, 64 sel, buy limit di low range
  kecil.
  - 0/64 positif, bahkan kotor −0,8…−1,0%.
  - Penyebab: adverse selection. Order terisi saat harga jebol (38–57% hari isi juga menembus low range sedang). Stop
    −7% di 39–46% trade vs target +7% di 22–34%.
- 9 Nov: klarifikasi pengguna "range dari harga pantulan tadi" → `pivot_range_results/`.
  - Range dari pivot zigzag (10%/3%, 10%/5%, 5%/3%), buy limit di pantulan bawah range kecil.
  - 0/24 positif, kotor −0,6…−1,5%. Stop 30–77% trade vs target 9–46%.
  - Harga pantulan lama bukan support (adverse selection).
