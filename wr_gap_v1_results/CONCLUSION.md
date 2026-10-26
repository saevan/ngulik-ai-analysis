# Apa yang membuat win rate kita belum seperti Swinger ideal? (V1, 26 Okt 2026)

Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `wr_gap_v1.py`. Mesin dapat mode baru `entry_mode='close_fill'`
(default tidak berubah; uji regresi lulus; bug entry di bar terakhir data diperbaiki sebelum hasil dipakai).
Biaya B, 2000-01-01..2025-08-15.

## Bagian A – jembatan win rate (per trade)
Tiap trade dipecah jadi tiga kaki:
- hari 1: fill → Close bar entry;
- pegang: Close bar entry → Close bar keputusan exit;
- fill exit: Close keputusan → harga jual.

| | Kita V1 tanpa batasan | Kita V1 realistis | Swinger ideal |
|---|---|---|---|
| WR seperti ditradingkan | 41,4% | 34,4% | 48,8% |
| Expectancy seperti ditradingkan | +11,4% | +6,0% | +6,5% |
| Kaki hari 1: rata-rata / % negatif | +0,5% / 42% | +0,2% / 47% | +2,7% / 0% |
| Kaki fill exit: rata-rata / % negatif | +0,5% / 16% | +0,3% / 18% | +2,7% / 0% |
| WR basis Close-ke-Close (biaya 0,9%) | 36,7% | 30,9% | 30,8% |
| Expectancy basis Close-ke-Close | +10,1% | +5,4% | +1,0% |

Swinger ideal bila hanya entry dipindah ke Close sinyal: WR 37,7%. Bila hanya exit dipindah ke Close sinyal: WR 38,9%.

Pecahan WR kita per jenis trade:
- Breakout: tanpa batasan 38,5%, realistis 31,6%.
- Bulanan: tanpa batasan 48,7%, realistis 43,6%.

Observasi:
1. Fill Swinger ideal memberi rata-rata +2,7% di entry dan +2,7% di exit per trade, tanpa pernah negatif. Ia membeli di
   TSL sebelumnya pada bar yang Close-nya sudah di atasnya, dan menjual di TSL sebelumnya pada bar yang Close-nya sudah
   di bawahnya.
2. Tanpa dua keuntungan fill itu, WR Swinger turun dari 48,8% ke 30,8% dan expectancy dari +6,5% ke +1,0%.
3. Pada basis yang sama (Close-ke-Close), WR kita sama atau lebih tinggi (36,7% / 30,9%) dan expectancy kita jauh lebih
   tinggi.

## Bagian B – uji yang bisa dieksekusi: konfirmasi breakout di Close, beli di Close itu
Close > HHV20 sebelumnya (× 1 / × 1,005), ER20 bar sebelumnya ≥ 0,2; dibeli di Close (pendekatan pre-closing).

| Sistem | WR tanpa batasan | CAGR | MDD | WR realistis | CAGR | MDD |
|---|---|---|---|---|---|---|
| V0 buy stop | 38,3% | 49,3% | −24% | 33,8% | 16,2% | −44% |
| V1 buy stop | 41,4% | 45,4% | −25% | 34,4% | 19,7% | −45% |
| V0 beli di Close, b 0 / 0,5% | 39,2 / 38,6% | 28,1 / 26,9% | −57 / −55% | 36,5 / 37,0% | 6,8 / 11,8% | −61 / −47% |
| V1 beli di Close, b 0 / 0,5% | 39,7 / 39,4% | 28,0 / 22,8% | −50 / −52% | 38,2 / 37,8% | 9,9 / 8,2% | −56 / −52% |

Hasil:
- Tidak menutup celah WR (perlu ≥ 45%), dan bukan kandidat. CAGR turun sekitar separuh dan MDD jauh lebih dalam.
- Beli di Close menghapus hari-1 negatif (0%), tapi kaki pegang jadi negatif (median −2,2…−2,6%). Breakout yang sudah
  terkonfirmasi di Close cenderung mundur di hari-hari berikutnya.

## Kesimpulan
- Celah WR kita terhadap Swinger ideal (34–41% vs 48,8%) seluruhnya dijelaskan oleh fill ideal Swinger di kedua sisi,
  yang tidak bisa dieksekusi.
- Pada basis harga yang sama, trade kita setara atau lebih baik dari Swinger, baik WR maupun expectancy.
- Mencoba "tahu Close dulu" secara eksekusi (beli di Close terkonfirmasi) hanya memindahkan kerugian dari hari 1 ke
  hari-hari sesudahnya.
- Kelemahan nyata kita yang tersisa:
  - 42–47% fill buy stop berakhir di bawah harga beli pada hari itu;
  - versi realistis jauh lebih lemah (WR breakout 31,6%).
- AFL aktif tidak diubah.
