# Sistem baru dari nol untuk 7 kriteria (15 Oktober 2026)

Kode: `new_system_search.py` (tahap 1, 1152 konfigurasi), `new_system_stage2.py` (tahap 2, 288 konfigurasi). Semua sinyal di Close i, fill di Open i+1 tradable (kriteria 7). Statistik per trade, setelah biaya: saham beli 0,15% jual 0,25%; forex 0,015% per sisi; crypto 0,1% per sisi. Satu posisi per instrumen (statistik trade, belum portofolio). Trade yang masih terbuka di akhir data ditutup di Close terakhir (tidak dibuang).

Definisi kriteria (dikunci sebelum pencarian):
1. mean ≥ 2× median dan mean − median ≥ 1 pp, mean > 0
2. rata-rata bar trade menang > rata-rata bar trade kalah
3. payout (avg win / avg loss) > 2
4. WR > 50%
5. expectancy > 0 dan profit factor > 1
6. universal: 1–5 lolos terpisah di saham, forex, crypto
7. eksekusi Open(i+1): dipenuhi oleh konstruksi

Pencarian HANYA di saham 2000–2015. Saham 2016–2025, forex (9 pair, Mei 2023–Mei 2026, sesi harian jam 00) dan crypto (8 koin Binance 2017–2025) tidak dipakai memilih.

## Tahap 1: keluarga entry × exit
Entry: pullback RSI2 dalam uptrend, new-low 5 hari di atas SMA200, dip ke bawah SMA10 dengan SMA50>SMA200, breakout HHV20+ER, breakout HHV55. Exit: stop Close ≤ entry − s ATR, time stop rugi, trailing aktif sesudah +a ATR, max hold.
- Tidak ada yang 5/5. WR >50% bersama payout >2 hanya muncul bila trade rugi tidak di-stop (ditahan sampai pulih), tetapi itu melanggar kriteria 2 (bar rugi 120–200 > bar menang).
- Mendekati: breakout HHV55 + stop 2 ATR + trailing 2 ATR sesudah +2 ATR (WR 49,8%, payout 2,01, bar menang 24 > bar kalah 13).

## Tahap 2: breakout + stop ATR + trailing teraktivasi
15 konfigurasi lolos 5/5 di saham 2000–2015. Teratas: **Close > HHV55 sebelumnya; stop Close ≤ entry − 3 ATR14; trailing aktif sesudah peak Close ≥ entry + 2 ATR, keluar saat Close ≤ peak − 2,5 ATR; eksekusi Open berikutnya.**

| Data | Trade | Mean | Median | WR | Payout | Bar menang / kalah | PF | Lolos 1–5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Saham 2000–15 (train) | 1876 | 5.69% | 1.09% | 53.8% | 2.03 | 33.2 / 21.3 | 2.37 | 5/5 |
| Saham 2016–25 | 1598 | 3.08% | −0.93% | 47.4% | 1.78 | 35.6 / 23.7 | 1.61 | 3/5 |
| Crypto 2017–25 | 189 | 16.69% | 5.07% | 57.7% | 2.30 | 28.9 / 24.7 | 3.14 | 5/5 |
| Forex 2023–26 | 72 | −0.11% | −0.33% | 41.7% | 1.23 | 60.7 / 27.6 | 0.88 | 1/5 |

Top-5 lainnya berpola sama: crypto 5/5, saham 2016–25 3/5 (WR 47–48%, payout 1,76–1,92), forex 1/5.

## Kesimpulan
- **Belum ada sistem yang memenuhi 7/7.** Kandidat terbaik lolos 5/5 di data pencarian dan di crypto (independen), tetapi gagal WR dan payout di saham 2016–2025 dan gagal di forex.
- Observasi: WR >50% dan payout >2 dan rugi lebih pendek dari menang hanya bisa bersamaan bila trend kuat (saham 2000–2015, crypto). Di periode/pasar yang lebih choppy (saham 2016–25, forex 2023–26) WR turun di bawah 50%.
- Forex hanya 3 tahun (≈70 trade per konfigurasi); ini sampel kecil, bukan bukti kuat gagal atau berhasil.
- Belum diuji: portofolio 10 slot/compounding (CAGR, bulan rekor), stress spread tick saham, biaya forex riil. AFL tidak diubah.
