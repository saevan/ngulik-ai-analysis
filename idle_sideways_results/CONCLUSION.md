# Hasil uji dana idle sideways

Preferensi pengguna untuk selalu memeriksa/menguji statement disimpan di AGENTS.md dan STRATEGY_NOTES.md. Fakta awal kandidat Breakout+ER/SMA30/fade2 memiliki idle sideways27.97% fee-only. Hipotesis bahwa menambah entry untuk memakai kas itu meningkatkan profit diuji dengan20simulasi, bukan langsung diterima.

Modul independen baru membeli pantulan masuk kembali ke lower Bollinger band dengan ER saham<0.3 dan proxy pasar sideways. Prioritas entry utama terlebih dahulu; hanya sisa kas/slot dipakai. Tidak ada pemaksaan entry saat syarat belum terpenuhi. Enam kombinasi band1/1.5/2 dan hold10/20 diuji pada dua biaya. Kandidat terpilih berdasar return tahunan ekuivalen sideways spread tertinggi (tetap negatif) adalah band2/hold20; diuji standalone dan reverse priority. Semua tetap in-sample.

Fee-only baseline -> gabungan band2/hold20: CAGR33.65% ->24.05%; return tahunan ekuivalen sideways20.10% ->6.30%; idle sideways27.97% ->14.32%; tambahan1252transaksi sekunder. Dengan stress spread: CAGR13.37% ->-4.63%; sideways0.51% ->-24.60%; idle28.22% ->15.02%; tambahan1284transaksi sekunder. Jadi dana lebih banyak bekerja tidak otomatis menghasilkan profit tambahan.

Standalone kandidat memberi CAGR-10.51% fee-only dan-23.44% spread. Ini bukti kandidat kedua sendiri belum memiliki kinerja portofolio bersih positif, bukan hanya masalah benturan alokasi. Posisi sekunder yang sudah terbuka masih dapat menghalangi sinyal utama di hari berikutnya; prioritas saat entry bukan jaminan nol opportunity cost. Tidak ada bukti seluruh strategi sideways pasti gagal, hanya keluarga yang diuji ini.

17unit test lulus termasuk prioritas primary atas secondary yang lebih awal secara alfabet. Baseline primary direproduksi, setiap entry sekunder diperiksa hanya pada tanggal regime sideways yang diketahui sebelumnya, mode standalone diperiksa tidak mengandung primary, dan cash/slot/PnL/atribusi direkonsiliasi. AFL aktif tidak diubah dan kandidat tidak diadopsi. Spread/fraksi adalah stress sintetis modern pada sejarah, bukan observed bid/ask. Return tahunan ekuivalen sideways bukan CAGR strategi standalone; keduanya dipisah dalam laporan.
