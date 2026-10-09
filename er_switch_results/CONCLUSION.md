# Putusan skema otomatis ER

24simulasi selesai (4ambang x3mode x2biaya). Skema entry switch berhasil: marketERprevious>=ambang mengaktifkan utama, marketERprevious<ambang mengaktifkan sekunder. Kedua gate tidak pernah aktif bersamaan; semua tanggal entry aktual diperiksa. Posisi lama tetap mengikuti exit masing-masing. Ini pengujian baru atas usulan pengguna, bukan adopsi atau pernyataan bahwa sekunder yang sebelumnya gagal telah lolos standalone.

ERper-saham saja0.3->0.4: CAGRfee33.65%->37.64%,spread13.37%->17.71%; fee-sideways20.10%->24.31%,bulanrekor108->111/308. Hasil in-sample, belumvalidasiindependen. Tidak otomatis mengganti utama.

Pada ambang0.4, menambahkan gate marketER pada primary menurunkan CAGRfee menjadi22.53%,spread13.84%. Mengaktifkan secondary pada gatechoppy menurunkanlagi menjadi7.10%fee dan-19.57%spread. Return tahunan ekuivalen sideways gabungan-7.29%fee,-32.81%spread. Primary-only gate0.4 memiliki76/308bulanrekor,combined41/308. Marketdays ER<0.4 sekitar71.10%, sehingga thresholdlebih tinggi memperluas waktu aktif secondary.

Pada seluruh ambang0.3/0.4/0.5/0.6, combinedfeeCAGR16.11/7.10/2.48/-5.26%; spread-10.00/-19.57/-24.06/-27.91%. Seluruh combined attribution sidewaysfee negatif. Jadi menaikkanER dan switchbelum memenuhi tujuan perform di sideways. Secondaryfixedbandreentry2std/hold20 belum punya edge terbukti; mekanismeregime tidak memberi edge otomatis. Ini tidak menyangkal semua arsitektur regimeswitch, hanya kandidat konkret diuji.

Evaluasi sideways tetap definisi marketproxyER0.3 pada semua percobaan; tidak mengganti yardstick saatubahthreshold. Proxy bukandataIHSG. ERtinggi tidak membedakan naik/turun;longonlybreakout memberi arahprimary. Asumsi spread counterfactual, data/universe/capacitylimits tetap.21unit tests plus accounting, baseline, gateeligibility dan attribution checks passed. AFL tidak diubah.
