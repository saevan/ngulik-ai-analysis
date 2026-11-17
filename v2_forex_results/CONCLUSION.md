# V2 di forex (17 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `v2_forex.py`. Hasil: `results.csv`, `per_pair.csv`,
`v2_trades_gross_04.csv`, `v2_equity_gross_04.csv`.

Data: 9 pasangan mayor, bar per jam 2023-05-01..2026-05-23 (3 tahun), tanpa volume, dijadikan sesi harian 04:00
(sensitivitas 00:00). Dua arah: tiap pasangan juga dibalik (1/harga) agar V2 yang long-only bisa mengambil sisi short.
18 instrumen. Biaya proporsional 0 / 0,05% / 0,10% pulang-pergi, tanpa komisi. Pembanding: Swinger ideal (fill ideal).

## Hasil (sesi 04:00)
| | Biaya | CAGR | MDD | Trade/th | WR | Menang / kalah | Payoff | Expectancy/trade | Modal terpakai | Paruh 1 / Paruh 2 (ann.) |
|---|---|---|---|---|---|---|---|---|---|---|
| V2 | 0 | −2,8% | −10,6% | 25,6 | 33% | +1,5% / −1,9% | 0,80 | −0,8% | 47% | −4,2% / −1,4% |
| V2 | 0,10% | −3,2% | −11,5% | 25,6 | 32% | +1,5% / −2,0% | 0,75 | −0,9% | 47% | −4,6% / −1,7% |
| Swinger ideal | 0 | +10,3% | −1,9% | 171 | 54% | +1,7% / −0,7% | 2,37 | +0,6% | 90% | +14,1% / +6,9% |
| Swinger ideal | 0,10% | +8,5% | −2,4% | 171 | 51% | +1,7% / −0,7% | 2,21 | +0,5% | 90% | +12,4% / +4,8% |

Sesi 00:00: V2 lebih buruk lagi (CAGR −5,7% kotor, WR 27%, payoff 0,51). Swinger ideal +10,2%.
Per pasangan dan arah (biaya 0,10%): 17 dari 18 negatif; hanya GBPJPY long positif (+1,1% × 6 trade). Hari ketika
pasangan dan kebalikannya dipegang bersamaan: 70 hari dari ~780.

## Pembanding dengan saham
| | V2 saham realistis (2000–25) | V2 forex (2023–26) |
|---|---|---|
| CAGR | +20,7% | −2,8% |
| WR | 41% | 33% |
| Rata-rata menang / kalah | +30% / −9% | +1,5% / −1,9% |
| Payoff | 3,5 | 0,8 |

Uji forex sebelumnya (Okt 2026, sistem lama, biaya nol): TimeHunter 17 trade WR 41% PF 0,97; modul breakout+ER
CAGR ≈ 0%. Hasil V2 konsisten dengan itu.

## Kesimpulan
- V2 tidak bekerja di forex pada sampel ini: rugi di kedua paruh, di kedua definisi sesi, dan di 17/18 pasangan-arah.
  Biaya bukan penyebabnya (kotor pun −2,8%/th).
- Penyebab mekanis: gerakan harian pasangan mayor kecil. Trade menang V2 hanya +1,5% dan kalah −1,9%, sehingga
  payoff 0,8 dengan WR 33% pasti rugi. Exit V2 (SMA30, fade 2 ATR) dirancang untuk ayunan saham 10–30%, bukan ayunan
  forex 1–3%. Breakout 20 hari + ER ≥ 0,2 juga tidak membawa kelanjutan tren di pasangan mayor harian.
- Swinger ideal positif (+10%/th) tetapi expectancy-nya +0,6% per trade, hampir seluruhnya bonus fill ideal yang
  tidak bisa dieksekusi. Di saham bonus itu +5,4% per trade dan masih ada pergerakan nyata di baliknya; di forex tidak.
- Batas: 3 tahun × 9 pasangan, zona waktu sumber tidak diketahui, tanpa leverage/swap/konversi mata uang, tanpa data
  volume. Cukup untuk mengatakan "tidak ada bukti V2 bekerja di forex", belum cukup untuk mengukur seberapa buruk.
