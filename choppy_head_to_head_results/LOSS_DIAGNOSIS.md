# Mengapa kerugian inverse besar

Audit diagnose_inverted_losses.py atas744trade versi inverse_market_choppy,4Jan2000–15Agustus2025,fee0.15/0.25%,tanpaspread.252losers,rata-rata19.9939%,holding126.87bar;101loss>20%,19loss>50%. Angka ini bukan versi tambahanstockERgate.

Identitas pertrade direkonsiliasi: returnClosepadasinyal + perubahanhargaOpenfillrelatifentry + dampakfee = netreturn. Rata-rata losers: -17.85797% sudah terbentuk sebelum eksekusi (Close sinyalexit, atau terminalClose untuk3terminaltrades), -1.81514poinpersentase tambahan setelah sinyal, -0.32083poinpersentasefee.6losers menunggu lebih dari1bar sesudahsinyalexit; bukan seluruh kerugian berasal dari nextOpen ataubiaya.

Entry murni=Close<SMA30 atau fading2ATR, marketERproxy<.3; tidak mensyaratkan rebound ataustockERchoppy. Harga melemah bisa langsung dibeli. Exit hanya jikaClose>priorHHV20DANstockER>=.3; tanpa stop/holdlimit/meanMArecoveryexit. Breakout ini bisa terjadi dari level yang sudah jauhdi bawahentry karenaHHVrolling turun; bukan jaminan pemulihan kerugian.171/252losers (67.86%) sempatmemiliki breakoutHHVsebelumsinyalexit pertama tetapiERtidakmemenuhi. Ini bukti filterERmenunda kesempatanexit pada transaksi tersebut, bukan bukti menghapusERakanmeningkatkanCAGR; perluablasi untuk klaimprofit.

Contohhistoris ledger:ARTO16Mar2022entry–24Mei2023exit,289bar,net-82.60%;Closepadasinyalexit sudah-82.53%. Harga data/aksi korporasi belumdivalidasi, bukan klaimprofit riil terverifikasi. ScriptmemeriksafirstexitconditiondanfillnexttradableOpen. Rawledgerdetaildanringkasantersimpan inverse_loss_audit.csv daninverse_loss_summary.csv.

Kesimpulan mekanisme: raw inversions membalik exit trend menjadi entry saat lemah, tetapi tidak menyediakan invalidasi kegagalan pemulihan; exit menunggu kekuatan breakout+ER. Asal loss dominan sebelum sinyal, bukanfee. Tidak mengubah strategi, tidakmengasumsikan stop lebihketat otomatismenyelesaikanWR/expectancy.
