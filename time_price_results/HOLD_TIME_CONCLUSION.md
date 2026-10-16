# Klaim: makin lama hold makin untung -> keluar hanya saat turun dari Open terbaru (16 Okt 2026)

Kode: `hold_time_study.py` (sinyal), `hold_time_portfolio.py` (66 uji), `hold_time_controls.py`, `hold_time_concentration.py`; engine `backtest_open_next.py` (opsi `fade`, `fade_profit_only`, default mati, regresi identik). Entry Close>HHV20 & ER20≥0,3, Open(i+1); portofolio 10 slot, fee + 1 fraksi + lot 100; train 2000–15, holdout 2016–25. 

## 1. Apakah hold lebih lama = untung lebih tinggi? (level sinyal, exit waktu murni, fee saja)
- Rata-rata return per trade naik dengan T (breakout train: 0,8% di T5 → 8,4% di T40 → 35,6% di T250), tetapi median datar (holdout T250: 1,8%), jadi kenaikan dibawa ekor kanan.
- Entry acak ikut naik (train T250: 35,2%), jadi sebagian besar adalah drift universe saham yang bertahan, bukan sinyal. Keunggulan breakout atas acak menyusut dengan T.
- Keuntungan per bar (log return ÷ T) puncaknya di T≈20 (breakout 0,14%/bar) lalu turun; hold lebih lama menaikkan total per trade, bukan per satuan waktu modal.

## 2. Exit hanya saat turun dari Open terbaru (portofolio)
- Fade murni jadi buy-and-hold bila d lebar: FADE_20 hanya 21 trade dalam 25 tahun, invested 99,7%, CAGR 10%. Fade ketat (3%) rugi (CAGR −11%, WR 33%).
- Fade hanya saat untung (loser tak punya exit): WR 80–92% tetapi loser ditahan 245–2.268 bar; CAGR 11–15%, MDD −50…−65%, 12–416 trade. WR tinggi itu artefak loser yang terkubur, dan dalam universe survivor mereka akhirnya pulih; di pasar nyata sebagian delisting.
- Menambah stop 3 ATR + batas 120 bar membuat CAGR 23–24% (holdout 26–33%), tetapi kontrol tanpa fade (SL3_T120: 21,1%, FADE8+SL3+T120: 18,5%) menunjukkan fade bukan penggerak; fade-hanya-untung menambah ≈3 pp, tidak konsisten antar periode.

## 3. Hold lebih lama dengan stop saja: tampak ekstrem tetapi rapuh
- SL3_T250: CAGR 44,5% (holdout 85%), WR 27,5%, payout 14,6. Top-5 trade = 124% dari laba (PANI, WIFI, TPIA, DSNG, SILO); entry acak dengan exit sama 12,6–18,6% (holdout 16–34%). Tanpa top-5, CAGR negatif atau ~0. Ini hasil beberapa multi-bagger di universe survivor, bukan bukti hold panjang selalu lebih baik.

## Kesimpulan
Klaim sebagian benar: total return per trade naik dengan lama hold dan stop+hold panjang menangkap ekor kanan. Tidak benar bahwa exit fading dari Open terbaru yang menciptakan hasil itu, dan tidak benar bahwa hold lebih lama memberi laba per waktu lebih tinggi. Hasil bergantung pada segelintir saham survivor; MDD tetap −50…−65%. 66 konfigurasi dilihat bersama sehingga ada risiko seleksi.
