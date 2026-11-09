# Dua range bertingkat dengan order limit (9 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `nested_range.py`; deskripsi tambahan `nested_range_diag.py`. Hasil:
- `results_all.csv`;
- `summary.csv`;
- `exit_diagnostic.csv`.

Setup:
- Range sedang: High/Low 20 atau 40 hari, lebar 10–40%. Range kecil: High/Low 5 atau 10 hari.
- Buy limit di low range kecil; jual limit di high range kecil atau di tengah range sedang.
- Stop: Close < low range sedang (−0% / −3%). Batas waktu 10 / 20 bar.
- Opsi: low range kecil harus di separuh bawah range sedang.
- Hanya saat pasar sideways, versi realistis, biaya B, 2000–2025.08, 64 sel.

## Hasil
- 0 dari 64 sel positif, bahkan sebelum biaya:
  - kotor −0,8…−1,0%;
  - bersih −1,5…−1,7%;
  - dengan fee pengguna 0,6% tanpa slippage tetap −1,4…−1,6%.
- WR 24–42%; WR impas 43–61%.
- Pilihan latih (20/10, target tengah range, tanpa margin stop, 10 bar): uji −1,37% (t −11,7). GAGAL.
- Kontrol hari acak lebih buruk lagi (53/64 sel di atas kontrol). Syaratnya sedikit membantu, tapi semua tetap rugi.

Rincian exit (sel contoh: 20/5, target high range kecil, stop −3%, 10 bar):

| Exit | Porsi | Rata-rata | Lama (bar) |
|---|---|---|---|
| Stop (range sedang jebol) | 39% | −6,9% | 5,3 |
| Target (pantulan tertangkap) | 22% | +6,9% | 5,7 |
| Waktu habis | 40% | +0,2% | 10 |

Di 38–57% trade, hari order limit terisi juga hari Low menembus low range sedang.

## Kesimpulan
- Order limit di bawah harga tidak perlu menunggu konfirmasi, tetapi terkena seleksi merugikan (adverse selection): order
  terisi terutama saat harga sedang jatuh menembus range.
- Pantulan penuh (+6,9…+8,7%) hanya tertangkap di sekitar 22–34% trade. Jebol (−6…−7,5%) terjadi di 39–46% trade.
- Range bertingkat dari High/Low N hari tidak menghasilkan Logic 2.
