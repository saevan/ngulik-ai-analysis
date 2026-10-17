# Mengejar Swinger ideal dengan eksekusi yang dikoreksi (17 Okt 2026, v2)

Kode `search_realistic_chase_v2.py`; engine `backtest_stop_execution.py` (touch_fill, touch_sell, stop_buffer+buffer_grid, order book pra-Open
untuk semua keluarga; default lama tidak berubah, regresi lulus). 1.536 konfigurasi, aturan seleksi dikunci (PLAN/FROZEN di-commit sebelum evaluasi).
Diverifikasi 3 pemeriksa independen: simulasi independen identik trade per trade; sisa bias eksekusi (grid tick, fill di Open, jual saat
auto-reject bawah, kas pra-Open) gabungan −1…−3 pp; kapasitas adalah sumber optimisme terbesar.
Skenario: A fee 0,15/0,25%; B A + slippage 0,25%/sisi; C B + beli ≤ 25% ADV20; D A + 0,5%/sisi. Rekor = bulan dengan ekuitas harian tertinggi baru.

## Jawaban
Tidak ada sistem kausal yang mendekati Swinger ideal pada bulan rekor di periode mana pun, atau pada CAGR 2000–25. Pada ukuran 10% seperti
Swinger, tidak ada konfigurasi yang mengalahkan CAGR Swinger di periode mana pun. Fill Swinger ideal (di level TSL pada bar sinyal) tidak kausal.

## Pilihan utama (aturan train, skenario B, tiap periode mulai Rp1 miliar)
Buy stop 0,5% di atas HHV20 (dibulatkan ke grid harga), ER20 bar sebelumnya ≥ 0,2, urutan momentum 120/20, aturan gap 2%, exit di Open berikutnya
saat breakout gagal / fading ≥ 2 ATR / Close < SMA30, 25% ekuitas per order (ukuran terbesar yang diuji; Swinger 10%).
| Periode | Pilihan utama | Swinger ideal (biaya sama, start baru) |
|---|---|---|
| 2000–15 (periode seleksi) | 40,1% · 74/192 · −23% | 116,7% · 145/192 |
| 2016–20 | 79,2% · 29/60 · −23% | 91,8% · 45/60 |
| 2021–25 | 54,1% · 20/56 · −24% | 65,7% · 42/56 |
| 2000–25 | 49,3% · 119/308 · −24% | 102,0% · 232/308 |
| 2000–25, ukuran 10% | 32,3% · 116/308 · −27% | |
| 2000–25, fee saja | 55,3% · 134/308 · −23% | 114,8% · 249/308 |
| 2000–25, slippage 0,5% (D) | 44,7% · 113/308 · −26% | |
| 2000–25, beli ≤ 25% ADV20 (C) | 25,3% · 79/308 · −36% | 28,6% · 175/308 · −14% |
| Walk-forward 2008–25 (B) | 38,6% · 65/212 · −54% | 83,4% · 161/212 · −21% |
| Tanpa 20 saham listing ≥2018: 2000–25 / 2021–25 | 41,6% · 106 / 16,9% · 8 | 98,3% · 227 / 50,9% · 39 |

## Batasan penting
- 2016–25 bukan out-of-sample bersih: hasil v1 konfigurasi ini sudah terlihat sebelum pembekuan v2, bagian tetap (momentum, aturan gap) dipilih
  sesudah melihat 2016–25, dan ±40.000 backtest sudah dijalankan pada data ini sejak 16 Okt.
- 2021–25 bertumpu pada 2021 (+235%; 2022–25 ±24%/tahun) dan pada saham listing ≥2018 (80% laba; WIFI dan PANI 67%). 80 saham lain pun survivor 2025.
- Walk-forward: bagian 2016–25 adalah pilihan utama itu sendiri; 2008–15 hanya 11,2%/tahun; MDD −54% dari konfigurasi breakout-terkonfirmasi-Close
  yang dipilih di fold 2011.
- Kapasitas: tanpa batas, order melampaui seluruh nilai transaksi harian sejak ±2010 (akhir Rp28,9 triliun); angka A/B adalah seri return akun kecil.
- Tetangga pilihan hanya 8 (di tepi grid); 2021–25 berkisar 31,5–78,0%.

## Pola lintas konfigurasi (hipotesis, bukan aturan)
- 2016–25: buy stop dengan buffer mengalahkan breakout-terkonfirmasi-Close + Open berikutnya (99,7% pasangan); tanpa buffer kalah di 2000–15.
- Buffer 0,5–1%: +2,5…+4 pp (71–77% pasangan).
- Channel 5–20 setara; channel 3 lebih buruk.
- Filter ER berbalik arah (0,3 terbaik 2000–15; tanpa/0,2 terbaik 2016–25).
- Exit Close-signal mengalahkan stop LLV5, tetapi tidak LLV10 pada CAGR 2021–25.
- Exit breakout-gagal di pilihan utama menurunkan CAGR di sebagian besar pasangan (tanpa itu: 73,1% / 78,0% di 2016–20 / 2021–25).
- Ukuran posisi adalah tuas CAGR terbesar (1/4 vs 1/10: +26…+29 pp, MDD −7,6 pp).
Uji berikut: universe point-in-time (termasuk delisting) atau forward test sesudah 2025-08-15, dengan batas likuiditas sesuai modal. AFL tidak diubah.
