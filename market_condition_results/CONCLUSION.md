# Kondisi pasar saat sistem kalah, dan mitigasi per kondisi (15 Oktober 2026)

Sistem: Breakout+ER buy stop di HHV20 sebelumnya (ER20 bar sebelumnya ≥0,3), fade2 sinyal Close → next Open, SMA30, tanpa gate pasar. Rp1 miliar, 10 slot, compounding. Fee 0,15/0,25%, spread 1 tick/sisi + lot 100. Kode: `analyze_market_conditions.py`, `mitigate_market_conditions.py`; mesin `backtest_stop_execution.py` (parameter baru default-nya = perilaku lama; regresi persis lulus).

Kondisi pasar dihitung dari proxy equal-weight 100 saham (bukan IHSG). Semua label memakai Close hari sebelumnya:
- trend: proxy di atas/bawah SMA200
- volatilitas: tertile 20 hari, batas diambil dari train 2000–2015 saja
- breadth: % saham di atas SMA50; luas ≥60%, sempit <40%
- drawdown proxy: dekat puncak > −10%, koreksi −10..−25%, bear dalam < −25%
- ER20 pasar

## 1. Di kondisi mana kita kalah (full 2000–2025, return harian dianualkan per kondisi)

| Kondisi | Porsi waktu | Kita fee | Kita spread | Swinger stop (kausal) | Swinger ideal |
|---|---:|---:|---:|---:|---:|
| Breadth luas | 36.9% | 81.0% | 54.4% | 85.4% | 164.3% |
| Breadth sedang | 30.9% | 43.5% | 17.7% | 27.5% | 124.5% |
| **Breadth sempit** | 32.3% | 3.9% | **−9.5%** | −11.1% | 62.4% |
| Bull (proxy > SMA200) | 74.6% | 47.2% | 25.8% | 39.0% | 117.1% |
| **Bear (proxy < SMA200)** | 25.4% | 23.7% | **2.7%** | 7.6% | 108.1% |
| **Bear + vol rendah** | 5.4% | −8.2% | **−19.8%** | 0.7% | 64.5% |
| Bear + vol tinggi | 8.6% | 16.8% | −0.7% | −1.4% | 125.1% |
| Koreksi −10..−25% | 20.9% | 32.5% | 10.0% | 4.1% | 78.9% |
| Bear dalam < −25% | 11.4% | 51.5% | 20.0% | 46.2% | 210.7% |
| ER pasar choppy | 55.3% | 25.8% | 4.9% | 13.9% | 87.2% |
| ER pasar lurus | 44.7% | 62.0% | 40.3% | 53.8% | 154.6% |

Observasi:
- Kita rugi atau hampir nol terutama saat **breadth sempit**, **bear**, dan khususnya **bear + volatilitas rendah** (pasar turun pelan dan sepi).
- Swinger kausal (stop order) juga rugi di breadth sempit. Jadi kelemahan ini bukan khas sistem kita. Swinger ideal positif di semua kondisi karena fill idealnya.
- **Bear dalam (proxy turun >25%) justru menguntungkan**, karena entry saat pemulihan.
- Per trade: rugi rata-rata kita 7–10% di semua kondisi vs Swinger ideal 3–4%. Selisih terbesar ada di bear + vol tinggi (10,0% vs 3,9%).

## 2. Mitigasi per kondisi (train 2000–2015 spread → freeze → evaluasi)

Kondisi: breadth sempit / bear / salah satunya. Tindakan: stop entry baru, ukuran entry 5% (setengah), jual semua di Open + stop entry, LLV10 stop intraday hanya di kondisi itu. 12 konfigurasi + base.

Pilihan beku: **breadth sempit ATAU bear → stop entry baru** (train spread 23,93%/59 vs base 20,89%/55).

| Window | Biaya | Base | Frozen |
|---|---|---|---|
| validation 2016–20 | spread | **23.7% / 20 / −22%** | 7.3% / 12 / −44% |
| test 2021–25 | spread | 11.6% / **10** / −30% | **16.0%** / 9 / **−25%** |
| full 2000–25 | spread | **19.5% / 80** / −43% | 19.3% / 71 / −44% |
| full 2000–25 | fees | **40.8% / 124** / −24% | 33.8% / 111 / −31% |

(CAGR / bulan rekor / MDD; semua konfigurasi di `comparison.csv`)

- **Frozen gagal di validation** (CAGR 23,7% → 7,3%) dan menurunkan bulan rekor di full.
- Tidak ada satu pun dari 12 tindakan yang lebih baik dari base di validation DAN test DAN full untuk CAGR dan bulan rekor sekaligus (dilihat pasca-freeze).
- **"Jual semua" selalu paling buruk.** Setengah ukuran dan stop-entry kadang memperbaiki MDD (misalnya trend_bear/half_size: full MDD −36% vs −43%), tetapi dengan mengorbankan CAGR atau bulan rekor.
- Interpretasi (belum dibuktikan kausal): pemulihan besar sering mulai saat breadth masih sempit / proxy masih di bawah SMA200. Contohnya 2016 di validation. Filter kondisi membuat kita melewatkan awal pemulihan. Rugi di kondisi buruk tampaknya adalah "biaya" untuk tetap ikut saat pemulihan.

## 3. Kesimpulan

Kita tahu di mana kita kalah: breadth sempit, bear, terutama bear + vol rendah. Tetapi **filter atau pengurangan eksposur berbasis kondisi pasar tidak terbukti memperbaiki CAGR dan bulan rekor di luar train.** Base buy stop tanpa tindakan kondisi tetap yang terbaik secara keseluruhan. Pilihan yang lebih masuk akal untuk diteliti: memperkecil rugi per trade (7–10% vs 3–4% Swinger) dengan aturan exit di level trade, bukan menghindari kondisi pasar.

Batasan: kondisi dipilih sesudah melihat atribusi full-history (bias pemilihan hipotesis). Data sudah pernah dilihat, 13 konfigurasi, proxy bukan IHSG. AFL tidak diubah.
