# Kesimpulan pengujian dua sistem

26 simulasi selesai. Sistem kedua memiliki entry dan exit mandiri, bukan tambahan exit pada sistem tren. Modul diuji bersama dalam satu akun dengan modal Rp1 miliar dan maksimal10posisi. Delapan kombinasi reserved-slot diuji pada fee-only dan stress spread; konfigurasi dengan CAGR spread tertinggi dipakai untuk sensitivitas shared-slot, standalone, dan prioritas terbalik. Semua hasil adalah in-sample.

Kandidat reserved-slot terpilih: ER20<0.30, Close<=SMA20-1.5ATR sebelumnya; exit kembali keSMA20, stop2ATR dari entry, atau umur15bar, lalu next tradable Open. Pembagian7slot tren/3slot range. Fee-only CAGR18.35% vsbaseline33.43%, bulanrekor85/308 vs127/308, transaksi2212 vs340. Stress spread CAGR0.29% vs29.92%, bulanrekor10/308 vs117/308, MDD-91.50% vs-59.70%, transaksi2358 vs340.

Pada hari pasar sideways yang sama, return tahunan ekuivalen fee-only turun18.97% ke4.10%; dengan stress spread turun15.25% ke-10.83%. Ini atribusi gabungan hari yang terpisah, bukan CAGR strategi sideways mandiri. Jadi penambahan transaksi tidak menutup kekurangan hasil sideways dalam pengujian ini.

Shared-slot mengurangi pengorbanan kapasitas tren, tetapi tetap tertinggal: fee-only CAGR21.84%,84/308bulanrekor,775transaksi; spread15.52%,65/308,853transaksi. Range-only terpilih menghasilkan CAGR-7.66% fee-only dan-30.87% spread. Prioritas terbalik juga tidak menyelamatkan kandidat reserved: spread-0.54% vsbaseline24.16%. Ini tidak membuktikan semua strategi sideways gagal, hanya keluarga entry/exit dan parameter yang diuji.

Pada konfigurasi gabungan fee-only terpilih, range menyumbang1971transaksi,1060entry pada hari pasar sideways, WR51.34%, mean return transaksi-0.14%. Pada spread mean return-2.35%. PnL rupiah gabungan dipengaruhi ukuran posisi dan waktu compounding, sehingga jangan disamakan dengan rata-rata return transaksi atau hasil standalone.

Kesimpulan: arsitektur dua sistem berhasil diimplementasikan, tetapi kandidat mean-reversion ini belum memenuhi tujuan performa dan tidak diadopsi ke AFL utama. Target ideal Swinger114.77% CAGR tetap aspiratif dengan bias fill terdokumentasi. Tidak ada klaim7kriteria atau validasi lintas pasar.12unit test lulus dan kurva baseline tepat direproduksi.
