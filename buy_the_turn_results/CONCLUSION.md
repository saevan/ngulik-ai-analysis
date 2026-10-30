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
