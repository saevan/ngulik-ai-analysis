# Mengikuti karakter Swinger ideal (WR >50%, rugi kecil) (15 Oktober 2026)

Benchmark: Swinger ideal fee-only full 2000–2025: CAGR 114,77%, 249/308 bulan rekor, WR 51,9%, avg win 16,5%, avg loss 3,2%, payout 5,17, rugi >10% 1,5%, hold 19 bar, modal terpakai 93%.

Basis: kandidat (buy stop HHV20 + lewati gap up 2% + jual Close saat gap down 2% + mom120, fade2, SMA30). Tuas (48 konfigurasi): take profit limit di entry + 3/5/8 ATR; stop breakeven sesudah +1/+2 ATR; trailing LLV5 sesudah +2 ATR; channel 20/10. Seleksi di train dengan FEE (basis biaya sama dengan Swinger ideal): WR >50% DAN CAGR > base DAN rekor ≥ base. Kode `match_swinger_ideal_character.py`; regresi base persis lulus.

## Hasil

Pilihan beku: **channel 10 + trailing LLV5 sesudah +2 ATR** (train fee WR 52,2%).

| Window | Base fee | Frozen fee | Base spread1 | Frozen spread1 |
|---|---|---|---|---|
| train | 51.0% / 84 / WR 48.3% | 58.1% / 103 / WR 52.2% | 27.6% / 63 | 17.0% / 55 |
| validation | 54.0% / 29 / WR 44.5% | 60.6% / 29 / WR 47.3% | 37.2% / 25 | 29.5% / 19 |
| test | 38.9% / 25 / WR 39.8% | 42.7% / 26 / WR 42.2% | 24.1% / 18 | 17.0% / 10 |
| full | 48.5% / 136 / WR 45.4% | 56.6% / 157 / WR 48.9% | 28.1% / 100 | 20.2% / 78 |

Frozen (full fee): avg win 12,3%, avg loss 5,2%, payout 2,35, rugi >10% 7,7%, hold 12,4 bar, 3910 trade. Dengan fee lebih baik di semua window. WR >50% hanya tercapai di train. Dengan spread lebih buruk.

## Apakah WR >50% membuat performa ikut naik? Tidak.

- WR >50% bisa dicapai: take profit 3 ATR → WR full 56,7% (fee). Tetapi CAGR turun ke 35,0% (base 48,5%) dan payout jatuh ke 1,23 karena avg win terpotong menjadi 9%. Avg loss tidak ikut mengecil (7,3%).
- Dari 12 konfigurasi dengan WR full >50% (fee), hanya 1 yang mengalahkan base. Rata-rata CAGR-nya 39,3%. Di test tidak ada konfigurasi yang WR-nya >50%.
- Korelasi lintas 48 konfigurasi (full fee): WR vs CAGR −0,19; avg loss vs CAGR −0,28; **payout vs CAGR +0,44**. Yang menaikkan hasil adalah rasio menang/kalah, bukan WR.
- Avg loss terkecil yang bisa dicapai ±3,7–4,1% (dengan breakeven), tidak sampai 3,2%, karena stop sering kena gap.

## Kenapa Swinger ideal bisa WR 52% dan rugi 3,2% sekaligus

Aturan Swinger yang sama dengan eksekusi nyata menghasilkan WR 34,4% dan rugi 5,9% (next Open), atau WR 29,2% dan rugi 3,0% (stop order). Kombinasi WR tinggi DAN rugi kecil (payout 5,2) hanya muncul dengan fill ideal di level sinyal bar yang sama (12,8% entry di bawah Low, 16,9% exit di atas High hari itu). Itu karakter fill, bukan karakter aturan, sehingga tidak dapat ditiru dengan order kausal.

## Kesimpulan

Target karakter yang dapat ditiru dan memang membantu (dengan fee): trade lebih banyak dan lebih pendek (channel 10), mengunci profit sesudah +2 ATR. Mengejar WR >50% dengan take profit merusak CAGR dan bulan rekor. Varian frozen hanya unggul jika biaya eksekusi riil mendekati fee-only. Data sudah pernah dilihat; AFL tidak diubah.
