# Garis tengah sebagai acuan pantulan saat sideways (13 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `midline_bounce.py`. Hasil: `results_all.csv`, `summary.csv`.

Dua pembacaan "cari garis tengah dulu sebagai acuan" yang belum pernah diuji:
- B. Garis tengah pantulan: setelah pantulan dari low L ke high H (minimal 2× ambang zigzag 3% / 5%), pasang buy
  limit di (L + H) / 2 saat harga turun kembali; target H; stop Close < L (0% / −3%); batas 10 / 20 bar. 8 sel.
- C. Garis tengah range (High/Low 20 / 40 hari) sebagai acuan arah: beli di Open berikutnya saat Close memantul dari
  bawah dan menembus kembali ke atas garis tengah (saham ER20 < 0,2); target atas range; stop Close < bawah range atau
  Close kembali di bawah garis tengah; batas 10 / 20 bar. 8 sel.
Hanya saat pasar sideways, universe realistis, biaya B, 2000–2025.08. Pembacaan ketiga (garis tengah range sebagai
target) sudah diuji sebelumnya di `high_wr_range_results` dan `nested_range_results`: semua rugi.

## Hasil
| | B: tengah pantulan (8 sel) | C: tembus garis tengah range (8 sel) |
|---|---|---|
| Bersih > 0 | 0 | 0 |
| Kotor (sebelum biaya) | −0,56…−0,93% | −0,39…−1,14% |
| Bersih (biaya 0,9%) | −1,36…−1,82% | −1,24…−2,00% |
| Dengan fee pengguna 0,6% | −1,16…−1,53% | −0,99…−1,74% |
| WR vs WR impas | 46–55% vs 58–68% | 26–53% vs 41–68% |
| Trade per tahun | 87–166 | 100–212 |
| Di atas kontrol acak | 1 | 1 |

Pilihan latih:
- B (ambang 5%, 10 bar, tanpa margin stop): uji −1,57% (t −5,5) vs kontrol −0,76%; 0/4 sub-periode. GAGAL.
- C (range 20, 20 bar, stop kembali di bawah garis tengah): uji −1,39% (t −10,4) vs kontrol −1,14%; 0/4. GAGAL.

Rincian:
- B: target tercapai 31–51% trade (+4,8…+7,1%), stop 18–43% (−5,4…−9,3%), sisanya habis waktu ≈ 0. Saham choppy
  (ER20 < 0,2, 61–65% setup) −1,3…−1,8%; saham yang sedang tren −1,7…−1,9%. Keduanya rugi.
- C dengan stop "kembali di bawah garis tengah": 64–74% trade kena stop dalam 4–6 bar (bolak-balik di sekitar garis
  tengah), rugi kecil tapi sering. Dengan stop bawah range: 46–71% trade habis waktu di sekitar nol.

## Kesimpulan
- Garis tengah pantulan tidak berfungsi sebagai support: ketika harga turun kembali ke tengah pantulan, peluang
  lanjut ke high dan jebol ke low hampir seimbang, dan ruginya lebih besar dari untungnya.
- Garis tengah range tidak memberi informasi arah: harga menembusnya bolak-balik, dan menunggu konfirmasi tembus
  membuat kita membeli setelah hari naik.
- Semua pembacaan "garis tengah sebagai acuan" (target, support, arah) sudah diuji dan rugi sebelum biaya. Ini
  konsisten dengan temuan sebelumnya bahwa timing masuk di dalam range tidak lebih baik dari hari acak.
