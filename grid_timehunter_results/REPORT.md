> **Arsip definisi keliru:** fading dalam laporan ini memakai harga entry.
> Pengguna mengoreksi bahwa acuannya harus Open pada setiap bar baru.
> Angka fading berikut tidak mewakili strategi yang dimaksud. Hasil koreksi
> disimpan terpisah di `../grid_timehunter_bar_open_results/REPORT.md`.

# Grid TimeHunter: waktu, harga, dan fading

Tanggal analisis: 4 Oktober 2026.

**Hasil: ditemukan kandidat 5/5 numerik pada data pencarian dan validasi, tetapi dua kandidat yang dipilih tidak mempertahankan WR >50% pada 2020–2025. Belum ada sistem 7/7 yang tervalidasi dari pencarian ini.**

## Ruang pencarian dan pemilihan

- 1.800 kombinasi = 8 waktu pegang × 9 pengaturan fading × 25 aturan entry.
- Waktu pegang: 10, 20, 30, 50, 75, 100, 150, 200 bar.
- Fading: tidak ada, 2%, 3%, 5%, 7,5%, 10%, 15%, 20%, 30% dari entry.
- Entry: selalu masuk, tren SMA, pullback dari high bergulir, rebound, atau breakout. Semua sinyal entry memakai bar yang sudah selesai.
- Train sampai 2014: semua konfigurasi. Minimal 200 transaksi/observasi dan 20 ticker.
- Shortlist 20 diurutkan menurut jumlah kriteria numerik, margin WR/payout, mean setelah membuang 1% hasil terbaik, kemudian jumlah transaksi.
- Validation 2015–2019: pilih satu kandidat; minimal 100 observasi dan 20 ticker. Parameter disimpan sebelum melihat test 2020–2025.
- Shortlist utama tidak berisi fading. Sebuah shortlist tambahan berisi 20 konfigurasi fading terbaik dari train dibuat sebagai eksplorasi lanjutan. Kandidatnya juga dipilih hanya menggunakan validation. Cabang ini dibuat setelah hasil test utama terlihat.
- Data 2020–2025 sudah pernah dilihat pada eksperimen sebelumnya; ini bukan holdout yang benar-benar baru untuk keseluruhan riset.
- 172 konfigurasi lolos 5/5 pada train setelah biaya, termasuk 91 dengan fading. Shortlist utama: 4 dari 20 lolos pada validation. Shortlist fading: 3 dari 20.

## Biaya, data, dan eksekusi

- Saham: 464,768 bar / 100 ticker. 1994-07-12 00:00:00 sampai 2025-08-15 00:00:00.
- Satu bar TLKM bertimestamp intrahari dikeluarkan karena status close hariannya tidak jelas. 31 rentang OHLC diperluas agar mencakup Open/Close; sumber CSV tidak diubah.
- Tidak mengisi order pada bar saham bervolume nol; order menunggu open pertama dengan volume positif. Ini hanya pendekatan keterisian, bukan bukti likuiditas pada open.
- Time exit dijadwalkan pada close bar ke-H, termasuk bar entry. Jika tidak bisa diperdagangkan, exit dapat tertunda melampaui H.
- Fading: Low menyentuh ambang sebelum deadline -> order jual pada open berikutnya yang dapat diperdagangkan. Gap tidak dibatasi oleh ambang fading.
- Reentry paling cepat satu bar sesudah bar penjualan, jika sinyal entry terpenuhi. Tidak menambah posisi saat rugi. Satu posisi long per ticker.
- Asumsi biaya saham 0,2% saat beli dan 0,2% saat jual, dihitung (1+return_gross)*(1-0.002)/(1+0.002)-1. Ini skenario, bukan tarif broker terverifikasi.
- Forex memakai asumsi 0,005% per sisi; spread dinamis, swap, slippage belum dimodelkan.
- Tiap periode dimulai tanpa posisi dan diakhiri dengan likuidasi pada close terakhir. Jika bar terakhir tidak dapat diperdagangkan, posisi dinilai dengan close terakhir (period_end_mark); nilai ini bukan transaksi keluar yang terlaksana.
- Angka return menggabungkan transaksi dengan bobot setara. Bukan return tahunan, bukan kurva modal portofolio, dan observasi lintas saham tidak independen.

## Kandidat yang dibekukan

**Utama:** close sebelumnya di atas SMA100, minimal 2% di bawah high tertinggi 20 bar, dan close naik dibanding close sebelumnya. Beli open berikutnya. Exit 200 bar, tanpa fading.

**Fading:** close sebelumnya di atas SMA100, minimal 5% di bawah high tertinggi 20 bar, dan close naik dibanding close sebelumnya. Beli open berikutnya. Exit 100 bar atau fading turun 30%.

| Kandidat/periode | N | WR net | Payout net | Mean net | Median net | Numerik |
|---|---:|---:|---:|---:|---:|---:|
| Utama/train | 1014 | 59.96% | 2.68 | 31.85% | 9.12% | 5/5 |
| Utama/validation | 433 | 52.42% | 2.67 | 17.87% | 2.04% | 5/5 |
| Utama/test | 580 | 43.62% | 3.62 | 19.11% | -3.29% | 4/5 |
| Utama/all | 1956 | 53.58% | 2.95 | 26.13% | 3.71% | 5/5 |
| Fading/train | 1561 | 54.07% | 2.29 | 15.27% | 3.16% | 5/5 |
| Fading/validation | 594 | 50.84% | 2.24 | 9.91% | 0.31% | 5/5 |
| Fading/test | 834 | 45.68% | 2.55 | 9.93% | -1.84% | 4/5 |
| Fading/all | 2960 | 50.98% | 2.37 | 12.82% | 0.76% | 5/5 |

All menjalankan satu simulasi kontinu; jumlahnya tidak sama dengan penjumlahan tiga periode yang masing-masing memaksa penutupan di batasnya.

## Tujuh kriteria pada kandidat fading, periode test

| Kriteria | Bukti | Status |
|---|---|---|
| Mean > median | 9.93% > -1.84% | Lolos |
| Rata-rata menang > rata-rata rugi | 40.76% > 16.00% | Lolos |
| Payout >2 | 2.55 | Lolos |
| WR >50% | 45.68% | Gagal |
| Expectancy positif | 9.93% | Lolos |
| Lintas pasar | Parameter sama di forex menghasilkan 0 transaksi untuk fading; kandidat utama hanya 5 transaksi | Belum terbukti / sampel tidak cukup |
| Tanpa informasi masa depan | Pengujian kausalitas dan referensi simulator, gap, antrean volume nol, deadline, biaya | Lolos audit model; real fill tetap asumsi |

Indikator harga dapat dihitung pada pasar lain, tetapi itu tidak membuktikan edge atau parameter universal. Forex yang tersedia per jam, sedangkan saham harian; jumlah bar identik bukan durasi identik. Tidak ada retuning pada forex.

## Risiko yang masih terlihat

- Kandidat fading: transaksi test terburuk net -44.93%; penurunan intratrade terburuk gross -45.24%. Ambang 30% tidak membatasi kerugian menjadi 30%.
- Kandidat utama: transaksi test terburuk net -62.12%.
- Fading test: mean setelah menghapus 1% transaksi terbaik = 4.21%. Ini hanya diagnostik konsentrasi, bukan validasi independen.
- Skor tidak mengukur drawdown portofolio, durasi pemulihan modal, atau konsentrasi posisi.
- Corporate action dan gap ekstrem belum diverifikasi terhadap vendor. Daftar saham juga belum terbukti bebas survivorship bias.
- Ribuan percobaan meningkatkan risiko menemukan hasil kebetulan. Tidak mencari ulang parameter berdasarkan test sampai terlihat lolos.

## Sensitivitas posisi pada batas periode

Tabel utama mencakup posisi akhir periode. Berikut hanya exit time/fading yang terlaksana; penutupan atau penilaian karena batas data dikeluarkan. Ini diagnostik, bukan pengganti perhitungan portofolio.

| Kandidat/periode | Mark tanpa fill | N exit biasa | WR | Payout | Mean | Numerik |
|---|---:|---:|---:|---:|---:|---:|
| Utama/train | 0 | 950 | 60.21% | 2.73 | 33.91% | 5/5 |
| Utama/validation | 1 | 372 | 54.57% | 2.62 | 20.94% | 5/5 |
| Utama/test | 0 | 492 | 43.70% | 3.69 | 21.00% | 4/5 |
| Fading/train | 0 | 1519 | 53.98% | 2.31 | 15.64% | 5/5 |
| Fading/validation | 0 | 553 | 50.99% | 2.23 | 10.36% | 5/5 |
| Fading/test | 0 | 760 | 45.13% | 2.52 | 9.86% | 4/5 |

## Reproduksi

```powershell
python -m unittest -v test_grid_timehunter.py
python -u grid_search_timehunter.py
python -u analyze_timehunter_fading_grid.py
python write_timehunter_grid_report.py
```

Seluruh parameter, grid train, shortlist validation, konfigurasi yang dibekukan, hasil forex, dan ledger transaksi disimpan di folder ini.
