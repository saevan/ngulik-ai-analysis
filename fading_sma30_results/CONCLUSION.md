# Kesimpulan

20 simulasi selesai. Fading lebih kecil memperpendek holding pada kedua entry, tetapi tidak otomatis meningkatkan CAGR. Semua memakai SMA30 exit dan tanpa hold200.

Breakout+ER fee-only: fade5 holding25.33bar,1989transaksi,CAGR35.24%,89/308rekor,MDD-39.47%; fade2 holding20.39bar,2392transaksi,CAGR33.65%,108/308rekor,MDD-34.90%. Jadi fade2 mendekati durasi Swinger ideal19.04bar, memperbaiki frekuensi rekor dan drawdown, dengan CAGR lebih rendah. Return tahunan ekuivalen sideways18.58% menjadi20.10%. Spread stress CAGR17.87% menjadi13.37%. Tidak menyamai target ideal114.77% atau jumlah3241transaksi.

Pullback AFL aktif sudah lebih cepat daripada Swinger: fade5 holding14.05bar,4451transaksi; fade2 menjadi12.75bar,4931transaksi. CAGR fee-only20.30% menjadi17.70%, spread-10.07% menjadi-15.34%. Menurunkan fading pada AFL ini justru menjauhkan durasi dan jumlah transaksi dari benchmark. Default AFL tidak diubah; fade2 hanya kandidat eksperimen Breakout+ER, bukan rekomendasi mengganti pullback.

Fade1/0.5 memangkas holding lebih jauh, tetapi hasil spread sangat buruk. Pada sebagian skenario ekuitas terkikis sehingga pembulatan100saham dan keterbatasan kas akhirnya mengurangi jumlah entry; hubungan ambang dengan totaltrade tidak harus monoton. 16unit test mesin lulus. Satu skenario hampir kehabisan equity menyingkap sensitivitas pembatalan numerik pada rekonsiliasi PnL; penjumlahan diganti math.fsum dengan toleransi absolut1e-12modalawal (Rp0.001), tanpa mengubah aturan atau transaksi. Seluruh20simulasi lolos pemeriksaan.

In-sample dan stress biaya sintetis, belum validasi out-of-sample. Target Swinger ideal mengandung bias fill terdokumentasi. Jangan menyamakan kemiripan durasi dengan keunggulan return.
