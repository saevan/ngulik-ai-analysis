# Entry untuk menaikkan WR setelah stop diperketat

22 simulasi selesai: 10 konfigurasi training 2000–2015, lalu baseline dan satu kandidat yang dibekukan diuji pada 2016–2020, 2021–2025, serta seluruh periode, masing-masing dengan fee dan fee+spread. Ini riset adaptif dengan data yang sebelumnya sudah pernah diperiksa, bukan holdout independen.

Basis eksperimen adalah SISTEM KEDUA Choppy Range Escape10/cost8/marketER20<0,30 ditambah stop 0,5 ATR dari entry. Stop tersebut dipilih karena rata-rata rugi 4,04% paling dekat dengan target Swinger, bukan karena terbaik CAGR. Stop memakai ATR yang diketahui sebelum entry, sinyal Close dan fill next tradable Open; tidak menjamin batas rugi intraday. Exit LLV10 dan fading2 dari Open bar berjalan tetap. Tidak ada H200. Sistem utama dan AFL aktif tidak berubah.

## Tuas yang terukur

Training fee-only: baseline WR24,13%. SMA30/100 menghasilkan24,02%/23,39%; ER saham minimum0,3/0,5 menghasilkan25,13%/27,68%; Close location minimum0,75/0,90 menghasilkan24,63%/23,92%; jarak breakout maksimum0,5/1ATR menghasilkan23,59%/23,81%; range/cost minimum16 menghasilkan19,20%. Ini perubahan satu tuas per konfigurasi, bukan bukti hubungan monoton universal. Konfigurasi yang dipilih adalah ER saham>=0,5 karena WR tertinggi yang memenuhi batas training dalam PLAN.json; dipilih sebelum validasi dijalankan.

ER PASAR tetap<0,30 (choppy), ER SAHAM pilihan>=0,50. Ini memilih saham dengan perubahan harga lebih terarah di tengah pasar agregat yang choppy, bukan mengubah pasar menjadi trending. Breakout sudah memberi syarat arah naik; ER sendiri mengukur efisiensi pergerakan tanpa tanda arah.

## Hasil seluruh periode 4 Januari 2000–15 Agustus 2025

Modal Rp1 miliar,10 slot, alokasi10% equity penutupan sebelumnya dibatasi kas, compounding. Fee0,15% beli/0,25% jual.

| Metrik | Stop0,5ATR tanpa filter baru | Tambah ER saham>=0,5 |
|---|---:|---:|
| Trade | 3385 | 965 |
| WR | 21,45% | 24,87% |
| Rata-rata rugi | 4,04% | 4,39% |
| Rata-rata untung | 18,13% | 21,36% |
| PF berdasarkan PnL rupiah | 1,08 | 1,47 |
| CAGR | 6,84% | 6,97% |
| Bulan rekor equity | 45/308 (14,61%) | 48/308 (15,58%) |
| Return tahunan ekuivalen sideways | -2,79% | 9,60% |

Dengan fraksi modern BEI, pembulatan100 saham,1tick per sisi: CAGR-8,02% menjadi1,77%, WR17,86% menjadi20,72%, rata-rata rugi4,54% menjadi5,01%, sideways equivalent-26,62% menjadi-0,13%. Ini asumsi stres seluruh sejarah, bukan rekonstruksi bid/offer historis.

WR fee-only juga naik dalam validasi20,80%->22,32% dan test17,63%->22,98%. Namun rata-rata rugi test naik3,94%->4,61%, melampaui toleransi relatif10% yang digunakan pada training. Kandidat test dengan spread CAGR0,33% dan sideways equivalent-0,28%; keunggulan setelah biaya masih tipis dan tidak positif pada hari sideways.

Swinger ideal sebagai target karakter, transaksi yang entry saat market choppy: WR50,46%, rata-rata rugi3,21%, rata-rata untung14,67%,1833trade. Target masih jauh: kandidat hanya24,87%WR,loss4,39%,965trade. Metrik ini berdasarkan entry regime; return sideways memakai atribusi tanggal equity, jangan dicampur dengan CAGR portofolio hanya trade-choppy.

Kesimpulan: ditemukan tuas yang menaikkan WR pada basis stop ketat, tetapi belum mendekati karakter Swinger atau membuktikan profit sideways setelah spread. Dibanding sistem kedua ASLI tanpa stop tambahan (feeCAGR10,20%,spread1,98%,WR36,92%), kandidat belum lebih baik pada CAGR/WR. Hasil tidak membuktikan WR bisa dinaikkan tanpa mengubah besar loss/frekuensi. Tidak diadopsi/digabung. Pemeriksaan kausalitas prefix seluruh input entry, eligibility choppy, baseline equity regression, serta13unit test terkait lolos. Engine melakukan pemeriksaan akuntansi dan atribusi.

Reproduksi: search_choppy_wr_after_stop.py. PLAN.json/FROZEN.json berisi aturan pemilihan; REPORT.md/comparison.csv memuat seluruh hasil dan ledger tiap simulasi tersimpan. Bulan rekor berarti ada penutupan harian equity melebihi seluruh riwayat/initial capital pada window tersebut; sideways equivalent adalah annualisasi atribusi return pada tanggal sideways yang terpisah, bukan CAGR strategi mandiri.
