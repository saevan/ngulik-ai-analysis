# Fading move vs buy-and-hold vs DCA (16 Okt 2026)

Kode `fading_move_vs_bh_dca.py`, hasil `summary.csv`, `per_ticker_lump.csv`. Sistem (STRATEGY_NOTES.md): selalu di saham; acuan = Open bar berjalan (reset tiap bar); sinyal Low ≤ Open·(1−X). Varian B (konvensi proyek, Open(i+1)): jual di Open tradable berikutnya, masuk lagi satu bar sesudahnya. Varian A (aspiratif): jual di level stop pada bar yang sama. 100 saham, 1 sleeve per saham, saham pecahan, 2000-01 s.d. 2025-08. Mode lump dan kontribusi bulanan (DCA) dengan arus kas identik untuk semua strategi. Biaya: gross 0; fees 0,15/0,25%; s10/s25/s50 = fees + slippage 0,10/0,25/0,50% per sisi. Versi pertama memakai pembulatan fraksi harga pada harga ter-adjust (biaya tersembunyi pada "gross"); ditemukan audit independen dan dibuang.

## Hasil (B, CAGR lump / XIRR DCA, pembanding B&H 14,0% / 18,0%)
- X 5%: gross 18,3% / 19,4%; fees 14,0% / 14,5%; s25 10,3% / 10,0%.
- X 8%: gross 17,6% / 18,5%; fees 16,1% / 17,3%; s25 14,9% / 16,1%; s50 13,7% / 15,1%.
- X 1–3%: gross tinggi di beberapa sel tetapi fees saja sudah ≤ 6%; dengan s25 negatif. Sinyal menyala di 57% / 33% / 19% bar, perputaran sangat tinggi.
- MDD tidak membaik untuk X ≥ 5% (−54…−69% vs B&H −59/−64%).
- DCA: tidak ada konfigurasi yang mengalahkan B&H sesudah fee.
- Lebar: dengan fee 0,15/0,25%, hanya 22 dari 100 saham (X 8%) yang mengalahkan B&H, rasio median 0,76; selisih agregat dibawa oleh ~5 saham (kontribusi ≥100%).
- Klaim "menambah lot saat turun": harga beli kembali (Open t+2) vs jual (Open t+1) rata-rata +0,04…+1,3% dan hanya 35–45% lebih rendah, jadi rata-rata membeli lebih mahal.

## Catatan
- Universe survivor (menguntungkan B&H lebih dari aturan keluar mana pun). Satu jalur historis, tanpa uji signifikansi. Varian A pada X kecil dengan fill tepat di level adalah artefak. Kontribusi DCA: MDD pada ekuitas yang terisi kontribusi hanya untuk perbandingan antar baris.
