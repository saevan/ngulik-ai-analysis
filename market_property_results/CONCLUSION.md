# Sifat pasar Kompas100 dan pemanfaatannya (15 Oktober 2026)

Kode: `analyze_market_properties.py` (ukur sifat per periode), `exploit_market_properties.py` (grid 16 konfigurasi, freeze di train), mesin `backtest_stop_execution.py` (parameter baru default = perilaku lama; regresi persis lulus untuk base next Open dan base buy stop).

Setup tetap: Rp1 miliar, 10 slot bersama, 10% equity Close sebelumnya, compounding, long only, fade2 ATR dari Open bar berjalan (sinyal Close → next Open), exit Close < SMA30, tanpa gate pasar. Fee 0,15/0,25%; spread 1 tick/sisi + lot 100.

## 1. Sifat pasar (train 2000–15 / validation 2016–20 / test 2021–25)

| Sifat | Train | Validation | Test | Stabil? |
|---|---:|---:|---:|---|
| Intraday sesudah gap up >2% (bps) | −48 | −88 | −75 | **ya: gap up memudar** |
| Intraday sesudah gap down >2% (bps) | +176 | +154 | +112 | **ya: gap down memantul** |
| Breakout HHV20+ER, maju 20 hari, volume ≥2× (%) | 6.47 | 6.84 | 3.17 | **ya, lebih kuat** |
| Breakout HHV20+ER, maju 20 hari, tanpa lonjakan volume (%) | 3.42 | 3.82 | 1.18 | |
| Momentum 120 hari (skip 20) top–bottom kuintil, 20 hari ke depan (%) | 0.72 | 1.10 | 1.22 | **ya** |
| Turn of month vs sisa bulan (bps/hari) | 17 vs 9 | 13 vs 8 | 8 vs 5 | ya, tapi kecil |
| Overnight rata-rata (bps) | −15 | +16 | +21 | tidak (berbalik) |
| Autokorelasi indeks harian | 0.12 | 0.10 | 0.00 | tidak |
| Low-vol minus high-vol (%) | +0.53 | −1.74 | −0.80 | tidak |

Semua angka equal-weight dan tanpa biaya; ini sifat statistik, bukan profit sistem.

## 2. Pemanfaatan (tuas ditetapkan sebelum grid; parameter 2%, 1,5×, 120 hari tidak dituning)

- **gap_skip**: batalkan buy stop jika Open sudah >2% di atas level (jangan beli gap up).
- **gapdown_close**: jika exit tertunda dan Open gap down >2% dari Close kemarin, jual di Close hari itu (closing auction), bukan di Open.
- **rank mom120**: saat slot penuh, dahulukan momentum 120 hari tertinggi (bukan alfabet).
- **entry next_open_vol**: breakout Close + ER + volume ≥1,5× di bar sinyal, beli next Open (alternatif buy stop).

Pilihan beku (train spread): **buy stop + gap_skip + gapdown_close, urutan alfabet** (28,0%/66 vs base buy stop 20,9%/55).

| Window | Biaya | Base buy stop | **Frozen** | Diagnostik: frozen + mom120 |
|---|---|---|---|---|
| validation 2016–20 | spread | 23.7% / 20 / −22% | **29.6% / 22** / −28% | 37.2% / 25 / −29% |
| test 2021–25 | spread | 11.6% / 10 / −30% | **14.7% / 10 / −25%** | 24.1% / 18 / −21% |
| full 2000–25 | spread | 19.5% / 80 / −43% | **25.4% / 95 / −39%** | 28.1% / 100 / −44% |
| validation | fees | 41.8% / 31 / −19% | 46.3% / 30 / −21% | 54.0% / 29 / −23% |
| test | fees | 25.2% / 17 / −22% | 27.8% / 21 / −19% | 38.9% / 25 / −16% |
| full | fees | 40.8% / 124 / −24% | **45.8% / 137 / −22%** | 48.5% / 136 / −25% |

(CAGR / bulan rekor / MDD; trade full spread: WR 38,9%→40,5%, avg loss 8,0%→7,5%, payout 2,42→2,58, hold ~21 bar)

**Pertama kalinya kandidat beku bertahan di validation DAN test setelah spread** (CAGR naik, bulan rekor tidak turun). Bulan rekor validation fee turun 1 (31→30).

## 3. Konsistensi tiap tuas (rata-rata selisih pasangan yang hanya beda satu tuas, 8 pasangan per window)

- **gapdown_close: CAGR naik di semua window dan kedua biaya** (+0,9 s/d +1,8 pp), bulan rekor umumnya naik. Tuas paling kuat.
- **mom120 rank: CAGR naik di semua window** (+0,6 s/d +7,4 pp; terbesar di test), tetapi MDD lebih buruk di train/validation. Tidak terpilih karena di train efeknya kecil.
- gap_skip: kuat di train (+2,7/+3,9 pp), campur di validation/test (rata-rata sedikit negatif). Belum terbukti stabil.
- next_open_vol (volume) lebih buruk dari buy stop di semua window. Sifat volume nyata, tetapi menunggu konfirmasi Close + next Open menghapus keuntungannya.

## 4. Batasan

Tanda sifat sudah dicek di validation/test sebelum tuas dipilih, jadi periode itu bukan holdout bersih untuk pemilihan tuas (parameter tidak dituning). Kolom diagnostik dilihat sesudah freeze. Jual di Close mengasumsikan bisa ikut closing auction BEI pada harga Close (+1 tick spread di skenario stress). Buy stop belum memodelkan slippage breakout cepat, auto-reject, antrean, likuiditas. Proxy & data: penyesuaian harga/corporate action dan survivorship belum tervalidasi. AFL tidak diubah.
