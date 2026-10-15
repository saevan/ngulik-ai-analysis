# Audit look-ahead bias: Model utuh dan Kandidat buy stop (15 Oktober 2026)

Kode `audit_lookahead.py`. Sistem: (A) Model utuh = sistem 1 breakout HHV20 + ER saham + gate ER pasar, ditambah modul choppy breakout ER saham ≥0,5 maks 5 slot, semua Open(i+1) (`backtest_two_module.py`); (B) Kandidat buy stop = buy stop HHV20 (ER20 bar sebelumnya ≥0,3), lewati gap up >2%, jual di Close bila exit tertunda dan Open gap down >2%, urutan mom120 (`backtest_stop_execution.py`).

## 1. Uji pemotongan data (sinyal + mesin)
Data dipotong di 2008-06-30, 2016-01-15, 2021-03-31; proxy pasar, ranking, dan indikator dihitung ulang hanya dari data terpotong. Hasil: **equity harian dan semua trade yang selesai sebelum tanggal potong identik** dengan run data penuh, untuk kedua sistem di ketiga tanggal. Label rezim ER pasar pada data terpotong juga identik. Artinya tidak ada keputusan yang memakai data sesudah tanggal keputusan.

## 2. Pemilihan fill buy stop (look-ahead intrahari)
Versi default memilih saham berdasarkan prioritas di antara saham yang benar-benar tersentuh level pada hari itu (diketahui di akhir hari) saat slot/kas terbatas. Versi ketat: sebelum Open, order hanya dipasang untuk K saham prioritas teratas (K = slot kosong); hanya order itu yang bisa terisi.

| Versi | Fee | Spread 1 tick |
|---|---|---|
| Buy stop default | 48.5% / 136 / MDD −24.9% (2281 trade) | 28.1% / 100 / −43.9% |
| **Buy stop order book ketat (kausal penuh)** | **44.4% / 137 / −18.4% (1669 trade)** | **28.8% / 104 / −30.5%** |
| Model utuh (Open(i+1)) | 34.1% / 105 / −32.0% | 17.2% / 67 / −46.8% |

Default sedikit melebih-lebihkan CAGR fee (+4,1 pp). Versi ketat tetap di atas model utuh dan bahkan lebih baik pada spread dan MDD. Angka resmi buy stop sebaiknya memakai versi ketat.

## 3. Universe (survivorship = look-ahead pada pemilihan saham)
100 ticker; 36 sudah ada di Januari 2000, 51 baru listing sesudah 2005; **tidak satu pun berhenti sebelum 2025** (semua punya data sampai 15 Agustus 2025). Daftar ini adalah saham yang bertahan sampai sekarang, bukan konstituen Kompas100 historis per tanggal. Saham yang delisting, bangkrut, atau keluar indeks tidak ada di data. Ini bias melihat masa depan pada universe dan membuat hasil semua sistem (termasuk Swinger) terlalu optimistis; besarnya tidak bisa diukur tanpa data konstituen historis.

## 4. Hal lain yang bukan look-ahead sinyal tetapi membuat hasil optimistis
- Harga tampak disesuaikan (corporate action) sehingga level harga lama tidak sama dengan harga riil saat itu; ini memengaruhi model biaya tick, bukan sinyal.
- Banyak konfigurasi diuji pada data yang sama dan beberapa tuas dipilih sesudah melihat validation/test (data snooping).
- `tradable` (volume > 0) pada hari entry dipakai untuk menolak fill; ini pembatasan konservatif (tidak memilih pemenang), bukan sumber profit.

## Kesimpulan
- Sinyal dan eksekusi kedua sistem lulus uji look-ahead (uji pemotongan identik).
- Buy stop punya look-ahead intrahari kecil pada pemilihan fill; sudah diperbaiki dengan opsi `strict_orders` dan hasilnya tetap unggul.
- Universe survivorship tidak lulus: data hanya berisi saham yang bertahan; ini bias terbesar yang tersisa dan berlaku untuk semua sistem.
