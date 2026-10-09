# Pembalikan sinyal utama: WR tinggi, belum profit sideways yang tahan biaya

18 simulasi selesai tanpa optimasi:3 interpretasi x2biaya x3periode. Acuan adalah modul penelitian Breakout20+ER saham20>=0.30 dengan exit Close<SMA30 atau fading2ATR dari Open bar berjalan. Bukan AFL aktif pullback (yang tidak mempunyai ER). Status strategi terkini belum terbukti lulus7kriteria; header AFL juga menyatakan demikian. ERsaham bukan ERpasar; entry utama dapat terjadi pada marketproxy sideways. Pembalikan sinyal tidak otomatis membuktikan adanya edge mean reversion.

## Interpretasi yang diuji

Yang dibalik adalah kondisi sinyal mentah, bukan tanggal transaksi terlaksana dari ledger utama. Long-only: original sell menjadi buy, original buy menjadi sell; bukan membuka short. Entry jika Close<SMA30 ATAU Open-Low>=2ATR14previous, lalu next tradable Open. Exit jika Close>HHVHigh20sebelumnya DAN ERsaham>=0.30, lalu next tradable Open. Entry tidak memakai filter range/cost8 dari eksperimen sebelumnya karena ini menguji pembalikan langsung.

market: entry ketika ERproxy pasar<0.30. market_stock: tambah ERsaham<0.30 pada bar sinyal. market_stock_stop: sama ditambah stop0.5entryATR berbasisClose/nextOpen. Dua versi murni tidak memakai stop/fading exit/hold tambahan. Tidak ada short. Semua exit diperbolehkan di luar choppy. Jika exit juga disyaratkan ERsaham<0.30 bersamaan originalbuy ERsaham>=0.30, kondisi itu mustahil terpenuhi; karena itu gate hanya membatasi entry. Switching entry tidak otomatis menutup posisi lama atau membebaskan modal.

## Hasil full4Jan2000–15Agustus2025

Rp1miliar,10slot,10%equity penutupan sebelumnya per entry dibatasi kas, compounding. Fee buy0.15%/sell0.25%. Spreadcounterfactual modern BEI1tick eachside+100shares, bukan orderbook/fraksi historis teramati.

| Varian | WR fee | Avg win fee | Avg loss fee | N | CAGR fee | CAGR spread | Sideways fee | Sideways spread |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Pasar choppy |66.13%|14.20%|19.99%|744|4.79%|-0.81%|-1.66%|-10.92%|
| Pasar+saham choppy |66.80%|13.75%|19.63%|753|4.77%|-0.60%|-2.68%|-11.43%|
| Pasar+saham+stop0.5 |19.52%|16.68%|3.99%|4432|-2.21%|-37.69%|-11.38%|-60.38%|

Sideways merupakan return tahunan ekuivalen atribusi return harian, bukan CAGR portofolio mandiri. Versi kedua murni: holding73.71bar, winner47.11bar, loser127.24bar;94trade rugi>20%,worst-90.29%.750exit originalbuy dan3terminal; pola bukan semata terminalmark. Cashsideways8.50%,MDD-68.55%,record61/308(19.81%),recordside38/280(13.57%). Cashrendah tidak berarti penggunaan modal produktif. StockERchoppy hanya pada entry tidak mencegah harga selanjutnya terus turun. Exit menunggu kondisi breakout baru dapat menahan posisi melemah lama; belum ada dekomposisi kausal faktor entry vs exit.

Swinger ideal sebagai target tetap: tradeentrychoppyWR50.46%,avgwin14.67%,avgloss3.21%,holding18.28bar. Jadi inversion WR sudah lebih tinggi tetapi loss jauh lebih besar dan payout0.70vs4.57. Bukan keberhasilan mengejar karakter benchmark secara keseluruhan.

Validasi fresh start market_stock spread:2016–2020 CAGR8.73%,sideways8.06%;2021–2025 CAGR-1.78%,sideways-9.13%. StopvarianttestspreadCAGR-22.45%. Hasil tidak konsisten lintasperiode, bukan edge robust. Riwayat sudah pernah diperiksa; bukan holdout independen. Tidak digabung/mainAFL tidak berubah.15unit tests lulus termasuk exit pada rezim nonchoppy, nextOpen execution, stock/market gate terpisah; prefix seluruhframe/eligibility/accounting juga diperiksa. NumPy warning inf*0 pada fade dinonaktifkan telah ditinjau: mask ATR>0 mengecualikan bar tersebut; bukan exit tambahan. Reproduksi backtest_choppy_inverted_signals.py, ledger/equity/comparison/PLAN/REPORT tersimpan.
