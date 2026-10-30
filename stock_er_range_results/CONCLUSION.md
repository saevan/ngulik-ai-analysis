# Range menurut ER masing-masing saham (30 Okt 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `stock_er_range.py`. Hasil: `movement.csv`, `first_passage.csv`,
`trades_by_class.csv`. Universe realistis, 2000–2025.08.

1. **Gerak saham.** Saham choppy (ER20 sendiri < 0,2) hanya sedikit lebih tenang: |return| harian 1,75% vs 2,26% untuk
   saham trending; ATR 3,6% vs 3,9%. Separuh hari-saham berstatus choppy.
2. **Bawah range (support).** Setelah Close dekat low 20 hari, peluang kembali ke tengah dulu sama dengan jalur acak saham
   itu sendiri di semua kelas:

   | Kelas ER saham | Peluang ke tengah dulu | Jalur acak | t |
   |---|---|---|---|
   | Choppy | 31,4% | 30,5% | 0,3 |
   | 0,2–0,3 | 27,6% | 27,9% | −0,6 |
   | Trending | 20,9% | 18,7% | 0,9 |

   Support tidak nyata, juga di saham choppy dan juga saat pasar sideways.
3. **Atas range (resistance).** Saham choppy yang Close dekat high 20 hari lebih sering turun ke tengah dulu:

   | Kelas ER saham | Peluang turun ke tengah dulu | Jalur acak | Selisih | t |
   |---|---|---|---|---|
   | Choppy | 35,8% | 30,6% | +6,3 pp | 5,0 |
   | 0,2–0,3 | 32,2% | 27,7% | +4,8 pp | 3,7 |
   | Trending | – | – | +1,6 pp | 1,8 |

   Resistance di atas range nyata pada saham choppy.
4. **Trade beli di bawah range** (target tengah, stop low − 1 ATR, maksimal 10 bar): rugi di semua kelas dan semua
   periode. Bersih −1,5% (choppy), −1,7% (0,2–0,3), −1,0% (trending); t −4…−8.

Kesimpulan:
- Melihat ER per saham tidak mengubah hasil untuk posisi beli: bagian bawah range tidak memantul lebih dari acak.
- Satu-satunya sifat range yang nyata ada di sisi atas saham choppy (lebih sering balik turun). Ini hanya bisa dipakai
  untuk short (terbatas di IDX), untuk menghindari membeli saham choppy di dekat high (sudah dilakukan filter ER), atau
  sebagai aturan jual. Aturan jual belum diuji.
- AFL tidak diubah.
