# Grid TimeHunter: waktu, harga, dan fading

Laporan dibuat (Asia/Jakarta): 2026-10-05T14:46:05.867006+07:00. Basis hasil: **gross**.

**Pada test 2020–2025, kandidat utama memenuhi 4/5 kriteria numerik dan kandidat fading memenuhi 4/5. Status lintas pasar dan kausalitas dilaporkan terpisah; skor 7/7 tidak diberikan otomatis.**

## Definisi fading yang dikoreksi pengguna

`Low[t] <= Open[t] * (1 - ambang)`. Acuan direset pada setiap bar baru. Harga saat entry hanya dipakai untuk menghitung PnL, bukan menentukan pemicu fading.

Contoh entry 100, open bar baru 120, fading 5%: level pemicunya 114. Sinyal dapat muncul saat posisi masih untung. Sebaliknya, entry 100 lalu gap ke open 80 dengan low 79 belum memicu fading 5%, karena level bar tersebut 76.

Jam/usia posisi tetap dihitung sejak entry; pergantian open tidak memulai ulang usia posisi. Model jual next-open tetap dipakai. Koreksi ini tidak mengubahnya menjadi jual intrabar.

Hasil di `../grid_timehunter_results/` memakai acuan entry yang keliru untuk maksud pengguna. Hasil lama dipertahankan sebagai arsip, bukan sebagai hasil fading yang benar.

Hasil dengan biaya dari `../grid_timehunter_bar_open_results/` dipertahankan sebagai arsip. Pencarian ini mengulang seluruh grid dengan asumsi biaya pada laporan ini.

## Ruang pencarian dan pemilihan

- 1,800 kombinasi = 8 waktu pegang × 9 pengaturan fading × 25 aturan entry.
- Waktu pegang: 10, 20, 30, 50, 75, 100, 150, 200 bar.
- Fading: tidak ada, 2.00%, 3.00%, 5.00%, 7.50%, 10.00%, 15.00%, 20.00%, 30.00% dari Open masing-masing bar.
- Entry: selalu masuk, tren SMA, pullback dari high bergulir, rebound, atau breakout. Semua sinyal entry memakai bar yang sudah selesai.
- Train sampai 2014: semua konfigurasi. Minimal 200 transaksi/observasi dan 20 ticker.
- Shortlist 20 diurutkan menurut jumlah kriteria numerik, margin WR/payout, mean setelah membuang 1% hasil terbaik, kemudian jumlah transaksi.
- Validation 2015–2019: pilih satu kandidat; minimal 100 observasi dan 20 ticker. Parameter disimpan sebelum melihat test 2020–2025.
- Dua shortlist sudah ditentukan sebelum rerun koreksi: shortlist keseluruhan dan shortlist khusus fading. Keduanya memakai ranking train lalu memilih satu kandidat menggunakan validation; parameter tidak dipilih berdasarkan test.
- Data 2020–2025 sudah pernah dilihat pada eksperimen sebelumnya; ini bukan holdout yang benar-benar baru untuk keseluruhan riset.
- 261 konfigurasi lolos 5/5 pada train (gross), termasuk 189 dengan fading. Shortlist utama: 8 dari 20 lolos pada validation. Shortlist fading: 4 dari 20.

## Biaya, data, dan eksekusi

- Saham: 464,768 bar / 100 ticker. 1994-07-12 00:00:00 sampai 2025-08-15 00:00:00.
- Satu bar TLKM bertimestamp intrahari dikeluarkan karena status close hariannya tidak jelas. 31 rentang OHLC diperluas agar mencakup Open/Close; sumber CSV tidak diubah.
- Tidak mengisi order pada bar saham bervolume nol; order menunggu open pertama dengan volume positif. Ini hanya pendekatan keterisian, bukan bukti likuiditas pada open.
- Time exit dijadwalkan pada close bar ke-H, termasuk bar entry. Jika tidak bisa diperdagangkan, exit dapat tertunda melampaui H.
- Fading: Low menyentuh ambang dari Open bar itu sebelum deadline -> order jual pada open berikutnya yang dapat diperdagangkan. Gap tidak dibatasi oleh ambang fading.
- Reentry paling cepat satu bar sesudah bar penjualan, jika sinyal entry terpenuhi. Tidak menambah posisi saat rugi. Satu posisi long per ticker.
- Seluruh fee, pajak, spread, slippage, swap, dan biaya lain dinonaktifkan. Biaya beli dan jual saham maupun forex = 0. Semua kriteria serta ranking train/validation dihitung dari return gross.
- Tiap periode dimulai tanpa posisi dan diakhiri dengan likuidasi pada close terakhir. Jika bar terakhir tidak dapat diperdagangkan, posisi dinilai dengan close terakhir (period_end_mark); nilai ini bukan transaksi keluar yang terlaksana.
- Angka return menggabungkan transaksi dengan bobot setara. Bukan return tahunan, bukan kurva modal portofolio, dan observasi lintas saham tidak independen.

## Kandidat yang dibekukan

**Utama:** Jika close bar sinyal di atas SMA100, minimal 2% di bawah high tertinggi 20 bar, dan close naik dibandingkan close sebelumnya, beli pada open berikutnya yang dapat diperdagangkan. Time exit pada close bar ke-200. Tanpa fading.

**Fading:** Jika close bar sinyal di atas SMA100, minimal 2% di bawah high tertinggi 20 bar, dan close naik dibandingkan close sebelumnya, beli pada open berikutnya yang dapat diperdagangkan. Time exit pada close bar ke-200. Fading 30.00% dari Open bar yang sedang berjalan; Low menyentuh level pemicu -> jual pada open berikutnya yang dapat diperdagangkan.

| Kandidat/periode | N | WR gross | Payout gross | Mean gross | Median gross | Numerik |
|---|---:|---:|---:|---:|---:|---:|
| Utama/train | 1014 | 60.16% | 2.63 | 32.37% | 9.55% | 5/5 |
| Utama/validation | 433 | 52.89% | 2.67 | 18.34% | 2.44% | 5/5 |
| Utama/test | 580 | 43.97% | 3.59 | 19.59% | -2.90% | 4/5 |
| Utama/all | 1956 | 53.78% | 2.94 | 26.63% | 4.12% | 5/5 |
| Fading/train | 1029 | 59.57% | 2.60 | 31.80% | 9.26% | 5/5 |
| Fading/validation | 436 | 52.52% | 2.64 | 17.84% | 1.98% | 5/5 |
| Fading/test | 580 | 43.97% | 3.59 | 19.59% | -2.90% | 4/5 |
| Fading/all | 1974 | 53.44% | 2.92 | 26.26% | 3.92% | 5/5 |

All menjalankan satu simulasi kontinu; jumlahnya tidak sama dengan penjumlahan tiga periode yang masing-masing memaksa penutupan di batasnya.

### Seberapa sering fading benar-benar bekerja

| Periode | Proporsi exit fading | Rata-rata bar per posisi |
|---|---:|---:|
| train | 3.50% | 189.99 |
| validation | 0.92% | 181.12 |
| test | 0.00% | 181.39 |
| all | 2.03% | 192.71 |

**Tidak ada exit fading pada test untuk kandidat terpilih. Hasil test tersebut tidak membuktikan manfaat tambahan fading.**

## Tujuh kriteria pada kandidat fading, periode test

| Kriteria | Bukti | Status |
|---|---|---|
| Mean > median | 19.59% > -2.90% | Lolos |
| Rata-rata menang > rata-rata rugi | 68.22% > 18.98% | Lolos |
| Payout >2 | 3.59 | Lolos |
| WR >50% | 43.97% | Gagal |
| Expectancy positif | 19.59% | Lolos |
| Lintas pasar | Forex fading: 5 observasi / 4 ticker, 3/5 numerik. Utama: 5 observasi | Belum terbukti: sampel tidak cukup |
| Tanpa informasi masa depan | Pengujian kausalitas dan referensi simulator, gap, antrean volume nol, deadline, biaya | Lolos audit model; real fill tetap asumsi |

Indikator harga dapat dihitung pada pasar lain, tetapi itu tidak membuktikan edge atau parameter universal. Forex yang tersedia per jam, sedangkan saham harian; jumlah bar identik bukan durasi identik. Tidak ada retuning pada forex. Batas diagnostik kecukupan sampel transfer pada laporan ini: 100 observasi dan 3 ticker; bahkan melampaui batas ini tidak membuktikan universal.

## Risiko yang masih terlihat

- Kandidat fading: transaksi test terburuk gross -61.97%; penurunan intratrade terburuk gross -74.48%. Ambang fading mengukur penurunan dalam satu bar, bukan kerugian kumulatif posisi. Penurunan bertahap antarbar dan gap dapat menimbulkan kerugian jauh lebih besar.
- Kandidat utama: transaksi test terburuk gross -61.97%.
- Fading test: mean setelah menghapus 1% transaksi terbaik = 8.35%. Ini hanya diagnostik konsentrasi, bukan validasi independen.
- Skor tidak mengukur drawdown portofolio, durasi pemulihan modal, atau konsentrasi posisi.
- Corporate action dan gap ekstrem belum diverifikasi terhadap vendor. Daftar saham juga belum terbukti bebas survivorship bias.
- Ribuan percobaan meningkatkan risiko menemukan hasil kebetulan. Tidak mencari ulang parameter berdasarkan test sampai terlihat lolos.

## Sensitivitas posisi pada batas periode

Tabel utama mencakup posisi akhir periode. Berikut hanya exit time/fading yang terlaksana; penutupan atau penilaian karena batas data dikeluarkan. Ini diagnostik, bukan pengganti perhitungan portofolio.

| Kandidat/periode | Mark tanpa fill | N exit biasa | WR | Payout | Mean | Numerik |
|---|---:|---:|---:|---:|---:|---:|
| Utama/train | 0 | 950 | 60.32% | 2.69 | 34.45% | 5/5 |
| Utama/validation | 1 | 372 | 55.11% | 2.60 | 21.43% | 5/5 |
| Utama/test | 0 | 492 | 44.11% | 3.67 | 21.49% | 4/5 |
| Fading/train | 0 | 965 | 59.69% | 2.66 | 33.81% | 5/5 |
| Fading/validation | 1 | 375 | 54.67% | 2.58 | 20.83% | 5/5 |
| Fading/test | 0 | 492 | 44.11% | 3.67 | 21.49% | 4/5 |

## Reproduksi

```powershell
python -m unittest -v test_grid_timehunter.py
python -u grid_search_timehunter.py
python -u analyze_timehunter_fading_grid.py
python write_timehunter_grid_report.py
```

Seluruh parameter, grid train, shortlist validation, konfigurasi yang dibekukan, hasil forex, dan ledger transaksi disimpan di folder ini.
