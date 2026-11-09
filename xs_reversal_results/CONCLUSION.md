# Mean reversion relatif (cross-sectional) untuk sideways (9 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `xs_reversal.py`. Hasil: `results_all.csv`, `summary.csv`.

Setup:
- Tiap hari saat pasar sideways besoknya, beli 5 saham yang paling turun dibanding saham lain (return 1/5/10 hari).
- Dipegang 5/10 bar. Entry di Open besok atau limit Close − 0,5 ATR.
- Universe realistis, biaya B, 2000–2025.08, 12 sel.
- Pembanding: 5 saham acak di hari yang sama, dan 5 saham yang paling naik.

## Hasil
Semua 12 sel rugi bersih: −0,9…−1,4% per trade (kotor −0,1…−0,5%).
- Saham yang paling turun vs saham acak: −0,18…+0,14 poin. Tidak ada efek "mengejar ketertinggalan".
- Saham yang paling turun vs yang paling naik: hampir sama (bersih −1,0…−1,4%).
- WR 41–45%; WR impas 52–55%.
- Pilihan latih (1 hari, pegang 5, limit): uji 2016–25 bersih −0,79% (t −3,8), 0/4 subperiode positif. GAGAL.

## Ringkasan semua uji mean reversion untuk sideways (long, data harian)
| Bentuk | Studi | Hasil |
|---|---|---|
| Beli di bawah/tengah range, fade | range_size_modules, mid_atr_sideways, wide_range, stock_er_range, established_range, swing_in_range | gagal, kotor ≈ entry acak |
| Buy limit di bawah harga | atr_dip_limit | pantulan ada tapi < biaya |
| Beli sesudah turun 5–20% | decline_bounce | tidak beda dari acak |
| Beli saat pantulan mulai | buy_the_turn | lebih buruk dari acak |
| Sinyal V2 dibalik saat choppy | choppy_inverted_signal (Okt) | WR 67%, sideways −2,7%/th (fee saja) |
| WR tinggi di bawah range | high_wr_range | WR 70–83%, semua rugi |
| Cermin V2 dengan ER bertanda | reverse_er | 18/18 rugi |
| Grid oversold (RSI2, volume, candle, breadth) | sideways_bounce_grid | 1/168 positif (+0,01%) |
| Pembalikan relatif | xs_reversal | 12/12 rugi |

## Kesimpulan
- Mean reversion long-only dengan data harian saham sudah diuji dalam 9 bentuk berbeda, dan semuanya gagal sesudah biaya.
- Efek pantulan yang ada sekitar 0,0–0,3% per trade, sedangkan biayanya 0,9%.
- Bentuk yang belum diuji membutuhkan hal yang belum kita punya:
  - data intraday;
  - short / pair trading;
  - biaya jauh lebih rendah.
