# SK-5 per kondisi pasar vs Swinger, dan karakteristik yang bisa dikejar (16 Okt 2026)

Kode: `analyze_sk5_regimes.py`, `decompose_sk5_gap.py`, `sk5_gap_levers.py`, `probe_sk5_posthoc.py`; engine `backtest_stop_execution.py`
(opsi baru `sma_arm`, `entry_sma`, default mati, regresi lulus). Diverifikasi 3 pemeriksa independen (hitung ulang identik < 1e-11 pp;
satu definisi dekomposisi dikoreksi, lihat bagian 3).
SK-5 = buy stop HHV5, ER20 ≥ 0,3, order pra-Open momentum 120/20, fading 2 ATR / Close<SMA30 / breakout palsu, 20% per posisi.
Kondisi pasar dari proxy equal-weight saham universe (survivor; 36 saham di 2000, 100 di 2025), label dari Close kemarin:
er20 = ER20 ≥ 0,3 dan arah 20 hari (uptrend 33%, sideways 55%, downtrend 11% hari); ret60 = return 60 hari >+5% / <−5% (51/30/19%).
Fee 0,15/0,25%, Rp1 miliar, tanpa batas likuiditas kecuali disebut. Return per kondisi = atribusi harian dianualkan (bukan sistem terpisah).

## 1. Kinerja per kondisi (er20, return tahunan pada hari kondisi itu)
| Sistem | Uptrend | Sideways | Downtrend |
|---|---:|---:|---:|
| Swinger ideal (tidak kausal) | 186,4% | 87,2% | 79,4% |
| SK-5 (fee) | 112,4% | 46,1% | 28,5% |
| SK-5 (slippage 0,25%/sisi) | 101,9% | 34,5% | 17,8% |
| Swinger stop order (kausal) | 91,1% | 13,9% | −19,5% |
| Swinger next Open (kausal) | 77,3% | 4,8% | −18,4% |
SK-5 = 60% / 53% / 36% dari Swinger ideal; di atas semua Swinger kausal di setiap kondisi untuk periode penuh (pengecualian: uptrend 2000–15
stop order 128,6% vs 115,9%; ret60 sideways 2021–25). Bulan berekor di antara bulan yang punya hari kondisi itu: SK-5 42/33/10% vs ideal 74/68/23%.
MDD rantai hari uptrend SK-5 −23% vs stop order −17%. Definisi ret60 memberi urutan yang sama (sideways paling lemah: SK-5 26,6% vs ideal 78,6%).

## 2. Karakter trade per kondisi saat entry (er20, SK-5 vs Swinger ideal)
| | Uptrend | Sideways | Downtrend |
|---|---|---|---|
| WR | 43% vs 55% | 43% vs 51% | 50% vs 51% |
| Avg win | 20,7% vs 21,2% | 12,7% vs 14,7% | 7,6% vs 14,7% |
| Avg loss | 4,3% vs 2,7% | 3,3% vs 3,2% | 2,5% vs 3,8% |
| Hold menang (bar) | 26,5 vs 28,0 | 15,0 vs 26,0 | 4,3 vs 25,9 |
| Trade/tahun | 21 vs 33 | 52 vs 72 | 10 vs 22 |
38% trade SK-5 (75% entry downtrend) dibeli saat Close di bawah SMA30 dan keluar ±2 bar.

## 3. Dari mana gap-nya (dekomposisi terkoreksi, pp return aritmetika tahunan, er20, fee)
Versi awal (`gap_decomposition_v1_superseded.csv`, modal terpakai × efisiensi) bias: laba hari entry masuk efisiensi tanpa dihitung sebagai modal.
| | Gap total | Dari hari entry | Dari posisi yang dipegang |
|---|---:|---:|---:|
| Uptrend | 30,3 | 16,9 | 13,4 |
| Sideways | 25,3 | 17,1 | 8,2 |
| Downtrend | 35,6 | 30,0 | 5,6 |
- Hari entry: return per rupiah yang masuk (sesudah biaya) ideal 1,8/1,5/2,1% vs SK-5 1,0/−0,1/0,9%, padahal nilai entry per hari SK-5 sama atau lebih besar.
  Ini fill ideal (beli di level pada bar yang sudah diketahui ditutup di atasnya) → tidak bisa dikejar secara kausal.
- Posisi dipegang: efisiensi SK-5 setara/lebih (92/60/38% vs 89/43/19% per unit modal), tetapi modal yang dipegang lebih kecil (79/54/24% vs 97/94/79%).

## 4. Tuas yang diuji untuk karakter yang tersisa
- Tahan breakout lemah lebih lama (`sma_arm`): modal terpakai naik 59→69%, CAGR 63,2→49,0%, rekor 139→123. Ditolak.
- Posisi lebih besar (1/4, 1/3): CAGR naik hanya di 2016–25, MDD lebih dalam, rekor turun; dengan batas 25% ADV keuntungan CAGR hilang. Ditolak.
- Entry hanya di atas SMA30 (post-hoc): CAGR 63,2→59,2%, return downtrend ≈0. Ditolak.
- Di 360 konfigurasi kausal, modal terpakai berkorelasi negatif dengan efisiensi (sideways −0,59, uptrend −0,76): modal bukan tuas gratis.
- ER 0,3→0,2: bulan rekor naik di 73 dari 90 sel; tahan batas likuiditas dan tanpa saham listing ≥2018.
- ER 0,2 + trailing LLV5 setelah +2 ATR (post-hoc): rekor naik di 18/18 sel. Full fee 66,5/172/−21 vs SK-5 63,2/139/−27; train 56,7/105 vs 67,0/96;
  validasi 75,3/33 vs 69,7/25; tes 97,9/36 vs 44,5/21; slippage 0,25% 52,2/142/−24 vs 51,8/117/−35; batas 25% ADV 28,2/118/−30 vs 27,5/94/−28;
  tanpa saham listing ≥2018 55,8/157/−21 vs 56,6/123/−29. Per kondisi: 118,7/48,4/30,3%.
- WR >50% bisa dicapai kausal (45 dari 360 konfigurasi; contoh ER .4, SMA30 + trail, tanpa exit breakout palsu: WR 53,5%, payout 2,45,
  63,1/143/−23), tetapi tidak menutup gap. Yang tidak bisa: WR >50% sekaligus payout ≈5.
- Seleksi train-only dan walk-forward tetap memilih SK-5; perbedaan walk-forward (54,3% vs 50,9%) dalam batas noise.

## 5. Batasan
Universe survivor: tanpa 20 saham yang listing ≥2018, SK-5 2021–25 turun 44,5→21,6% (rekor 21→9), full 63,2→56,6%. Label er20 berganti ±30×/tahun
(median 3 hari); downtrend 139 episode, hanya 21 ≥10 hari; 3 episode = 53% return downtrend SK-5; 2 trade (ULTJ 2001, WIFI 2025) = 68% laba
entry downtrend. Tanpa batas likuiditas posisi jauh melebihi nilai transaksi. Tuas di bagian 4 dirancang sesudah melihat seluruh periode. AFL tidak diubah.
