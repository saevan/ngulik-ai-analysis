# Rancangan kembali ke utama dan inverse, 9 Oktober2026

User mengembalikan fokus dari kandidat pullback/lowATR/LLV ke sistem utama penelitian Breakout+ER dan pembalikan sinyalnya. Ini implementasi riset dalam backtest_primary_inverse_switch.py; bukan mengubah AFLaktifpullback. Default lama mesin tetap, style inverse baru bersifat opsional. Tidak mengklaim7kriteria atau setaraSwinger.

## Sinyal dan switching

ERpasar20 dari proxy equal-weight harga saham yang tersedia, ambang0.30, barpasarsebelumnya untuk gateOpen; bukanIHSG. ER>=.30 hanyaizinkan entryutama,ER<.30 hanyaentryinverse;warmupunknown tidakentry. Keduaizin salingeksklusif. ERbesar tidakmengkodearahnaik,tetaplongonly.

Sinyal utama asli: Close>priorHHVHigh20 DAN ERsaham20>=.30. Exit utama Close<SMA30 ATAU Open-Low>=2ATR14barsebelumnya. FadingdariOpenbarberjalan,bukanentry. Inverse entry menggunakan kondisi exitutama tersebut, denganATRvalid; inverse exit menggunakan kondisi buyutama asli breakout20+ERsaham>=.30. Tidakmembalik transaksi ledger, tidakshort. Tidak menambahkanstopATR/H200/exitERpasar/LLVdari eksperimen sebelumnya.

SinyalClose dieksekusi Openberikutnyayangdapatdiperdagangkan. Entrybuilderdibatasi eligibility padaexecutionbar, tidakantrianentrylamamelintasi regime. Exitpending bertahan saat suspensi. Posisi menyimpan modul asal;pergantianER hanya menggantiizinentry, bukan memaksa jual/mengubahexitposisilama. Karena itu posisikeduamodulbisaoverlapsetelahregimeberubah. Kalau maksud user kelak ingin forcedrotation, itu varianberbeda yangbelumdiimplementasikan.

SharedRp1miliar,10slot,onepositionperticker,alokasientry10%equityClosehari sebelumnya dibatasikas,compoundingtanpaleverage;tidakmenjumlahCAGRstandalone. Tidakreentrytickerpadahariexit. TerminalClosevaluationmengikuti dataengineexisting. Mainownership/inverseexit danstandaloneequivalence diujiunit.

## Hasil8runs full4Jan2000–15Agustus2025

Feeallinbuy.15%/sell.25%. SpreadstressmodernBEIgrid1/2/5/10/25,1ticktiapsisi,100shares,seluruhsejarahcounterfactualbukanbidask/fraksihistoris.

| Portofolio | CAGRfee | CAGRspread | Rekorfee/308 | Sideannualeqfee | Sideannualeqspread |
|---|---:|---:|---:|---:|---:|
| Utamaasli(stockERsaja) |33.65%|13.37%|108|20.10%|0.51%|
| UtamaentrypasarER>=.3 |27.90%|15.96%|91|15.43%|14.82%|
| InverseentrypasarER<.3 |4.79%|-0.81%|63|-1.66%|-10.92%|
| Gabungan |15.80%|5.51%|81|6.54%|-2.52%|

GabunganfeeWR55.11%,1321trade,81/308bulanrekor26.30%,MDD-58.38%. SpreadWR50.49%,36/308rekor11.69%,MDD-74.37%. Sideeq adalah annualisasi atribusireturnhanya tanggalberlabelchoppy, bukanCAGRportofoliomandiri. RekorATHclosingequityglobal, tidakresetregime.

Gabunganfee:utama666tradeWR46.10%meanhold22.31;inverse655WR64.27%,win13.38%,loss18.73%,meanhold73.52. Utamagatedstandalone1528trade. Penambahaninverse mengubahjalurkas/slot danrealizedtrades;tidakmenjamin mengisiidle secara produktif. Mainentryprioritytidakbisamenggusurposisiinverseyangmasihterbuka. Janganmengartikandiffjumlahtrade sebagai daftaridentik866tradehilangtanpapairing.

18tests lulus termasukregimechangesretainownership daninversecustomexit parity;complementarygates,prefixcausality,actualentryeligibility,akuntansi/atribusi diperiksa. Rerunoriginalmain daninversestand alonesamaequityhasilsebelumnyadua biaya. Datahistoris sudahdilihat,belumvalidasiindependen/nativeAmiBroker;likuiditas/aksi korporasi/universe limitations tetap. Rancangan diterapkansebagai riset sesuai arahanuser, tetapi gabungan belummengunggulikontrolutama danbelumperformsidewaysafterspread. AFLaktif tidakdiubah.
