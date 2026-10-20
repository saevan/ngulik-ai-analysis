# Sifat pasar Kompas100 v2: yang nyata, yang bisa dipakai, yang sudah berubah (18 Okt 2026)

Kode dan data: `market_properties_v2/`. Rencana uji `PLAN.md` di-commit sebelum ada hasil (commit 1ef33c5). Hasil tiap uji ada
di `results/*_tests.csv`, klasifikasi akhir di `results/ALL_classified.csv` (`classify.py`).

**Setup**
- 100 saham Kompas100 saat ini, harga adjusted, 2000-01-01 sampai 2025-08-15. Cek tambahan 1994–99 (dulu hanya dipakai
  sebagai pemanasan indikator).
- Return diukur dari Open besok (atau dari level buy stop). Return abnormal = dikurangi rata-rata equal-weight semua saham
  pada jendela yang sama.
- Statistik: t Newey-West; koreksi Benjamini-Hochberg atas 62 uji utama.
- Subperiode: 2000–07, 2008–15, 2016–20, 2021–25. Universe pembanding: tanpa 20 saham yang listing 2018 atau sesudahnya.
- Biaya B = fee 0,15% beli / 0,25% jual + slippage 0,25% per sisi (round trip 0,90%).

**Kriteria lolos**, dikunci sebelum hasil:
1. |t| ≥ 3 dan q ≤ 5%.
2. Tanda sama di minimal 3 dari 4 subperiode.
3. Bertahan tanpa saham listing ≥2018.
4. Bisa dipakai setelah biaya.

**Verifikasi**
- Setiap keluarga uji dihitung ulang oleh pemeriksa independen dengan kodenya sendiri.
- Keluarga A–D: 34 dari 34 cocok, tidak ada yang terbantah.
- Satu kritikus menyerang semua interpretasi eksploratif.
- Status verifikasi W1–W4 ada di bagian akhir.

## Jawaban singkat

Dari 62 sifat yang diuji, 19 lolos kriteria 1–3. Hanya 3 yang bisa dipakai, dan ketiganya berupa aturan di dalam sistem,
bukan trade baru:
1. Entry buy stop intraday 0,5% di atas HHV20.
2. Filter ER pada breakout. Makin halus jalur harga 20 hari terakhir, makin baik; efeknya terkumpul di ER ≥ 0,5.
3. Saat harus exit dan Open gap down >2%, jual di Close, bukan di Open. Manfaatnya mengecil sejak call auction diperluas
   ke semua saham pada 9 Des 2024.

Sifat lain yang sering dipercaya:
- Sudah memudar: trend jangka pendek, efek Senin, pembalikan gap.
- Artefak daftar saham 2025: "premi" saham tidak likuid, momentum saham kecil.
- Tidak signifikan: kalender, konfirmasi volume, rezim pasar untuk breakout, exit breakout gagal, cut loss di hari ke-5.

## 1. Bisa dipakai (lolos 4 kriteria)

| Sifat | Ukuran (2000–25) | Subperiode 2000-07 / 08-15 / 16-20 / 21-25 | Tanpa listing ≥2018 | Cara pakai dan catatan |
|---|---|---|---|---|
| Buy stop intraday 0,5% di atas HHV20 → return 20 hari vs pasar | +1,16% (t 5,0) | +1,83 / +0,79 / +1,18 / +0,85 | +1,05% | Jenis entry, bukan trade tersendiri. Rata-rata per trade +0,85% < biaya B. +0,37% didapat di hari fill (dengan asumsi fill tepat di level), dan bagian ini menyusut ke +0,15% di 2021–25. Breakout konfirmasi Close + beli Open besok hanya +0,79% (rapuh). |
| ER20 ≥ 0,3 dikurangi < 0,3 di antara breakout | +1,49 pp per trade (t 3,8) | +0,84 / +0,52 / +2,39 / +2,67 | +1,21 pp | Filter. Per kelompok ER: <0,2: −0,17%; 0,2–0,3: −0,04%; 0,3–0,5: +0,48%; ≥0,5: +2,17% (t 4,2). Di backtest portofolio v2, ER 0,3 justru kalah dari ER 0,2 / tanpa ER di 2016–25. Efek per trade ≠ efek portofolio, karena trade lebih sedikit dan modal menganggur. |
| Exit dengan Open gap down: jual di Close, bukan di Open | Intraday hari itu +2,15% (hari exit SMA30); +1,4…+2,1% per exit menurut kritikus | Positif di semua subperiode | Sama | Aturan `gapdown_close` di sistem. Desember 2024 – Agustus 2025 hanya +0,3…+0,6% (t ≤ 2). Pantau terus. |

## 2. Nyata, tapi tidak bisa dipakai sendiri

- **Trend jangka pendek (TSMOM 5–60 hari, autokorelasi indeks).** TSMOM 20 hari +1,20% per 20 hari (t 6,1). Efeknya
  menurun bertahap: 2000–10 +2,0%, 2011–15 +0,7%, 2016–19 +0,4%, 2021–25 +0,09% (t 0,5). Memakainya sendiri butuh short.
  "Kelanjutan harian" (A1.1) bukan ukuran trend: perubahannya mengikuti pergeseran overnight/intraday (bagian 3).
- **Pembalikan gap di sesi yang sama.** Gap up >2%: −1,14% vs pasar dari Open ke Close. Gap down: +1,86%.
  - Kritikus menunjukkan ini sifat cetakan harga Open: besarnya beberapa tick, terkumpul di saham tidak likuid dan bertick
    besar, dan hampir hilang di saham non-LQ45 setelah call auction diperluas pada 9 Des 2024.
  - Membeli gap down di Open lalu menjual di Close tidak layak dengan biaya wajar.
  - Aturan "jangan beli gap up di Open" tidak didukung untuk entry breakout: entry breakout yang gap up justru lebih baik
    selama 20 hari.
  - Catatan: angka −1,8%/trade di `ABCD_exploratory.csv` (X-B4-e) memakai model biaya yang menghitung tick dua kali. Angka
    yang dipakai adalah dari kritikus.
- **Gap down → 5 hari berikutnya:** +0,56% vs pasar. Di bawah biaya.
- **Efek Senin:** −28 bps/hari, tiga perempatnya intraday. Sudah tidak signifikan sejak 2016–20 dan tidak terdeteksi di
  2021–25.
- **"Premi" saham tidak likuid** (Amihud +1,7%/bulan; nilai transaksi rendah −1,9%/bulan). Simulasi keanggotaan semu oleh
  kritikus menghasilkan spread sebesar itu hanya dari memakai daftar Kompas100 2025. Jangan dipakai.
- **Breakout Close HHV20 → 20 hari:** +0,79% (t 3,1). Rapuh: t 2,5 dengan definisi jendela ketat, dan breakout pertama dalam
  satu run ≈ 0%. Efeknya datang dari breakout ulang di dalam trend yang sudah berjalan.
- **Exit trailing LLV10 vs hold tetap 20 bar:** +1,22% per trade (rata-rata per trade). Tetapi posisi ditahan 31 vs 20 bar,
  dan per unit waktu modal tidak ada keuntungan bersih setelah biaya. Untuk saham lama di 2021–25 hasilnya terbalik (−1,27%,
  t −3,9).
- **Breadth pasar** (≥60% saham di atas SMA50 dikurangi <40%): +3,3% per 20 hari (t 4,0), negatif di 2021–25.
  - Aturan "kas saat breadth <40%" setelah biaya B: CAGR 21,2% vs 22,9% jika selalu masuk, Sharpe 1,30 vs 1,03, MDD −41%
    vs −62%.
  - Jadi aturan ini mengurangi risiko, bukan menambah return, dan melemah di 2016–25.
  - Breadth tumpang tindih dengan arah trend indeks (korelasi 0,83).
- **Volume spike pada hari naik:** +1,1% per 20 hari, tetapi seluruhnya dari saham tidak likuid (saham likuid +0,03%).
- **Volatilitas mengelompok** (deskriptif). Vol targeting yang dibangun di atasnya tidak memberi perbaikan setelah biaya.

## 3. Berubah rezim: overnight vs intraday

- 2000–2012: rata-rata saham rugi overnight dan untung intraday.
- Sejak 2016: untung overnight (+11…+27 bps/hari) dan rugi intraday (−5…−23 bps/hari).
- Berlaku di semua tingkat likuiditas, value-weighted, dan saham lama.
- Titik patahnya Feb–Mei 2013, saat pre-closing call auction mulai berlaku (2 Jan 2013). Sebelumnya Close cenderung di
  harga tertinggi hari itu. Sesudahnya banyak Close dekat harga terendah, lalu Open naik sedikit.

Ini sifat pembentukan harga, bukan premi overnight yang bisa ditradingkan sendiri (+20 bps/hari < fee).

Relevan untuk timing eksekusi (eksploratif, `x_execution_timing.py`):
- Malam setelah hari breakout, return rata-rata +24 bps (2016–20) dan +39 bps (2021–25). Membeli sinyal breakout Close di
  closing auction lebih murah daripada di Open besok.
- Malam setelah sinyal exit SMA30, return +29 bps. Jual di Open besok tetap lebih baik daripada di Close sinyal.

## 4. Tidak terbukti (41 dari 62)

- **Momentum sebagai ranking.**
  - mom120, dipakai di sistem: top–bottom +0,71%/bulan (t 1,5).
  - MOM12-1: +1,44%/bulan (t 2,75; t 3,07 dengan data-error mask simetris).
  - Kuintil momentum teratas (eksploratif): +0,86%/bulan, tetapi value-weighted hanya +0,14% dan pada saham yang sudah
    likuid +0,28%. Sebagai ranking breakout: saham likuid t 1,7; 2021–25 tanpa listing baru ≈ 0.
- **Konfirmasi volume pada breakout:** +0,86 pp (t 2,2).
- **Rezim pasar:** di atas atau di bawah SMA200 tidak mengubah return breakout relatif terhadap pasar (−0,45 pp, t −0,5).
- **Gap menembus level buy stop** (≥2%): tidak ada penalti (+0,15 pp, t 0,1). Aturan `gap_skip` tidak didukung.
- **Breakout gagal** (Close kembali di bawah level dalam 3 hari): sesudahnya tidak kalah dari pasar (+0,24%, t 1,3). Exit
  breakout gagal tidak didukung. Ini konsisten dengan v2: membuang aturan itu menaikkan CAGR di sebagian besar pasangan.
- **Cut loss cepat.** Trade yang rugi ≥5% di hari ke-5 setelahnya bergerak seperti trade datar. Selisih pemenang vs
  pecundang +2,8 pp (t 1,9). "Jijik rugi, sayang untung" tidak terbukti sebagai sifat statistik.
- **Drift setelah hari ke-20:** +1,8 bps/hari (t 2,0). Drift abnormal terkumpul di 20 hari pertama (5,5 bps/hari).
- **Kalender:** turn of month (+6,5 bps, t 1,2), Jumat, Desember, Januari, sebelum/sesudah Lebaran, sebelum libur.
- **Sifat silang lainnya:** volatilitas rendah, MAX, beta, kedekatan dengan high 52 minggu, ER60 bertanda.
- **Kejadian ekstrem:** Close di High/Low ±15%, run-up +50%, crash −33%. Juga vol timing, drawdown >25%, dan lead-lag saham
  besar → kecil (adanya di gap overnight, tidak terjangkau dari Open).
- **Hari fading** (Open − Low ≥ 2 ATR): sesudahnya tidak ada kelanjutan signifikan (5 hari −0,28%, t −1,6). Eksploratif.

## 5. Arti untuk aturan sistem utama (pilihan v2: HHV20 buy stop +0,5%, ER ≥ 0,2, mom120, gap 2%, fade/SMA30/failed exit, 25%)

| Aturan | Bukti v2 | Status |
|---|---|---|
| Buy stop di atas level | W1.5 +1,16% vs breakout Close +0,79% | Didukung |
| ER ≥ 0,2 | Arah didukung, tetapi kelompok 0,2–0,3 ≈ 0 dan efek terkumpul di ≥0,5 | Kandidat uji: ER 0,3/0,5, atau ER sebagai ranking |
| Ranking mom120 | Tidak signifikan; tidak robust di saham likuid | Kandidat uji: ranking ER vs mom120 |
| gap_skip 2% | Tidak ada penalti gap; entry breakout gap up lebih baik | Tidak didukung, kandidat dibuang |
| gapdown_close 2% | +1,4…+2,1% per exit historis, mengecil sejak Des 2024 | Didukung, pantau |
| Exit breakout gagal | Sesudah gagal tidak kalah dari pasar | Tidak didukung, kandidat dibuang |
| Exit fade 2 ATR | Tidak ada informasi signifikan sesudah hari fade | Netral |
| Exit SMA30 di Open besok | Malam sesudah sinyal exit +29 bps | Tetap di Open besok |
| Hold / exit trailing | Drift abnormal terkumpul di 20 hari pertama. 10% trade teratas = 93% laba 60 hari, tetapi entry acak lebih ekstrem (128%), jadi ini sifat umum return saham, bukan khas breakout. Trailing LLV10 tidak memberi keuntungan bersih per waktu modal | Tidak ada bukti untuk mengubah exit ke arah hold lebih lama |

## 6. Perubahan struktur pasar yang perlu diingat

- Persistensi trend jangka pendek menurun bertahap sejak 2011 dan ≈ 0 di 2021–25.
- Sejak pre-closing auction (2013), pola overnight/intraday berbalik.
- Sejak call auction diperluas (9 Des 2024), pembalikan gap di saham non-LQ45 hilang dan manfaat `gapdown_close` mengecil.
  Periode sesudahnya masih pendek (sekitar 8 bulan, termasuk trading halt Mar–Apr 2025).
- Efek Senin hilang bertahap sejak 2016.
- Implikasi: edge breakout per trade kini bergantung pada mekanik buy stop dan pemilihan ER tinggi, bukan pada trend pasar
  umum.

## 7. Batasan

- **Survivorship:** daftar Kompas100 2025. Cek tanpa listing ≥2018 tidak menghapus seleksi atas keberhasilan sesudahnya.
  Sifat yang menguntungkan saham tidak likuid, momentum saham kecil, atau episode suspensi/tidak likuid (bagian dari
  breakout HHV20–HHV250) terlalu optimistis.
- **Proxy pasar:** equal-weight dari saham survivor, bukan IHSG.
- **Data:**
  - Harga adjusted; artefak tick di harga rendah sebelum 2008.
  - Dua bar CTRA tunggal pada hari tidak normal (2008-01-11; Sabtu 2009-06-06; idx +20%).
  - Mask data-error 50% tidak simetris. Sensitivitas: tidak ada vonis yang berubah; D1 mendekati batas.
- **Kronologi auction:** tanggal pre-opening (LQ45 sejak 18 Mei 2009), pre-closing (2 Jan 2013) dan perluasan (9 Des 2024)
  berasal dari laporan pers yang dikumpulkan kritikus, belum dicek dengan aturan primer BEI. Keanggotaan LQ45 juga diproksikan
  (40 saham dengan nilai transaksi tertinggi), karena tidak ada di data.
- **Multiple testing:** 62 uji utama, puluhan uji eksploratif (tidak diklasifikasi), dan sekitar 40.000 backtest sebelumnya
  di data yang sama.
- **Eksekusi:** fill di level stop dan di Open/Close cetak tidak bisa diverifikasi dengan bar harian. Biaya wajar berbeda
  antara saham dengan auction (fee saja) dan tanpa auction (fee + sekitar 1 tick).
- **Tingkat event vs portofolio:** sifat per trade tidak otomatis menjadi CAGR. Contohnya ER, yang hasilnya berbeda di
  backtest portofolio.

## 8. Langkah berikut yang disarankan

1. Uji tuas portofolio yang dikunci lebih dulu pada pilihan v2, dengan skenario B dan periode sama:
   - buang `gap_skip`;
   - buang exit breakout gagal;
   - ER 0,3 / 0,5 vs 0,2;
   - ranking ER vs mom120;
   - untuk varian sinyal Close: beli di closing auction vs Open besok.
2. Universe point-in-time, termasuk saham yang delisting, untuk sifat yang sensitif survivorship.
3. Pantau data sesudah 2025-08-15, khususnya efek perluasan call auction.

AFL aktif tidak diubah.

## Status verifikasi

- A–D: 34 dari 34 cocok, tidak ada yang terbantah; 5 dikonfirmasi dengan catatan (B3, B4, D7, D9, D10).
- Kritikus A–D: klaim C-a, C-c, C-d, C-e, C-f, C-g didukung dengan catatan; C-b dibantah. Pernyataan di atas sudah memakai
  rumusan koreksinya.
- W2: 5 dari 5 cocok; W2.4 dan W2.5 dengan catatan (angka per trade yang dipakai adalah rata-rata per trade).
- W1: 10 dari 10 cocok persis; W1.1 dan W1.5 dengan catatan. W1.1 lolos t ≥ 3 hanya tipis (tanpa satu saham t 2,8).
  W1.5: +0,37% di hari fill berasal dari asumsi fill tepat di harga stop di luar fraksi; dengan fill di tick berikutnya
  W1.5 = +0,86% (t 3,7), kriteria 1–3 tetap lolos tetapi pas di biaya B. Jadi W1.5 mendukung pilihan jenis entry (buy stop),
  bukan trade tersendiri. W1.7 (ER) robust di semua variasi.
- W3, W4: belum diverifikasi silang (agen terhenti batas pemakaian); analis menjalankan self-check, W4 juga re-derivasi
  independen sendiri.
