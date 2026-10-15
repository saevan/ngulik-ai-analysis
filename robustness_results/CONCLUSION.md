# Putaran otonom: ketahanan & tuas biaya (15 Oktober 2026)

Kandidat yang diuji: **buy stop HHV20 (ER20 bar sebelumnya ≥0,3) + lewati gap up >2% + jual di Close saat gap down >2%**, fade2 dari Open bar berjalan (Close → next Open), exit Close < SMA30, tanpa gate pasar. Rp1 miliar, 10 slot, 10% equity, compounding. Format: CAGR / bulan rekor / MDD.

## 1. Day-trade gap down (kas menganggur rata-rata 25%) — DITOLAK
Beli Open saat gap down >2%, jual Close. Rata-rata per trade fee-only +0,7% s/d +2,7%. Dengan spread 1 tick/sisi −0,7% s/d −2,4% (kecuali gap >4% di test +0,4%). Tidak dibangun ke portofolio. Pantulan nyata, tetapi lebih kecil dari biaya tick.

## 2. Stress kandidat (`stress_frozen_candidate.py`, `stress.csv`)

| Stress | Base buy stop full | Kandidat full | + mom120 full | Kandidat test |
|---|---|---|---|---|
| spread 1 tick | 19.5/80/−43 | 25.4/95/−39 | 28.1/100/−44 | 14.7/10/−25 |
| spread 1 + auto-reject | 18.9/76/−42 | 24.1/94/−39 | 26.3/97/−44 | 11.5/9/−25 |
| spread 2 tick | 5.0/29/−71 | 11.3/55/−52 | 13.6/58/−55 | 3.7/6/−37 |
| spread 2 + auto-reject | 4.7/29/−66 | 10.2/53/−51 | 12.6/60/−55 | 1.0/6/−43 |
| spread 3 tick | −7.5/0/−90 | −0.8/14/−74 | 1.3/12/−77 | −6.2/4/−54 |

Urutan acak (5 seed, spread 1), full: base 17,5–21,1% (rata 19,3%), kandidat 21,5–25,8% (rata 24,4%).
Kesimpulan: kandidat lebih baik dari base di semua stress. **Biaya adalah risiko terbesar**: 2 tick/sisi memotong CAGR sekitar setengah; 3 tick menghapus edge.

## 3. Tuas biaya (`optimize_cost_levers.py`, `cost_lever_results/`)
- Filter tick/harga (≤1% atau ≤0,5%): **merusak** di hampir semua window. Profit datang dari saham harga rendah.
- Fading 3 atau 5: lebih baik di train, lebih buruk di validation. Tidak stabil.
- **mom120 (urutkan momentum 120 hari, skip 20)**: CAGR naik di semua window dan kedua tingkat spread (+0,3 s/d +4,2 pp), bulan rekor naik di 7 dari 8 kombinasi; MDD campur.
- Pilihan beku (fade3+mom120) gagal di validation (spread1 24,6%/21 vs 29,6%/22). Tidak diadopsi.

## 4. Jual saat gap up (`test_gapup_exit.py`, `gapup_exit_results/`)
Tidak ada level yang lolos syarat train. Gap up 4% merusak semua window. Ditolak.

## 5. Kandidat terbaik saat ini
**buy stop + lewati gap up 2% + jual Close saat gap down 2% + urutan mom120**:

| Window | Fee | Spread 1 tick | Spread 2 tick |
|---|---|---|---|
| train 2000–15 | 51.0/84/−25 | 27.6/63/−44 | 11.6/40/−55 |
| validation 2016–20 | 54.0/29/−23 | 37.2/25/−29 | 24.7/19/−37 |
| test 2021–25 | 38.9/25/−16 | 24.1/18/−21 | 12.3/10/−27 |
| full 2000–25 | 48.5/136/−25 | 28.1/100/−44 | 13.6/58/−55 |

Pembanding sistem awal (Breakout+ER next Open, full): fee 33,65%/108, spread 13,37%/52. Sistem gabungan utama+inverse: 15,80%/81 dan 5,51%/36.

Status: kandidat kuat, BUKAN terbukti out-of-sample. mom120 ditambahkan sesudah melihat window validation/test. Semua data sudah pernah dilihat. Belum dimodelkan: slippage stop saat breakout cepat (sebagian ditangkap stress 2–3 tick), antrean, likuiditas, corporate action. AFL aktif tidak diubah.
