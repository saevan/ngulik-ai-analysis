# TimeHunter: pengaruh tuas pada periode gabungan

Data saham harian 12 Juli 1994–15 Agustus 2025; 100 ticker; seluruh biaya nol. Fading dari Open bar berjalan; exit next tradable Open. Hold dihitung termasuk bar entry. Tidak memotong posisi pada batas 2014/2019.

Grid: 1800 konfigurasi = 8 hold × 9 fading × 25 entry. Lolos lima kriteria numerik: 296. Ini pencarian in-sample, bukan validasi independen atau bukti tujuh kriteria.

PF = jumlah return positif / absolut jumlah return negatif, dengan bobot notional entry sama per transaksi. Payout = rata-rata return positif / absolut rata-rata return negatif. PF ini bukan PF berbasis laba rupiah portofolio dengan ukuran posisi berubah. Mean adalah return per transaksi, bukan CAGR. Worst adalah transaksi terburuk, bukan maximum drawdown portofolio.

Average loss ditampilkan sebagai magnitudo positif: makin kecil berarti kerugian rata-rata lebih kecil. Posisi akhir periode ditutup/ditandai sesuai engine sebelumnya; survivorship dan corporate action belum diverifikasi.

## Tuas hold: dimensi lain tetap pada kandidat H200/fade30%/trend100-rebound2
| Hold | Fading | Entry | N | WR | PF | Payout | Mean | Median | Avg win | Avg loss | Worst |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 0.3 | trend_100_rebound_2 | 19036 | 46.98% | 1.431 | 1.465 | 1.25% | 0.00% | 8.85% | 6.04% | -80.19% |
| 20 | 0.3 | trend_100_rebound_2 | 11406 | 48.90% | 1.630 | 1.603 | 2.50% | 0.00% | 13.22% | 8.25% | -80.19% |
| 30 | 0.3 | trend_100_rebound_2 | 8434 | 49.93% | 1.782 | 1.694 | 3.74% | 0.00% | 17.06% | 10.08% | -82.08% |
| 50 | 0.3 | trend_100_rebound_2 | 5716 | 51.01% | 1.977 | 1.823 | 5.99% | 0.76% | 23.75% | 13.03% | -82.35% |
| 75 | 0.3 | trend_100_rebound_2 | 4171 | 52.00% | 2.259 | 2.016 | 9.16% | 1.30% | 31.60% | 15.67% | -84.91% |
| 100 | 0.3 | trend_100_rebound_2 | 3378 | 52.61% | 2.577 | 2.254 | 12.78% | 1.71% | 39.69% | 17.61% | -92.22% |
| 150 | 0.3 | trend_100_rebound_2 | 2511 | 52.65% | 2.873 | 2.523 | 19.05% | 2.35% | 55.49% | 22.00% | -90.57% |
| 200 | 0.3 | trend_100_rebound_2 | 1974 | 53.44% | 3.418 | 2.916 | 26.26% | 3.92% | 69.45% | 23.82% | -90.27% |
## Tuas fade: dimensi lain tetap pada kandidat H200/fade30%/trend100-rebound2
| Hold | Fading | Entry | N | WR | PF | Payout | Mean | Median | Avg win | Avg loss | Worst |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 200 | off | trend_100_rebound_2 | 1956 | 53.78% | 3.487 | 2.940 | 26.63% | 4.12% | 69.43% | 23.61% | -90.57% |
| 200 | 0.02 | trend_100_rebound_2 | 34169 | 36.48% | 1.318 | 1.992 | 0.54% | -0.77% | 6.11% | 3.07% | -62.50% |
| 200 | 0.03 | trend_100_rebound_2 | 24711 | 37.47% | 1.369 | 2.050 | 0.86% | -1.10% | 8.55% | 4.17% | -62.50% |
| 200 | 0.05 | trend_100_rebound_2 | 11584 | 40.15% | 1.545 | 2.134 | 2.31% | -1.81% | 16.29% | 7.63% | -60.00% |
| 200 | 0.075 | trend_100_rebound_2 | 4920 | 44.67% | 1.960 | 2.281 | 6.99% | -1.44% | 31.96% | 14.01% | -83.96% |
| 200 | 0.1 | trend_100_rebound_2 | 3119 | 47.74% | 2.352 | 2.434 | 12.56% | 0.00% | 45.76% | 18.80% | -83.96% |
| 200 | 0.15 | trend_100_rebound_2 | 2264 | 51.37% | 2.828 | 2.580 | 19.60% | 1.47% | 59.04% | 22.89% | -89.00% |
| 200 | 0.2 | trend_100_rebound_2 | 2076 | 52.22% | 3.159 | 2.801 | 23.86% | 2.51% | 66.85% | 23.87% | -90.00% |
| 200 | 0.3 | trend_100_rebound_2 | 1974 | 53.44% | 3.418 | 2.916 | 26.26% | 3.92% | 69.45% | 23.82% | -90.27% |
## Tuas entry: dimensi lain tetap pada kandidat H200/fade30%/trend100-rebound2
| Hold | Fading | Entry | N | WR | PF | Payout | Mean | Median | Avg win | Avg loss | Worst |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 200 | 0.3 | always | 2411 | 52.59% | 3.424 | 2.970 | 27.42% | 2.76% | 73.65% | 24.79% | -92.00% |
| 200 | 0.3 | trend_20 | 2321 | 52.52% | 3.280 | 2.887 | 25.83% | 2.74% | 70.75% | 24.51% | -92.00% |
| 200 | 0.3 | trend_50 | 2230 | 52.29% | 3.223 | 2.875 | 25.32% | 2.96% | 70.21% | 24.42% | -92.08% |
| 200 | 0.3 | trend_100 | 2087 | 53.62% | 3.463 | 2.931 | 26.41% | 4.11% | 69.24% | 23.62% | -90.29% |
| 200 | 0.3 | trend_200 | 1881 | 53.06% | 3.532 | 3.068 | 26.72% | 2.34% | 70.26% | 22.90% | -86.52% |
| 200 | 0.3 | dip_20_2 | 2386 | 52.81% | 3.327 | 2.867 | 26.13% | 2.81% | 70.74% | 24.67% | -92.00% |
| 200 | 0.3 | dip_20_5 | 2347 | 52.07% | 3.280 | 2.920 | 25.79% | 2.31% | 71.25% | 24.40% | -92.00% |
| 200 | 0.3 | dip_20_10 | 2138 | 52.99% | 3.270 | 2.800 | 25.97% | 2.34% | 70.58% | 25.21% | -92.19% |
| 200 | 0.3 | dip_20_15 | 1812 | 53.75% | 3.408 | 2.831 | 27.94% | 3.10% | 73.57% | 25.99% | -92.62% |
| 200 | 0.3 | dip_50_2 | 2385 | 52.91% | 3.295 | 2.838 | 26.18% | 2.99% | 71.02% | 25.02% | -92.00% |
| 200 | 0.3 | dip_50_5 | 2361 | 52.86% | 3.311 | 2.871 | 26.35% | 2.99% | 71.42% | 24.88% | -92.00% |
| 200 | 0.3 | dip_50_10 | 2224 | 51.98% | 3.218 | 2.870 | 25.29% | 1.77% | 70.58% | 24.59% | -92.00% |
| 200 | 0.3 | dip_50_15 | 1991 | 52.24% | 3.230 | 2.839 | 26.23% | 2.45% | 72.73% | 25.62% | -92.19% |
| 200 | 0.3 | trend_100_dip_2 | 2041 | 53.11% | 3.395 | 2.922 | 26.20% | 3.14% | 69.93% | 23.94% | -90.29% |
| 200 | 0.3 | trend_100_dip_5 | 1899 | 53.45% | 3.559 | 3.037 | 27.68% | 3.10% | 72.01% | 23.71% | -87.18% |
| 200 | 0.3 | trend_100_dip_10 | 1506 | 53.72% | 3.691 | 3.116 | 30.26% | 3.62% | 77.27% | 24.80% | -89.61% |
| 200 | 0.3 | trend_100_rebound_2 | 1974 | 53.44% | 3.418 | 2.916 | 26.26% | 3.92% | 69.45% | 23.82% | -90.27% |
| 200 | 0.3 | trend_100_rebound_5 | 1802 | 53.33% | 3.467 | 2.976 | 27.07% | 3.44% | 71.33% | 23.96% | -89.89% |
| 200 | 0.3 | trend_200_dip_2 | 1822 | 52.91% | 3.498 | 3.074 | 26.05% | 2.50% | 68.95% | 22.43% | -92.03% |
| 200 | 0.3 | trend_200_dip_5 | 1716 | 52.91% | 3.526 | 3.111 | 26.96% | 2.91% | 71.13% | 22.87% | -85.47% |
| 200 | 0.3 | trend_200_dip_10 | 1384 | 52.96% | 3.625 | 3.156 | 29.31% | 2.71% | 76.41% | 24.22% | -89.61% |
| 200 | 0.3 | trend_200_rebound_2 | 1773 | 53.36% | 3.514 | 3.035 | 26.20% | 3.19% | 68.62% | 22.61% | -92.03% |
| 200 | 0.3 | trend_200_rebound_5 | 1623 | 52.19% | 3.377 | 3.066 | 26.09% | 2.04% | 71.04% | 23.17% | -89.89% |
| 200 | 0.3 | breakout_20 | 2004 | 54.34% | 3.414 | 2.828 | 26.21% | 4.27% | 68.22% | 24.13% | -88.57% |
| 200 | 0.3 | breakout_50 | 1679 | 54.44% | 3.632 | 2.984 | 27.78% | 4.17% | 70.43% | 23.60% | -90.36% |
## Perubahan berpasangan di seluruh grid
Delta = sesudah minus sebelum. Setiap pasangan hanya mengubah satu tuas. Median merangkum variasi konfigurasi, bukan estimasi kausal atau uji signifikansi. Persentase naik dihitung dari pasangan konfigurasi yang sangat berkorelasi.
| Tuas | Sebelum → sesudah | Metrik | Pasangan | Median delta | Proporsi naik |
|---|---|---|---:|---:|---:|
| hold | 10 → 20 | wr | 225 | +0.83 pp | 63.1% |
| hold | 10 → 20 | pf | 225 | +0.132 | 99.1% |
| hold | 10 → 20 | mean | 225 | +0.92 pp | 99.6% |
| hold | 20 → 30 | wr | 225 | +0.31 pp | 56.4% |
| hold | 20 → 30 | pf | 225 | +0.090 | 99.6% |
| hold | 20 → 30 | mean | 225 | +0.87 pp | 100.0% |
| hold | 30 → 50 | wr | 225 | +0.01 pp | 50.7% |
| hold | 30 → 50 | pf | 225 | +0.139 | 99.1% |
| hold | 30 → 50 | mean | 225 | +1.56 pp | 99.1% |
| hold | 50 → 75 | wr | 225 | +0.01 pp | 52.0% |
| hold | 50 → 75 | pf | 225 | +0.138 | 96.4% |
| hold | 50 → 75 | mean | 225 | +1.77 pp | 97.8% |
| hold | 75 → 100 | wr | 225 | +0.00 pp | 50.7% |
| hold | 75 → 100 | pf | 225 | +0.102 | 99.6% |
| hold | 75 → 100 | mean | 225 | +1.37 pp | 100.0% |
| hold | 100 → 150 | wr | 225 | -0.07 pp | 29.8% |
| hold | 100 → 150 | pf | 225 | +0.163 | 81.8% |
| hold | 100 → 150 | mean | 225 | +2.30 pp | 84.0% |
| hold | 150 → 200 | wr | 225 | -0.00 pp | 48.9% |
| hold | 150 → 200 | pf | 225 | +0.112 | 97.3% |
| hold | 150 → 200 | mean | 225 | +1.60 pp | 96.9% |
| fade | off → 0.02 | wr | 200 | -13.55 pp | 0.0% |
| fade | off → 0.02 | pf | 200 | -0.759 | 0.5% |
| fade | off → 0.02 | mean | 200 | -7.12 pp | 0.0% |
| fade | off → 0.03 | wr | 200 | -12.92 pp | 0.0% |
| fade | off → 0.03 | pf | 200 | -0.714 | 0.5% |
| fade | off → 0.03 | mean | 200 | -6.81 pp | 0.0% |
| fade | off → 0.05 | wr | 200 | -10.50 pp | 0.0% |
| fade | off → 0.05 | pf | 200 | -0.574 | 0.0% |
| fade | off → 0.05 | mean | 200 | -5.68 pp | 0.0% |
| fade | off → 0.075 | wr | 200 | -5.99 pp | 0.0% |
| fade | off → 0.075 | pf | 200 | -0.411 | 0.0% |
| fade | off → 0.075 | mean | 200 | -3.83 pp | 0.0% |
| fade | off → 0.1 | wr | 200 | -2.86 pp | 0.0% |
| fade | off → 0.1 | pf | 200 | -0.261 | 0.0% |
| fade | off → 0.1 | mean | 200 | -2.23 pp | 0.0% |
| fade | off → 0.15 | wr | 200 | -1.06 pp | 0.5% |
| fade | off → 0.15 | pf | 200 | -0.140 | 0.0% |
| fade | off → 0.15 | mean | 200 | -0.88 pp | 0.5% |
| fade | off → 0.2 | wr | 200 | -0.46 pp | 3.0% |
| fade | off → 0.2 | pf | 200 | -0.057 | 4.0% |
| fade | off → 0.2 | mean | 200 | -0.29 pp | 7.0% |
| fade | off → 0.3 | wr | 200 | -0.08 pp | 15.0% |
| fade | off → 0.3 | pf | 200 | -0.001 | 44.0% |
| fade | off → 0.3 | mean | 200 | +0.00 pp | 50.5% |
| fade | 0.02 → 0.03 | wr | 200 | +0.64 pp | 91.0% |
| fade | 0.02 → 0.03 | pf | 200 | +0.045 | 95.0% |
| fade | 0.02 → 0.03 | mean | 200 | +0.27 pp | 100.0% |
| fade | 0.03 → 0.05 | wr | 200 | +2.76 pp | 100.0% |
| fade | 0.03 → 0.05 | pf | 200 | +0.126 | 96.5% |
| fade | 0.03 → 0.05 | mean | 200 | +1.03 pp | 100.0% |
| fade | 0.05 → 0.075 | wr | 200 | +4.01 pp | 100.0% |
| fade | 0.05 → 0.075 | pf | 200 | +0.182 | 97.5% |
| fade | 0.05 → 0.075 | mean | 200 | +1.88 pp | 100.0% |
| fade | 0.075 → 0.1 | wr | 200 | +2.69 pp | 100.0% |
| fade | 0.075 → 0.1 | pf | 200 | +0.142 | 99.5% |
| fade | 0.075 → 0.1 | mean | 200 | +1.49 pp | 99.5% |
| fade | 0.1 → 0.15 | wr | 200 | +1.75 pp | 100.0% |
| fade | 0.1 → 0.15 | pf | 200 | +0.123 | 100.0% |
| fade | 0.1 → 0.15 | mean | 200 | +1.30 pp | 100.0% |
| fade | 0.15 → 0.2 | wr | 200 | +0.48 pp | 98.5% |
| fade | 0.15 → 0.2 | pf | 200 | +0.072 | 100.0% |
| fade | 0.15 → 0.2 | mean | 200 | +0.52 pp | 99.5% |
| fade | 0.2 → 0.3 | wr | 200 | +0.37 pp | 95.0% |
| fade | 0.2 → 0.3 | pf | 200 | +0.051 | 97.5% |
| fade | 0.2 → 0.3 | mean | 200 | +0.32 pp | 96.0% |
| entry | always → trend_100 | wr | 72 | +1.36 pp | 97.2% |
| entry | always → trend_100 | pf | 72 | +0.155 | 100.0% |
| entry | always → trend_100 | mean | 72 | +0.50 pp | 98.6% |
| entry | trend_100 → trend_100_dip_2 | wr | 72 | +0.08 pp | 62.5% |
| entry | trend_100 → trend_100_dip_2 | pf | 72 | +0.002 | 58.3% |
| entry | trend_100 → trend_100_dip_2 | mean | 72 | +0.02 pp | 56.9% |
| entry | trend_100_dip_2 → trend_100_rebound_2 | wr | 72 | -0.32 pp | 29.2% |
| entry | trend_100_dip_2 → trend_100_rebound_2 | pf | 72 | -0.024 | 22.2% |
| entry | trend_100_dip_2 → trend_100_rebound_2 | mean | 72 | -0.03 pp | 30.6% |
| entry | trend_100_rebound_2 → trend_200_rebound_2 | wr | 72 | -0.16 pp | 37.5% |
| entry | trend_100_rebound_2 → trend_200_rebound_2 | pf | 72 | -0.021 | 16.7% |
| entry | trend_100_rebound_2 → trend_200_rebound_2 | mean | 72 | -0.10 pp | 6.9% |
| entry | trend_100_rebound_2 → trend_100_rebound_5 | wr | 72 | -0.49 pp | 13.9% |
| entry | trend_100_rebound_2 → trend_100_rebound_5 | pf | 72 | -0.036 | 25.0% |
| entry | trend_100_rebound_2 → trend_100_rebound_5 | mean | 72 | +0.03 pp | 55.6% |
| entry | always → breakout_20 | wr | 72 | +2.12 pp | 88.9% |
| entry | always → breakout_20 | pf | 72 | +0.243 | 98.6% |
| entry | always → breakout_20 | mean | 72 | +1.14 pp | 98.6% |
| entry | breakout_20 → breakout_50 | wr | 72 | +1.41 pp | 98.6% |
| entry | breakout_20 → breakout_50 | pf | 72 | +0.197 | 100.0% |
| entry | breakout_20 → breakout_50 | mean | 72 | +0.68 pp | 98.6% |
## Lima konfigurasi tertinggi menurut wr (N >= 200, ticker >= 20)
| Hold | Fading | Entry | N | WR | PF | Payout | Mean | Median | Avg win | Avg loss | Worst |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 200 | off | breakout_20 | 1982 | 54.89% | 3.565 | 2.897 | 27.17% | 4.73% | 68.79% | 23.75% | -91.67% |
| 200 | off | breakout_50 | 1671 | 54.82% | 3.737 | 3.023 | 28.26% | 4.40% | 70.38% | 23.28% | -90.29% |
| 75 | off | breakout_50 | 3020 | 54.64% | 2.564 | 2.054 | 11.04% | 2.83% | 33.13% | 16.13% | -88.05% |
| 75 | 0.3 | breakout_50 | 3022 | 54.63% | 2.567 | 2.057 | 11.06% | 2.83% | 33.18% | 16.13% | -88.05% |
| 75 | 0.2 | breakout_50 | 3048 | 54.49% | 2.506 | 2.013 | 10.37% | 2.71% | 31.65% | 15.72% | -70.98% |
## Lima konfigurasi tertinggi menurut pf (N >= 200, ticker >= 20)
| Hold | Fading | Entry | N | WR | PF | Payout | Mean | Median | Avg win | Avg loss | Worst |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 200 | off | trend_100_dip_10 | 1489 | 54.26% | 3.739 | 3.101 | 30.00% | 4.21% | 75.47% | 24.34% | -89.61% |
| 200 | off | breakout_50 | 1671 | 54.82% | 3.737 | 3.023 | 28.26% | 4.40% | 70.38% | 23.28% | -90.29% |
| 200 | off | trend_200_dip_10 | 1373 | 53.46% | 3.709 | 3.173 | 29.67% | 3.36% | 76.00% | 23.95% | -89.61% |
| 200 | off | trend_200_dip_5 | 1704 | 53.35% | 3.696 | 3.200 | 28.24% | 3.09% | 72.58% | 22.68% | -85.47% |
| 200 | 0.3 | trend_100_dip_10 | 1506 | 53.72% | 3.691 | 3.116 | 30.26% | 3.62% | 77.27% | 24.80% | -89.61% |
## Lima konfigurasi tertinggi menurut mean (N >= 200, ticker >= 20)
| Hold | Fading | Entry | N | WR | PF | Payout | Mean | Median | Avg win | Avg loss | Worst |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 200 | 0.3 | trend_100_dip_10 | 1506 | 53.72% | 3.691 | 3.116 | 30.26% | 3.62% | 77.27% | 24.80% | -89.61% |
| 200 | off | trend_100_dip_10 | 1489 | 54.26% | 3.739 | 3.101 | 30.00% | 4.21% | 75.47% | 24.34% | -89.61% |
| 200 | off | trend_200_dip_10 | 1373 | 53.46% | 3.709 | 3.173 | 29.67% | 3.36% | 76.00% | 23.95% | -89.61% |
| 200 | 0.3 | trend_200_dip_10 | 1384 | 52.96% | 3.625 | 3.156 | 29.31% | 2.71% | 76.41% | 24.22% | -89.61% |
| 200 | off | breakout_50 | 1671 | 54.82% | 3.737 | 3.023 | 28.26% | 4.40% | 70.38% | 23.28% | -90.29% |