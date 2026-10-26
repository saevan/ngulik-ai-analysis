# Exit waktu yang di-reset setiap trade mencetak high baru (ide pengguna, 26 Okt 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `high_reset_exit.py`. Opsi mesin: `high_reset_bars` (default mati; uji
regresi lulus). Diterapkan ke trade breakout V1; modul bulanan tetap. Biaya B, 2000–2025.

| Varian | WR realistis / tanpa batasan | CAGR realistis (latih / uji) | MDD realistis | CAGR tanpa batasan | MDD tanpa batasan | Bulan rekor (R / U) |
|---|---|---|---|---|---|---|
| V1 | 34,4% / 41,4% | 19,7% (18,5 / 21,7) | −45% | 45,4% | −25% | 63 / 127 |
| Hanya exit ini, x = 15 | 45,4% / 46,9% | 21,7% (21,6 / 21,9) | −37% | 41,4% | −48% | 67 / 95 |
| Hanya exit ini, x = 20 | 45,3% / 47,6% | 20,4% (16,6 / 27,0) | −41% | 39,7% | −45% | 69 / 81 |
| Hanya exit ini, x = 5 / 10 / 30 | 43–46% / 46–50% | 14,6–17,8% | −48…−56% | 37–45% | −36…−43% | 47–56 / 99–108 |
| Ditambah ke exit asli, x = 5–30 | 34–37% / 40–43% | 13,4–21,6% | −42…−53% | 31–47% | −25…−34% | 54–65 / 102–130 |
| Breakout gagal + exit ini, x = 5–30 | 37–40% / 39–42% | 12,7–20,3% | −41…−52% | 35–42% | −37…−47% | 45–65 / 85–108 |

Hasil:
- Tidak ada varian yang lolos.
- Varian terdekat ("hanya exit ini, x = 15") lebih baik dari V1 di versi realistis: CAGR latih dan uji lebih tinggi, MDD
  −37% vs −45%, WR 45%. Ia gagal karena di versi tanpa batasan MDD −48% vs −25%, dan bulan rekor turun ke 95 dari 127.
- Tetangganya (x = 10 / 20) tidak konsisten. Jadi x = 15 bisa jadi kebetulan.
- Exit ini menaikkan WR breakout ke 42–47%, karena posisi bertahan selama harga masih mencetak high baru. Tapi ia
  melepas trend yang sedang konsolidasi lama, dan menahan posisi yang jatuh tajam tanpa stop harga (tanpa SMA30/fade).
  Itulah sebabnya MDD membesar.
- AFL tidak diubah.

## Tambahan: V1 tanpa exit SMA30 (`no_sma30_check.py`, `no_sma30.csv`, eksploratif)
| Varian | WR realistis / tanpa batasan | CAGR realistis (latih / uji) | MDD realistis | Rekor (R / U) | CAGR tanpa batasan | MDD tanpa batasan |
|---|---|---|---|---|---|---|
| V1 | 34,4% / 41,4% | 19,7% (18,5 / 21,7) | −45% | 63 / 127 | 45,4% | −25% |
| Tanpa SMA30 (fade + breakout gagal saja) | 39,3% / 41,4% | 18,3% (17,2 / 20,1) | −55% | 65 / 93 | 29,4% | −42% |
| Tanpa SMA30 + reset x10 | 37,1% / 40,8% | 20,2% (16,8 / 26,1) | −39% | 63 / 105 | 36,4% | −33% |
| Tanpa SMA30 + reset x15 | 38,2% / 41,0% | 20,3% (20,0 / 20,8) | −41% | 61 / 120 | 44,1% | −32% |
| Tanpa SMA30 + reset x20 | 37,2% / 41,8% | 23,0% (19,9 / 28,3) | −40% | 75 / 114 | 42,1% | −35% |
| Tanpa SMA30 + reset x30 | 38,5% / 39,9% | 18,3% (16,5 / 21,3) | −41% | 56 / 102 | 37,5% | −37% |

Hasil:
- Membuang SMA30 saja merugikan: trade breakout dipegang sekitar 48–65 bar, CAGR tanpa batasan turun ke 29%, MDD −42…−55%.
- Bila SMA30 diganti exit reset x20, versi realistis membaik (23,0%, lebih baik di latih dan uji, MDD −40%, 75 bulan
  rekor). Tapi versi tanpa batasan turun (42,1%, MDD −35% vs −25%). Menurut aturan rencana sebelumnya, ini tidak lolos
  (MDD lebih dari 5 pp lebih dalam).
- WR hanya naik ke 37–39% (realistis).
