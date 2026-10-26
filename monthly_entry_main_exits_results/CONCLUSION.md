# Entry bulanan dengan exit yang sudah ada (klarifikasi pengguna, 26 Okt 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `monthly_entry_main_exits.py`. Opsi mesin: `extra_main_exits` (default
mati; uji regresi lulus).

**Cek kesesuaian.** V2 saat ini TIDAK sesuai maksud pengguna. Posisi bulanan di V2 hanya keluar lewat aturannya sendiri
(trend 120 hari gagal di akhir bulan), tanpa fading dan SMA30. Itulah sebabnya trade bulanan dipegang sekitar 130 bar.

Versi sesuai maksud: posisi bulanan memakai exit yang sama (fading 2 ATR, Close < SMA30).

| Varian (realistis) | CAGR (latih / uji) | Bulan rekor | MDD | WR | Trade bulanan: WR / expectancy / lama pegang | CAGR tanpa batasan | MDD tanpa batasan |
|---|---|---|---|---|---|---|---|
| V2 sekarang (exit bulanan sendiri) | 20,7% (20,1 / 21,7) | 63 | −46% | 40,9% | 43% / +18,0% / 133 bar | 50,6% | −27% |
| Breakout saja (tanpa modul bulanan) | 19,4% (17,3 / 22,9) | 62 | −37% | 41,7% | – | 47,6% | −30% |
| F1 (filter sekarang) + exit lama, 10% | 15,1% (12,5 / 19,7) | 52 | −48% | 39,3% | 36% / +0,3% / 11 bar | 44,7% | −39% |
| F1 + exit lama, 25% | 15,7% | 41 | −50% | 38,6% | 36% / +0,2% / 9 bar | 48,0% | −33% |
| F2 (ER20 ≥ 0,4 saja) + exit lama, 10% | 20,0% (17,9 / 23,5) | 65 | −46% | 39,8% | 38% / +2,1% / 21 bar | 47,9% | −29% |
| F2 + exit lama, 25% | 18,9% | 59 | −46% | 39,8% | 37% / +2,1% / 21 bar | 50,8% | −45% |
| F3 (F1 dan Close > SMA30) + exit lama, 10% / 25% | 15,7–16,0% | 46–54 | −48…−50% | 38–39% | 32–34% / +0,8…1,4% / 17–19 bar | 45–47% | −35…−42% |

Hasil: tidak ada yang lolos.
- Dengan exit lama, trade bulanan kena exit SMA30 (61–83%) atau fading jauh sebelum sempat breakout. F1: separuh trade
  bulanan keluar ≤ 2 bar karena Close-nya sudah di bawah SMA30.
- Expectancy trade bulanan turun ke sekitar 0–2%.
- Versi terbaik (F2, 10%) hampir sama dengan "breakout saja".

Kesimpulan:
- Entry awal bulan dengan exit lama tidak menambah apa-apa. Manfaat modul bulanan di V2 datang dari exit-nya sendiri
  (memegang selama trend 120 hari masih naik).
- Tanpa modul bulanan sama sekali (breakout saja) MDD realistis lebih kecil (−37% vs −46%), dengan CAGR sedikit lebih
  rendah.
- Keputusan desain dikembalikan ke pengguna. AFL tidak diubah.

## Putaran 2: filter SMA untuk entry bulanan (`monthly_entry_sma_filter.py`, `sma_diagnostic.csv`, `sma_grid.csv`)
**Diagnostik** (trade bulanan F1 tanpa filter SMA; realistis | tanpa batasan):
| Posisi saat dibeli | Trade | Expectancy | Lama pegang | Keluar ≤ 2 bar |
|---|---|---|---|---|
| Di bawah SMA30 | 299 \| 373 | −0,8% \| −0,7% | 2 bar | 98% \| 94% |
| Di atas SMA30 | 312 \| 411 | +1,4% \| +5,0% | 19 \| 20 bar | 3% \| 5% |
| 0–5% di atas SMA30 | 52 \| 49 | ≈0% \| +1,6% | 9–19 bar | – |
| 5–10% di atas SMA30 | 125 \| 131 | −0,5% \| +5,1% | 17–20 bar | – |
| > 10% di atas SMA30 | 135 \| 231 | +3,5% \| +5,7% | 21 bar | – |

Pola SMA20 dan SMA50 sama dengan SMA30. Pilihan F2 (ER20 ≥ 0,4 + naik 20 hari) hampir semuanya sudah di atas SMA20/30/50.

**Grid** (30 sel, pilih di periode latih): pilihan = F2 + Close ≥ 1,03 × SMA30.
| | CAGR realistis (latih / uji) | MDD realistis | Rekor | CAGR tanpa batasan | MDD tanpa batasan |
|---|---|---|---|---|---|
| Pilihan | 20,2% (18,2 / 23,5) | −46% | 66 | 48,6% | −27% |
| Breakout saja | 19,4% (17,3 / 22,9) | −37% | 62 | 47,6% | −30% |
| V2 sekarang | 20,7% (20,1 / 21,7) | −46% | 63 | 50,6% | −27% |

Hasil:
- Pilihan tidak lolos: MDD realistis 9 pp lebih dalam daripada "breakout saja" (batas 5 pp). Return-nya hanya +0,8 pp.
- Filter di atas SMA30 memang menghapus pembelian yang langsung kena exit.
- Tapi trade bulanan yang tersisa tetap kecil (expectancy +2…3% realistis, sekitar 21 bar).
- Modul bulanan dengan exit lama hanya menambah sedikit return dengan risiko lebih besar.

## Filter lama (Close > Close 120, ER20 ≥ 0,3) + Close > SMA30 (`monthly_f1_sma30.py`, `f1_sma30.csv`)
| | CAGR realistis (latih / uji) | MDD realistis | Rekor | WR realistis | Trade bulanan: expectancy / lama pegang | CAGR tanpa batasan | MDD tanpa batasan |
|---|---|---|---|---|---|---|---|
| V2 sekarang | 20,7% (20,1 / 21,7) | −46% | 63 | 40,9% | +18,0% / 133 bar | 50,6% | −27% |
| Breakout saja | 19,4% (17,3 / 22,9) | −37% | 62 | 41,7% | – | 47,6% | −30% |
| + SMA30, exit lama | 16,0% (13,1 / 21,0) | −48% | 54 | 38,6% | +1,4% / 19 bar | 45,2% | −35% |
| + SMA30, exit bulanan sendiri | 19,4% (17,8 / 22,1) | −49% | 58 | 40,9% | +15,5% / 149 bar | 44,8% | −33% |

Menambah filter SMA30 ke filter lama tidak memperbaiki apa pun:
- dengan exit lama hasilnya di bawah "breakout saja";
- dengan exit bulanan sendiri hasilnya di bawah V2 sekarang (MDD lebih dalam, CAGR tanpa batasan turun).

## Aturan sesuai maksud pengguna: tiap awal bulan beli saham dengan Close > SMA30, exit lama (`monthly_sma30_simple.py`, `sma30_simple.csv`)
| | CAGR realistis (latih / uji) | MDD realistis | Rekor | WR realistis | Trade bulanan: WR / expectancy / bar | CAGR tanpa batasan | MDD tanpa batasan |
|---|---|---|---|---|---|---|---|
| V2 sekarang | 20,7% (20,1 / 21,7) | −46% | 63 | 40,9% | 43% / +18,0% / 133 | 50,6% | −27% |
| Breakout saja | 19,4% (17,3 / 22,9) | −37% | 62 | 41,7% | – | 47,6% | −30% |
| SMA30, 10% (maks 35%) | 16,9% (16,7 / 17,1) | −45% | 59 | 33,4% | 28% / +0,2% / 13 | 41,5% | −27% |
| SMA30, 25% | 15,1% | −61% | 49 | 33,8% | 28% / +0,2% / 13 | 44,2% | −44% |
| SMA30 + ER20 ≥ 0,2, 10% | 17,3% (15,2 / 20,7) | −48% | 54 | 37,0% | 32% / +0,5% / 16 | 42,4% | −41% |
| SMA30 + ER20 ≥ 0,2, 25% | 16,7% | −58% | 58 | 37,3% | 32% / +0,5% / 16 | 46,5% | −46% |

Semua varian di bawah "breakout saja". Trade bulanan memiliki WR 28–32% dan expectancy sekitar 0%, sama dengan memilih
saham acak di awal bulan.
