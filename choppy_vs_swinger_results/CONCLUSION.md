# Performa saat pasar choppy: kandidat vs Swinger (15 Oktober 2026)

Choppy = ER20 proxy equal-weight 100 saham < 0,3, label dari Close hari sebelumnya (`analyze_portfolio_regimes.regime_proxy`, sama dengan riset sebelumnya; bukan IHSG). 55,3% waktu 2000–2025 choppy. Sistem dijalankan penuh sepanjang sejarah (tanpa gate); angka "choppy" = atribusi return harian pada hari choppy, dianualkan (bukan CAGR sistem terpisah). Bulan rekor choppy = bulan yang punya hari choppy dengan equity melewati ATH (dari 280 bulan yang punya hari choppy). Trade dikelompokkan menurut kondisi saat entry. File: `daily_by_state.csv`, `trades_by_entry_state.csv`, `choppy_by_period.csv`.

| Sistem | Return choppy/thn | Rekor choppy /280 | Return trend/thn | Modal terpakai saat choppy | DD rantai hari choppy |
|---|---:|---:|---:|---:|---:|
| Kandidat (fee) | 32.5% | 86 | 71.0% | 71.8% | −21.6% |
| Kandidat ch10+trail2 (fee) | 34.0% | 99 | 89.8% | 68.8% | −23.1% |
| Kandidat (spread 1 tick) | 13.0% | 60 | 49.5% | 71.5% | −30.8% |
| Sistem awal (fee) | 20.1% | 57 | 52.5% | 72.0% | −27.2% |
| Swinger ideal (fee, tidak bisa dieksekusi) | 87.2% | 191 | 154.6% | 93.5% | −16.8% |
| Swinger stop order (fee) | 13.9% | 52 | 53.8% | 81.6% | −38.5% |
| Swinger next Open (fee) | 4.8% | 42 | 45.9% | 93.7% | −52.1% |

Per periode (return choppy/thn): kandidat fee 35.5% / 27.8% / 29.0% (2000–15 / 2016–20 / 2021–25); Swinger stop order 14.0% / 5.8% / 21.5%; Swinger next Open 10.5% / −4.5% / −1.1%; Swinger ideal 95.8% / 59.7% / 91.7%.

Trade yang entry saat choppy:

| Sistem | Trade | WR | Avg win | Avg loss | Rugi < −10% | Expectancy | Hold |
|---|---:|---:|---:|---:|---:|---:|---:|
| Kandidat (fee) | 1412 | 44.1% | 17.2% | 6.6% | 11.3% | +3.9% | 20.5 |
| Kandidat ch10+trail2 (fee) | 2340 | 46.9% | 11.5% | 5.2% | 7.6% | +2.6% | 11.9 |
| Swinger ideal (fee) | 1833 | 50.5% | 14.7% | 3.2% | 1.5% | +5.8% | 18.3 |
| Swinger stop order (fee) | 4253 | 28.3% | 10.5% | 2.9% | 2.3% | +0.8% | 7.8 |
| Swinger next Open (fee) | 1827 | 33.2% | 15.3% | 5.9% | 9.0% | +1.1% | 19.4 |

Kesimpulan:
- Pada biaya yang sama (fee), kandidat di hari choppy ~2,3× Swinger stop order dan ~7× Swinger next Open, stabil di ketiga periode. Kandidat juga mengalahkan sistem awal (20,1%) dan modul inverse lama (choppy −9% sesudah spread).
- Masih jauh di bawah Swinger ideal (87%), dan selisih terbesar ada di rugi per trade (6,6% vs 3,2%) serta modal terpakai (72% vs 94%). Sebagian besar keunggulan Swinger ideal berasal dari fill di level sinyal (lihat swinger_gap_results).
- Choppy tetap kondisi terlemah kandidat: return choppy kira-kira setengah dari return trend (32,5% vs 71,0%).
- Sesudah spread 1 tick, return choppy kandidat turun ke 13,0%/thn, setara Swinger stop order fee-only.
