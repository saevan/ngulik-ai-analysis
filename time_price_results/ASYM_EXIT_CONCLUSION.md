# Exit asimetris "jijik rugi, sayang untung" (16 Okt 2026)

Aturan (klarifikasi pengguna): entry breakout (Close>HHV20 & ER20≥0,3, Open berikutnya). Status di Close sebelumnya menentukan acuan:
untung -> exit bila Low ≤ Open terbaru·(1−fp) (acuan diperbarui tiap bar); rugi -> exit bila Low ≤ harga masuk·(1−lp), atau sesudah lt Close
berturut-turut rugi (jam direset saat untung). Sinyal di Close, fill Open berikutnya. Portofolio 10 slot, fee + 1 fraksi + lot 100.
Grid 80 konfigurasi (fp 3/5/8/12%, lp 3/5/8/12%/tanpa, lt 5/10/20/tanpa); pilih 3 terbaik di train (CAGR, rekor ≥ median), lalu holdout/full + entry acak.
Kode `asym_exit_portfolio.py`, opsi `asym` di `backtest_open_next.py` (default mati, regresi identik). Hasil `asym_exit_portfolio.csv`.

## Karakter: tercapai
- Bar menang > bar kalah di 95% konfigurasi (pilihan: menang 363–598 bar, kalah 62–91 bar); payout > 2 di 73%; mean jauh di atas median.
- WR rendah: hanya 5% konfigurasi WR ≥ 50%; pilihan WR 19–29%.

## Kinerja
| Pilihan train | Train | Holdout | Full (satu run kontinu) | MDD full | Top-5 trade / laba |
|---|---:|---:|---:|---:|---:|
| fp12 lp3 lt20 | 22,4% | 29,6% | 12,3% | −48% | 82% |
| fp12 lp12 lt20 | 25,0% | 27,4% | 11,4% | −68% | 90% |
| fp12 lp– lt20 | 24,0% | 21,7% | 17,0% | −64% | 57% |
- Run kontinu 2000–2025 jauh lebih rendah dari kedua potongan: posisi pemenang ditahan ratusan bar dan memblok slot, jadi hasil sangat bergantung jalur (saham mana yang kebetulan dapat slot).
- Entry acak dengan exit sama: CAGR 6–11%, MDD −67…−80%. Sinyal breakout menambah ~3–9 pp.
- fp 3% buruk (median −9,9%), fp 8–12% terbaik; stop harga saat rugi tidak membantu (median tanpa lp 11,6% vs 5–9%); jam rugi 20 bar terbaik.
- Pembanding: SL3_T40 18,6% / −52% (engine sama); sistem UTS 15,8% / −31% (engine berbeda, buy stop + likuiditas).

## Kesimpulan
Karakter yang diinginkan (rugi dibuang cepat, untung ditahan lama) memang tercipta, tetapi tidak menghasilkan CAGR lebih tinggi secara stabil: full run 11–19% dengan MDD −47…−68%, laba terkonsentrasi di segelintir trade, dan WR jauh di bawah 50%. Universe survivor menguntungkan penahanan panjang, jadi angka ini cenderung optimistis.
