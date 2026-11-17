# Kapan V2 tertinggal dari Swinger ideal di saham? (17 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `v2_lag_when.py`. Hasil: `by_year.csv`, `by_condition.csv`,
`by_market_speed.csv`, `by_v2_positions.csv`. V2 realistis vs Swinger ideal, biaya B, 2000-01-01..2025-08-15.
CAGR 21,5% vs 107,4%; selisih log total 13,2.

- Per tahun: V2 tertinggal di 25 dari 26 tahun; hanya 2025 unggul (+93,5% vs +8,2%). Selisih terbesar:
  2003 (+100% vs +378%), 2009 (+22% vs +253%), 2001 (+10% vs +163%), 2010, 2021, 2007, 2008 (−36% vs +89%).
  Yaitu tahun pemulihan kuat sesudah krisis dan tahun krisis itu sendiri.
- Per kondisi pasar: porsi selisih naik 41% (33% hari), sideways 51% (56% hari), turun 8% (11% hari).
  Per hari, selisih paling tajam saat naik (1,24× porsi harinya). Return per tahun V2 / Swinger: naik 48% / 186%,
  sideways 10% / 79%, turun 13% / 66%. Modal terpakai V2 83% / 62% / 38% vs Swinger 96% / 94% / 82%.
- Per kecepatan pasar (return proxy 20 hari): naik cepat (kuintil teratas, median +10,5%) menyumbang 30% selisih;
  V2 +49%/th vs Swinger +236%/th. Kuintil lain masing-masing 16–20%.
- Per jumlah posisi V2: 0–2 posisi (8% hari) 9% selisih; 3–6 posisi (52% hari) 54%; 7+ posisi (41% hari) 38%.
  Selisih tidak hanya dari kas menganggur; saat penuh pun V2 tertinggal (40% vs 129%/th).
- Pengingat (`v2_gap_results`): selisih saat sideways/turun sebagian besar bonus fill ideal; trade Swinger yang
  terlewat hanya bernilai nyata saat pasar naik (+2,7%/trade, +4,7% di saham ER ≥ 0,2).

## Addendum: kenapa V2 menang di 2025? (`v2_2025_why.py`, `y2025_*.csv`)
2025 = 1 Jan..15 Agu. V2 realistis +93,5%, Swinger ideal +8,2%, pasar EW sekitar +10%.
- Satu posisi menentukan: WIFI dari modul bulanan (beli 2 Sep 2024, masih dipegang 15 Agu 2025, 225 bar, +880% per
  trade) menyumbang +68,9% dari ekuitas awal 2025, yaitu 74% dari kenaikan tahun itu. Tanpa WIFI: +24,6%.
  Tanpa 3 posisi teratas (WIFI, BRPT +37,8%, ENRG +36,4%): −0,7%. Tanpa 5 teratas: −14,6%.
- Modul bulanan +74,1% (WIFI dan PTRO, keduanya dipegang sejak 2024), breakout +19,2%.
- 16 posisi aktif di 2025, WR 31%, median −4,6%. Polanya sama dengan tahun lain: sedikit pemenang raksasa.
- Swinger ideal: 127 trade, WR 27%, median −2,0%; tanpa 3 teratas −9,2%. Swinger hanya sekali masuk WIFI (18 bar):
  exit 5 hari-nya tidak bisa memegang tren panjang.
- Per bulan: Jan +27,1% dan Feb +19,8% (pasar −1,4% dan −9,7%, turun/sideways), Mar −13,5% (pasar jatuh), Jul +45,4%.
  V2 naik justru saat pasar turun, karena WIFI naik sendiri.
- Catatan: WIFI listing Des 2020 dan ada di Kompas100 2025 karena sudah naik (bias survivor). Kemenangan 2025 adalah
  kemenangan satu saham tren panjang, bukan keunggulan sistem yang luas.
