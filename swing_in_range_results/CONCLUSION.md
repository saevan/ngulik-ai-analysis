# Swing trading yang bisa dieksekusi di dalam sideways sedang/besar (30 Okt 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `swing_in_range.py`. Hasil: `results.csv`, `trades.csv.gz`.
Saham choppy (ER20 < 0,2) dengan range 20 bar 10–20% / 20–40% / 10–40%. Buy stop di high 5 bar, jual stop di low 5 bar
(ditambah varian take profit di high range). Versi realistis, biaya B, 2000–2025.08.

Hasil: semua 12 sel rugi.
- Kotor per trade −0,07…−0,61%, sama dengan entry acak (kontrol −0,13…−0,45%).
- Bersih −1,0…−1,5% (t −2,7…−14). Negatif di hampir semua subperiode; hanya 20–40% di 2016–20 positif.
- Win rate 27–39%. Menang +4…+10%, kalah −2,8…−4,8%.

Kesimpulan:
- Range sideways bisa kita lihat secara real time, tapi cara masuk yang bisa dieksekusi tidak punya keunggulan atas acak.
- Laba Swinger ideal di range 10–40% (+5…+9%/trade) hampir seluruhnya dari fill idealnya (sekitar +5,4%/trade).
- Tidak ada modul yang diadopsi.
