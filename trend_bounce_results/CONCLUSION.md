# Apakah ER lebih tinggi memberi pantulan lebih besar yang bisa dimanfaatkan? (13 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `trend_bounce.py`. Hasil: `bounce_by_er_direction.csv`,
`results_all.csv`, `summary.csv`, `pick_by_market.csv`.

## Bagian 1: ukuran pantulan menurut ER saham (deskriptif, universe realistis, 2000–2025.08)
Zigzag 3% (median / p90 / porsi ≥ 20%; arah 20 hari naik):
| ER20 saat low terkonfirmasi | Jumlah pantulan | Median | p90 | ≥ 20% | Tangkapan real time bersih |
|---|---|---|---|---|---|
| < 0,2 | 4.020 | 7,5% | 19% | 9% | −0,9% |
| 0,2–0,3 | 1.718 | 7,9% | 21% | 11% | −0,3% |
| 0,3–0,4 | 1.181 | 8,4% | 21% | 12% | −0,3% |
| 0,4–0,5 | 641 | 8,9% | 24% | 16% | −0,2% |
| ≥ 0,5 | 427 | 10,3% | 30% | 22% | +1,0% |

Zigzag 5%: median 11% (ER < 0,2) → 13% (0,3–0,4) → 14% (0,4–0,5) → 17% (≥ 0,5); p90 29% → 35% → 35% → 51%;
tangkapan bersih −0,5% → +0,7% → +0,1% → +3,4%. Arah turun memberi angka yang hampir sama dengan arah naik.
Jadi: ya, makin tinggi ER, pantulannya makin besar dan makin sering besar, secara monoton. Tapi jumlahnya makin
sedikit: pantulan ≥ 3% di saham ER ≥ 0,5 hanya sekitar 33 per tahun di seluruh 100 saham.

## Bagian 2: aturan "beli pantulan terkonfirmasi di saham ber-ER tinggi" (24 sel)
Entry Open setelah low terkonfirmasi; exit Close turun X% dari puncak atau Close < low; biaya B.

| X | Syarat ER | Arah | Trade/th | WR | WR impas | Menang / kalah | Bersih | t | Kontrol (hari acak, saham sama) |
|---|---|---|---|---|---|---|---|---|---|
| 3% | ≥ 0,2 | naik | 148 | 35% | 39% | +8,4% / −4,0% | −0,48% | −2,4 | −0,50% |
| 3% | ≥ 0,5 | naik | 16 | 36% | 34% | +11,1% / −4,5% | +0,10% | 0,2 | +0,05% |
| 5% | ≥ 0,3 | naik | 42 | 38% | 37% | +12,0% / −5,8% | −0,11% | −0,2 | −0,12% |
| 5% | ≥ 0,5 | naik | 5,7 | 40% | 33% | +17,0% / −7,0% | +1,37% | 1,0 | +0,70% |
| 5% | ≥ 0,5 | bebas (pilihan latih) | 12,6 | 45% | 37% | +14,7% / −7,2% | +0,83% | 0,9 | −0,18% |
| 10% | ≥ 0,2 | naik | 33 | 43% | 39% | +15,2% / −8,4% | +0,91% | 1,4 | +0,09% |
| 10% | ≥ 0,5 | bebas | 3,6 | 51% | 35% | +16,9% / −7,9% | +2,73% | 1,5 | +1,10% |
| referensi: ER < 0,2 | semua X | | 43–305 | 32–35% | 39–43% | | −0,8…−1,0% | | −0,4…−0,8% |

- 10/24 sel bersih > 0; 15/24 di atas kontrol; 0 sel dengan t ≥ 2 di periode uji.
- Pola monoton: pada setiap X, makin tinggi syarat ER makin baik hasilnya, dan referensi ER < 0,2 selalu terburuk.
- Pilihan latih (X 5%, ER ≥ 0,5, arah bebas): latih +1,09%, uji +0,56% (t 0,48) vs kontrol −0,63%, 4/4 sub-periode
  positif. GAGAL pada syarat t ≥ 2. Per kondisi pasar di periode uji: turun +5,3% (52 trade), sideways +1,2% (54),
  naik −1,0% (51); di periode latih urutannya berbeda (naik +3,6%, sideways −1,3%). Tidak konsisten.

## Kesimpulan
- Benar: ER yang lebih tinggi memberi pantulan yang lebih besar (median 7,5% → 10,3%, p90 19% → 30% untuk zigzag 3%),
  dan di ER ≥ 0,4–0,5 tangkapan real time berubah dari negatif menjadi sedikit positif.
- Tetapi "bisa dimanfaatkan" belum terbukti:
  - setup-nya langka (ER ≥ 0,5: 4–31 trade per tahun dari 100 saham);
  - keunggulannya kecil (+0,6…+3% per trade) dan tidak bisa dibedakan dari nol (t ≤ 1,5);
  - sebagian berasal dari sahamnya yang sedang tren (kontrol hari acak juga positif), bukan dari pantulannya;
  - pilihan latih gagal di uji.
- Ini logika ikut tren (entry pullback), wilayah Logic 1, dan jauh lebih lemah dari breakout V2 (expectancy +7,3% per
  trade). Bukan Logic 2 untuk sideways: irisan sideways-nya kecil dan tidak konsisten.
