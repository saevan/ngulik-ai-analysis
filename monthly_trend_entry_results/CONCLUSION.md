# Unsur waktu: beli saham yang sedang trending di awal bulan (26 Okt 2026)

Rencana dikunci di `PLAN.md` sebelum hasil, untuk langkah 1 dan langkah 2.
- Kode: `monthly_trend_entry.py` (langkah 1), `monthly_watchlist_gate.py` (langkah 2), `monthly_watchlist_robustness.py`
  (cek tetangga, post hoc).
- Mesin dapat opsi baru `entry_mode='signal'` / `signal_fn` / `exit_signal_fn` (default mati; uji regresi lulus).
- Cek mekanisme: di versi realistis 100% entry jatuh di hari bursa pertama bulan itu dan 99–100% exit bulanan di hari
  pertama bulan berikutnya. Di versi tanpa batasan 7–12% entry tertunda karena saham tidak ditransaksikan hari itu.
- Biaya B, 2000-01-01..2025-08-15.
- Pembanding: Swinger ideal (WR 48,8%, expectancy +6,5%, 1,88R, 126 trade/th, 102,0%, 232 bulan rekor, MDD −21%).
  Sistem kita V0 sebagai acuan.

Filter "sedang trending" dicek di Close akhir bulan:

| Filter | Syarat |
|---|---|
| F_sma30 | Close > SMA30 |
| F_sma120 | Close > SMA120 |
| F_er | ER20 ≥ 0,3 dan naik 20 bar |
| F_high | Close ≥ 95% dari Close tertinggi 120 bar |
| F_mom | Close > Close 120 bar lalu |

## Langkah 1: sistem bulanan berdiri sendiri (beli di Open hari pertama bulan, urutan mom120)
Angka dalam versi realistis; tanpa batasan dalam kurung.

| Sel | WR | E/trade | E_R | Trade/th | CAGR | Bulan rekor | MDD |
|---|---|---|---|---|---|---|---|
| V0 (sistem kita) | 33,8% | +2,5% | 0,52R | 34 | 16,2% (49,3%) | 52 (119) | −44% (−24%) |
| F_mom, keluar saat filter gagal di akhir bulan, 25% | 41,1% | +21,1% | 1,31R | 9 | 16,7% (40,1%) | 62 (82) | −56% (−70%) |
| F_mom, keluar saat filter gagal, 10% | 42,6% | +18,3% | 1,18R | 15 | 17,3% (35,1%) | 66 (96) | −53% (−50%) |
| F_sma120, keluar saat filter gagal, 10% | 38,2% | +12,0% | 0,92R | 21 | 16,1% (40,6%) | 54 (109) | −57% (−52%) |
| F_er, keluar saat filter gagal, 10% | 46,6% | +1,3% | 0,17R | 44 | 4,6% (20,1%) | 40 (81) | −41% (−41%) |
| F_high, keluar saat filter gagal, 10% | 44,0% | +2,6% | 0,31R | 34 | 8,0% (24,6%) | 44 (94) | −35% (−43%) |
| Filter apa pun + exit sistem kita | 31–36% | +0,5…1,6% | – | 24–85 | 3,5–7,9% | 26–36 | −35…−55% |
| Kontrol: pilih acak, pegang 1 bulan | 46–49% | ≈0% | – | 49 | −4,8…+3,3% | 17–21 | −72…−93% |
| Kontrol: tanpa filter, urutan mom120, exit sistem | 32,1% | +1,0% | – | 40 | 7,1% | 27 | −49% |

Hasil (kriteria PLAN): tidak ada sel yang lolos. Sel F_mom gagal karena MDD −53…−56%, hanya 2 dari 4 subperiode lebih
baik dari V0, dan WR < 45%.

Observasi:
1. Membeli tiap awal bulan tidak membawa WR ke 50%.
   - WR tertinggi ada di F_er (46–47%), tapi expectancy-nya hanya +1,3…1,8%.
   - Pegang 1 bulan dengan pilihan acak juga memberi WR 46–49% dengan expectancy ≈ 0.
   - Jadi WR ~50% dari pegang berbasis waktu adalah tingkat lempar koin, bukan tanda edge.
2. Filter trending penting.
   - Dengan waktu entry yang sama, F_mom/F_sma120 + exit bulanan memberi 15–17%/th di versi realistis.
   - Tanpa filter: 7,1% (urutan mom120) dan ≤ 3,3% (pilih acak).
3. Hasil terbaik (F_mom bulanan) karakternya lain dari sistem kita:
   - sedikit trade (9–15/th), pegang sekitar 5 bulan (median 100 bar);
   - expectancy besar (+18…21%/trade, 1,2–1,3R);
   - modal terpakai 88–94%;
   - CAGR realistis setara V0, bulan rekor lebih banyak, tapi MDD jauh lebih dalam.
4. Entry bulanan + exit sistem kita buruk. Exit SMA30 menjual posisi bulanan rata-rata setelah 9–10 bar.

## Langkah 2: filter awal bulan sebagai daftar pantau untuk buy stop sistem kita
Sepanjang bulan m, buy stop hanya aktif di saham yang lolos filter pada Close terakhir bulan m−1.

| Daftar pantau | Lolos filter | WR (tanpa batasan / realistis) | CAGR realistis | Rekor | MDD realistis | Subperiode ≥ V0 | CAGR tanpa batasan |
|---|---|---|---|---|---|---|---|
| V0 (semua saham) | 100% | 38,3% / 33,8% | 16,2% | 52 | −44% | – | 49,3% |
| F_mom (Close > Close 120 bar lalu) | 48% | 38,6% / 34,3% | 17,5% | 57 | −44% | 3 dari 4 | 49,3% |
| F_sma120 | 48% | 38,8% / 34,0% | 18,1% | 52 | −38% | 1 dari 4 | 52,9% |
| F_sma30 | 48% | 36,7% / 33,5% | 10,4% | 34 | −61% | – | 45,8% |
| F_er | 17% | 37,9% / 32,8% | 10,8% | 36 | −41% | – | 37,7% |
| F_high | 19% | 35,9% / 31,3% | 9,1% | 35 | −51% | – | 32,6% |
| Acak 50% (3 seed) | 50% | – | 8,3–12,9% | 37–48 | −42…−50% | – | 31,9–45,0% |
| Acak 70% (3 seed) | 70% | – | 14,9–15,6% | 49–55 | −39…−44% | – | 44,8–46,4% |

F_mom lolos semua kriteria langkah 2, tapi tipis: +1,3 pp CAGR realistis dan +5 bulan rekor. WR hampir tidak berubah
(+0,3…0,5 pp).

Cek tetangga (post hoc):
- Versi realistis, lookback trend lain:

  | Filter | Close > Close 60 | 90 | 120 | 180 | 250 bar lalu | SMA60 | SMA120 | SMA200 |
  |---|---|---|---|---|---|---|---|---|
  | CAGR realistis | 16,8% | 19,1% | 17,5% | 14,6% | 17,1% | 15,6% | 18,1% | 17,4% |

  6 dari 8 di atas V0, dan MDD umumnya sama atau lebih baik (kecuali SMA60).
- Tanpa batasan: lookback pendek naik (60/90 bar: 55%; SMA60/120: 53%), lookback panjang turun (180/250 bar: 43–44%).
- Holdout 1995–99 (tanpa batasan): tanpa daftar pantau 55,7%; 120 bar 51,4%; 90 bar 77,3%; 180 bar 49,0%; SMA120
  56,1%. Hasilnya campur.
- WR di semua varian tetap 33–35% (realistis) dan 37–39% (tanpa batasan).

## Kesimpulan
- Unsur waktu (beli di awal bulan) + filter trending tidak menyelesaikan masalah win rate. WR sistem bulanan 38–47%; yang
  mendekati 50% expectancy-nya kecil, dan pegang 1 bulan acak pun sudah ~47%.
- Sebagai daftar pantau untuk sistem kita, filter trend jangka menengah (Close > Close 90–120 bar lalu atau > SMA120)
  memberi perbaikan kecil yang cukup konsisten di versi realistis: CAGR +1…3 pp, MDD sama atau lebih baik. Tapi WR tidak
  naik, karena trade kalah kita datang dari breakout yang gagal di hari pertama, dan filter bulanan tidak menyaring itu.
- Kandidat ini belum diadopsi. Kalau mau dikejar: uji pra-registrasi gabungan daftar pantau trend + tanpa aturan breakout
  gagal di versi realistis.
- AFL tidak diubah.

## Batasan
- Universe survivor.
- 30 + 5 + 8 varian di satu data set.
- Cek tetangga dan holdout dilakukan setelah melihat hasil langkah 2.

## Langkah 3 dan 4: entry bulanan DITAMBAHKAN, entry breakout tetap (klarifikasi pengguna)
Kode: `monthly_add_entry.py` (langkah 3), `monthly_add_entry_allowance.py` (langkah 4). Mesin dapat opsi entry kedua
(`extra_signal_fn`, `extra_exit_signal_fn`, `extra_size_div`, `extra_first`, `extra_priority`, `extra_max_frac`; default
mati; uji regresi lulus; V0 identik).

Desainnya: satu portofolio dengan modal dan slot bersama.
- Entry breakout dan exit-nya tidak diubah.
- Entry bulanan: saham yang lolos filter di Close akhir bulan dibeli di Open hari pertama bulan, dan dijual saat filter
  gagal di akhir bulan.

Langkah 3 (tanpa jatah modal). Masalahnya perebutan modal:
- Bulanan didahulukan (P1): posisi bulanan dipegang sekitar 5 bulan dan memakan modal. Trade breakout turun dari
  797 ke 28–70 (tanpa batasan), jadi praktis mengganti, bukan menambah. F_mom: realistis 20,0% tapi MDD −61%; tanpa
  batasan 38,8%, MDD −66%.
- Breakout didahulukan (P2): order buy stop pra-Open memesan seluruh kas setiap hari, jadi entry bulanan hanya dapat
  1–13 trade dalam 25 tahun. Hasilnya praktis sama dengan V0 (kontrol acak P2: 16,4–17,3% realistis).
- Pembagian modal tetap 50/50 (V0 + F_mom bulanan berdiri sendiri): realistis 18,7%, 67 bulan rekor, MDD −51%; tanpa
  batasan 46,4%, 115, MDD −27%.

Langkah 4 (bulanan didahulukan, tapi posisi bulanan maksimal A% dari ekuitas; order 10%):
| Varian | CAGR realistis | Rekor | MDD realistis | WR realistis | Subperiode ≥ V0 | Breakout tersisa | CAGR tanpa batasan | MDD tanpa batasan | WR tanpa batasan |
|---|---|---|---|---|---|---|---|---|---|
| V0 | 16,2% | 52 | −44% | 33,8% | – | 100% | 49,3% | −24% | 38,3% |
| F_mom, A 20% | 17,8% | 50 | −49% | 34,0% | 1 dari 4 | 86% / 82% | 42,0% | −40% | 37,5% |
| F_mom, A 35% | 18,6% | 64 | −48% | 33,7% | 3 dari 4 | 71% / 66% | 45,0% | −39% | 40,8% |
| F_mom, A 50% | 18,0% | 58 | −47% | 34,6% | 2 dari 4 | 56% / 48% | 39,4% | −45% | 38,8% |
| F_sma120, A 20–50% | 10,6–15,0% | 41–48 | −46…−52% | 32,5–33,2% | 0–2 | 58–86% | 38,9–45,6% | −29…−33% | 37,7–39,8% |
| Acak bulanan (3 seed), A 20–50% | 10,4–16,6% | 35–57 | −39…−51% | 39–45% | – | 61–92% | 34,8–48,7% | −22…−44% | 42–45% |

Hasil: tidak ada yang lolos.
- Varian terdekat F_mom A 35% gagal karena:
  - MDD tanpa batasan −39% (batas −29%);
  - breakout tersisa hanya 66% di versi tanpa batasan;
  - WR realistis tidak naik.
- Trade bulanan sendiri punya WR 41–43% dan expectancy besar (+14…+56%/trade), tapi menggeser sekitar 30% trade
  breakout.
- WR gabungan versi realistis tetap 34%.
- Tambahan acak menaikkan WR gabungan ke 39–45% tanpa menaikkan return. Lagi-lagi WR naik tanpa edge.

## Kesimpulan akhir (langkah 1–4)
- Unsur waktu, baik sebagai pengganti, daftar pantau, maupun tambahan, tidak membawa WR sistem kita ke dekat Swinger ideal
  (48,8%).
- Yang konsisten: trend jangka menengah (Close > Close 90–120 bar lalu) sedikit menaikkan CAGR realistis (+1…3 pp) dan
  bulan rekor. Tapi di versi tanpa batasan selalu ada harga (CAGR turun atau MDD lebih dalam), kecuali sebagai daftar
  pantau.
- Penyebab WR rendah tetap breakout yang gagal di hari pertama. Itu masalah waktu entry di dalam hari, bukan pemilihan
  saham per bulan.

## Dampak menambahkan beli awal bulan (F_mom, jatah 35%; rincian) – `impact_monthly_add.py`, `impact_*.csv`
| | V0 realistis | + bulanan realistis | V0 tanpa batasan | + bulanan tanpa batasan |
|---|---|---|---|---|
| CAGR | 16,2% | 18,6% | 49,3% | 45,0% |
| Bulan rekor | 52 | 64 | 119 | 116 |
| MDD | −44% | −48% | −24% | −39% |
| WR gabungan | 33,8% | 33,7% | 38,3% | 40,8% |
| Modal terpakai | 48% | 64% | 49% | 65% |
| Trade breakout | 861 | 609 (413 sama, 448 hilang, 196 baru) | 797 | 529 (337 sama, 460 hilang, 192 baru) |
| Trade bulanan | – | 218, WR 41%, +21%/trade, ±133 bar, 47% laba | – | 235, WR 42%, +40%/trade, ±140 bar, 20% laba |

Return tahunan per kondisi pasar (modal terpakai dalam kurung):
| | Uptrend | Sideways | Downtrend |
|---|---|---|---|
| V0 realistis | 34% (72%) | 10% (41%) | 5% (14%) |
| + bulanan realistis | 40% (80%) | 10% (60%) | 13% (40%) |
| V0 tanpa batasan | 113% (70%) | 33% (43%) | 7% (14%) |
| + bulanan tanpa batasan | 81% (78%) | 34% (62%) | 26% (42%) |

Per tahun:
- Realistis lebih baik di 14 dari 26 tahun (median +2,1 pp; terbaik 2003 +45 pp; terburuk 2007 −35 pp).
- Tanpa batasan lebih baik di 12 dari 26 tahun (median −1,5 pp; 2021 −149 pp).

Interpretasi:
- Beli awal bulan memakai kas yang menganggur dan menambah eksposur saat downtrend dan sideways. Return downtrend naik,
  tapi MDD ikut lebih dalam.
- Modul ini juga mengubah separuh trade breakout lewat perebutan modal dan slot.
- Di versi tanpa batasan, trade breakout yang hilang adalah pemenang besar saat uptrend, sehingga hasilnya lebih buruk.
- WR gabungan tidak berubah.

## Kenapa naik saat uptrend dan downtrend? – `impact_monthly_why.py`, `why_*.csv` (eksploratif)
Metodenya:
- P&L harian tiap trade (ditandai di Close) dipisah per jenis posisi dan per kondisi hari itu.
- Kontribusi = P&L / ekuitas kemarin, dijumlah sederhana × 252, sehingga bagian-bagiannya bisa dijumlah.
- Kontrol: tambahan bulanan acak (jatah modal sama, saham dipilih acak, dipegang 1 bulan).

Versi realistis (kontribusi per tahun):
| Kondisi | V0 total | + bulanan F_mom: total = breakout + bulanan | + bulanan acak (3 seed): total |
|---|---|---|---|
| Uptrend | 32,9% | 36,9% = 22,7% + 14,5% | 31,9–36,3% |
| Sideways | 11,4% | 11,4% = 6,9% + 4,7% | 5,3–11,8% |
| Downtrend | 5,8% | 13,6% = −0,1% + 12,9% | 3,6–7,7% |

Versi tanpa batasan:
| Kondisi | V0 total | + bulanan F_mom: total = breakout + bulanan | + bulanan acak (3 seed): total |
|---|---|---|---|
| Uptrend | 80,4% | 62,9% = 44,8% + 18,5% | 65,7–75,5% |
| Sideways | 31,0% | 32,2% = 25,2% + 7,3% | 24,3–27,4% |
| Downtrend | 8,0% | 24,8% = 11,2% + 13,0% | 3,4–13,8% |

Cek pasar tanpa sistem: rata-rata equal-weight saham yang layak (realistis), dikelompokkan menurut lolos/tidaknya F_mom di
akhir bulan sebelumnya.
| Kondisi | Lolos F_mom | Tidak lolos |
|---|---|---|
| Uptrend | 31,8% | 44,0% |
| Sideways | 6,3% | −0,5% |
| Downtrend | 28,7% | 1,2% |

Rata-rata aritmetik ini terlalu tinggi secara absolut; yang dibaca hanya selisihnya.

Interpretasi:
- **Downtrend: efek pemilihan saham.** Breakout kita hampir tidak memegang apa-apa (modal terpakai 14%). Posisi bulanan
  di saham yang trend 6 bulannya naik bertahan jauh lebih baik saat pasar turun. Tambahan acak dengan modal yang sama
  tidak memberi efek ini.
- **Uptrend (realistis): efek modal tambahan.** Tambahan acak memberi kenaikan yang mirip. Breakout kehilangan sekitar
  10 pp karena tergusur, dan posisi bulanan menambah sekitar 15 pp.
- **Uptrend (tanpa batasan): yang menang adalah efek tergusur.** Kontribusi breakout turun dari 81% ke 45%.
- Saat uptrend, saham momentum justru kalah dari saham lain (31,8% vs 44,0%), jadi keunggulan F_mom hanya ada saat
  pasar turun dan sideways.

## Langkah 5: ER pada entry bulanan (klaim pengguna: modul berguna saat market trending) – `monthly_add_er_gate.py`
Rencana dikunci sebelum hasil. Robustness (post hoc): `monthly_add_er_robustness.py`.

Prediksi ER market akhir bulan:
- Bila ER20 market ≥ 0,3 di akhir bulan, 59% hari bulan berikutnya trending.
- Bila < 0,3, hanya 32% (tanpa syarat: 45%).
- Jadi prediksinya ada, tapi tidak kuat.

| Varian (jatah 35%) | CAGR realistis | Rekor | MDD | WR | CAGR tanpa batasan | Rekor | MDD | WR | Breakout tersisa |
|---|---|---|---|---|---|---|---|---|---|
| V0 | 16,2% | 52 | −44% | 33,8% | 49,3% | 119 | −24% | 38,3% | 100% |
| + bulanan tanpa ER (G0) | 18,6% | 64 | −48% | 33,7% | 45,0% | 116 | −39% | 40,8% | 71% / 66% |
| + bulanan, entry hanya saat market trending (G1) | 16,8% | 58 | −40% | 33,4% | 47,3% | 119 | −40% | 39,8% | 78% / 76% |
| G1 + jual saat market sideways (X1) | 16,5% | 58 | −38% | 37,0% | 50,3% | 124 | −32% | 42,0% | 89% / 90% |
| ER market & ER saham + X1 (G3) | 17,6% | 57 | −43% | 37,5% | 48,2% | 115 | −24% | 41,2% | 94% / 92% |
| ER saham ≥ 0,3 (G2) | 19,7% | 63 | −45% | 34,4% | 45,4% | 127 | −25% | 41,4% | 75% / 72% |

Swinger ideal: 102,0% / 232 / −21% / WR 48,8%.

Return tahunan per kondisi (realistis, uptrend / sideways / downtrend):
| Varian | Uptrend | Sideways | Downtrend |
|---|---|---|---|
| V0 | 34% | 10% | 5% |
| G0 | 40% | 10% | 13% |
| G1 + X1 | 45% | 6% | 2% |
| G3 + X1 | 37% | 11% | 4% |
| G2 | 43% | 10% | 16% |

Hasil (kriteria PLAN):
- **"ER membantu"** (versi ER market mengalahkan versi tanpa ER di kedua versi dengan MDD tidak lebih dari 2 pp lebih
  dalam): terpenuhi di 4 dari 8 sel ER market, tapi hampir semuanya pada pembanding G0+X1 yang lemah. Terhadap G0+X0
  (versi tanpa ER terbaik), ER market:
  - menurunkan CAGR realistis (16,5–17,6% vs 18,6%);
  - mengurangi MDD dan breakout yang tergusur;
  - menaikkan WR sedikit (37–38% realistis);
  - membuat versi tanpa batasan setara V0.
- **Yang lolos semua kriteria kandidat hanya ER saham (G2)**, bukan ER market.
- Robustness G2 (ambang ER saham 0,2–0,4 × jatah 25–45%):
  - Realistis: 14 dari 15 sel ≥ V0 (15–23%). Tapi median subperiode yang ≥ V0 hanya 2 dari 4.
  - Tanpa batasan: 39–50%, dan MDD dalam (−45…−49%) di ambang 0,2–0,25.
  - Holdout 1995–99: 52,5–55,2% vs V0 55,7%, MDD lebih dalam.

Interpretasi:
- Keuntungan modul bulanan saat downtrend datang dari posisi yang dibeli SEBELUM market turun.
- Membatasi entry/exit dengan ER market memotong manfaat itu: downtrend turun dari 13% ke 2–4%. Yang tersisa adalah
  versi "lebih jinak": lebih sedikit breakout tergusur, MDD lebih kecil.
- ER saham sebagai filter tambahan sedikit lebih baik di versi realistis, tapi belum konsisten antar periode.
- WR tetap jauh dari Swinger ideal.
- Tidak ada yang diadopsi.
