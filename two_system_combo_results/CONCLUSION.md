# Sistem 1 (breakout ER-gated) + sistem 2 (kebalikan sinyal, hanya saat choppy) (15 Oktober 2026)

Kode `test_two_system_combo.py`. Sistem 1: beli Close > HHV20 dan ER20 saham ≥0,3, hanya bila ER20 pasar ≥0,3 di Close sinyal; jual Close < SMA30 atau fading 2 ATR (Open bar berjalan). Sistem 2: beli = sinyal jual mentah sistem 1, hanya bila ER20 pasar <0,3; jual = sinyal beli mentah sistem 1 (breakout + ER saham). Semua eksekusi Open berikutnya, long only, Rp1 miliar, 10 slot bersama, 10% equity, compounding, sistem 1 didahulukan tiap hari, posisi dibawa melintasi pergantian rezim. Fee 0,15/0,25%; spread1 = fee + 1 tick per sisi + lot 100. Regresi: kurva sistem 1, sistem 2 dan gabungan full sama persis dengan `primary_inverse_switch_results`.

Format: CAGR / bulan rekor / MDD.

| Varian | Biaya | Train 2000–15 | Validation 2016–20 | Test 2021–25 | Full 2000–25 |
|---|---|---|---|---|---|
| Sistem 1 saja | fee | 35.5% / 67 / −39% | 23.6% / 22 / −28% | 8.1% / 5 / −21% | **27.9% / 91 / −39%** |
| Sistem 1 saja | spread1 | 20.6% / 51 / −50% | 14.5% / 21 / −34% | 2.0% / 3 / −30% | **16.0% / 65 / −50%** |
| **Gabungan (sesuai model)** | fee | 17.7% / 58 / −58% | 23.2% / 22 / −37% | 5.1% / 10 / −50% | **15.8% / 81 / −58%** |
| **Gabungan (sesuai model)** | spread1 | 4.6% / 26 / −74% | 14.8% / 15 / −39% | 1.0% / 10 / −54% | **5.5% / 36 / −74%** |
| Sistem 2 saja | fee | 3.7% / 39 | 13.6% / 27 | −0.7% / 8 | 4.8% / 63 / −66% |
| Sistem 2 saja | spread1 | −3.0% / 1 | 8.3% / 17 | −3.2% / 8 | −0.8% / 2 / −74% |
| Gabungan, sistem 2 maks 5 slot | fee | 27.3% / 58 / −44% | 26.7% / 21 / −29% | 10.5% / 7 / −32% | 25.0% / 83 / −44% |
| Gabungan, sistem 2 maks 5 slot | spread1 | 13.2% / 42 / −52% | 17.9% / 19 / −32% | 4.5% / 7 / −42% | 13.5% / 61 / −52% |
| Gabungan, sistem 2 jual saat ER pasar kembali trend | fee | 20.9% / 53 | 27.6% / 20 | 7.8% / 6 | 19.7% / 71 / −65% |
| Gabungan, sistem 2 jual saat ER pasar kembali trend | spread1 | −14.0% / 0 | 1.4% / 13 | −6.6% / 4 | −9.8% / 0 / −95% |
| Gabungan, jual sistem 2 juga butuh ER pasar ≥0,3 | fee | 20.1% / 54 | 41.6% / 27 | 7.4% / 9 | 20.0% / 82 / −63% |
| Gabungan, jual sistem 2 juga butuh ER pasar ≥0,3 | spread1 | 8.8% / 29 | 34.0% / 20 | 3.7% / 8 | 11.1% / 49 / −77% |

Diagnosis (full, gabungan sesuai model):
- Dana idle memang berputar: modal terpakai 51% → 93%.
- Tetapi sistem 2 memakai rata-rata 6,4 dari 10 slot pada hari trend, sehingga trade sistem 1 turun 1528 → 666 (posisi sistem 2 ditahan rata-rata 73,5 bar).
- Kualitas trade sistem 2: WR 64,3%, avg win 13,4%, avg loss 18,7%, payout 0,71 (fee). WR tinggi, tetapi rugi lebih besar dari menang.
- Return harian saat choppy justru turun: sistem 1 saja 15,4%/thn (posisi yang dibawa dari trend), gabungan 6,5%/thn (fee); spread 14,8% → −2,5%.

Kesimpulan:
- Gabungan sesuai model lebih buruk dari sistem 1 saja di full 2000–25 (fee 27,9% → 15,8%, rekor 91 → 81; spread 16,0% → 5,5%, rekor 65 → 36). Validation hampir sama; di test bulan rekor naik (5 → 10) tetapi CAGR turun.
- Membatasi sistem 2 maks 5 slot lebih baik dari sistem 1 saja di validation dan test (kedua biaya), tetapi lebih buruk di train dan full. Belum konsisten.
- Menjual sistem 2 saat pasar kembali trend memperpendek hold (10 bar) tetapi membuat sistem 2 rugi; dengan spread hancur.
- Masalah intinya bukan dana idle, melainkan sistem 2 sebagai kebalikan murni memiliki payout <1 dan hold panjang. Ini konsisten dengan riset sebelumnya (choppy_inverted_signal_results, optimized_inverse_regime_results).
