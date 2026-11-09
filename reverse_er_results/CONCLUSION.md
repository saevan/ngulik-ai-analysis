# "ER kebalikan" untuk Logic 2 sideways (9 Nov 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `reverse_er.py`. Hasil: `results_all.csv`, `summary.csv`.

## Konsep
- 1 − ER atau 1/ER berisi informasi yang sama dengan ER, hanya dibalik. Tidak ada informasi baru.
- "ER rendah → pakai logika terbalik" sudah gagal di 5 studi (8–9 Okt). Contoh: sinyal terbalik WR 66,8%, tetapi menang
  +13,8% vs kalah −19,6%. Sideways −2,7%/th dengan fee saja, dan −11,4% dengan spread.
- Versi baru yang diuji di sini adalah cermin V2 dengan ER bertanda:
  - beli saat saham turun secara efisien (ER20 bertanda ≤ −0,3/−0,4/−0,5) dan Close di low 20 hari baru;
  - hanya saat pasar sideways, beli di Open besok.

## Hasil (realistis, biaya B 0,9%, 2000–2025.08, 18 sel)
Semua sel rugi bersih: −0,6…−1,8% per trade.

| Sel terbaik per ER | WR | WR impas | Menang / kalah | Bersih | Kontrol acak sideways |
|---|---|---|---|---|---|
| ER ≤ −0,3, exit Close > SMA10 | 57% | 63% | +4,7% / −5,7% | −0,74% | −0,88% |
| ER ≤ −0,4, exit Close > SMA10 | 59% | 64% | +4,9% / −6,3% | −0,97% | −1,01% |
| ER ≤ −0,5, exit Close > SMA10 | 61% | 65% | +5,1% / −6,9% | −0,63% (t −1,6) | −1,08% |

Pilihan dari periode latih (ER ≤ −0,5, exit Close > SMA10, tanpa stop):
- uji 2016–25: bersih −0,43% (t −1,0) vs kontrol −0,99%;
- 1 dari 4 subperiode positif;
- GAGAL.

Sebelum biaya, sel terbaik hanya +0,27% per trade. Dengan fee pengguna 0,6% tanpa slippage tetap rugi (−0,33%).

## Kesimpulan
- Ada sedikit efek pantul: makin efisien turunnya, sinyal makin baik dari hari acak (+0,1…+0,45 poin). Tapi efeknya
  jauh di bawah biaya.
- "ER kebalikan" tidak bisa jadi Logic 2 sideways dengan data harian saham: tidak dalam bentuk 1 − ER, tidak sebagai
  saklar logika terbalik, dan tidak sebagai cermin bertanda dari V2.
