# Log riset 15–21 Oktober 2026 (ringkasan percakapan dan hasil)

Ringkasan permintaan pengguna dan jawabannya. Rincian, angka lengkap dan batasan ada di `CONCLUSION.md` tiap folder.
Semua uji: rencana dikunci (PLAN.md di-commit) sebelum hasil, angka dicek ulang pemeriksa independen. AFL aktif tidak
pernah diubah. Biaya B = fee 0,15%/0,25% + slippage 0,25% per sisi (round trip 0,90%), kecuali disebut lain.

## Mengejar Swinger ideal
- `swinger_like_system_results/`, `overfit_results/`, `lookahead_audit_results/`, `sk5_regime_results/`: SK-5 dan kandidat
  awal; aturan fill ketat (High > level) ternyata terlalu optimistis; parameter SK-5 tidak lolos uji overfitting.
- `realistic_chase_v2_results/`: uji ulang dengan eksekusi dikoreksi. Pilihan utama v2 = buy stop 0,5% di atas HHV20 (grid
  harga), ER20 ≥ 0,2, urutan mom120, gap 2%, exit fade 2 ATR / Close < SMA30 / breakout gagal, 25% ekuitas per order.
  B 2000–25: 49,3% CAGR / 119 bulan rekor / MDD −24% vs Swinger ideal 102,0% / 232. Tidak ada sistem kausal yang
  mendekati; fill Swinger ideal tidak bisa dieksekusi.

## Sifat pasar
- `market_properties_v2/`: 62 uji pra-registrasi. Yang bisa dipakai hanya sebagai aturan di dalam sistem: buy stop di atas
  level (W1.5), filter ER (W1.7), jual di Close saat Open gap down (melemah sejak call auction 9 Des 2024). Trend jangka
  pendek memudar sejak 2011 (≈0 di 2021–25); pola overnight/intraday berbalik sejak 2013; efek Senin hilang; premi
  ilikuiditas = artefak daftar Kompas100 2025.
- `property_levers_results/`: menerapkan sifat-sifat itu sebagai tuas portofolio tidak menaikkan hasil; hanya
  `gapdown_close` terkonfirmasi.

## Survivorship, data basi, likuiditas
- `pit_universe_results/`: hanya saham yang likuid saat itu + filter data basi + batas order 25% ADV20: CAGR 2000–25
  turun dari 49% ke sekitar 16% (MDD −44%). Separuh entry versi lama membeli lebih dari seluruh transaksi hari itu.
  Survivorship penuh belum bisa dihapus: data saham delisting tidak ada dan jaringan sesi memblokir sumber data.
- `regime_breakdown_results/`: versi realistis uptrend 34%/th, sideways 10%, downtrend 5%.

## Logika kedua untuk sideways (semua gagal setelah biaya)
- `sideways_swings_results/`: ayunan sideways banyak (±410/th ≥5%), sistem hanya ikut 5%.
- `atr_dip_limit_results/`: buy limit x ATR di bawah Close: pantulan ada, terlalu kecil.
- `choppy_range_module_results/`: beli di bawah range saat choppy: rugi sebelum biaya.
- `sideways_dip_property_results/`: beli koreksi saham kuat di Close, jual di Open: +0,34% kotor, di bawah biaya.
- `sideways_properties/`: saat sideways range tidak dihormati lebih dari kebetulan; arah keluar tidak bisa ditebak.
- `lowest_low_time_results/`: entry lowest low + x bar, exit tanpa puncak baru x bar: entry ≈ acak; ER saham/pasar tidak
  menolong.
- `mid_atr_sideways_results/`: titik tengah + ATR per lebar range: rugi; range lebar positif tapi rapuh.
- `established_range_results/`: range yang sudah bolak-balik: pantulan lebih sering tapi kecil, rugi sebelum biaya.
- `range_size_modules_results/`: range kecil/menyempit vs besar, fade vs breakout: fade rugi; breakout ≈ breakout HHV20
  sistem utama, ≈0 setelah biaya dengan fill di grid.
Kesimpulan: di data ini tidak ada logika sideways berbasis level harga yang menutup biaya. Arah yang tersisa: parkir dana
menganggur, data point-in-time (termasuk delisting), forward test sesudah 2025-08-15.

## Lain-lain
- Dashboard pemindai harian dengan data Yahoo Finance: belum ada; ditunda pengguna (Yahoo diblokir jaringan sesi).
- Repo: https://github.com/saevan/ngulik-ai-analysis (branch `claude/blissful-mccarthy-mufwoy`), private.

## 26 Oktober 2026 – Keunggulan dan kelemahan vs Prototype Swinger
- `compare_vs_swinger_results/`: perbandingan karakter lengkap (B 2000–25). Ringkasan di CONCLUSION.md folder itu:
  kita 49,3% (realistis 16,2%) vs Swinger ideal 102,0% (dengan batasan realistis yang sama 31,9%); versi Swinger yang
  bisa dieksekusi 14,9% (next Open, MDD −64%) atau runtuh (stop order). Kelemahan utama kita: win rate 38%, modal
  terpakai 49%, bulan rekor 119 vs 232, lemah saat sideways/downtrend, bergantung pada saham listing baru.
