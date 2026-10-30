# Beli saat pantulan mulai, setelah penurunan (30 Okt 2026)
Rencana dikunci di `PLAN.md` sebelum hasil. Kode: `buy_the_turn.py`. Hasil: `results.csv`, `trades.csv.gz`.

Bug sebelum hasil dibaca: entry yang Open-nya sudah di atas target tercatat terjual di target (rugi palsu). Diperbaiki
dengan melewati trade seperti itu.

Setup: dalam 10 bar Close turun ≥ X% (10/15/20%) dari high 20 bar, dan masih ≥ X/2 di bawahnya. Pemicu: Close di atas
high 3 bar sebelumnya. Beli di Open besok. Target pulih 50% / 100% dari penurunan; stop Close di bawah low penurunan;
maksimal 10 bar. Versi realistis, biaya B.

Hasil: semua 12 sel rugi, dan lebih buruk dari entry acak di setup yang sama.
- Kotor −0,1…−1,1% vs kontrol acak +0,2…−0,7%.
- Bersih −1,3…−2,1% (t −2,9…−9,1).
- Rugi di hampir semua subperiode.
- Target 50%: WR 49–57%, tapi menang +2,6…+5,2% vs kalah −3,3…−7,1%.

Kesimpulan:
- Menunggu konfirmasi pantulan membuat kita membeli setelah hari naik (lebih mahal). Sisa geraknya acak, sementara stop di
  bawah low penurunan jauh.
- Pantulan setelah penurunan tidak bisa dimanfaatkan dengan data harian:
  - beli setelah turun ≈ acak;
  - buy limit di bawah harga: pantulan ada tapi < biaya;
  - beli saat berbalik: lebih buruk dari acak.

## Addendum: tanpa target, exit hanya lewat stop atau waktu (`buy_the_turn_notarget.py`, `notarget.csv`)
- Semua 12 sel rugi: bersih −1,5…−2,0% (t −1,8…−6,8). Kotor di bawah kontrol acak.
- WR 38–43%; WR impas 47–52%.
- Rata-rata menang +7,6…+13,6% vs kalah −6,1…−11,3%.

WR mean reversion di uji kita:
- Dengan target 50%: WR 49–57%, WR impas 65–71% (menang kecil +2,6…+5,2%, kalah besar −3,3…−7,1%).
- Dengan target 100%: WR 41–43%, WR impas 52–57%.
- Uji range sebelumnya (`choppy_range_module`): WR 55–62%, butuh sekitar 72% (menang +4,7% vs kalah −9,1%).
- Strategi mean reversion umumnya bergantung pada WR tinggi (sering disebut 60–75%) dengan payout < 1. Ini pengetahuan umum,
  bukan dari data kita. Di data harian IDX, WR yang tercapai selalu 5–20 poin di bawah WR impas.
