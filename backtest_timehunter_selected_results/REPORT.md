# Backtest ulang kandidat TimeHunter

Waktu run (Asia/Jakarta): 2026-10-05T08:40:08.326628+07:00.

Ini pengulangan kandidat yang sudah dipilih. Tidak ada grid search atau pemilihan parameter berdasarkan hasil run ini. Data periode uji pernah dilihat sebelumnya, jadi bukan validasi independen baru.

## Aturan dan data

- Kandidat: `{"hold": 200, "dip": 0.3, "entry_name": "trend_100_rebound_2"}`.
- Entry kandidat: close bar sebelumnya di atas SMA100, minimal 2% di bawah high tertinggi 20 bar, dan close naik dari close sebelumnya. Beli next-open.
- Exit kandidat: close bar ke-200, atau Low turun 30.00% dari **Open bar yang sedang berjalan** lalu jual next-open.
- Acuan fading direset setiap bar. Bukan harga entry, bukan high sebelumnya. Harga entry tetap menjadi dasar PnL.
- Pembanding tanpa fading memakai entry dan hold yang sama; baseline TimeHunter memakai entry tanpa filter dan close bar ke-50.
- Satu posisi long per ticker. Reentry paling cepat bar setelah penjualan dan mengikuti filter entry. Usia posisi direset hanya saat entry baru.
- Data: 464,768 bar dari 100 ticker, 1994-07-12 00:00:00 sampai 2025-08-15 00:00:00.
- Biaya ilustratif 0.20% beli + 0.20% jual. Spread, slippage, likuiditas order, dan pajak terpisah belum dimodelkan.
- 31 rentang OHLC dinormalkan; satu bar bertimestamp intrahari dikeluarkan. Bar volume nol tidak dianggap bisa mengisi order; order menunggu open bar berikutnya dengan volume positif.
- Setiap periode dimulai tanpa posisi. Posisi akhir periode ditutup/ditandai pada close terakhir. `period_end_mark` adalah penilaian tanpa fill yang terlaksana.

## Hasil sebelum dan sesudah biaya

| Periode / strategi | N | WR gross | WR net | Mean gross | Mean net | Median net | Payout net |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1994-2025 / Kandidat + fading | 1974 | 53.44% | 53.24% | 26.26% | 25.75% | 3.50% | 2.93 |
| 1994-2025 / Kandidat tanpa fading | 1956 | 53.78% | 53.58% | 26.63% | 26.13% | 3.71% | 2.95 |
| 1994-2025 / TimeHunter 50 | 9242 | 50.55% | 50.27% | 5.55% | 5.13% | 0.10% | 1.74 |
| 2020-2025 / Kandidat + fading | 580 | 43.97% | 43.62% | 19.59% | 19.11% | -3.29% | 3.62 |
| 2020-2025 / Kandidat tanpa fading | 580 | 43.97% | 43.62% | 19.59% | 19.11% | -3.29% | 3.62 |
| 2020-2025 / TimeHunter 50 | 2599 | 45.63% | 45.29% | 3.89% | 3.48% | -1.47% | 1.86 |

**Mean adalah rata-rata persentase per transaksi/observasi, bukan return tahunan atau return portofolio.** Durasi pegang dan jumlah transaksi berbeda; mean lebih besar tidak otomatis berarti sistem lebih baik.

## Rincian risiko dan eksekusi

| Periode / strategi | Avg win net | Avg loss net | Terburuk net | Terburuk intratrade gross | Avg bar | Exit fading | Mark tanpa fill | Numerik |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1994-2025 / Kandidat + fading | 69.03% | -23.53% | -90.31% | -91.67% | 192.71 | 40 | 0 | 5/5 |
| 1994-2025 / Kandidat tanpa fading | 69.02% | -23.37% | -90.60% | -92.45% | 195.06 | 0 | 0 | 5/5 |
| 1994-2025 / TimeHunter 50 | 23.56% | -13.51% | -84.51% | -87.50% | 50.02 | 0 | 0 | 4/5 |
| 2020-2025 / Kandidat + fading | 68.09% | -18.78% | -62.12% | -74.48% | 181.39 | 0 | 0 | 4/5 |
| 2020-2025 / Kandidat tanpa fading | 68.09% | -18.78% | -62.12% | -74.48% | 181.39 | 0 | 0 | 4/5 |
| 2020-2025 / TimeHunter 50 | 21.98% | -11.84% | -51.99% | -62.10% | 48.39 | 0 | 0 | 3/5 |

Penurunan intratrade dihitung dari entry ke harga terendah selama posisi masih terbuka; angka ini **bukan maximum drawdown portofolio**.

Pada kandidat fading periode 2020-2025 terdapat 0 exit fading. Kesamaan ledger dengan kandidat tanpa fading: True.

## Lima kriteria numerik pada kandidat periode 2020-2025

| Kriteria | Hasil |
|---|---|
| Mean > median | Lolos |
| Avg win > avg loss | Lolos |
| Payout > 2 | Lolos |
| WR > 50% | Gagal |
| Expectancy > 0 | Lolos |

Kausalitas dan transfer lintas pasar tidak diberi poin otomatis. Run ini hanya memakai saham; pengujian forex sebelumnya terlalu sedikit untuk membuktikan lintas pasar. Corporate action, saham delisting, dan survivorship bias belum diverifikasi. Statistik tidak menentukan alokasi modal maupun pertumbuhan suatu portofolio.

## Reproduksi

```powershell
python -u backtest_timehunter_selected.py
```

Ringkasan mesin tersimpan di `summary.json` dan seluruh transaksi ada dalam CSV untuk masing-masing strategi/periode.
