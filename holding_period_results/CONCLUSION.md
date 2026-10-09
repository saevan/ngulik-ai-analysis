# Kesimpulan uji holding

Sebanyak 24 simulasi: batas holding 10,20,30,50,75,100,150,200 bar pada fee-only, stress spread, dan fee-only dengan prioritas ticker dibalik. Batas holding bukan rata-rata holding aktual. Tidak ada modul sideways baru dalam pengujian ini.

Memperpendek holding meningkatkan transaksi, tetapi tidak secara konsisten meningkatkan CAGR atau bulan rekor. H50 fee-only memberi CAGR33.82% dibanding H20033.43%, namun bulan rekor turun97/308 dari127/308. H20 memberi CAGR29.41% dan102/308bulanrekor. Setelah stress spread, H20029.92% mengalahkan seluruh holding lebih pendek yang diuji; H50 menjadi22.08%, H20 menjadi8.41%.

Efeknya bergantung prioritas saham. Prioritas terbalik fee-only terbaik H30 CAGR30.95%, sedangkan H20027.73%; jadi H200 bukan optimum universal. Pencarian ini belum menemukan holding pendek yang mendominasi pada CAGR, frekuensi rekor, biaya, dan prioritas. Semua hasil masih jauh dari target ideal Swinger114.77%/80.84%bulanrekor/-18.81%MDD, yang tetap memiliki bias fill terdokumentasi.

Rata-rata keuntungan transaksi menang fee-only turun dari62.39% pada H200 ke26.99% pada H50 dan14.29% pada H20. Payout masing-masing3.16,2.06,1.72. Komposisi transaksi berbeda sehingga angka ini bukan estimasi matched-trade keuntungan yang pasti hilang. Exit lebih awal juga dapat mengurangi kerugian, sehingga dampak bersih harus dilihat pada seluruh portofolio.

Reinvestasi sudah terjadi otomatis pada sinyal entry berikutnya, dengan batas kas/10slot yang sama. Maka tabel sudah memasukkan pengganti keuntungan melalui transaksi baru dari logika awal. Belum ada bukti bahwa peluang tambahan dari logika kedua akan menutup kekurangan; hal tersebut memerlukan pengujian tersendiri. Jangan menambahkan CAGR dua strategi atau menganggap slot yang kosong pasti berisi transaksi menguntungkan.

Delapan unit test portofolio dan biaya lulus. Seluruh simulasi menjalankan pemeriksaan saldo, slot, dan rekonsiliasi PnL; H200 mereproduksi kurva baseline. AFL utama tidak diubah.
