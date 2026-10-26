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
