# Apakah ER memberi tahu apa yang akan terjadi? (9 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `er_regime_check.py`. Hasil: `er_forward.csv`, `regime_transition_20d.csv`.
Data:
- Saham: universe realistis, 196.817 hari saham, 2000–2025.08.
- Pasar: proxy EW `regime_proxy`, 6.201 hari.
ER20 hari ini dibandingkan dengan perilaku 20 hari ke depan.

## Saham
| ER20 saham hari ini (porsi hari) | ER20 20 hari lagi (median) | P(nanti ER < 0,2) | Lanjut arah 20 hari | Tetap di range 20 hari | Jebol atas saja / bawah saja | Lebar range ke depan |
|---|---|---|---|---|---|---|
| < 0,1 (27%) | 0,20 | 50% | +0,1% | 16% | 37% / 38% | 15,7% |
| 0,1–0,2 (23%) | 0,20 | 50% | +0,6% | 19% | 37% / 36% | 15,9% |
| 0,2–0,3 (20%) | 0,19 | 51% | +0,7% | 21% | 38% / 35% | 16,7% |
| 0,3–0,5 (22%) | 0,19 | 51% | +0,9% | 22% | 40% / 33% | 17,9% |
| ≥ 0,5 (8%) | 0,20 | 50% | +1,2% | 20% | 44% / 34% | 21,1% |
| Semua | 0,20 | 50% | +0,6% | 20% | 38% / 36% | 16,8% |

Pantulan ke depan, dengan bias jendela pendek, jadi hanya perbandingan antarkelompok yang bermakna:
- autokorelasi lag-1: −0,063 (ER < 0,1) vs −0,027 (ER ≥ 0,5);
- VR(5): 0,63 vs 0,67.

## Pasar (proxy EW)
| ER20 pasar hari ini | ER20 20 hari lagi (median) | P(nanti ER ≥ 0,3) | Lanjut arah 20 hari |
|---|---|---|---|
| < 0,1 | 0,25 | 41% | −0,1% |
| 0,1–0,2 | 0,25 | 42% | +0,8% |
| 0,2–0,3 | 0,25 | 43% | +1,3% |
| 0,3–0,5 | 0,28 | 46% | +2,3% |
| ≥ 0,5 | 0,30 | 49% | +3,6% |

Label 20 hari lagi (porsi baris):
| Sekarang \ 20 hari lagi | Turun | Sideways | Naik |
|---|---|---|---|
| Turun | 17% | 59% | 23% |
| Sideways | 12% | 58% | 30% |
| Naik | 8% | 50% | 42% |

## Penilaian klaim
- Benar: ER menggambarkan kondisi 20 hari terakhir. Itu memang definisinya.
- Benar untuk logika tren: makin tinggi ER, arah lama makin cenderung berlanjut.
  - saham: +0,1% → +1,2% per 20 hari;
  - pasar: −0,1% → +3,6%.
- Salah untuk logika pantulan. ER rendah tidak meramalkan bolak-balik:
  - Saham choppy hari ini 20 hari lagi tidak lebih choppy dari saham lain: median ER 0,20 dan P(ER < 0,2) 50%, sama
    di semua kelompok.
  - Hanya 16% saham ER < 0,1 tetap di range-nya 20 hari ke depan, lebih jarang daripada saham ber-ER tinggi (20%).
    Sisanya jebol, dengan arah atas/bawah seimbang (37% / 38%).
  - Pantulan harian hanya sedikit lebih kuat (selisih autokorelasi 0,036).
  - Pasar sideways punya label yang sama 20 hari lagi hanya 58%, hampir sama dengan porsi sideways dari kondisi lain
    (50–59%).
- Arti ER rendah adalah "tidak ada informasi tren", bukan "akan memantul". Ini menjelaskan kenapa semua upaya Logic 2
  berbasis ER rendah gagal.
- Peran ER yang didukung data: filter untuk Logic 1 (masuk saat ada tren). Saat ER rendah, tindakan yang didukung data
  adalah tidak memaksakan sinyal, lalu memarkir kas.
