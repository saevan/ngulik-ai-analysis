# Kalibrasi v3: adakah modul lebih baik dari V2 untuk mengejar Swinger ideal? (26 Okt 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `calibrate_v3.py`. Hasil: `grid.csv`, `selection.csv`.
144 konfigurasi × 2 versi. Tuas: filter swing, ER, ranking, crash guard, modul bulanan, ukuran order. Biaya B,
2000–2025.08.

**Hasil seleksi:** pilihan dari periode latih = V2 sekarang sendiri. Hanya 8 konfigurasi lolos syarat risiko, dan V2
punya CAGR latih realistis tertinggi di antaranya. Tidak ada modul yang lebih baik.

Efek tiap tuas (median CAGR atas konfigurasi lain; realistis | tanpa batasan):
| Tuas | Hasil |
|---|---|
| Filter swing | lewati swing turun 15,9% \| 39,0%; off 15,3% \| 38,4%; wajib swing naik 10,5% \| 29,5%. Hanya "lewati swing turun" sedikit positif. |
| ER breakout | 0,2: 14,7% \| 37,3%; 0,3: 14,5% \| 35,3%; 0,5: 13,7% \| 35,5%. Lebih ketat lebih buruk. |
| Ranking | mom120 15,6% \| 38,7%; ER20 13,1% \| 34,4%. mom120 lebih baik. |
| Crash guard | off 14,9% \| 37,3%; on 13,2% \| 34,5%. Menurunkan CAGR. |
| Modul bulanan | off 14,7% \| 35,5%; on 13,7% \| 37,0%. Campur. |
| Ukuran order | 25%: 14,3% \| 35,5%; 33%: 14,0% \| 37,0%. Campur. |

Catatan:
- Beberapa konfigurasi lebih tinggi di periode uji. Contoh: breakout saja dengan ukuran 33% punya CAGR realistis 21,9%
  (uji 29,1%), tanpa batasan 58,1%, MDD −25%. Tapi CAGR latihnya (17,7%) di bawah V2, jadi memilihnya sekarang sama dengan
  memilih setelah melihat hasil uji.
- Peringkat latih dan uji tidak stabil.

Jarak ke Swinger ideal tetap: V2 realistis 20,7% / 63 bulan rekor vs 102,0% / 232. Tidak ada tuas dari temuan struktur
pasar yang menutup jarak ini. Sebabnya tetap fill ideal yang tidak bisa dieksekusi, ditambah batas likuiditas.
