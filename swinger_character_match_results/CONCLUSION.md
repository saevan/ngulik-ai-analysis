# Menyamakan karakter kandidat dengan Swinger (15 Oktober 2026)

Kandidat: buy stop HHV20 (ER20 bar sebelumnya ≥0,3) + lewati gap up >2% + jual di Close saat gap down >2% + urutan mom120, fade2 dari Open bar berjalan, SMA30. Rp1 miliar, 10 slot, compounding. Swinger hanya punya skenario fee (beli 0,15% jual 0,25%). Kode: `match_swinger_character.py`; mesin `backtest_stop_execution.py` (parameter baru default = perilaku lama; regresi persis lulus).

## 1. Selisih karakter (full 2000–2025, fee)

| | Kandidat | Swinger ideal | Swinger stop order |
|---|---:|---:|---:|
| Trade | 2281 | 3241 | 7266 |
| Rugi rata-rata | −6.48% | −3.19% | −2.99% |
| Rugi berjalan maksimum (MAE) trade rugi | −9.50% | −6.26% | −4.85% |
| % trade rugi yang lebih buruk dari −10% | 19.6% | 3.2% | 3.8% |
| % trade rugi yang sempat untung >5% | 40.5% | 35.1% | 18.1% |
| Profit yang dilepas kembali pada trade menang (MFE − hasil) | 14.6 pp | 11.4 pp | 10.1 pp |
| Hold trade rugi (median) | 13 bar | 8 bar | 2 bar |
| Rata-rata posisi terbuka / modal terpakai | 7.4 / 74.6% | 9.4 / 93.0% | 8.2 / 81.8% |

Rugi kandidat lebih dalam dan lebih lama, profit yang dilepas lebih besar, dan modal lebih banyak menganggur.

## 2. Tuas peniru Swinger (18 konfigurasi)

- stop awal intraday: tidak ada / LLV5 sebelum entry (level `sup` Swinger) / entry − 2 ATR
- trailing stop LLV5 (TSL Swinger) aktif sesudah Close ≥ entry + k ATR: tidak ada / k=2 / k=4
- channel buy stop: HHV20 / HHV10 (lebih banyak entry, lebih mirip HHV5 Swinger)

Aturan beku (train spread 1 tick): tidak ada konfigurasi yang lolos. Kandidat tetap.

## 3. Hasil: tergantung biaya

Rata-rata efek tiap tuas (pasangan yang hanya beda satu tuas):

| Tuas | Fee saja (asumsi Swinger) | Spread 1 tick | Spread 2 tick |
|---|---|---|---|
| Channel 20 → 10 | CAGR +5.3/+10.4/+1.0 pp (train/val/test), rekor +12/+1.6/+0.1 | −6.4/−0.5/−4.9 pp | −12.2/−5.5/−7.7 pp |
| Trailing LLV5 sesudah +2 ATR | +1.8/+1.4/+3.4 pp, rekor +6.8/+1.8/+1.8 | −4.4/−5.2/−1.6 pp | −7.4/−7.2/−4.4 pp |
| Trailing sesudah +4 ATR | campur | negatif | negatif |
| Stop awal LLV5 | −3.2/−1.1/−1.4 pp | negatif | negatif |
| Stop awal 2 ATR | −3.8/−1.3/−5.7 pp | −12/−7.6/−16 pp | −17/−11/−18 pp |

Kombinasi terbaik di skenario fee: **channel 10 + trailing sesudah +2 ATR**.

| Window | Fee: kandidat | Fee: ch10+trail2 | Spread 1: kandidat | Spread 1: ch10+trail2 |
|---|---|---|---|---|
| train | 51.0% / 84 / −25% | 58.1% / 103 / −21% | 27.6% / 63 | 17.0% / 55 |
| validation | 54.0% / 29 / −23% | 60.6% / 29 / −21% | 37.2% / 25 | 29.5% / 19 |
| test | 38.9% / 25 / −16% | 42.7% / 26 / −21% | 24.1% / 18 | 17.0% / 10 |
| full | 48.5% / 136 / −25% | **56.6% / 157 / −21%** | **28.1% / 100** | 20.2% / 78 |

Karakter ch10+trail2 (full, fee): 3910 trade, WR 48.9%, avg win 12.3%, avg loss 5.2%, rugi >10% 15.2%, hold 12.4 bar.

## 4. Kesimpulan

- **Observasi:** dengan biaya fee saja (asumsi yang sama dengan benchmark Swinger), meniru Swinger lewat channel lebih pendek dan trailing setelah profit menaikkan CAGR dan bulan rekor di train, validation, dan test.
- **Tetapi** efek itu berbalik negatif begitu ditambah spread 1–2 tick per sisi, karena trade bertambah 70% dan setiap trade membayar spread.
- **Stop awal (pemotong rugi) tidak membantu** di skenario mana pun: rugi rata-rata hampir tidak turun (6,5% → 6,0–6,3%) karena stop sering kena gap, sementara profit ikut terpotong.
- Interpretasi (belum terbukti): keunggulan Swinger ideal butuh dua hal yang tidak kita punya, yaitu fill di level tanpa gap dan biaya mendekati nol. Kalau biaya eksekusi riil mendekati fee-only (saham likuid, spread tipis), varian ch10+trail2 layak dipertimbangkan. Kalau spread ≥1 tick per sisi, kandidat HHV20 tanpa trailing tetap lebih baik.
- Yang menentukan pilihan adalah biaya eksekusi riil. Data historis bid/offer tidak tersedia, jadi ini belum bisa diputuskan dari data.

Batasan: data sudah pernah dilihat, 18 konfigurasi, tick grid modern diterapkan ke harga historis yang disesuaikan. AFL tidak diubah.
