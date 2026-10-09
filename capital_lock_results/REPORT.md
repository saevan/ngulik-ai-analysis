# Dana idle versus dana terikat saat sideways

Pemeriksaan saham2000-2025, modul Breakout+ER H200, fee beli0.15% jual0.25%, tanpa spread agar sama dengan benchmark. Semua ukuran adalah rata-rata snapshot penutupan pada3453hari berlabel pasar sideways. Rekonstruksi nilai posisi cocok dengan kurva equity tersimpan pada ketiga sistem.

| Ukuran | Kita | Swinger ideal | Swinger next Open |
|---|---:|---:|---:|
| Kas/equity | 6.23% | 6.50% | 6.29% |
| Equity dalam posisi sedang rugi net | 35.98% | 20.65% | 34.17% |
| Equity dalam posisi umur>=50bar | 68.78% | 6.07% | 9.97% |
| Equity dalam posisi umur>=100bar | 45.48% | 0.82% | 3.06% |
| Equity dalam posisi umur>=50bar dan masih rugi | 23.18% | 0.78% | 2.17% |
| Equity dalam posisi umur>=100bar dan masih rugi | 13.76% | 0.23% | 0.76% |
| Equity dalam posisi umur>=50bar, return net antara-5% dan+5% | 10.60% | 1.17% | 1.78% |
| Hari dengan10slot penuh | 87.98% | 76.80% | 75.30% |
| Umur posisi berbobot nilai, dirata-rata per hari | 96.86bar | 18.02bar | 23.30bar |

Kelompok umur/rugi/stagnan saling tumpang tindih, tidak boleh dijumlahkan. Bobot adalah nilai pasar posisi dibagi equity, bukan modal awal atau kerugian kumulatif. Posisi belum rugi/untung dinilai dari estimasi likuidasi Close dikurangi fee jual versus biaya entry termasuk fee beli. Umur50/100bar dan stagnan+/-5% adalah definisi diagnostik eksplisit, bukan aturan exit yang sudah terbukti.

Kas idle rata-rata hampir identik sehingga tidak mendukung kas idle sebagai penjelasan utama kesenjangan. Dana dan slot yang terikat lama jelas lebih besar pada sistem kita, termasuk posisi rugi atau belum banyak bergerak. Sepanjang seluruh backtest, baseline mencatat10697penolakan sinyal karena slot penuh, nol karena kas pada tahap setelah pengecekan slot; ini bukan angka khusus sideways, bukan10697transaksi unik, dan bukan bukti keuntungan yang pasti terlewat. Penolakan slot diperiksa sebelum kas, jadi nol penolakan kas bukan bukti semua sinyal bisa didanai.

Ini bukti hambatan perputaran, belum bukti penyebab utama selisih CAGR atau bahwa menjual posisi itu menguntungkan. Swinger nextOpen memiliki dana rugi total hampir sama tetapi durasi posisi jauh lebih singkat; return tahunan ekuivalen sidewaysnya4.81%, di bawah kita18.97%. Uji holding lebih pendek sebelumnya juga tidak otomatis memperbaiki hasil setelah biaya. Swinger ideal memiliki bias waktu/fill terdokumentasi.

Hipotesis lanjutan yang lebih spesifik: evaluasi penggantian posisi yang sudah lama dan belum produktif, bukan memotong semua pemenang atau memaksa seluruh kas selalu habis. Untuk menyatakan manfaat, perlu simulasi exit dan replacement bersama dengan sinyal yang sudah tersedia, biaya, batas slot, serta penilaian pada data yang tidak dipakai memilih parameter. Tidak ada perubahan aturan trading dalam diagnosis ini.
