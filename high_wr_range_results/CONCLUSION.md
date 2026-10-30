# Beli di bawah range untuk win rate ~70% (30 Okt 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `high_wr_range.py`. Hasil: `results_all.csv` (semua periode),
`summary.csv` (ringkasan per sel).

Setup: saham choppy (ER20 sendiri < 0,2), lebar range 20 bar 10–40%, Close di 20% bawah range. Beli di Open besok.
- Target: +2% / +3% / +5% atau tengah range.
- Stop: tanpa stop / Close < low range × 0,95 / Close < entry × 0,90.
- Batas waktu: 5 / 10 / 20 bar.
- Total 36 sel. Versi realistis, biaya B 0,90% pp, 2000-01-01..2025-08-15.
- Satu posisi per saham, level trade (belum portofolio).
- Kontrol: hari acak di kondisi choppy + lebar yang sama, Close di separuh bawah range.

## Hasil
Win rate 70%+ bisa dicapai, tetapi semua 36 sel tetap rugi bersih:
- WR 45–83%. Sel dengan WR ≥ 70%: target +2% (waktu 10/20 bar) dan target +3% dengan 20 bar.
- WR impas 61–92%. Setiap sel berada 9–17 poin di bawah WR impasnya.
- Contoh WR tertinggi (target +2%, tanpa stop, 20 bar):
  - WR 82,6%, padahal WR impas 92%;
  - rata-rata menang +2,0% vs kalah −12,0%.
- Bersih per trade −1,4…−1,9% (log return; t penuh −3,9…−16). Dengan return biasa −1,1…−1,5%.
- Sebelum biaya pun rugi: kotor (return biasa) −0,2…−0,6%. Dengan fee pengguna 0,60% tanpa slippage tetap rugi.
- Kontrol acak (separuh bawah range) hasilnya sama (−1,2…−1,8%). Posisi di 20% bawah range tidak memberi keunggulan.

Pilihan dari periode latih (WR latih ≥ 65%, bersih latih tertinggi): target +3%, tanpa stop, 10 bar.
- Latih 2000–15: WR 68,4%, bersih −1,40%.
- Uji 2016–25: WR 66,3%, bersih −1,60% (t −8,4).
- 0 dari 4 subperiode positif.
- GAGAL semua syarat kecuali WR.

## Kesimpulan
- Mengejar WR tinggi dengan target kecil hanya memindahkan masalah. WR naik karena trade yang belum kena target ditahan
  lebih lama, sehingga kerugiannya juga membesar.
- Yang menentukan adalah WR di atas WR impas: (rata-rata kalah + biaya) / (rata-rata menang + rata-rata kalah). WR 70%
  dengan menang +2% dan kalah −8% butuh WR impas sekitar 89%.
- Bawah range saham choppy bukan support: saham yang tidak memantul terus turun. Ini konsisten dengan uji sebelumnya.
  Batas range tidak dihormati lebih dari acak; sifat nyata hanya di atas range (resistance), dan itu hanya bisa dipakai
  dengan short.
- Modul beli-di-bawah-range tidak bisa jadi Logic 2 dengan data harian saham, baik dengan biaya B maupun dengan fee
  pengguna.

Catatan: hasil di level trade, data survivor (100 saham Kompas100 saat ini). Bias survivor membuat "beli murah" terlihat
lebih baik dari sebenarnya, jadi hasil nyata kemungkinan lebih buruk.

## Addendum: apakah sahamnya kurang choppy? (`high_wr_range_choppy_check.py`, `choppy_check.csv`)
Diuji pada dua sel: pilihan latih (+3%, tanpa stop, 10 bar) dan WR tertinggi (+2%, tanpa stop, 20 bar), 2000–2025.

Tidak ada kelompok yang untung. Bersih per trade:

| Kelompok | +3%, 10 bar | +2%, 20 bar |
|---|---|---|
| Market sideways / naik / turun | −1,5% / −1,1% / −1,5% | −1,3% / −1,3% / −1,6% |
| ER20 < 0,1 vs 0,1–0,2 | −1,4% / −1,4% | −1,2% / −1,5% |
| Choppy 21 hari berturut-turut (111/121 trade) | −1,4% | −1,7% |
| ER60 < 0,2 juga | −1,4% | −1,3% |

Sesudah entry (melihat masa depan, hanya deskripsi):
- Close jatuh di bawah low range selama trade di 46% / 39% trade.
  - Kelompok ini: WR 34% / 56%, bersih −5,3% / −5,1%.
  - Yang tetap di dalam range: WR 96% / 99,7%, bersih +1,9% / +1,1%.
- Saham yang ER20-nya ≥ 0,3 saat exit (berubah jadi tren): 20% / 10% trade. Bersihnya −10,1% / −14,4%.

Kesimpulan:
- Sahamnya sudah choppy, dan makin choppy pun tidak membantu.
- Masalahnya, choppy diukur dari masa lalu. Itu tidak meramalkan range akan bertahan: hampir separuh trade jebol ke bawah,
  dan sebagian berubah jadi tren turun.
- Untungnya hanya ada kalau kita tahu duluan range akan bertahan. Itu tidak bisa diketahui dengan data harian. Rezim pasar
  dan tingkat/lamanya choppy tidak membedakannya.
