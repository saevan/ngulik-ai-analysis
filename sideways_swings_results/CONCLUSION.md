# Pantulan di dalam range saat sideways (9 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `sideways_swings.py`. Hasil:
- `bounces.csv.gz`;
- `bounce_summary.csv`;
- `range_width.csv`.

Metode:
- Zigzag pada Close dengan ambang balik X.
- Low swing terkonfirmasi saat Close naik X% di atasnya; high swing terkonfirmasi saat Close turun X% di bawahnya.
- Kondisi pasar diambil pada hari low terkonfirmasi.
- Universe realistis, 2000–2025.08.

## Pantulan saat pasar sideways (semua saham)
| Ambang X | Pantulan per tahun (semua saham) | Turun sebelumnya (median) | Pantulan low → high (median / rata-rata) | Lama low → high | Yang tertangkap real time (rata-rata) | Sesudah biaya 0,9% | Trade positif |
|---|---|---|---|---|---|---|---|
| 3% | 344 | −7,1% | +7,5% / +10,2% | 4 bar | +0,2% | −0,7% | 30% |
| 5% | 201 | −10,4% | +11,2% / +15,3% | 7 bar | +0,4% | −0,5% | 32% |
| 10% | 81 | −17,7% | +21,6% / +29,4% | 17 bar | +1,5% | +0,6% (median −5,3%) | 34% |

Pembanding, ambang 10%:
- naik: tertangkap +3,8%, bersih +2,9%;
- turun: +1,7% / +0,8%.

Saham ER20 < 0,2 saat sideways mirip: tertangkap +0,1% / +0,3% / +1,3%.

Lebar range 20 hari (median):
- sideways 16,7%;
- naik 16,3%;
- turun 22,1%;
- saham ER20 < 0,2 saat sideways 14,5%.

## Observasi
- Pantulan saat sideways memang besar dan sering, dan besarnya kira-kira sama dengan penurunan sebelumnya. Kalau dilihat
  setelah kejadian, pantulan ambang 5% median +11% dalam 7 bar.
- Secara real time, low baru diketahui setelah harga naik X%, dan high baru diketahui setelah harga turun X%. Dua
  konfirmasi itu (sekitar 2X) memakan hampir seluruh pantulan: yang tertangkap hanya +0,2…+1,5% sebelum biaya.
- Ambang 10% sedikit positif rata-ratanya (+0,6% bersih), tetapi mediannya −5,3% dan hanya 34% trade positif. Ini
  sebenarnya logika ikut tren (beli setelah naik 10%), bukan menangkap pantulan. Ini deskripsi, belum diuji sebagai
  sistem (eksekusi di Close, tanpa uji signifikansi atau portofolio).
