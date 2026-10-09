# Mulai di sini

1. Unggah Ngulik_AI_LENGKAP.zip ke percakapan web yang mendukung lampiran ZIP dan eksekusi Python, bersama HANDOFF_CONTEXT.md bila perlu agar konteks mudah dibaca.
2. Tempel isi PROMPT_LANJUTKAN.txt. Minta ekstrak ZIP, baca konteks dan verifikasi file sebelum melanjutkan penelitian.
3. Jika antarmuka Codex yang dipakai meminta repository/environment, ekstrak ZIP dan masukkan isinya ke repository privat, lalu hubungkan repository tersebut. ZIP adalah paket pemindahan file, bukan impor otomatis riwayat percakapan. Saya belum membuat atau mengunggah repository.

Dokumentasi resmi alur repository/cloud environment: https://learn.chatgpt.com/docs/environments/cloud-environment (dicek 9 Oktober 2026). Dukungan upload dan batas ukuran bergantung antarmuka; bila ZIP tidak diterima, gunakan alur repository tersebut.

ZIP memuat seluruh file penelitian yang terlihat di workspace: Python, AFL, Markdown, CSV, JSON, TXT dan input Data. Cache, folder tersembunyi, konfigurasi akun dan lingkungan lokal tidak disertakan. Ini ringkasan konteks terstruktur, bukan ekspor transkrip lengkap Claude/VS Code.

## Menjalankan setelah ekstrak

Gunakan Python3.11 atau versi kompatibel. Dari root folder hasil ekstrak:

```sh
python -m pip install -r requirements-handoff.txt
python verify_handoff.py
python -m unittest test_regime_rotation test_inverse_switch test_er_switch test_secondary_portfolio test_standalone_sideways test_breakout_er_portfolio test_idx_costs
```

Untuk audit hasil yang sudah ada, baca optimized_inverse_regime_results/comparison.csv, FROZEN.json dan CONCLUSION.md. Tidak perlu langsung mengulang48simulasi. Jika sengaja ingin hitung ulang semuanya:

```sh
python -u optimize_primary_inverse_regimes.py
```

Perintah tersebut menulis ulang output optimasi. --resume hanya memakai hasil cache yang sudah tersedia, bukan verifikasi hitung ulang. AFL memerlukan AmiBroker untuk uji native; Python di paket adalah mesin simulasi penelitian. requirements disematkan sesuai versi lokal yang sudah lulus tes; instalasi di web mungkin memerlukan akses paket.
