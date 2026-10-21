# Definisi strategi yang disepakati

## Koreksi pengguna: fading (4 Oktober 2026)

Fading adalah penurunan dari **open bar yang sedang berjalan / open baru**,
bukan dari open saat entry posisi. Acuan direset setiap bar.

Rumus sinyal dengan ambang d: `Low[t] <= Open[t] * (1 - d)`.

Contoh: posisi dibeli pada 100. Bar berikutnya open 120. Dengan fading 5%,
level pemicu bar tersebut 114, bukan 95. Sinyal dapat muncul meskipun posisi
masih untung dibandingkan harga beli. Sebaliknya, gap dari 100 ke open 80
dengan low 79 tidak menyentuh fading 5% pada bar itu (levelnya 76).

Harga entry tetap digunakan untuk menghitung PnL. Jam/usia posisi tidak
dimulai ulang hanya karena bar baru; reset usia setelah transaksi baru.

Asumsi simulasi yang dipertahankan saat koreksi ini: sinyal berdasarkan Low
dieksekusi pada open berikutnya yang bisa diperdagangkan; masuk kembali paling
cepat bar setelah penjualan dan sesuai filter entry. Ini model eksekusi yang
terpisah dari definisi acuan harga; belum memodelkan jual intrabar di level pemicu.

## Tujuan

- TimeHunter: penelitian sistem investasi uang riil.
- RecoverHunter: penelitian strategi lomba sekitar 1-2 minggu.
- Fokus aktif: TimeHunter dengan unsur harga dan waktu, mencari tujuh kriteria.

## Preferensi pengguna: tanpa biaya (5 Oktober 2026)

Untuk pencarian sistem saat ini, gunakan hasil **gross saja**. Fee, pajak,
spread, slippage, dan penyesuaian biaya lainnya ditetapkan nol. Pemilihan dan
penilaian kandidat juga berdasarkan gross, bukan hanya menampilkan gross dari
kandidat yang dahulu dipilih berdasarkan hasil setelah biaya.

`grid_search_timehunter.py` dan skrip turunannya memakai STOCK_COST=0 dan
FOREX_COST=0. Hasil aktif: `grid_timehunter_gross_results/`,
`backtest_timehunter_selected_gross_results/`, dan
`timehunter_bar_open_price_gross_results.csv`.

Penghitungan ini tetap menggunakan fading dari open setiap bar baru, sinyal
tanpa informasi masa depan, serta pembagian periode pencarian/validasi/uji.
Hasil lama dengan biaya dipertahankan sebagai arsip, bukan dasar ranking aktif.

## Hasil yang sudah tidak sesuai definisi fading

`grid_timehunter_results/` dan `timehunter_price_results.csv` memakai acuan entry.
Angka fading di sana merupakan hasil definisi lama yang keliru, bukan hasil
strategi fading yang dimaksud pengguna. Disimpan untuk jejak audit.

Hasil koreksi: `grid_timehunter_bar_open_results/` dan
`timehunter_bar_open_price_results.csv`. Skrip aktif sudah memakai open tiap bar.
Skrip Claude historis lain belum semuanya diperbarui; jangan menganggap label
"fading" pada skrip lama berarti definisi yang sudah dikoreksi ini.


## Varian indikator lebih pendek (6 Oktober 2026)

Pengguna meminta indikator diperkecil untuk menambah trade. AFL aktif memakai SMA30 (parameter SMA period), hold200/High20/pullback2%/fading30%/rebound1 tetap. SMA100 masih dapat dipilih sebagai baseline. Periode kontinu, biaya nol. Backtest ulang: 2.181 trade, WR52,59%, PF3,107, payout2,736, lima kriteria numerik lolos; bukan validasi independen. Hasil di timehunter_sma30_results, reproduksi backtest_timehunter_sma30.py.

## Batasan pengembangan yang ditegaskan pengguna (6 Oktober 2026)

Pengguna menegaskan: jangan membuat logika baru; tambahkan pengetahuan hasil eksperimen ke logika awal dengan ketentuan yang sama. Acuan implementasi tetap AFL utama SMA30/High20/pullback2%/rebound1/hold200/fading30% dari Open setiap bar. Entry next tradable Open, exit fading next tradable Open, satu posisi per saham, periode gabungan dan biaya nol.

Tujuh kriteria tetap: mean > median, avg win > magnitudo avg loss, payout > 2, WR > 50%, expectancy positif, penerapan lintas pasar, serta kausalitas eksekusi. Lima numerik saja tidak membuktikan tujuh kriteria.

Pengetahuan untuk pengembangan terkontrol:
- Memperpendek SMA dapat menambah transaksi, tetapi WR/PF/payout harus diperiksa kembali; bukan hanya frekuensi yang berubah.
- Fading ketat dapat memangkas calon pemenang. Payout/right tail besar bukan alasan mengabaikan WR > 50%.
- Mempertahankan pemenang dan melepas kerugian lebih cepat adalah sasaran evaluasi, bukan izin otomatis mengganti entry, hold, atau syarat fading sekaligus.
- Uji satu perubahan terhadap baseline dengan data/asumsi sama; jangan menganggap perubahan meningkatkan semua metrik.

Eksperimen TimeHunter_RightTail_Gross.afl dan hold400/loss-only fading tetap arsip riset terpisah, bukan baseline aktif. Tidak ada perubahan aturan strategi baru yang diadopsi dari eksperimen itu pada penegasan ini.

## Uji transfer lintas pasar tanpa retuning (6 Oktober 2026)

Skrip backtest_timehunter_cross_market.py menguji baseline SMA30/High20/pullback2/rebound1/H200/fade30 pada saham, sembilan pasangan forex lokal dan delapan crypto spot Binance. Seluruh biaya nol. Tidak ada perubahan AFL/parameter.

Hasil full: saham 2.181 trade WR52,59% PF3,11 numerik5/5; crypto124 trade WR59,68% PF6,11 numerik5/5; forex daily sumber04:00 sebanyak17 trade WR41,18% PF0,97 numerik2/5. Forex dengan batas tengah malam sumber menghasilkan15 trade WR53,33% numerik5/5. Zona waktu sumber forex tidak diketahui; sensitivitas batas hari dan sampel kecil melarang klaim universal. Fading30% tidak pernah terpicu pada forex, tetapi42 exit crypto memakainya.

Periode bersama 2023-07-01–2025-08-15: saham4/5, forex04:00 1/5, crypto5/5. Crypto berasal dari delapan pasangan yang masih ada, bukan seluruh universe; hanya5 dari8 pasangan lolos numerik secara individual, sampel11–19 trade/pasangan. Hasil ada di timehunter_cross_market_results; raw crypto dan sumber/hash di Data/crypto_binance_daily. Universalitas tetap BELUM TERBUKTI; jangan otomatis mengubah parameter menurut pasar atau mengadopsi logika baru.


## Normalisasi ATR diotorisasi (6 Oktober 2026)

Pengguna meminta perbaikan sesudah riset universal. AFL utama kini pullback1ATR/fading2ATR memakai ATR14 sebelumnya; SMA30/High20/rebound1/hold200/eksekusi tetap. Default ditentukan sebelum hasil, sama lintas pasar. Baseline persen tersimpan TimeHunter_Fading_Percent_Baseline.afl. Forex tanpa volume perlu Require positive volume=No. Default saham5162 WR47,71%, forex96 WR53,13%, crypto334 WR49,10%; masing-masing4/5 numerik. Belum universal/7/7, tidak ada dari12 pasangan koefisien lolos5/5 pada tiga pasar sekaligus. Hasil timehunter_atr_results;24 tes lolos, AFL belum dijalankan langsung.


## Kandidat hasil pencarian bersama (6 Oktober 2026)

Pencarian90 pasangan ATR pada struktur aktif menemukan3 kandidat5/5 pada tiga pasar, tetapi tidak tahan batas hari forex. Pencarian lanjutan1500 kombinasi SMA/High/hold/pull/fade menyisakan1 kandidat5/5 pada saham,crypto,forex04 danforex00: SMA30/High10/hold200/ATR14/pull0.25/fade5, rebound1 dan eksekusi sama. AFL riset terpisah TimeHunter_ATR_Shared_Candidate.afl; AFL utama tidak otomatis diganti. Hasil timehunter_shared_search_results. Full sejak2000 jika data tersedia: saham2098 WR53.57% payout2.67; crypto106 WR54.72% payout14.93; forex04 43 WR51.16% payout2.09; forex00 47 WR57.45% payout2.30. BELUM7/7: common-period saham/forex gagal; forex04 tanpa terminal closures WR48.65%; crypto dipengaruhi DOGE+16939%. Seluruh pencarian in-sample, bukan validasi independen.


## Modul breakout + ER dari pengguna (6 Oktober 2026)

Pengguna mengusulkan breakout HHV yang hanya aktif saat tidak choppy menurut Kaufman ER. Uji terpisah: Close > HHV High20 sebelumnya (tidak termasuk bar sinyal), ER20>=0.30 default yang ditentukan sebelum hasil. Entry nextOpen; exit tetap hold200/fade5 ATR14 sebelumnya. Tanpa SMA/pullback tambahan, belum digabungkan ke sistem utuh. Sensitivitas ER0.2/0.4/0.5 dan kontrol tanpaER, per aset bukan indeks pasar. Modal1miliar/posisi100ribu tetap agar sebanding dengan equity sebelumnya. Saham default:1704 trade, WR53.76%, PF3.515, CAGR0.15834%, bulanrekor103/308=33.44%; kontrol CAGR0.16565%, bulanrekor108/308=35.06%. Crypto defaultCAGR0.20614%, bulanrekor13/97=13.40%. Forex04 defaultCAGR0.000752%, bulanrekor5/37=13.51%. Filter belum meningkatkan semua metrik; tetap riset in-sample, main AFL tidak diubah. Kode backtest_breakout_er.py, hasil breakout_er_results;27 tes lolos.


## Alokasi compounding diminta pengguna

Modal1miliar,10 alokasi masing-masing awal100juta; setiap entry10% equity penutupan sebelumnya dibatasi kas, tanpa leverage. Lot ditafsirkan alokasi modal, unit fractional bukan lot bursa. Maks10 posisi, satu per aset, prioritasticker alfabet saat sinyalbersamaan; sensitivitas alfabetterbalik. Diterapkan pada modul breakoutHigh20+ER20>=0.3 serta kontroltanpaER, exitH200/fade5ATR14 sama. SahamER CAGR34.14%,128/308bulanrekor=41.56%,MDD-56.07%; prioritasbalik28.41%,96/308=31.17%. TanpaER utama18.67%,80/308=25.97%; balik31.48%,111/308=36.04%, sehingga klaim ERunggul tidakrobust. Hasil breakout_er_compounding_results, kode backtest_breakout_er_portfolio.py,31teslolos. Forex/crypto perpasar portofolioterpisah, tanpa konversimata uang atau slippage/kapasitaslikuiditas. AFL belum diubah untuk model portofolio ini.


## Biaya dan estimasi spread diotorisasi (6 Oktober 2026)

Pengguna meminta fee, beli offer/jual bid, fraksi BEI; menyetujui all-in buy0.15%/sell0.25%. Ini memperbarui preferensi tanpa biaya untuk uji eksekusi terkini; jangan tambahkan pajak/levy lagi di atas feeall-in. Modal1miliar/10slot/compounding tetap. Data OHLC adjusted/pecahan dan raw orderbook tidak tersedia: fraksi modern1/2/5/10/25 serta100shares diterapkan sebagai sensitivitas counterfactual2000?2025, bukan rekonstruksi historis/guaranteed fills. Hasil breakout_er_idx_cost_results:feeonlyCAGR33.43%,127/308bulanrekor; fee+1tick EACH SIDE+roundlot CAGR29.92%,117/308=37.99%,MDD-59.70%;2tick27.10%,109/308;3tick24.43%,99/308. Reversepriority1tick24.16%,82/308.35teslolos. Belum memodelkan likuiditas/depth/price limits/historicaltickregimes/aksi korporasi. AFL belum diubah menjadi implementasi biaya ini.


## Keputusan pengguna: ganti exit hold200 dengan SMA30

Pengguna memilih SMA30 dan meminta menghapus hold200 dari logic aktif. TimeHunter_ATR_Shared_Candidate.afl sekarang Close<TrendMA(default30) memberi exit next tradable Open, fading5ATR dari Open bar berjalan tetap, tanpa batas umur. Entry pullback tetap. Versi sebelumnya diarsipkan TimeHunter_ATR_Shared_Candidate_H200_Archive.afl. H200 hanya baseline historis, bukan pilihan aktif. Untuk modul Breakout+ER penelitian selanjutnya gunakan hold=None,exit_sma=30 secara eksplisit; default mesin historis dipertahankan untuk reproduksi skrip lama. AFL masih harness gross fixed-notional, bukan implementasi biaya/alokasi portofolio10slot. Hasil terakhir ada di sma30_exit_results; tidak lulus tujuh kriteria dan belum native-AmiBroker validated.

## Sistem kedua mandiri diotorisasi pengguna

9Oktober arahanterbaru kembaliutama+inverse switching, menggantifokus kandidatlowATRholding: backtest_primary_inverse_switch.py/primary_inverse_switch_results8runs. GateER PASAR20>=.3utama/<.3inverse,unknownnone;utama asli breakout20+stockER>=.3 exitsSMA30/fade2;inverse rawselljadi buy,rawbuyjadi sell. Exitownerpreserved saatregimeberubah,tidakforcedrotate,tanpastop/H200,shared1billion10slot. Optional secondary style inverse mesin;defaultlama intact. GabunganfeeCAGR15.80WR55.11MDD-58.38rekor81/308side6.54;spreadCAGR5.51WR50.49MDD-74.37rekor36/308side-2.52. Maintrendgatealone27.90/15.96fee/spread,side15.43/14.82. Gabunganmain666trades vs1528standalone,inverse655hold73.52loss18.73. Masihbelummembaik;risetarsitektursesuaipengguna,AFLpullbackaktifbelumdiganti.18tests/prefix/eligibility/complementarity/akuntansi/regresimain+inverseked uabiayalolos. STRATEGY.mdmerinciperbedaanERmarket/stockdanentryswitchvsforcedrotation.

9Oktober usermenyukai kandidat holdingmendekati(capATR4%,cost8,pullbackSMA20,LLV5/stop2,nohold)daninginWRnaik. Audit4run audit_choppy_holding_candidate.py/choppy_holding_candidate_audit_results:WRbase31.65,nostop32.29,LLV10 32.51,nocapATR33.18;jadi tidakmenutupgapSwinger51.53. Winnerhold28.20vsSwinger27.01,loser10.10vs10.89.1732losers:1258LLV5,473stop,1terminal;997(57.56%)sempatCloseprofitnet,201>5%;735tidakpernah. GrossWR32.28vsnet31.65jadi feealonebukanutama. Auditretrospektifbukanjaminanexitcepatprofit. UserfocuskandidatbukanadopsiAFL. Baselineequityexactregression/prefix/accountinglolos. CONCLUSION.md.

9Oktober permintaanbuatkarakterSwinger danlanjutkan:81simulasi/52configtrainunik dalam search_choppy_swinger_profile.py(31run),_cost.py(23),_risk_profile.py(19),validate_choppy_risk_profit.py(8). Ringkasan choppy_swinger_profile_results/CONCLUSION.md,ALL_COMPARISONS.csv. Semua gagal minimal1gateprofiletrain. Recoverycost8/HHV5/stop2/age20fullfeeWR59.99win4.51loss7.26hold7.80CAGR-5.34;capATR4%/LLV5WR31.65loss4.96hold15.83CAGR4.29side-1.81;cap4/LLV10WR32.51loss6.02hold25.38CAGR9.51side2.98,spreadCAGR2.64side-8.30. LLV10trainspread14.50(side3.54)tetapivalid-5.81,test-21.44,reverse-16.18. BelumsetaraSwinger/robust,takdiadopsi/mainAFLtetap. GateWR45-60loss<=5avgwin>=10hold10-30N900profit+sidepositive;frozenbeforevalidation,datapernahdilihat.18tests/prefix/eligibility/accountinglolos.

9Oktober tuasexitWRvshold: grid_choppy_exit_levers.py/choppy_exit_lever_grid_results18runsHHV5/20/40 xnoER/.3/.5 xfees/spread,entryinversemarketchoppytetap. HHV20ERnone/.3/.5feeWR66.69/66.13/66.58,hold44.23/74.63/147.35,loss15.58/19.99/23.52. TanpaERHHV5/20/40WR62.12/66.69/66.71,hold16/44.23/77.48. ERkuatmemengaruhihold,tapikeduat uasubahWRdanhold;interaksi:ERketatmeredamefekHHVterhadaphold. BukanpembagianbreakoutkhususWR/ERkhusushold. Semua9gridnegatifsideeqdikeduaskenariobiaya. Fullsensitivitybukanvalidasiindependen;mainAFLtetap,prefix/eligibility/baselineregressionlolos. CONCLUSION.md.

9Oktober exitbreakoutsaja diminta: backtest_choppy_breakout_only_exit.py/choppy_breakout_only_exit_results18runs(3exitx2costx3windows). Entryinversemarketonlytetap;exitClose>priorHHVHigh20tanpaER,nextOpen,tanpastop. FullfeeWR66.69,win9.88,loss15.58,N1234,hold44.23(loser80.04),CAGR3.64,sideeq-2.86,rekor34/308,MDD-70.30;spreadCAGR-5.50,side-17.70. BaselineHHV+ERCAGR4.79/side-1.66. Validfee21.24/spread11.61,testfee1.73/spread-2.78. PenghapusanERmengecilkanlossdanholdtapiwinjugaturun,belumperformsideways.20tests/prefix/eligibility/regressionlolos;tidakadopsi/AFLtetap. CONCLUSION.md.

9Oktober pengguna menegaskan lagi setiapdugaan harusditest, janganhanyamenawarkanuji. Fadingmempercepatentry diuji test_fading_entry_ablation.py+audit_fading_entry_timing.py / choppy_fading_entry_test_results6runs. ExitERpasar>=.3tetap(versirisetbelumadopsi).264/2276episode sahamchoppy dengankeduasinyal: fadingfirstlebihawal,median4bar;379episodehanyafading. Gabunganfee70/3738actualentryfading-only(1.87%),bukan70tambahantrade netto;SMA-only3737trade. SMA-onlyWR41.26CAGR-9.23;gabungan41.36/-8.75;fade-only1617WR42.42CAGR-4.47,avgloss6.29vs5.18gabungan. SpreadCAGR-29.59/-29.50/-16.18. Dugaanbenarbersyaratpadasinyal,bukansemuaentryatauprofit. Baselineregression/prefix/eligibilitylolos,mainAFLtetap. CONCLUSION.md.

9Oktober exitERnonchoppy: backtest_choppy_er_exit.py/choppy_er_exit_results24runs(4exitx2costx3windows),entryinversemarketonlytetap. ExitERpasar>=.3 currentClose->nextOpen menggantiHHV+ERlama:fullfeeWR66.13->41.36,loss19.99->5.18,win14.20->6.21,hold74.63->10.28,N744->3738,CAGR4.79->-8.75,sideeq-1.66->-11.66;spreadCAGR-29.50. ERsahamonlyfeeCAGR-6.49;originalORmarketER-9.36. Matched481:130/163losersmembaik,153/318winnersmenjadiloss. MarketERvalidfee-1.99,test-4.38;spread-22.40/-18.32. ERunsigned(naik/turun), bukanbreakoutprofit. Tidakadopsi,AFLtetap.18tests/prefix/baselineregressionlolos. CONCLUSION.md.

9Oktober audit loss inversemarketonly: diagnose_inverted_losses.py, choppy_head_to_head_results/inverse_loss_audit.csv/summary danLOSS_DIAGNOSIS.md.252losersdari744,avg19.99%,hold126.87;avg17.86%loss sudahpadaCloseexit(atau3terminalmarks),nextfillmenambah1.82pp,fee.32pp;identitypertradereconciled.171/252losers punyaHHVbreakoutlebihawal tanpaER>=.3,menunjukkangateERmenundaexitkesempatan,bukanka usalprofitmenghapusER.101loss>20%,19>50%,6delayedfills. EntryrawsellSMA/fade tidakmensyaratkanrebound;exitrawbuyHHV20+ERtanpastop. TidakubahAFL.

9Oktober head-to-head choppy diminta: backtest_choppy_head_to_head.py / choppy_head_to_head_results4reruns. Swinger ideal kini ENTRYdigate marketproxyER20<.3 untukperbandingan, exitunchanged; bukan sekadarfilter1833ledgerlama. GatedSwinger2575trade,WR51.53,win14.69,loss3.14,hold19.20,sideannualeq99.26,record195/28069.64%,cash9.82. Inversemarketonly744,WR66.13,loss19.99,hold74.63,loser126.87,side-1.66,record37/280,cash8.70,slots10. Inversemarket+stockversilama753,WR66.80,side-2.68,record38/280. FullcalendarCAGR4.79/4.77/71.13 beda dari sideannualeq. 3453harichoppy,feebuy.15sell.25,tanpaspreadkedua. Originalbenchmarkdaninverseequityregressionlolos;eligibilityentrydiperiksa. Cashidle bukanmasalahutamaversiinverse. RESULT.md/METHOD.md. MainAFLtetap.

8Oktober pembalikansinyal pengguna: backtest_choppy_inverted_signals.py / choppy_inverted_signal_results18runs,3interpretasi pasaronly/pasar+stock/pasar+stockstop0.5 xfees/spread xfull/2016-2020/2021-2025. AcuanmainresearchBreakout20+stockER>=.3; buybaru=Close<SMA30 OR fade2; sellbaru=breakout20ANDER>=.3; nextOpen, longonly, rawconditions bukanledgertrades. Gatechoppyentryonly, exitallowedrezimberubah supaya tidakmustahilstockER<.3AND>=.3. Noextraexitpurevariant. Fullpasar+stockfeeWR66.80%,win13.75%,loss19.63%,753trades,hold73.71(loser127.24),CAGR4.77%,sideeq-2.68%,cash8.50%,MDD-68.55%;spreadCAGR-.60%,sideeq-11.43%. StopWR19.52loss3.99feeCAGR-2.21,spread-37.69. Purevalidspread8.73,test-1.78;tidakrobust/tidakgabung/AFLtetap.15tests/prefix/eligibility/accountinglolos. Koreksi: AFLaktif tanpaER, latestbelum7/7; ERstockbukanmarketgate. CONCLUSION.md merinci.

8Oktober entrybaru tanpa memangkas peluang: search_choppy_new_entries.py / choppy_new_entry_results23simulasi,11configtrainspread2000-2015+frozendiagnostic12checks. Entryshortbreakout/reclaimMA/failedbreakdown/pullback/channelflip; marketER<.3,cost8,exitstop0.5ATR/LLV10/fade2 tetap. MinimumN80%baseline stop-only ditetapkansebelumhasil; seluruhalternatifgagalminimal1gate. Diagnostikpullback20 (C>SMA20,Low<=SMA5,C>Cprev,C>Open,nextOpen)fullfeeN3812vs3385,WR22.46vs21.45,loss3.95vs4.04,CAGR12.13vs6.84,rekor62vs45/308,sidecash15.01vs31.32%. Sideannualeqmasih-.42%,spread-27.57%;CAGRspread-6.36%,testspread-22.75%,WRtest14.97vs15.55baseline. Frekuensiterjaga namunbelumedgeaftercost,tidakadopsi/mainAFLtetap.13tests/prefix/eligibility/regressionlolos. CONCLUSION.md memuatlogikabedaAFLaktifdanbatasasumsi. Risetadaptifbukanholdoutindependen.

8Oktober diagnosis terbaru vsSwinger: compare_latest_choppy_swinger.py membaca ledger,hasil choppy_wr_after_stop_results/latest_vs_swinger_choppy.csv dan SIDEWAYS_DIAGNOSIS.md. Kandidat stop0.5+stockER>=.5: sidewayscash79.93%,slots1.84 vsSwinger6.50%/9.44;stop-onlycash31.32%slots6.70. WR24.87vs50.46,loss4.39vs3.21,avgwin21.36vs14.67,expectancy2.02vs5.81,N965vs1833. Payout4.87vs4.57 sudahlebihbesar. Winnerhold26.76vs25.97;loser5.21vs10.44, bukanlagilossditahanterlalulama. Sideannualeq9.60vs87.15,rekor35/280vs191/280. Feeonly keduapihak,tradeentrychoppyvsdailyregime dibedakan. Bukan dekomposisi kausalCAGR;idlelebihbesar tidakmembuktikan tambahantradeprofit. Janganpakaiidle18.89%/loss7.96% versi original untuk kandidat terbaru. AFLtetap.

8 Oktober 2026, menaikkan WR sesudah mitigasi: search_choppy_wr_after_stop.py / choppy_wr_after_stop_results selesai22run,10konfigurasi entry tunggal training2000-2015 lalu frozen vsbaseline2016-2020/2021-2025/full dua biaya. Stop0.5entryATR tetap, LLV10/fade2 tetap, marketER<.3. ER SAHAM>=.5 paling menaikkan WR dengan guard training; SMA/extension/cost16 tidak. FullfeeWR21.45->24.87%,loss4.04->4.39%,N3385->965,CAGR6.84->6.97%,PFmoney1.08->1.47,rekor45->48/308,sideeq-2.79->9.60%. SpreadCAGR-8.02->1.77%,sideeq-26.62->-0.13%;testspreadCAGR.33%,sideeq-.28%. BelumtargetSwingerchoppyWR50.46/loss3.21; bahkanoriginaltanpastopCAGRfee10.20/spread1.98 masihlebihbaik. Testlossmelewatiguardrelatif10%training. Tidakadopsi/mainAFLtetap.13tests/prefix/eligibility/baselineregressionlolos. Rincian CONCLUSION.md; previously seen data, bukan validasi independen.

8 Oktober 2026, lanjutan mitigasi: mitigate_failed_breakout.py / choppy_early_failure_results selesai 14 simulasi. Exit tambahan hanya sistem kedua: Close di bawah entry dan level breakout ASLI selama 1/2 penutupan berturut-turut dalam 3/5/10 bar awal, lalu next tradable Open. Semua variasi menurunkan avg loss dan WR, tetapi CAGR di bawah baseline dalam dua skenario biaya. Kandidat CAGR tertinggi 3bar/2close: fee loss6.68%, WR32.51%, CAGR9.69%, rekor57/308; baseline7.96%/36.92%/10.20%/55. Spread CAGR0.12% vs1.98%, sideways equivalent-15.03% vs-12.32%. Matched-entry:490/1053 original losers membaik,62/607 original winners berubah rugi. Tidak adopsi, tidak gabung, AFL utama tetap. Early_failure opsional off default; bukan guaranteed stop. Rincian CONCLUSION.md dan REPORT.md. Digabung uji sebelumnya,34 simulasi mitigasi selesai; avg loss lebih kecil belum berarti edge lebih baik.

8Oktober mitigasi loss sistemkedua: mitigate_choppy_losses.py/choppy_loss_mitigation_results,20run exit-only, entrytetap. FixedentryATRClosestop0.5/1/1.5/2 nextOpen, LLV5/3,comboLLV5+stop1. Semuaavg losslebihkecil namunsetelahfeeCAGRdi bawahbaseline10.20%;spreadbaseline1.98%,seluruhmitigasiprimaryprioritynegatif. Stop0.5loss4.04%vs7.96% tetapiWR21.45%vs36.92%;matchedentries266/596baselinewinnersmenjadiloss. Tidakadopsi,mainAFLtidakdiubah. Entry_stop_atr opsional mesin offdefault; bukan guaranteedintradaystop.

8Oktober2026: permintaan membuat sistemkedua menyerupai karakterSwinger diuji36run kanalflip/rangeescape/failedbreakdown dengan filter rentang/biaya. Script search_choppy_channel_system.py; strictresults choppy_channel_system_results, --market-only results choppy_channel_market_only_results. Prototipe diagnostik RangeEscape10/costmultiple8, ERpasar<0.3 (bukanERsaham), exitpriorLLV10 ataufade2 nextOpen, tanpaH200. FullfeeCAGR10.20%,55/308rekor,WR36.92%,meanhold24.34; fullspread1.98% namuntest2021-2025spread-7.43%,sidewaysfullspread-12.32%. Belum performsideways/benchmark dan tidakdigabung. Seluruh20konfigurasi training gagal minimal satu gatekelulusan. Tetap pisahkan profitfullperiode dari profitpada harisideways. AFL utama tidakdiubah.

Usulan terbaru diuji di backtest_er_switch.py/er_switch_results: ambangER0.3/0.4/0.5/0.6; perbandingan naikkanERsaham saja, tambahmarketERgateprimary, lalu automaticentryswitchsecondary. Higherthreshold memperluaschoppygate. PrimarySMA30/fade2/noH200,secondarybandreentry2std/hold20diagnosticfixed.24simulasi; fullswitchmasihburuk disideways. ERsaham0.4saja membaikinsample fee37.64%spread17.71%,bukanotomatisdipilih. Gateberlakupadaentry;posisilamatidakdipaksajual. MainAFL tidakdiubah,belumadaedgechoppyterbukti.

7Oktober: pengguna menegaskan sistem sideways harus terbukti perform secara mandiri SEBELUM digabung ke utama. Jangan menjadikan berkurangnya idle atau bertambahnya transaksi sebagai syarat kelulusan. Pencarian terpisah di search_standalone_sideways.py: train2000-2015 untuk memilih,2016-2020/2021-2025 tanpa retuning. Seluruh data pernah dilihat sebelumnya sehingga bukan holdout eksternal murni. Uji RSI2oversold diatasSMA200, support rejection, dan breakout5 diatasSMA50 saat marketproxy sideways; hasil belum ada yang lolos. Versi kontrol exitbelowSMA di standalone_sideways_results; versi recoveryexitaboveSMA untuk meanreversion di standalone_sideways_recovery_results. Tidak digabung dan AFL tidak diubah.

Pengguna meminta entry dan exit mandiri untuk sistem sideways, digabung dengan sistem tren dalam portofolio yang sama guna mengejar Swinger. Ini memperluas scope dari perubahan exit saja. Prototipe backtest opsi secondary pada backtest_breakout_er_portfolio.py, runner search_dual_system.py, hasil dual_system_results.26simulasi mean-reversion ER<0.3/SMA20/ATR belum meningkatkan hasil gabungan; jangan menganggap semua strategi sideways gagal. Maks10slot/modal1miliar bersama; tidak menjumlahkan CAGR modul. AFL aktif tetap belum diganti.

## Preferensi verifikasi hipotesis pengguna

Klarifikasi pengguna: "acak" pada diskusi WR berarti mencoba/mengubah tuas indikator untuk mengetahui pengaruhnya pada WR, bukan entry acak. Gunakan variasi satu tuas perbandingan dengan biaya/entry/exit lain tetap, nilai WR bersama payout/expectancy. Eksperimen random entry sempat dimulai lalu dihentikan; hasilparsial tidak boleh dianggap eksperimen selesai.

Penegasan7Oktober2026: untuk seterusnya setiap statement/dugaan strategi pengguna harus dicek atau diuji terlebih dahulu. Pisahkan fakta terukur, hipotesis, dan kesimpulan kausal; jangan hanya menyetujui. Simpan preferensi ini dalam konteks proyek. Target Swinger ideal diterima sebagai benchmark karakter hasil, transaksi boleh berbeda. Versi utama penelitian terkini Breakout+ER/SMA30/fade2 mempunyai idle sideways27.97%; angkaidle6.23% milik H200 tidak berlaku lagi.

Pengguna meminta semua pernyataannya diperiksa atau diuji terlebih dahulu. Jangan menerima dugaan sebab-akibat sebagai fakta. Swinger fill ideal dipilih sebagai target aspiratif; tetap pisahkan dari hasil kausal yang dapat dieksekusi. Hipotesis holding lebih pendek diuji pada modul Breakout+ER dengan entry, fading, modal dan biaya tetap; lebih banyak transaksi belum berarti CAGR lebih tinggi. Jangan otomatis mengubah AFL kandidat berdasarkan hasil pencarian in-sample.

## Prototype Swinger benchmark diminta pengguna

Ditemukan versi asli installed AmiBroker Formulas/Custom/prototype swinger.afl, identik Downloads/Test Algo; snapshot Prototype_Swinger_Source.afl (sha256 D7F4EDF5567D10704B5F111E0FF39768BB48851A6E98C4AE478A24B2B8CE4708). Swing5 HHV/LLV state TSL, Buy Cross(C,tsl),Sell Cross(tsl,C);fill e=priorTSL pada bar sinyal. MACD/RSI/Stoch hanya warna chart. User meminta fillideal bukanClose. Benchmark2000?2025 modal1billion10slot compounding, fee0.15/0.25 tetap tanpa spread/tick scenario. Literalideal net CAGR114.77%,249/308bulanrekor80.84%,MDD-18.81%; NAMUN sinyalClose memanfaatkan harga lebihawal dan964fill luarOHLC, bukan causal/executable. Pembanding stop-order intraday previousTSL gap-aware net30.25%,102/308=33.12%,MDD-49.67%; ini interpretasiorder bukan sinyalasli identik. Sinyalasli nextOpen net21.51%,83/308=26.95%,MDD-55.52%. Hasil prototype_swinger_benchmark_results;4testsdanledgercashchecklolos; bukan nativeAmiBroker. Benchmarkblokentryexit memilikisamebar/gap/volumeassumptionsdidokumentasikan.


## Checkpoint migrasi web ? 9 Oktober 2026

Optimasi optimize_primary_inverse_regimes.py selesai48run, optimized_inverse_regime_results/CONCLUSION.md. GridHHV10/20,SMA20/30,rotateFalse/True:semua8gagaltrain own-regime profit. FROZEN HHV20/SMA20/carry passed=false hanya diagnostik. Fullfee gabungan15.54%,spread3.65%,testspread-1.11%; baselineSMA30 full15.80%/5.51%,testspread1.02%. InverseSMA20fullspreadCAGR-0.89%,choppyannual-9.12%. Tidakadopsi/defaultAFLtetap.20tests lulus kembali. Pengguna meminta paket Download untuk melanjutkan web; baca HANDOFF_CONTEXT.md sebagai urutan konteks terbaru, bukan memakai kronologi catatan lama sebagai konfigurasi aktif.

## Ringkasan 15–21 Oktober 2026
Lihat `RESEARCH_LOG_2026-10-15_21.md` untuk ringkasan per permintaan pengguna dan folder hasilnya. Inti: pilihan utama v2
(buy stop HHV20 +0,5%, ER20 ≥ 0,2) B 2000–25 49,3% vs Swinger ideal 102,0%; dengan universe point-in-time + filter data
basi + batas likuiditas sekitar 16%/th, MDD −44%. Tujuh pendekatan logika kedua untuk sideways tidak menutup biaya.
AFL aktif tidak diubah.
