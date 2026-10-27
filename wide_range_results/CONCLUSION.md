# Range lebih lebar / lebih panjang: adakah yang tidak tergerus biaya? (27 Okt 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `wide_range.py` (grid 64 sel), `wide_range_confirm.py` (konfirmasi).
Hasil: `results.csv`, `confirm.csv`.

Setup: saham choppy (ER sendiri < 0,3) dengan range N hari (20/60/120/250) dan lebar range 10–20 / 20–40 / 40–80 / > 80%.
Beli di Open besok saat Close di 20% bawah range. Target: tengah atau zona atas range. Ada varian dengan stop dan tanpa
stop. Versi realistis, biaya B.

## Hasil grid (64 sel): tidak ada yang lolos
- Range 10–40% (semua N): rugi sebelum biaya (−0,4…−1,8% kotor per trade).
- Range 40–80% pada N 60–250: sekitar nol atau rugi.
- Range sangat lebar (> 80%) pada N 60–250: kotor +2…+5,6%. Tapi kontrol acak (setengah bawah range, saham sama) juga
  +2…+3,4%, t ≤ 1,5, trade sedikit, dan rugi rata-rata −13…−29%. Ini saham yang habis jatuh/melonjak tajam, bukan range
  sideways.
- Kandidat: N = 20, lebar 40–80%, tanpa stop. Bersih +1,7…+2,1%/trade, t 1,7–2,0, positif di 4/4 periode, median trade
  +3,9%, sekitar 8,6 trade/th, masih positif tanpa 3 saham teratas.

## Konfirmasi kandidat (rencana dikunci): tidak diterima
| Cek | Hasil |
|---|---|
| Holdout 1995–99 | +0,74% per trade (rata-rata kejadian), tapi seri harian −0,92% (t −0,4). Lemah. |
| Tetangga (N 15/20/30 × lebar 30–60 / 40–80 / 50–100%) | Hanya 2 dari 9 positif (hanya N = 20 dengan lebar ≥ 40%). Median t −0,6. **Gagal.** |
| 2021–25 | +2,9% (t 1,8). Lolos. |

Kandidat hanya muncul di satu panjang range (20 hari). N = 15 dan N = 30 rugi, jadi ini tepi pisau, kemungkinan
kebetulan.

## Kesimpulan
- Range yang lebih lebar memang memberi gerakan besar per trade, tapi tidak memberi edge yang kokoh.
- Range lebar sebagian besar adalah saham yang habis jatuh. Membeli bagian bawahnya adalah jenis trade yang paling
  "dibantu" oleh bias survivor (saham yang jatuh lalu delisting tidak ada di data).
- Tidak ada modul range yang diadopsi. AFL tidak diubah.
