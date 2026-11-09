# Logic A: breakout swing 5 hari, dieksekusi realistis (9 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `logic_a_swing5.py`. Hasil: `results.csv`, `trades_*.csv`.

Logika:
- Sinyal sama dengan arah Swinger: Close menembus garis trailing 5 hari.
- Eksekusi nyata: beli dan jual di Open berikutnya.
- 10% per order, maksimal 10 posisi, biaya B.
- Versi realistis: likuid point-in-time + filter data basi + order ≤ 25% ADV20.

Varian:
- A0: tanpa filter.
- A1: naik = semua saham; sideways = hanya ER20 ≥ 0,2; turun = tidak beli.
- A2: naik = semua saham; sideways dan turun = hanya ER20 ≥ 0,2.

## Hasil (B, 2000-01-01..2025-08-15)
| Realistis | CAGR | MDD | 2000–07 | 2008–15 | 2016–20 | 2021–25 |
|---|---|---|---|---|---|---|
| A0 | −2,8% | −93% | +19,8% | −8,6% | −6,6% | −21,5% |
| A1 | +4,9% | −69% | +20,2% | −3,6% | −1,8% | +2,7% |
| A2 | +3,0% | −71% | +18,2% | −7,3% | +0,9% | −0,7% |
| Swinger ideal | +102,0% | −21% | +150% | +88% | +90% | +70% |

| Return per tahun pada hari berkondisi | Naik | Sideways | Turun |
|---|---|---|---|
| A0 realistis | +26,8% | −14,0% | −19,9% |
| A1 realistis | +19,9% | −1,6% | −1,2% (modal terpakai 16%) |
| A2 realistis | +20,4% | −3,5% | −9,3% |
| Swinger ideal | +185,7% | +79,2% | +65,8% |

Kualitas trade:
- A1 realistis: WR 33,5%, menang +13,7% / kalah −5,7%, payoff 2,4, expectancy +0,8%/trade.
- Swinger ideal: WR 48,8%, +17,0% / −3,5%, payoff 4,9, +6,5%/trade.
- Biaya: sekitar 86–122 trade per tahun × 10% × 0,9% ≈ 8–11% modal per tahun.

Versi tanpa batasan (konteks saja): CAGR A0 / A1 / A2 = 14,1% / 21,4% / 19,3%; MDD −64% / −41% / −52%.

## Kesimpulan
- Tidak ada varian yang lolos syarat. Rugi di sebagian subperiode, dan sideways negatif di semua varian realistis.
- Meniru entry Swinger dengan eksekusi nyata tidak meniru hasilnya:
  - WR turun dari 49% ke 32–36%;
  - rugi rata-rata membesar dari −3,5% ke −5,3…−6,8%, karena beli dan jual terjadi sesudah candle sinyal;
  - biaya trade yang sering memakan sekitar 8–11% modal per tahun.
- Filter kondisi membantu: A1 > A2 > A0. Tidak membeli saat turun memperbaiki MDD dari −93% ke −69%.
- Sebagai catatan, V2 realistis lebih baik di setiap kondisi (naik +47,8%, sideways +9,7%, turun +13,1%; CAGR 20,7%).
- Petunjuk: rentang waktu 5 hari terlalu pendek untuk eksekusi nyata ditambah biaya. Langkah berikutnya yang wajar adalah
  menguji panjang swing yang lebih lama.
