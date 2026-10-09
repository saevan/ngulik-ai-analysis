# Kesimpulan optimasi utama + inverse, 9 Oktober 2026

48 simulasi selesai: 8 konfigurasi x3 mode training spread +24 evaluasi lanjutan. Semua8 konfigurasi gagal syarat training. HHV20/SMA20/carry dibekukan sebagai diagnostik, BUKAN kandidat lolos. Baseline HHV20/SMA30 tetap; AFL aktif tidak diubah.

Modal Rp1miliar/10slot bersama/compounding. Fee beli0.15% jual0.25%; spread stress1tick per sisi+lot100. Sinyal completed Close, fill next tradable Open. Full4Jan2000?15Agu2025; train2000?2015, validation2016?2020, test2021?2025. Data sudah pernah dieksplorasi, bukan holdout independen.

Trend/choppy annual adalah atribusi return harian dianualkan, bukan standalone CAGR. Rekor ialah bulan dengan daily Close equity melampaui seluruh ATH sebelumnya.

| Window | Biaya | Mode | SMA | CAGR | Trend annual | Choppy annual | WR | Hold bar | Rekor/bulan |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| validation | fees | combined | 20 | 22.37% | 29.76% | 16.91% | 56.08% | 41.72 | 28/60 |
| validation | fees | combined | 30 | 23.16% | 33.51% | 15.68% | 60.64% | 49.45 | 22/60 |
| validation | fees | primary | 20 | 20.50% | 40.15% | 7.15% | 35.61% | 15.02 | 19/60 |
| validation | fees | inverse | 20 | 8.94% | 5.80% | 11.44% | 70.21% | 77.72 | 21/60 |
| validation | spread | combined | 20 | 12.20% | 17.85% | 8.00% | 51.01% | 41.72 | 17/60 |
| validation | spread | combined | 30 | 14.79% | 23.77% | 8.26% | 55.02% | 49.45 | 15/60 |
| validation | spread | primary | 20 | 9.89% | 13.21% | 7.37% | 32.31% | 15.06 | 17/60 |
| validation | spread | inverse | 20 | 3.98% | 5.06% | 3.15% | 65.25% | 77.72 | 17/60 |
| test | fees | combined | 20 | 3.01% | 9.92% | -0.39% | 47.09% | 50.60 | 6/56 |
| test | fees | combined | 30 | 5.11% | 12.78% | 1.35% | 48.82% | 53.46 | 10/56 |
| test | fees | primary | 20 | 9.48% | -3.70% | 16.98% | 36.00% | 14.86 | 9/56 |
| test | fees | inverse | 20 | 0.63% | 11.30% | -4.48% | 58.96% | 79.06 | 8/56 |
| test | spread | combined | 20 | -1.11% | 3.83% | -3.58% | 45.29% | 50.60 | 4/56 |
| test | spread | combined | 30 | 1.02% | 7.20% | -2.04% | 46.92% | 53.46 | 10/56 |
| test | spread | primary | 20 | 2.23% | -21.67% | 17.33% | 33.43% | 14.86 | 3/56 |
| test | spread | inverse | 20 | -1.86% | 11.30% | -8.05% | 58.21% | 79.06 | 8/56 |
| full | fees | combined | 20 | 15.54% | 27.45% | 6.73% | 52.59% | 41.32 | 88/308 |
| full | fees | combined | 30 | 15.80% | 28.37% | 6.54% | 55.11% | 47.70 | 81/308 |
| full | fees | primary | 20 | 24.62% | 39.84% | 13.55% | 40.52% | 15.84 | 89/308 |
| full | fees | inverse | 20 | 4.63% | 10.37% | 0.21% | 65.58% | 72.68 | 51/308 |
| full | spread | combined | 20 | 3.65% | 13.05% | -3.37% | 48.00% | 41.32 | 30/308 |
| full | spread | combined | 30 | 5.51% | 16.37% | -2.52% | 50.49% | 47.70 | 36/308 |
| full | spread | primary | 20 | 10.70% | 7.80% | 13.11% | 36.69% | 15.85 | 48/308 |
| full | spread | inverse | 20 | -0.89% | 10.31% | -9.12% | 61.91% | 72.68 | 5/308 |

Kesimpulan: tidak ada bukti bahwa optimasi ini membuat kedua modul perform di rezimnya. Kandidat diagnostik kalah baseline pada full dan test sesudah spread. Prioritas penelitian berikutnya tetap expectancy inverse saat choppy.

Verifikasi:20unit tests lulus; runner memeriksa prefix causality, gate komplementer, eligibility entry, akuntansi dan exact equity regression baseline full.
