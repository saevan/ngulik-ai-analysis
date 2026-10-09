# Uji dugaan fading mempercepat pembelian

9 Oktober2026. Enam full-period backtest selesai:entry gabungan/SMA-only/fading-only x fee/spread. Exit dikunci pada versi penelitian terakhir ERPASAR>=.3 saatClose->nexttradableOpen; bukan exitbreakout lama dan bukan perubahan default/AFL. MarketentrygateER20<.3,Close<SMA30OROpen-Low>=2ATR14previous,ATRvalid,sinyalshift1bar,tradableexecution. ModalRp1miliar/10slot/compounding,4Jan2000–15Agustus2025,feeallinbuy.15/sell.25%. SpreadstressmodernIDX1tickeachside100shares bukanbidaskhistoris. Tidak ada optimasi/adopsi.

Signal timing diperiksa per saham x episode pasarchoppy berturut-turut, pada tanggal kesempatanentrynextOpen yangeligible; mengabaikanstateportofolio untukmengisolasiwaktusinyal.19860episodepunyasinyalentry;2276punyakedua jenis;264fadinglebihawal(11.60%dariepisodekeduasinyal),549pertamasama. Pada264kasus medianlead4bar saham,mean6.125bar.379episodehanyafadingtanpaSMAsebelumepisodeberakhir, jadi tambahan kesempatan, bukanleadterukur. Perbandingandengan sinyalSMAmasa depan ini auditretrospektif, bukanaturanentrylookahead.

Opportunitybars SMA136189,fading3197,overlap2141,fading-only1056. Countbar ini bukantransaksi. Portofoliogabunganfee3738trades,70entry(1.87%)fading-only pada barpemicu, yakniSMA-only tidakmemenuhisyarat padaentryyangsama. Bukanberarti70transaksitambahannetto: perubahanstate/cash/slotdapatmenggantitransaksilain. Jumlahtrade SMA-only3737, gabungan3738, fading-only1617.

| Entry | Trade fee | WR fee | Avg loss fee | CAGR fee | CAGR spread |
|---|---:|---:|---:|---:|---:|
| SMA saja |3737|41.26%|5.19%|-9.23%|-29.59%|
| Fading saja |1617|42.42%|6.29%|-4.47%|-16.18%|
| Gabungan |3738|41.36%|5.18%|-8.75%|-29.50%|

Kesimpulan dugaan: benar bersyarat, fading dapatmemajukan firsteligibleentrysignal, bukansemuaentrydanbukaneksekusiintraday. Actual70entrymembuktikanjalurfadingdipakai ketikaSMAfalse, tetapbelummenjaminhargaentrylebihbaik atauprofit. Gabungan sedikitlebihbaikdariSMA-only dalamujiini tetapi tetapmerugi; fading-only lebihsedikittrade danlebihbesaravgloss. Temuanbukanedgeuniversal, datain-sample, exitpenelitianterakhirsendiribelumlayak.

Gabunganexactregressionterhadapchoppy_er_exit_resultsloloskeduaskenario;prefixcausalitysemuaframe/eligibility/akuntansidiperiksa. Scripts test_fading_entry_ablation.py dan audit_fading_entry_timing.py. Detail signal_episode_timing.csv, timing_summary.csv, actual_fading_only_entries.csv, ledger/equity/REPORTtersimpan. AFL/main tidakdiubah.
