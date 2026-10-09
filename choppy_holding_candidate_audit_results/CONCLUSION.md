# Diagnosis WR kandidat holding yang disukai pengguna

Versi yang dipilih untuk fokus riset: pullbackClose>SMA20,Low<=SMA5,Close>CpreviousdanOpen,marketER20<.3,ATRprevious/Close<=4%,range20>=8kaliestimasicost. ExitClose<priorLLV5 ataufixedentry2ATRstop,semuanextOpen,tanpaholdlimit. TidakmengubahAFLutama. Usermenyukaikandidatinibukanberartisudahlolostarget.

4rerunonefactorfull2000–15Agustus2025,feeallinbuy.15%sell.25%,Rp1miliar/10slotcompounding. Baselineequityregressionexactlolos,prefixdanakuntansidiperiksa. BenchmarkSwingeridealentrymarketchoppy darihead-to-headsebelumnya.

| Varian | WR | Avg loss | Holding | CAGR |
|---|---:|---:|---:|---:|
| Baseline LLV5/stop2/cap4% |31.65%|4.96%|15.83|4.29%|
| Tanpa stop2 |32.29%|5.15%|16.6|3.56%|
| LLV10 |32.51%|6.02%|25.38|9.51%|
| Tanpa capATR |33.18%|5.83%|16.4|10.97%|

Stopremoval menaikkanWRhanya.64pp,LLV10+.86pp,capremoval+1.54pp; tidakmendekatiselisih19.88ppkeSwinger51.53. Ini ablasidalamkonfiginitidakmenolaksemuavariasidimasa depan. GrossWR32.28%vsnet31.65%;feealone .63pp, bukanpenjelasanutama selisih. FillSwingeridealtetapberbeda, diterimasebagai target; tidakmengatribusikan seluruhgapbenchmarksecara kausalkeentry saja.

Conditionalduration: kandidatwinner28.20bar vsSwinger27.01,loser10.10vs10.89. Meanholding15.83vs19.20 juga dipengaruhiproporsiwinner/loser, bukan durasisetiapkelompok yangberbeda jauh.

2534trade,1732losers.1258losers(72.63%)berlabelcustom_exitLLV5,473stop,1terminal. Labelprioritasexitbukanbuktibahwatidakadasinyallainpadabar sama. LLV5menjualketikalevelbawahpecah,bukanpadasaatprofitmencapaipuncak.997/1732losers(57.56%)sempatCloseprofitnet(markfeeexit)sebelumhariOpenliquidation;201(11.61%)pernah>5%.735tidakpernahCloseprofitnet. IntradayHightidakdipakaiuntukklaimprofitrealizable;CloseexitdaydikecualikankarenasudahkeluardiOpen. Ini auditretrospektif, bukanfilterentrylookahead;menjualsegera saatpositif dapatmemotongwinnerbesar danbelumdiujisebagaiperbaikan.

Entry sudahmengonfirmasicandlehijau danCnaik; tapibelummenuntuttembusresistensi/reclaimpreviousHigh ataupulihpadabatasrange. Tidakbisa menyimpulkan tiaploseradalahentrysalah. Data menunjukkan dua kelompok untukpengujianlanjutan:reboundyangtidakpernahprofitClose danreboundsempatprofitlalugagal. Mengubahholdingrata-rata sajatidakcukup,stopdanATRfilterbukanpenjelasanutamagapberdasarkanablasi.

Rawloserpaths.csv,loser_summary.csv,comparison/ledger/equitytersimpan. audit_choppy_holding_candidate.py mereproduksi4ablasi; PLAN.json mencatat empatablasi danCONCLUSION.md merincidefinisinya. Tidakadopsi/tidakgabung. Semuahasilhistorispernahdilihat,bukanvalidasiindependen.
