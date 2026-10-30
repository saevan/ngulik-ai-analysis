# Penurunan dan pantulan saat saham sideways (30 Okt 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `decline_bounce.py`. Hasil: `anatomy.csv`, `realtime.csv`.
Universe realistis, 2000–2025.08. Saham sideways = ER20 < 0,2 di awal penurunan.

## 1. Anatomi ayunan (pivot ±3 bar; titik terendah diketahui setelah kejadian)
| Penurunan (high → low) | Kejadian | Lama turun | Pantulan median (dari low) | Pulih ≥ separuh | Pulih penuh / high baru |
|---|---|---|---|---|---|
| 0–5% | 2.375 | 3 bar | 5,3% | 98% | 80% |
| 5–10% | 3.673 | 4 bar | 7,8% | 92% | 53% |
| 10–15% | 1.630 | 6 bar | 10,2% | 79% | 30% |
| 15–20% | 784 | 8 bar | 12,4% | 64% | 20% |
| 20–30% | 493 | 10 bar | 16,6% | 53% | 10% |
| > 30% | 217 | 12 bar | 29,6% | 48% | 6% |

Saham tidak sideways: polanya hampir sama.

Pembanding jalur acak (bar harian saham yang sama diacak urutannya):
- Penurunan kecil: pantulan di data nyata lebih kecil dari acak (median rasio 1,4 vs 2,3 untuk 0–5%).
- Penurunan besar: pantulan lebih besar dari acak (> 30%: 29,6% vs 18,6%).

Ini terutama efek volatilitas berkelompok (penurunan besar terjadi di masa bergejolak, jadi pantulannya juga besar).
Survivorship juga ikut berperan (saham yang jatuh lalu delisting tidak ada di data).

## 2. Versi real time: Close pertama yang X% di bawah high 20 hari, saham sideways, beli di Open besok
| X | Kejadian | 10 hari: naik maks / turun maks / return | Hari acak: naik maks / turun maks / return | Selisih return (t) |
|---|---|---|---|---|
| 5% | 7.483 | +5,9% / −5,6% / +0,3% | +5,9% / −5,6% / +0,2% | +0,1% (1,0) |
| 10% | 4.175 | +6,9% / −7,1% / −0,1% | +6,5% / −6,0% / +0,2% | −0,4% (−1,6) |
| 15% | 1.630 | +8,4% / −8,2% / +0,1% | +6,9% / −6,4% / +0,4% | −0,3% (−1,0) |
| 20% | 601 | +10,6% / −8,6% / +1,1% | +7,1% / −6,8% / −0,1% | +1,2% (1,4) |

Untuk 20 hari, selisihnya −0,4…+1,4% (t ≤ 1,3).

## Kesimpulan
- Ukuran pantulan sebanding dengan ukuran penurunan.
- Tapi pantulan diukur dari titik terendah yang hanya diketahui setelah kejadian.
- Secara real time, setelah turun X%, naik maksimum dan turun maksimum ke depan sama-sama membesar (volatilitas). Arahnya
  tidak lebih baik dari hari acak.
- Membeli setelah penurunan tidak memberi keunggulan yang signifikan.
- Penurunan ≥ 20% sedikit positif (+1,2%), tapi tidak signifikan dan hanya sekitar 24 kejadian per tahun.
