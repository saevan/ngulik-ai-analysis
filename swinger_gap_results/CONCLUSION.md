# Sistem kita vs Prototype Swinger: di mana kalah, dan mitigasi kausal (15 Oktober 2026)

Kode: `backtest_stop_execution.py` (mesin stop order intraday; mode dasar mereproduksi persis kurva Breakout+ER fade2/SMA30 lama untuk fee dan spread) dan `mitigate_swinger_gap.py` (grid 32 konfigurasi, train → freeze → evaluasi). Rencana: `PLAN.json`, pilihan: `FROZEN.json`, angka: `comparison.csv`, `diagnostic_post_freeze.csv`, `yearly_buystop.csv`, `swinger_fill_decomposition.csv`.

Setup: Rp1 miliar, 10 slot bersama, 10% equity Close sebelumnya, compounding, long only. Fee beli 0,15% jual 0,25%. Spread stress 1 tick per sisi + lot 100. Swinger hanya punya skenario fee (fill ideal tanpa spread).

## 1. Di mana kita kalah (full 2000–2025, fee saja)

| Sistem | Trade | WR | Avg win | Avg loss | Loss >10% | Hold | CAGR | Rekor/308 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Kita: Breakout+ER fade2 (next Open) | 2392 | 40.84% | 19.73% | 7.00% | 12.79% | 20.4 | 33.65% | 108 |
| Swinger fill ideal AFL | 3241 | 51.90% | 16.51% | 3.19% | 1.54% | 19.0 | 114.77% | 249 |
| Swinger stop order kausal | 7266 | 29.19% | 11.36% | 2.99% | 2.67% | 8.0 | 30.25% | 102 |
| Swinger next Open kausal | 3086 | 34.38% | 17.58% | 5.93% | – | 19.9 | 21.51% | 83 |

- **Kita kalah di sisi rugi:** avg loss 7,0% vs 3,2%, dan 12,8% trade rugi >10% vs 1,5%. Avg win kita justru lebih besar.
- **Sumber keunggulan Swinger ideal adalah fill-nya.** Trade yang sama dihitung ulang dengan fill next Open: rata-rata return per trade turun dari 7,46% ke 2,25% dan WR dari 52,7% ke 33,9%. Fill ideal rata-rata 2,6 pp lebih baik di entry dan 2,5 pp di exit. 12,8% harga entry ideal di bawah Low hari itu dan 16,9% harga exit ideal di atas High hari itu (tidak mungkin dieksekusi).
- Versi Swinger yang bisa dieksekusi (stop order 30,25%, next Open 21,51%) sudah di bawah sistem kita (33,65%).

## 2. Mitigasi yang diuji (train 2000–2015, spread)

Grid 2 gate pasar (none / ER pasar ≥0,3) × 2 entry (next Open / buy stop intraday di HHV20) × 2 fading (sinyal Close→next Open / stop intraday di Open−2ATR) × LLV trailing stop (none/5/10/20).

- **Menyalin exit Swinger (LLV5 stop) memang memperkecil avg loss (8,45%→6,72%), tetapi WR turun dan CAGR jatuh 14,10%→0,12%.** Rugi yang lebih kecil tidak menutup profit yang ikut terpotong.
- **Fading intraday lebih buruk** dari fading yang dieksekusi di next Open, di semua kombinasi.
- **Buy stop di level HHV20 (analog kausal dari entry level Swinger) konsisten lebih baik**, di 16/16 pasangan perbandingan train. Contoh tanpa gate: 14,10%/41 rekor → 20,89%/55 rekor.
- Pilihan yang dibekukan sesuai aturan: gate ER pasar + buy stop + LLV20 (train 22,25%/58).

## 3. Evaluasi

| Window | Biaya | Base (next Open) | Frozen (gate ER+buy stop+LLV20) | Buy stop tanpa gate (diagnostik pasca-freeze) |
|---|---|---|---|---|
| validation 2016–20 | fees | 30.88% / 22 / MDD −25.5% | 34.80% / 31 / −22.9% | **41.83% / 31 / −18.7%** |
| validation 2016–20 | spread | 15.51% / 13 / −31.9% | **24.35% / 23** / −28.1% | 23.73% / 20 / **−22.5%** |
| test 2021–25 | fees | 19.79% / 12 / −27.5% | 12.22% / 10 / −19.5% | **25.16% / 17** / −21.7% |
| test 2021–25 | spread | 7.63% / 8 / −42.3% | 5.76% / 3 / −29.2% | **11.61% / 10** / −30.3% |
| full 2000–25 | fees | 33.65% / 108 / −34.9% | 32.33% / 108 / −26.7% | **40.84% / 124 / −23.9%** |
| full 2000–25 | spread | 13.37% / 52 / −52.6% | **20.07%** / 79 / −38.9% | 19.50% / **80** / −43.0% |

(format: CAGR / bulan rekor / MDD)

- Frozen menang di validation tapi kalah di test, sama seperti optimasi sebelumnya. Penyebabnya **gate pasar ER**: gate ini konsisten membantu di train tetapi merugikan di 2021–2025.
- **Buy stop tanpa gate lebih baik dari base di semua window dan kedua biaya**, untuk CAGR, bulan rekor, dan MDD. Per tahun (fee), dia lebih baik di 19 dari 26 tahun. WR naik 40,8%→44,3%, avg loss hampir sama (6,9%).
- Peringatan: konfigurasi itu ada di grid (train 20,89%/55), tetapi **tidak terpilih oleh aturan**. Angka validation/test di atas dilihat sesudah freeze, jadi statusnya kandidat kuat yang perlu dikonfirmasi, bukan hasil out-of-sample bersih.

## 4. Asumsi dan batasan buy stop

Level HHV20 dan ER20 dihitung dari bar sebelumnya; order hanya dipasang bila Close sebelumnya ≤ level. Fill = max(Open, level) ketika High > level, ditambah 1 tick di skenario spread. Tidak ada fill di luar range OHLC (cek di kolom outside). Belum dimodelkan: slippage stop order saat breakout cepat, auto-reject atas BEI, antrean order, likuiditas, kemungkinan sinyal palsu intraday yang ditutup di bawah level (ini sudah ikut dalam hasil, karena entry tidak menunggu Close). Prioritas alfabet saat slot penuh. Uang dan slot dari stop intraday tidak dipakai ulang di hari yang sama. Data sudah pernah dilihat; 32+ konfigurasi = risiko multiple testing. AFL aktif tidak diubah.
