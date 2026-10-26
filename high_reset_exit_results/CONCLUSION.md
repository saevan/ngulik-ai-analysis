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
