# "Range jebol → ER lurus → Logic 2 otomatis terjual" (9 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `er_switch_exit.py`. Hasil:
- `results_all.csv`;
- `summary_by_exit.csv`;
- `training_picks.csv`;
- `stopped_trades_er_timing.csv`.

Setup:
- Logic 2 range: nested 64 sel + pivot 24 sel.
- Entry hanya saat saham choppy (ER20 < 0,2) dan pasar sideways. Versi realistis, biaya B, 2000–2025.08.

## Hasil (rata-rata semua sel, 2000–25)
| Sistem | Exit | WR | Menang / kalah | Kotor | Bersih | Sel bersih > 0 |
|---|---|---|---|---|---|---|
| Nested | stop harga (asli) | 42% | +4,9% / −5,4% | −1,08% | −1,87% | 0/64 |
| Nested | ER20 ≥ 0,2 | 36% | +4,2% / −3,5% | −0,73% | −1,50% | 0/64 |
| Nested | ER20 ≥ 0,3 | 42% | +4,7% / −5,2% | −1,04% | −1,82% | 0/64 |
| Nested | pasar keluar dari sideways | 41% | +4,3% / −5,1% | −1,25% | −1,92% | 0/64 |
| Nested | stop harga + ER20 ≥ 0,3 | 39% | +4,7% / −4,4% | −0,95% | −1,70% | 0/64 |
| Pivot | stop harga (asli) | 36% | +5,5% / −4,9% | −1,07% | −1,86% | 0/24 |
| Pivot | ER20 ≥ 0,2 | 34% | +4,7% / −3,6% | −0,86% | −1,63% | 0/24 |
| Pivot | ER20 ≥ 0,3 | 40% | +5,5% / −5,6% | −1,20% | −2,04% | 0/24 |
| Pivot | pasar keluar dari sideways | 40% | +4,7% / −5,5% | −1,41% | −2,16% | 0/24 |
| Pivot | stop harga + ER20 ≥ 0,3 | 33% | +5,2% / −4,0% | −0,92% | −1,71% | 0/24 |

Pilihan latih semua varian gagal di uji 2016–25 (bersih −1,3…−1,7%, 0/4 subperiode positif).

Kapan ER berubah saat range jebol? Trade yang kena stop harga, sel pilihan latih:
| Sistem | Trade kena stop | Sempat ER20 ≥ 0,3 sebelum stop | Bar ke ER ≥ 0,3 / ke stop (median) | Return saat ER ≥ 0,3 / saat stop |
|---|---|---|---|---|
| Nested | 1.793 | 26% | 2 / 3 | −3,0% / −3,8% |
| Pivot | 1.964 | 15% | 2 / 2 | −2,9% / −2,5% |

## Penilaian klaim
- Sebagian benar secara mekanis: ER akhirnya naik setelah range jebol. Exit ER20 ≥ 0,2 memperkecil rugi rata-rata
  (−5,4% → −3,5%).
- Tapi:
  1. ER20 terlambat. Di 74–85% kejadian jebol, harga sudah menembus stop sebelum ER20 mencapai 0,3. Saat ER mencapai
     0,3, rugi sudah −3%.
  2. ER tidak punya arah. Exit ER juga menjual saat harga memantul naik dengan lurus, sehingga menang ikut mengecil
     (+4,9% → +4,2%) dan WR turun (42% → 36%).
  3. Tidak ada varian yang membuat Logic 2 untung: 0/88 sel untuk semua varian exit, dan kotornya tetap negatif.
  4. Logic 1 (V2) hanya membeli breakout ke atas. Jebol ke bawah tidak mengaktifkan Logic 1; dananya hanya kembali
     jadi kas.
- Masalah Logic 2 ada di entry (adverse selection: terisi saat harga jebol), bukan di exit, sehingga saklar ER tidak
  memperbaikinya.
