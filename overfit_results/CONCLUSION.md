# Uji overfitting SK-5 (dan kandidat post-hoc ER 0,2 + trailing) — 17 Okt 2026

Kode `overfit_tests_sk5.py`, `overfit_noise_calibration.py`; engine `backtest_stop_execution.py` (mode kontrol `entry_mode='random'`, default
tidak berubah, regresi lulus). Periode 2000-01..2025-08, Rp1 miliar, fee 0,15/0,25% (basis Swinger), tanpa batas likuiditas kecuali disebut.
Verifikasi: PBO dan Deflated Sharpe dihitung ulang independen dan identik (selisih <1e-13). Audit kode kontrol acak/noise dan kritik tafsir
oleh pemeriksa independen gagal jalan (batas sesi); diperiksa sendiri saja.

## Hasil
| Uji | SK-5 | Lulus? |
|---|---|---|
| PBO (CSCV, 360 konfigurasi, 12.870 split) | fee 4–7%, slippage 0,25% 10–24% | ya untuk keluarga sistem* |
| Deflated Sharpe (N=360 / 6.000) | ≈1,0 (Sharpe bulanan 0,49 vs ambang 0,13–0,17) | ya untuk keluarga sistem** |
| Plateau parameter (satu per satu + channel×ER, termasuk nilai di luar grid) | 53–72% CAGR, tanpa puncak tajam | ya |
| Entry acak, exit/ukuran/biaya sama (50 seed × 2) | median 8–14%, maks 27% vs 63,2%; 0/100 menyamai | ya |
| Urutan acak dari sinyal asli (30 seed) | median 48%, maks 62% vs 63,2% | ya (urutan momentum menambah ±15 pp) |
| Bootstrap universe (80% saham, 50 draw) | p5 50,8% / 125 rekor (median 57,4% / 136) | ya |
| Tahun kalender | 0 tahun rugi (terlemah 2022 +1,7%) | ya |
| Noise harga ±0,25% per OHLC (20 draw) | 63,2→51,8% (−18%); HHV20 −5%, Swinger ideal −24% | sedang |
| Train→validasi→tes | 67,0 → 69,7 → 44,5% | turun di 2021–25 |
| Walk-forward 2008–25 | 49,3% vs 63,2% in-sample | degradasi ±22% |

*PBO rendah terutama karena HHV5 + ukuran 20% mendominasi grid. Di dalam pojok HHV5 & 20% (40 konfigurasi) PBO 0,73 (fee) / 0,53 (slippage):
memilih ER 0,3 + exit cand + exit breakout palsu di antara tetangganya tidak lebih baik dari acak. ER 0,3 bahkan lembah lokal
(ER 0,25 / 0,35 / tanpa ER lebih baik, terutama 2016–25). Berdasarkan Sharpe, SK-5 di peringkat 138/360.
**DSR ≈1 untuk semua anggota grid, termasuk yang terburuk; ini menunjukkan Sharpe keluarga sistem bukan keberuntungan seleksi, bukan bahwa
parameter SK-5 tidak overfit. Label N=6.000 memakai sebaran Sharpe dari 360 konfigurasi; bila sebaran 6.000 run lebih lebar, DSR versi
slippage bisa turun ke ±0,4. Autokorelasi bulanan 0,2 menurunkan z ±17% (tetap signifikan). Slope degradasi CSCV bersifat mekanis.

## Kandidat post-hoc ER 0,2 + trailing
Plateau dan kontrol serupa (entry acak 0/100, bootstrap p5 51,8% / 148 rekor, noise −23%, tanpa tahun rugi), tetapi dipilih sesudah melihat
semua periode, jadi hanya baris DSR N=6.000 yang relevan dan pembagian in/out-of-sample-nya tidak bersih.

## Kesimpulan
- Keluarga sistem (buy stop HHV pendek, urutan momentum, ukuran ±20%) lulus uji overfitting standar: edge-nya bukan kebetulan seleksi dan
  jauh di atas entry acak.
- Parameter spesifik SK-5 tidak lulus: di antara konfigurasi serupa, pilihannya setara undian, dan ER 0,3 bukan nilai terbaik. Harapkan
  kinerja di kisaran plateau (≈55–70% fee tanpa batas likuiditas; walk-forward 49%), bukan angka tepat 63,2%.
- Tidak bisa dideteksi uji ini: survivorship universe (tanpa saham listing ≥2018, 2021–25 turun 44,5→21,6%), snooping riset (kerangka tetap
  dipilih dari semua periode), harga ter-adjust, fill buy stop ideal, kapasitas (batas 25% ADV: ±28%). AFL tidak diubah.
