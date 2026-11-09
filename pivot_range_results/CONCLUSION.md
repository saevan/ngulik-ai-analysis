# Dua range dari harga pantulan (pivot zigzag) (9 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `pivot_range.py`. Hasil: `results_all.csv`, `summary.csv`.

Setup:
- Range sedang = swing low/high terakhir zigzag 10% atau 5%. Range kecil = swing terakhir zigzag 3% atau 5%. Semua
  pivot dipakai hanya setelah terkonfirmasi.
- Buy limit di harga pantulan bawah range kecil; jual di harga pantulan atas range kecil atau di tengah range sedang.
- Stop: Close < low range sedang (−0% / −3%). Batas waktu 10 / 20 bar.
- Hanya saat pasar sideways, versi realistis, biaya B, 2000–2025.08, 24 sel.

## Hasil
- 0 dari 24 sel positif, bahkan sebelum biaya:
  - kotor −0,6…−1,5%;
  - bersih −1,3…−2,4%;
  - dengan fee pengguna 0,6% tetap −1,2…−2,1%.
- WR 24–47%; WR impas 42–65%.
- Exit:
  - target (pantulan tertangkap): 9–46% trade, +3,9…+10,2%;
  - stop (range sedang jebol): 30–77% trade, −2,4…−8,5%.
- Pilihan latih (5%/3%, target high range kecil, tanpa margin stop, 10 bar): uji −1,37% (t −11,4). GAGAL.
- Dibanding kontrol hari acak dengan mekanisme sama, hanya 15/24 sel di atasnya.

## Kesimpulan
- Harga pantulan sebelumnya tidak berfungsi sebagai support. Saat harga kembali ke sana, order limit terisi terutama
  ketika harga terus jatuh melewatinya. Ini adverse selection yang sama dengan range High/Low N hari
  (`nested_range_results`).
- Dua range bertingkat, dari High/Low maupun dari harga pantulan, tidak menghasilkan Logic 2 sideways dengan data harian.
