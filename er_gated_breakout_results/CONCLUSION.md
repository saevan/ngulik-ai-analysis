# Model pengguna: breakout HHV hanya saat ER pasar tidak choppy (15 Oktober 2026)

Kode `test_er_gated_breakout.py`. Entry Close > HHV20 (20 High sebelumnya), sinyal di Close, fill Open berikutnya. ER20 ambang 0,3: ER saham itu sendiri dan/atau ER pasar (proxy equal-weight 100 saham, bukan IHSG), keduanya diketahui di Close sinyal. Exit sistem utama: Close < SMA30 atau Open − Low bar berjalan ≥ 2 ATR14 sebelumnya, fill Open berikutnya, tanpa batas hold. Posisi tidak dipaksa keluar saat pasar menjadi choppy (spesifikasi utama). Rp1 miliar, 10 slot, 10% equity, compounding, urutan alfabet. Fee 0,15/0,25%; spread1 = fee + 1 tick per sisi + lot 100. Regresi: varian ER saham dan ER saham+pasar mereproduksi persis kurva riset sebelumnya (fading_sma30 fade2; primary_trend_only).

Format: CAGR / bulan rekor / MDD.

| Varian | Biaya | Train 2000–15 | Validation 2016–20 | Test 2021–25 | Full 2000–25 |
|---|---|---|---|---|---|
| **ER saham + ER pasar (model)** | fee | 35.5% / 67 / −39% | 23.6% / 22 / −28% | 8.1% / 5 / −21% | **27.9% / 91 / −39%** |
| **ER saham + ER pasar (model)** | spread1 | 20.6% / 51 / −50% | 14.5% / 21 / −34% | 2.0% / 3 / −30% | **16.0% / 65 / −50%** |
| ER pasar saja | fee | 36.8% / 66 | 18.9% / 22 | 5.5% / 8 | 27.0% / 91 / −34% |
| ER pasar saja | spread1 | 19.7% / 51 | 8.0% / 19 | −1.6% / 2 | 13.3% / 60 / −49% |
| ER saham saja (tanpa gate pasar) | fee | 38.4% / 75 | 30.9% / 22 | 19.8% / 12 | 33.6% / 108 / −35% |
| ER saham saja (tanpa gate pasar) | spread1 | 14.1% / 41 | 15.5% / 13 | 7.6% / 8 | 13.4% / 52 / −53% |
| Tanpa ER | fee | 42.3% / 70 | 19.4% / 15 | 5.7% / 9 | 31.8% / 93 / −47% |
| Tanpa ER | spread1 | 13.7% / 36 | 2.1% / 11 | −6.2% / 6 | 8.2% / 36 / −63% |
| Model + paksa keluar saat choppy | fee | 20.5% / 44 | 12.0% / 12 | 0.1% / 2 | 15.1% / 53 / −34% |
| Model + paksa keluar saat choppy | spread1 | 4.3% / 23 | −1.2% / 8 | −8.5% / 1 | 1.0% / 23 / −77% |
| Model, ambang ER pasar 0,2 | fee / spread1 | | | | 31.2% / 96 ; 16.2% / 60 |
| Model, ambang ER pasar 0,4 | fee / spread1 | | | | 20.2% / 65 ; 11.2% / 46 |

Karakter model (full, fee): 1528 trade, WR 43,7%, avg win 20,2%, avg loss 6,9%, payout 2,94, hold 21,3 bar, modal terpakai 51%. Atribusi harian: hari trend 45,2%/thn, hari choppy 15,4%/thn (posisi yang dibawa dari trend).

Kesimpulan:
- Model memfilter breakout saat choppy sesuai tujuan: entry hanya di hari ER pasar ≥0,3, trade turun 2392 → 1528.
- Dengan biaya spread, gate ER pasar memperbaiki full 2000–25 (13,4% / 52 → 16,0% / 65; MDD −53% → −50%). Dengan fee saja, gate menurunkan (33,6% / 108 → 27,9% / 91).
- Di test 2021–25, gate merugikan pada kedua biaya (fee 19,8% → 8,1%; spread 7,6% → 2,0%). Di validation dengan spread, bulan rekor naik (13 → 21) tetapi CAGR sedikit turun.
- Sebagai modul, modal hanya terpakai 51% (vs 75% tanpa gate); sisa kas menunggu modul choppy.
- Memaksa keluar saat pasar berubah choppy jauh lebih buruk di semua periode.
- Ambang 0,2/0,4 adalah sensitivitas, bukan hasil optimasi.
