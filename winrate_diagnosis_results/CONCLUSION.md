# Kenapa win rate kita di bawah 50%, dan apakah "harga + waktu" memberi WR ~50%? (26 Okt 2026)

Sistem: pilihan utama v2 (buy stop 0,5% di atas HHV20, ER20 ≥ 0,2, exit fade 2 ATR / Close < SMA30 / breakout gagal,
25% ekuitas per order). Biaya B (round trip 0,90%), 2000-01-01..2025-08-15. Pembanding: Prototype Swinger ideal saja
(B: WR 48,8%, payout 4,90). Kode: `diagnose_winrate.py` (langkah 1, eksploratif, dijalankan sebelum PLAN),
`winrate_price_time_portfolio.py` (langkah 2, dikunci di PLAN.md sebelum hasil). Opsi baru mesin `max_hold` (default mati;
uji regresi lulus, V0 identik). Pengecekan: exit waktu jatuh tepat di Open pertama yang bisa ditransaksikan setelah n bar
(814/814 cocok).

## Langkah 1 – dari mana trade kalah (797 trade, versi tanpa batasan)
| | Kita | Kita realistis | Swinger ideal |
|---|---|---|---|
| WR setelah biaya | 38,3% | 33,8% | 48,8% |
| WR sebelum biaya | 40,4% | 36,1% | 52,9% |
| Trade keluar "breakout gagal" (Close hari entry < level HHV20) | 26,7%, WR 1,5% | 30,0% | – |
| Bagian dari semua trade kalah | 43% | 44% | – |
| WR jika trade breakout gagal dikeluarkan | 51,7% | 47,3% | – |
| Close hari entry di bawah harga fill | 42% (WR 18%) | 47% | 0% (konstruksi fill ideal) |
| WR exit SMA30 (40% trade) | 42,4% | 38,4% | – |
| WR exit fading (27% trade) | 66,7% | 66,7% | – |
| WR uptrend / sideways / downtrend | 37 / 40 / 27% | 35 / 33 / 27% | 52 / 47 / 48% |
| WR 2000-07 / 08-15 / 16-20 / 21-25 | 45 / 38 / 36 / 32% | 42 / 30 / 34 / 28% | 55 / 53 / 45 / 42% |
| Trade kalah: median lama / MFE / MAE | 4 bar / +2,8% / −6,5% | 5 / +2,2% / −6,0% | 8 / +4,0% / −4,9% |
| Trade kalah yang sempat Close > biaya / > +5% | 41% / 22% | 41% / 19% | 83% / 23% |

Observasi:
1. Biaya hanya membalik 2% trade dari menang ke kalah. Biaya bukan penyebab utama.
2. Penyebab terbesar adalah entry buy stop. Di 42% trade, Close hari entry sudah di bawah harga fill. Seperempat trade
   ditutup sebagai breakout gagal dengan WR 1,5%. Tanpa trade itu WR kita 51,7%.
3. Swinger ideal tidak pernah punya hari entry seperti itu, karena fill-nya di level TSL yang sudah dilewati Close bar
   sinyal. Fill itu tidak bisa dieksekusi (catatan singkat).
4. Exit SMA30 memotong banyak trade di sekitar impas (WR 42%).
5. WR turun dari periode ke periode untuk kedua sistem. Ini sejalan dengan memudarnya trend jangka pendek sejak 2011
   (market_properties_v2).

Interpretasi: WR rendah adalah harga dari desain "potong cepat, biarkan pemenang lari". Dengan payout 5,06, WR impas
cuma 1/(1+5,06) = 16,5%. Ini bukan bukti sistemnya rusak.

## Langkah 2 – exit harga/waktu di portofolio (entry, ukuran dan biaya sama; hanya exit diganti)
| Sel | WR | Payout | CAGR | Bulan rekor | MDD | Modal terpakai | CAGR realistis | Subperiode ≥ V0 |
|---|---|---|---|---|---|---|---|---|
| V0 (asli) | 38,3% | 5,06 | 49,3% | 119 | −24,1% | 49% | 16,2% | – |
| Waktu saja 10 / 20 / 40 bar | 53–56% | 1,7–2,0 | 29,9 / 39,7 / 39,3% | 87–98 | −29…−42% | 39–71% | 11,2 / 13,4 / 18,6% | 0–2 dari 4 |
| V0 + batas waktu 20 / 40 / 60 | 38–42% | 3,3–5,0 | 39,5 / 43,2 / 48,0% | 107–120 | −24…−27% | 42–48% | 15,4–17,1% | 0–1 |
| Breakout gagal + waktu 20 / 40 | 43,7% | 2,9–3,2 | 36,7 / 36,9% | 92–94 | −33 / −45% | 50–66% | 16,1 / 20,7% | 0 |
| Take profit 3 ATR + waktu 10/20/40 | 56–71% | 0,7–1,1 | 17–24% | 75–102 | −31…−34% | 35–58% | 5–8% | 0 |
| Take profit 6 ATR + waktu 10/20/40 | 53–59% | 1,2–1,4 | 21–22% | 78–83 | −31…−33% | 38–66% | 10–18% | 0 |

Swinger ideal B: WR 48,8%, 102,0% CAGR, 232 bulan rekor, MDD −21%.

Hasil (kriteria di PLAN.md):
- Tidak ada sel yang lolos.
- Klaim "harga + waktu memberi WR ~50%" benar: WR 53–71% tercapai. Tapi semua versi itu menurunkan CAGR dan bulan
  rekor di uji utama.
- Take profit menaikkan WR paling tinggi, tapi payout jatuh ke ≤ 1,4 dan CAGR ke 17–24%.

Catatan, bukan temuan yang diadopsi:
- Di versi realistis, menahan 40 bar memberi CAGR lebih tinggi daripada V0: "waktu 40" 18,6% dan "breakout gagal +
  waktu 40" 20,7% (MDD −38,6% vs −44,4%).
- Penjelasan yang mungkin: batas 25% ADV membuat modal banyak menganggur, jadi posisi yang ditahan lebih lama memakai
  modal itu.
- Ini satu dari 15 sel dan gagal di versi tanpa batasan (0/4 subperiode). Kalau mau dikejar, harus diuji ulang
  pra-registrasi khusus di versi realistis.
- Holdout 1995–99 (deskriptif): V0 55,7%; waktu 20 67,5%; breakout gagal + waktu 20 70,5%. Hasilnya campur dan tidak
  dipakai memilih.

## Kesimpulan
- WR kita di bawah 50% terutama karena entry buy stop membeli sebelum breakout terkonfirmasi. 42% fill berakhir di bawah
  harga fill pada hari itu juga, dan aturan breakout gagal memotongnya dengan rugi kecil.
- Exit SMA30 dan memudarnya trend sejak 2011 menambah sisanya.
- WR bisa dinaikkan ke 50–70% dengan exit harga + waktu, tapi selalu dibayar dengan CAGR dan bulan rekor yang lebih
  rendah.
- Yang membuat Swinger ideal punya WR 49% sekaligus payout 4,9 adalah fill-nya yang tidak bisa dieksekusi, bukan
  exit-nya.
- AFL aktif tidak diubah.

## Batasan
- Universe survivor (Kompas100 2025).
- Langkah 1 eksploratif dan sudah dilihat sebelum grid langkah 2 dikunci.
- 15 sel diuji di satu data set.

## Tambahan: pembahasan lanjutan dan koreksi (26 Okt 2026, eksploratif)
Kode: `explore_failed_breakouts.py` (`failed_breakout_features.csv`) dan `winrate_exit_variants_realistic.py`
(`exit_variants_realistic.csv`). Varian exit tanpa batasan diambil dari grid v2 (`realistic_chase_v2_results/full_AB.csv`).

**Koreksi.** Kalimat "exit SMA30 memotong banyak trade di sekitar impas" salah.
- Exit SMA30 (341 trade): median keluar −2,0%, dan hanya 20% yang keluar dalam ±3%.
- Median puncaknya +12%. Jadi trade ini sempat naik lalu mengembalikan semua untungnya (give-back) sebelum Close jatuh di
  bawah SMA30.

**Trade breakout gagal.**
- Jumlahnya 213 trade, rata-rata −3,7%, median −3,0%. Mereka menyumbang 31% dari total rugi.
- Jumlah trade gagal naik dari periode ke periode:

  | | 2000-07 | 2008-15 | 2016-20 | 2021-25 |
  |---|---|---|---|---|
  | Porsi trade gagal | 20% | 24% | 34% | 34% |
  | Porsi trade gagal, versi realistis | 22% | 29% | 34% | 40% |
  | WR trade yang tidak gagal | 55% | 50% | 54% | 48% |

  Turunnya WR dari waktu ke waktu terutama datang dari makin seringnya breakout gagal di hari pertama.

**Bisakah kegagalan ditebak sebelum order** (kuintil fitur yang diketahui sebelum Open; galat ±3,5 pp per kelompok; banyak
perbandingan)?
- Kegagalan lebih sering:
  - setelah hari sebelumnya naik besar (kuintil teratas 35% vs 21–24%; realistis 41% vs 21%);
  - saat volume kemarin tinggi (35% vs 21%);
  - pada saham dengan volatilitas tinggi (40% vs 16%).
- Tapi expectancy kelompok itu tidak lebih rendah. Kuintil volatilitas tertinggi justru punya expectancy +10,4%, yang
  tertinggi. Filter seperti ini menaikkan WR tanpa menaikkan expectancy.
- Pembeda lain (ER, mom120, jarak ke level, umur level, Open vs level, kondisi pasar) tidak menunjukkan pola jelas.

**Varian yang sudah ada (B, 2000–25):**
| Varian | WR | CAGR | Bulan rekor | MDD | Realistis: WR / CAGR / rekor / MDD |
|---|---|---|---|---|---|
| V0 (pilihan utama) | 38,3% | 49,3% | 119 | −24% | 33,8% / 16,2% / 52 / −44% |
| Tanpa aturan breakout gagal | 46,0% | 47,6% | 119 | −30% | 41,7% / 19,4% / 62 / −37% |
| Trailing LLV5 setelah +2 ATR, tanpa aturan breakout gagal | 54,2% | 43,6% | 123 | −23% | 49,7% / 17,7% / 64 / −48% |
| Trailing + aturan breakout gagal | 43,9% | 37,4% | 114 | −23% | 40,3% / 14,7% / 54 / −44% |
| Buffer 1% | 40,4% | 47,1% | 117 | −25% | – |
| Tanpa buffer | 32,3% | 47,5% | 110 | −30% | – |
| Tunggu Close > HHV20, beli Open besok | 33,5% | 26,7% | 79 | −61% | – |

Menunggu konfirmasi Close tidak menaikkan WR dan memotong CAGR separuh.

Di versi realistis, tanpa aturan breakout gagal lebih baik di CAGR, bulan rekor dan MDD:
- subperiode 34,8 / 2,0 / 24,0 / 21,7% vs V0 28,7 / −0,3 / 25,5 / 17,0%, jadi lebih baik di 3 dari 4;
- di versi tanpa batasan hasilnya sedikit lebih buruk.

Aturan itu dipilih di universe tanpa batasan. Ini eksploratif dan belum diadopsi. Perlu uji pra-registrasi di versi
realistis.

## Tambahan: apakah V1 sudah mencampur harga dan waktu? (`v1_time_exit_check.py`, `v1_time_exit.csv`, eksploratif)
- Modul bulanan sudah berbasis waktu: entry di awal bulan, cek di akhir bulan.
- Modul breakout hanya berbasis harga. Satu-satunya unsur waktu adalah aturan breakout gagal di Close hari entry.

Hasil menambah unsur waktu ke trade breakout V1:

| Varian | WR tanpa batasan / realistis | CAGR tanpa batasan / realistis | MDD tanpa batasan / realistis |
|---|---|---|---|
| V1 | 41,4% / 34,4% | 45,4% / 19,7% | −25% / −45% |
| Exit asli + batas waktu 10 / 20 / 40 bar | 40–45% / 35–40% | 32–41% / 12–18% | −29…−32% / −40…−55% |
| Waktu saja 10 / 20 / 40 bar | 51–53% / 48–50% | 33–39% / 13–19% | −38…−46% / −47…−49% |
| Breakout gagal + waktu 10 / 20 / 40 bar | 43–47% / 40–42% | 31–44% / 11–18% | −36…−40% / −42…−54% |

WR ~50% tercapai dengan exit waktu saja. Tapi CAGR, bulan rekor dan MDD selalu lebih buruk dari V1. Ini sama dengan
temuan di V0.
