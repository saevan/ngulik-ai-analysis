# Grid search filter modul bulanan: menangkap kenaikan sebelum breakout (26 Okt 2026)

Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `monthly_filter_grid.py`. Hasil: `summary.csv`, `grid.csv`.
36 kombinasi filter: trend 60/120/250 bar × ER20 saham 0/0,2/0,3/0,4 × kedekatan ke puncak 60 hari (mati / ≤5% / ≤10%
di bawah, dan belum breakout). Breakout tidak diubah. Biaya B. Periode latih 2000–2015, periode uji 2016–2025.

## Hasil
- Pilihan dari periode latih (CAGR realistis tertinggi, syarat ≥ 70% trade breakout tetap jalan) = **(120, ER 0,3, tanpa
  kedekatan), yaitu filter V1 sekarang**.
- Sel dengan CAGR latih lebih tinggi (lookback 250) gagal syarat kapasitas: hanya 56–67% breakout tersisa, dan MDD tanpa
  batasan −36…−51%.
- Tidak ditemukan filter yang lebih baik dari V1 dengan aturan seleksi ini.

| | V0 | V1 = pilihan | Rentang 36 sel |
|---|---|---|---|
| CAGR realistis latih / uji | 13,3% / 21,3% | 18,5% / 21,7% | 13,0–21,1% / 7,0–26,5% |
| MDD realistis (uji) | −44% | −34% | −28…−45% |
| CAGR tanpa batasan latih / uji | 40,0% / 66,1% | 39,3% / 56,2% | 29–41% / 48–85% |

## Apakah modul bulanan menangkap kenaikan sebelum breakout?
- 80–96% trade bulanan memang kemudian menyentuh level breakout buy stop selama dipegang.
- Tapi rata-rata harga beli bulanan hanya 1–5% lebih murah dari level breakout itu (V1: +4,0%).
- Filter "dekat puncak, belum breakout" justru memperkecil keuntungan awal ini (+1–3%), karena sahamnya sudah dekat
  level.
- Laba modul bulanan (expectancy +10…+70% per trade) terutama datang dari memegang lama (sekitar 6 bulan), bukan dari
  masuk lebih awal.

## Kesimpulan
- Filter V1 sudah yang terbaik di grid ini menurut aturan seleksi.
- "Masuk sebelum breakout" hanya menambah sekitar 4% per trade. Potensi tambahan dari mencari filter lain kecil.
- Celah dengan Swinger ideal tidak tertutup dengan cara ini.
- AFL tidak diubah.
