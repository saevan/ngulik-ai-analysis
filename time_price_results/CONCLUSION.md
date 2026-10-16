# Uji klaim: gabungkan waktu dan harga agar WR 50%; entry breakout, keluar harga atau waktu (16 Okt 2026)

Kode: `time_price_study.py` (level sinyal, 1.254 baris di `grid.csv`), `time_price_portfolio.py` (portofolio 10 slot, `portfolio.csv`). Entry: Close > HHV20 dan ER20 ≥ 0,3 di Close i, beli Open berikutnya; exit dinilai di Close, terisi Open berikutnya. Level sinyal: fee 0,15/0,25% tanpa spread, sinyal saling tumpang tindih. Portofolio: fee + 1 fraksi per sisi + lot 100. Train 2000–2015, holdout 2016–2025 (tidak dipakai memilih). Diverifikasi 3 pemeriksa independen (hitung ulang cocok ≤0,1 pp WR; tidak ada look-ahead).

## Hasil
1. WR ≥ 50% mudah dicapai di level sinyal (185 dari 418 sel), tetapi lewat target harga ia dibeli dengan payout < 1 (median payout 0,88).
2. Gabungan stop + target + waktu: WR 52–58% dengan payout 0,9–1,2. Di portofolio dengan spread CAGR −6% s.d. +1% (SL3_TP3_T40 WR 52,7%, payout 0,90, CAGR −2,1%). Gabungan tidak lebih baik dari komponennya.
3. Yang positif adalah exit waktu murni: T40 WR 50,4%, payout 1,61, CAGR 18,6%, MDD −59,6%; SL3_T40 WR 44,6%, payout 1,86, CAGR 18,6%, MDD −52%. WR 50% hanya T40 saja, dan di holdout 46%.
4. Entry acak dengan exit sama jauh lebih buruk (T40: CAGR 2,8%), jadi sinyal breakout membawa edge; WR acak ~46–52% di level sinyal dijelaskan struktur exit + drift universe survivor.

## Catatan
- Kontrol acak: frekuensi ~6% terlalu tinggi dan seed antar-ticker berkorelasi; tidak dicocokkan rezim.
- Survivorship bias universe; angka level sinyal tanpa spread sehingga terlalu optimistis untuk exit ketat.
- Belum diuji: MDD ~−52…−60% jauh lebih dalam dari sistem aktif (UTS −31%), jadi ini bukan penggantinya.
