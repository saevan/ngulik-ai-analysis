# Status: belum mencapai karakter Swinger saat choppy

9 Oktober2026.81 simulasi selesai dalam4batch;52konfigurasi training unik, ditambah pemeriksaan kandidat beku pada2016–2020,2021–2025,seluruhperiode danprioritas tickerterbalik. Tidak ada konfigurasi yang lolos seluruhgate training yang ditetapkan. TidakmengubahAFLaktif/main, tidakmenggabungkan kandidat gagal. Ini hasil negatif penelitian, bukan strategi selesai memenuhi target.

## Target dan metode

Benchmark tetap Swingerideal yang entryhanya pada tanggal marketproxyER20<.30,full4Jan2000–15Agustus2025. Fee0.15%beli/0.25%jual,modalRp1miliar/10slot/10%equitysebelumnya perentrycashcap compounding. Targetfull:WR51.53%,avgwin14.69%,avgloss3.14%,holding19.20bar,2575trade. Dailychoppyannualequivalent99.26%,records195/280. Kandidat seluruhnya nextOpen dari sinyalClose dan stopClose; benchmarkfillideal dipertahankan sesuai pilihan pengguna.

Gate eksplorasi train2000–2015:WR45–60%,loss<=5%,avgwin>=10%,hold10–30bar,N>=900,CAGR>0,sideannualeq>0,moneyPF>1.1. Ini rentang pendekatan sementara, bukan klaim karakter persis sama. Jika tidak ada pass, kandidat terdekat menurut distanceyangditetapkan tetap diuji hanya diagnostik. Parameter dibekukan sebelumvalidasi; seluruhriwayatpernahdilihat sebelumnya sehingga bukanholdoutindependen.

## Eksperimen

1. search_choppy_swinger_profile.py:24kombinasi inverse/pantulanbawahrentang/pullback xexitSMA20/HHV5 xstop1/2entryATR xdengan/tanpaumur20bar.31runs.
2. search_choppy_swinger_profile_cost.py:16kombinasi pantulan/pullback denganrange20>=8kaliestimasi biayafeespread padaClose sinyal.23runs. KontrolSMA20 padaentrypullbackdiatasSMA20 cenderungkeluarsangatcepat; hasil ini bukan kandidat yang dipilih.
3. search_choppy_swinger_risk_profile.py:12kombinasi pantulanbawahdenganClose>SMA50 ataupullbackSMA20,exitClose<priorLLV5/10,stop2entryATR,tanpabatasumur,range/cost8,ATRprevious/Close<=1.5%/2.5%/4%.19runs. Cap memakaiClose yangdiketahui,bukanhargaOpenmasa depan; bukanjaminanmaxlosskarenaexitClose/nextOpen/gap.
4. validate_choppy_risk_profit.py:8runs kandidatLLV10/cap4% yang dipilih dari TRAINING batch3 karena profitfull/sidepositif danN>=900, meski gagalWR/lossgate; direplikasi train laluvalidasi tanpa retuning. Bukan seleksi berdasarhasiltest.

## Seluruh periode, fee-only

| Karakter | Swingerideal | Recovery cost8/HHV5/stop2/age20 | LowATR cap4/LLV5/stop2 | LowATR cap4/LLV10/stop2 |
|---|---:|---:|---:|---:|
| WR |51.53%|59.99%|31.65%|32.51%|
| Avgwin |14.69%|4.51%|12.56%|18.24%|
| Avgloss |3.14%|7.26%|4.96%|6.02%|
| Holdbar |19.20|7.80|15.83|25.38|
| N |2575|5266|2534|1778|
| FullCAGR |71.13%|-5.34%|4.29%|9.51%|
| Annualequivalent harichoppy |99.26%|-14.47%|-1.81%|2.98%|

Metriktrade memakai umurtransaksi yang masuk saat choppy; bisa meliputi tanggaltrending. Sideannualeq mengannualisasi atribusi logreturn pada tanggalchoppy saja,bukanCAGRportofoliomandiri. FullCAGR mencakupseluruhkalender.

SpreadstressmodernIDX1tickmasingmasingsisi/100shares:ketigakandidatdiatasCAGR-22.23%/-4.89%/+2.64%;sideannualeq-39.64%/-16.61%/-8.30%. Stressbukanbidask/fraksihistoris. KandidatLLV10memiliki trainingCAGRspread14.50%/side3.54%,tetapivalid2016–2020CAGR-5.81%/side-16.98%,test2021–2025CAGR-21.44%/side-27.79%;reverseprioritytest-16.18%/side-28.65%. Jadi profittrainingdanfulltidakmembuktikanrobustnesssideways.

Kesimpulan: kandidatWRtinggi menghasilkanwinnerterlalukecil/lossbesar; kandidatdurasi/frekuensilebihdekatmasihWRrendah. Karakter belum tercapai bersamaan. Tidak ada alasan empiris dari pencarian ini untuk mengganti sistem utama. Semua prototipe dapat direproduksi dari script danPLAN/FROZEN masingmasing. ALL_COMPARISONS.csv menyatukan81hasil.18unit tests terkaitengine/stop/timeexit/biaya lulus, prefixentry/exit sertaeligible/accounting/atribusi diperiksa setiaprun. Data selecteduniverse/corporateactions/liquiditylimitations tetap.
