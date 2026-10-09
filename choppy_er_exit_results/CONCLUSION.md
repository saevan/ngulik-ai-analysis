# Exit ketika ER tidak lagi choppy

9 Oktober2026:24simulasi selesai (4exit x2biaya xfull/2016-2020/2021-2025). Entry inverse MARKETchoppy sama di semua kasus: sinyalSMA30below ataufade2 dari Open, previous-completedmarketER<.3,entrynexttradableOpen. Tanpastop/H200. Primary/AFLaktif tidakberubah. ER20>=.3 mengukurgerakterarah, bisa naik atau turun; bukan bukti breakout naik atau posisi telahprofit.

Exitbaseline=Close>priorHHV20ANDstockER>=.3. MarketER menggantinya dengan ERPASAR>=.3 padaClose; stockER dengan ERSAHAM>=.3; gabunganoriginalORmarketER. SemuaexitnexttradableOpen;currentCloseERtidakdilagdua kali, gateentry memakai regimeyangsudahlag. State>=batas untukmenangkapnonchoppyberkelanjutan, bukan hanyacrosssatu hari. Pendingexitpersistsetelahsinyal meskiERkembalichoppy/suspensi. Evaluasipadaobservasibar saham yangtersedia.

Full4Jan2000–15Agustus2025,Rp1miliar/10slot/compounding,feeallinbuy.15%sell.25%:

| Metrik | Exitlama | ExitERpasar |
|---|---:|---:|
| WR |66.13%|41.36%|
| Avgwin |14.20%|6.21%|
| Avgloss |19.99%|5.18%|
| Holdingbar |74.63|10.28|
| Transaksi |744|3738|
| CAGR |4.79%|-8.75%|
| Annualequivalentsideways |-1.66%|-11.66%|
| MDD |-65.54%|-91.57%|
| Recordmonths |63/308|0/308|

Hasil berarti holding/loss berkurang tetapi profitabilitas memburuk. Matchedentry481(ticker,tanggal sama):130/163original loser membaik,153/318original winner berubah loss. Hanya auditretrospektif pasangan, bukan filterprediksi atau atribusipenuhCAGR;kas/slotmengubahrealizedtrades.

ExitERsaham fullfeeWR35.68%,loss4.41%,CAGR-6.49%,side-12.03%. GabunganoriginalORmarketERfeeCAGR-9.36%,side-12.73%. Tidakada variasifullfee yangmeningkatkanCAGRatau profitdaysideways dibandingbaseline.

Denganstressspread1tickeachside,fraksimodernBEI/100shares:baselineCAGR-.81%,marketER-29.50%,stockER-35.28%,gabungan-31.90%. MarketERside-44.10%. Asumsicounterfactual, bukanbidaskhistoris. MarketERvalid2016-2020fee-1.99%/spread-22.40%;test2021-2025fee-4.38%/spread-18.32%. Kerugianbukansekadar satuperiodefull.

Kesimpulan: usul berhasil sebagai pemendekholding/pengurangavg loss, belum sebagai peningkatanedge. ERpasar menjawabrezimagregat,bukanapakahpemulihanposisisaham sudahcukup; sinyalbolehmuncul saatgerakturun menguat atau sahammasihbelumpulih. Tidakadopsi/tidakgabung. Datahistoris adaptif,bukanvalidasiindependen. Sideannualequivalent mengannualisasiatribusi logreturn padaharisideways, bukanCAGRportofoliomandiri.18tests lulus (exitmarketnextOpen, stockdowntrendER, gabungansinyal,engine),prefixentry/exit danregresibaselineequitylolos. Script backtest_choppy_er_exit.py, REPORT/comparison/ledgerdisimpan.
