# Pantulan saat ER saham bilang choppy (13 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `choppy_bounces.py`. Hasil: `bounce_by_er.csv`,
`histogram_choppy_3pct.csv`, `bounces.csv.gz`. Deskriptif, tanpa aturan trading.

Pantulan = kaki naik zigzag Close dengan ambang balik 3% / 5% / 10%, dari swing low ke swing high. Label diambil di bar
saat low terkonfirmasi (momen real time pertama). Universe realistis, 2000–2025.08. Choppy = ER20 saham < 0,2.

## Saham choppy (ER20 < 0,2), semua kondisi pasar
| Ambang | Pantulan per saham per tahun | Turun sebelumnya | Pantulan p25 / median / p75 / p90 | ≥ 5% / ≥ 10% / ≥ 20% | Lama (bar) | Dalam ATR14 | Terhadap lebar range 20 hari | Pulih ke high sebelumnya |
|---|---|---|---|---|---|---|---|---|
| 3% | 20,9 | −7,0% | 4,8 / 7,4 / 12,3 / 19,3% | 72% / 34% / 9% | 4 | 2,0× | 47% | 50% |
| 5% | 12,6 | −10,1% | 7,5 / 11,2 / 18,5 / 28,4% | 100% / 57% / 22% | 8 | 2,8× | 66% | 50% |
| 10% | 5,2 | −17,9% | 14,5 / 21,4 / 34,6 / 54,0% | 100% / 100% / 54% | 16 | 4,7× | 104% | 47% |

Choppy + pasar sideways (62.974 hari saham): angkanya sama (median 7,3% / 10,9% / 21,2%; 20,9 / 12,9 / 5,4 per tahun).

Sebaran ukuran pantulan, ambang 3%, saham choppy (8.187 pantulan):
| Ukuran | Porsi | Lama (bar) | Tangkapan real time bersih (rata-rata) | Positif |
|---|---|---|---|---|
| 3–5% | 27% | 2 | −5,0% | 0% |
| 5–7% | 20% | 3 | −4,1% | 0% |
| 7–10% | 19% | 5 | −2,6% | 14% |
| 10–15% | 17% | 7 | +0,5% | 65% |
| 15–20% | 8% | 9 | +4,8% | 90% |
| > 20% | 9% | 11 | +14,6% | 97% |

## Pembanding: saham yang sedang tren (ER20 ≥ 0,3)
| Ambang | Per tahun | Median pantulan | p90 | ≥ 20% |
|---|---|---|---|---|
| 3% | 17,7 | 8,7% | 24,4% | 15% |
| 5% | 9,0 | 13,6% | 36,2% | 31% |
| 10% | 3,0 | 26,8% | 62,4% | 65% |

## Tangkapan real time (Close saat low terkonfirmasi → Close saat high terkonfirmasi), saham choppy
| Ambang | Median | Rata-rata bersih (biaya 0,9%) | Positif |
|---|---|---|---|
| 3% | −2,3% | −0,9% | 30% |
| 5% | −3,0% | −0,6% | 32% |
| 10% | −4,8% | +0,3% | 33% |

## Observasi
- Saat ER bilang choppy, pantulan memang sering: sekitar 21 pantulan ≥ 3% per saham per tahun (hampir 2 per bulan),
  13 pantulan ≥ 5%, dan 5 pantulan ≥ 10%.
- Ukurannya: biasanya 5–12% (median 7%), selesai dalam 4 hari, sebesar 2 ATR, atau separuh lebar range 20 hari.
  Satu dari tiga mencapai 10%, satu dari sepuluh mencapai 20%. Separuhnya kembali ke high sebelumnya, separuhnya tidak.
- Choppy tidak membuat pantulan lebih besar: saham yang sedang tren memantul lebih jarang tetapi lebih besar (median
  8,7% vs 7,4%; p90 24% vs 19%). ER rendah hanya berarti pantulannya lebih sering dan lebih pendek.
- Secara real time, hanya pantulan ≥ 10% (34% dari semua pantulan) yang menyisakan untung sesudah konfirmasi dua ujung.
  Saat low terkonfirmasi, pantulan 4% dan 20% terlihat sama, sehingga rata-rata tangkapannya negatif.
