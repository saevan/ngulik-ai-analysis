# Kenapa V2 belum seoptimal Swinger ideal? (9 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `v2_gap_vs_swinger.py`. Hasil:
- `bridge_and_identity.csv`;
- `identity_decomposition.csv`;
- `missed_big_moves.csv`;
- `losses_by_exit.csv`.

Biaya B, 2000-01-01..2025-08-15.

## A. Jembatan CAGR
V2 realistis 20,7% → V2 tanpa batasan 50,7% → Swinger ideal 102,0%. Batasan realistis (likuid, data basi, 25% ADV20)
hanya berlaku untuk V2; pembanding tidak punya batasan itu.

## B. Uang × kesempatan × kualitas (kontribusi per tahun = trade per tahun × bobot rata-rata × return tertimbang)
| | Trade per tahun | Bobot per trade | Return tertimbang per trade | Kontribusi per tahun |
|---|---|---|---|---|
| V2 realistis | 28,3 | 15,0% | +5,6% | 23,9% |
| V2 tanpa batasan | 27,5 | 14,8% | +12,6% | 51,4% |
| Swinger ideal | 126,5 | 9,6% | +6,6% | 80,2% |

Celah V2 realistis → Swinger (log 1,21):
- jumlah trade +1,50 (124% dari celah);
- bobot −0,44 (V2 justru memakai posisi lebih besar);
- kualitas +0,16 (13%).

## C. Pergerakan besar yang terlewat
- Dari 163 trade terbaik Swinger (5% teratas, rata-rata +83%), V2 realistis memegang saham yang sama hanya di 15% harinya.
  - 76% dari trade itu tidak tersentuh V2 sama sekali.
  - V2 tanpa batasan: 25% hari, 58% tidak tersentuh.
- Sebaliknya, dari 37 trade terbaik V2 (rata-rata +138%), Swinger sempat masuk di 70% saham itu, tetapi hanya memegang 19%
  harinya.

## D. Besar rugi per exit (V2 realistis)
| Exit | Porsi trade | WR | Porsi dari trade rugi | Rata-rata rugi | Lama (bar) | Rugi < −10% |
|---|---|---|---|---|---|---|
| Close < SMA30 | 54% | 34% | 60% | −6,5% | 16 | 15% |
| Fade 2 ATR | 20% | 55% | 15% | −7,0% | 9 | 23% |
| Exit modul bulanan | 26% | 43% | 25% | −14,8% | 74 | 54% |
| Semua V2 | | 41% | | −8,7% | 29 | 26% |
| Swinger ideal | | 49% | | −3,5% | 11 | 3% |

Catatan: rugi Swinger ideal ikut diperkecil fill exit-nya. Dengan basis Close-ke-Close, rugi rata-ratanya −6,7%.

## E. Modal menganggur
- Rata-rata modal terpakai V2 realistis 66%: naik 83%, sideways 62%, turun 38%. Swinger: 96 / 94 / 82%.
- Hari dengan kas ≥ 25% ekuitas (cukup untuk satu order V2 lagi tapi tidak ada sinyal): 56% hari. Per kondisi: naik 29%,
  sideways 64%, turun 94%.

## Kesimpulan
Urutan penyebab:
1. Kesempatan terlalu sedikit. Jumlah trade (28 vs 126 per tahun) menjelaskan seluruh celah, dan V2 melewatkan 76% trade
   raksasa Swinger. Kualitas per trade bukan masalahnya.
2. Batasan realistis memotong CAGR dari 50,7% ke 20,7%. Return per trade turun dari +12,6% ke +5,6%, karena saham likuid
   bergerak lebih kecil dan batas ADV memotong posisi di saham kecil.
3. Modal menganggur: lebih dari separuh hari kas cukup untuk order baru tetapi tidak ada sinyal.
4. Rugi lebih besar, terutama dari exit modul bulanan (−14,8%, 74 bar).
5. Fill ideal Swinger, yang tidak bisa ditiru, sudah tercatat di sidik jari langkah 1.

Uji berikutnya yang wajar: kenapa V2 melewatkan trade raksasa Swinger. Kemungkinannya: ER memblokir, belum tembus HHV20,
modal penuh, atau saham tidak likuid saat itu.

## Addendum: di kondisi pasar apa Swinger trading sementara V2 tidak? (`v2_gap_by_condition.py`, `by_condition_*.csv`)
V2 realistis. Breakdown = Close proxy kemarin di low 20 hari baru (irisan yang tumpang tindih).

| Kondisi (porsi hari) | Trade per tahun Swinger / V2 | Modal terpakai Swinger / V2 | Hari Swinger ≥ 75% terpakai & V2 < 25% |
|---|---|---|---|
| Naik (33%) | 33 / 10 | 96% / 83% | 0,3% |
| Sideways (56%) | 72 / 17 | 94% / 62% | 5,5% |
| Turun (11%) | 22 / 1,4 | 82% / 38% | 11,7% |
| Breakdown (8%) | 16 / 1,2 | 73% / 45% | 5,4% |

Trade Swinger yang tidak tersentuh V2 (V2 tidak pernah memegang saham itu selama trade): 88% dari semua trade Swinger.

| Kondisi saat entry | Per tahun | Return seperti ditradingkan | Pergerakan harga (Close-ke-Close bersih) | Trade yang juga dipegang V2: pergerakan |
|---|---|---|---|---|
| Naik | 29,4 | +9,5% | **+2,7%** | +8,6% |
| Sideways | 63,1 | +4,1% | **−0,8%** | +9,2% |
| Turun | 18,7 | +3,8% | **−2,2%** | +9,3% |
| Breakdown | 14,4 | +3,3% | **−1,8%** | +16,5% |

Yang tidak tersentuh, dipecah menurut saham (pergerakan bersih per trade):
- Naik: ER20 ≥ 0,2 → 13,3/th, +4,7%; ER20 < 0,2 → 16,1/th, +1,2%; di atas SMA30 → 24,0/th, +2,8%.
- Sideways: ER20 < 0,2 (67% dari yang terlewat) → −1,4%; ER20 ≥ 0,2 → +0,3%.
- Turun dan breakdown: semua kelompok negatif.

Kesimpulan:
- Swinger trading jauh lebih banyak di semua kondisi. Selisih jumlah terbesar ada di sideways (+55 trade per tahun), dan
  selisih relatif terbesar saat turun (15×).
- Hanya saat pasar naik trade yang terlewat itu membawa pergerakan harga nyata: +2,7%/trade, dan +4,7% di saham ER20 ≥ 0,2
  (sekitar 13 trade per tahun).
- Saat sideways, turun, dan breakdown, pergerakan trade yang terlewat negatif. Untung Swinger di sana berasal dari fill-nya,
  jadi V2 tidak masuk di sana bukan kelemahan.
- Trade Swinger yang juga dipegang V2 adalah yang terbaik (pergerakan +8,6…+16,5%).
- Catatan: pergerakan diukur dari Close sinyal sampai Close exit Swinger, bukan dengan exit V2.
