# Struktur dasar market IDX (Kompas100, 1994–2025.08) – `market_structure_check.py`
Bar dengan volume 0 dikeluarkan. Candle hijau = Close > Open bar itu; merah = Close < Open; datar = sama.

## Klaim pengguna: jumlah candle merah dan hijau seimbang
| Timeframe (per saham) | Hijau | Merah | Datar | Rata-rata badan hijau / merah |
|---|---|---|---|---|
| Harian | 37,3% | 42,4% | 20,3% | +2,7% / −2,2% |
| Mingguan | 44,4% | 45,1% | 10,5% | +5,7% / −4,4% |
| Bulanan | 48,3% | 47,0% | 4,7% | +12,8% / −8,8% |

Harian per periode (hijau / merah): 1994–99 32 / 30; 2000–07 35 / 31; 2008–15 40 / 41; 2016–20 38 / 48; 2021–25 38 / 51.

- Bulanan: hampir seimbang. Mingguan: hampir seimbang.
- Harian: tidak seimbang. Sejak 2016 candle merah jauh lebih banyak, karena harga cenderung turun dari Open ke Close.
- Ukuran tidak seimbang: candle hijau rata-rata lebih besar.
- Indeks equal-weight survivor tidak seimbang (hari naik 57%, bulan naik 66%) karena bias survivor dan rata-rata
  aritmetik.
- Kesimpulan: benar sebagian. Jumlah merah/hijau per saham mendekati 50/50 makin besar timeframe-nya, tapi tidak di
  harian, dan besar candle tidak seimbang.

## Struktur dasar lain yang terukur
| Struktur | Hasil |
|---|---|
| Ekor gemuk | Kurtosis harian median 9,7; gerakan > 3 sd terjadi 1,8% hari (distribusi normal: 0,27%, jadi 6,5× lebih sering) |
| Volatilitas berkelompok | Autokorelasi \|return\| lag 1 = 0,28, lag 10 = 0,12. Hari bergejolak diikuti hari bergejolak. |
| Arah harian saham tak punya ingatan | Autokorelasi return harian per saham −0,01 |
| Indeks pasar punya ingatan positif | Autokorelasi return harian indeks EW +0,14 (sebagian karena saham yang jarang ditransaksikan) |
| Hari naik vs turun | Naik 38,9% (rata-rata +2,7%), turun 42,1% (−2,5%), datar sisanya |
| Gap | Gap naik 34% hari, gap turun 23%. Gap naik > 0,5% tertutup di hari yang sama 69%; gap turun 58%. |

# Baterai struktur v3 (rencana `PLAN.md` dikunci sebelum hasil; kode `market_structure_battery.py`)
Panel Kompas100 2000–2025.08. "Abnormal" = dibanding rata-rata semua saham hari itu. t = Newey-West. Universe "all" dan
"eligible" (likuid point-in-time + data tidak basi). Ringkasan uji kejadian: `events_summary.csv`.
Catatan teknis: pandas 3 `stack()` tidak membuang NaN. Bug ini ditemukan dan diperbaiki sebelum hasil dibaca.

| # | Struktur | Hasil | Bisa dipakai? |
|---|---|---|---|
| S0 | Harga di data | Sebelum 2021, 26–41% Close bukan bilangan bulat (2021–25: 8%), jadi harga lama sudah disesuaikan (adjusted). Lonjakan split tidak mengganggu sinyal. | Info data |
| S1 | ARA / ARB (perkiraan batas) | ARA sekitar 11 kali/th. Besoknya Open gap naik 72% kasus (rata-rata +2,9%), tapi dari Open besok tidak ada kelanjutan (5 hari +1,2%, t 0,7). ARB sering di 2020–23 (batas 7%); besoknya gap turun 47%, lalu tidak ada efek. | Tidak (kenaikan terjadi di gap) |
| S2 | Struktur swing (pivot ±3 bar) | Struktur turun (LH+LL): −0,65%/20 hari vs pasar (t −4,9; negatif di 4/4 periode; eligible −0,29%, t −1,9). Struktur naik (HH+HL): +0,44% (t 3,0; 4/4). Tapi state tidak memprediksi swing berikutnya: peluang swing high berikutnya lebih tinggi 38,9% (naik) vs 38,6% (turun). Melemah di 2021–25. | Filter kecil (< biaya untuk trade sendiri) |
| S3 | Panjang dan retracement swing | Kaki naik median 4 bar / +9%. Peluang kaki berakhir sekitar 20%/bar di semua umur, jadi tanpa ingatan waktu: kaki yang sudah lama tidak lebih kuat atau lemah. Retracement dangkal → high baru (70%) hanya efek mekanis. Retracement dalam (61,8–100%) → high baru 43% vs 58% bila mekanis: kaki naik berikutnya lebih kecil. | Info: koreksi dalam = sinyal lemah |
| S4 | Squeeze volatilitas | Setelah ATR10/ATR100 di 10% terbawah, range 10 hari berikutnya justru 0,80× normal (volatilitas berkelompok, bukan meledak). Arah tidak terprediksi. | Tidak (mitos squeeze → ledakan) |
| S5 | Angka bulat (2021–25, harga sesuai fraksi) | Level …00 dan …50 sama saja: Close di atas level setelah disentuh 48% vs 48%. | Tidak ada efek angka bulat |
| S6 | High/low 60 hari sebagai resistance/support | High 60 hari justru lebih sering ditembus (55–60%) daripada level sembarang di jarak sama (52–54%). Low 60 hari yang dekat (≤ 2%) juga lebih sering jebol (56–62% vs 53–57%). | Bukan resistance/support. High cenderung tembus (mendukung breakout). |
| S7 | Posisi Close dalam range hari itu (CLV) | Close dekat Low → malam berikutnya +32 bps (2021–25 +3); Close dekat High → −32 bps (2021–25 −5). Efek cetak harga Close, mengecil sejak call auction. | Tidak (< biaya) |
| S8 | Korelasi antar saham | Rata-rata korelasi 60 hari 0,43 saat pasar turun > 10%, vs 0,23–0,25 saat normal atau naik. | Risiko: diversifikasi hilang saat crash |
| S9 | Durasi kondisi pasar | Median uptrend 3 hari, sideways 5, downtrend 3 (rata-rata 9 / 9 / 5). Naik ↔ turun selalu lewat sideways. Dari sideways: 63% ke uptrend, 37% ke downtrend. | Info: kondisi berganti cepat |
| S10 | Gap ≥ 2% | Sekitar separuh tertutup di hari yang sama, sekitar 72% dalam 5 hari. Gap naik makin sering tertutup (45% → 58% di 2021–25). | Info (v2: tidak menutup biaya) |

Kesimpulan:
- Tidak ada struktur baru yang bisa jadi trade sendiri setelah biaya B (0,9%).
- Yang berguna sebagai filter atau risiko:
  - hindari saham dengan struktur swing turun;
  - koreksi dalam (> 61,8%) = trend melemah;
  - high 60 hari cenderung tembus, bukan menahan;
  - korelasi melonjak saat crash, jadi kecilkan risiko total.
- Mitos yang tidak terbukti di data ini: squeeze → ledakan, angka bulat, high/low sebagai resistance/support, umur trend
  memberi informasi.
