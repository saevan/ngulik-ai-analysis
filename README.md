# Ngulik AI Analysis

Workspace privat riset TimeHunter dan benchmark Swinger. Kode, data, laporan dan konteks penelitian tersedia dalam repository ini.

Mulai dari [HANDOFF_CONTEXT.md](HANDOFF_CONTEXT.md), [AGENTS.md](AGENTS.md), dan [kesimpulan terbaru](optimized_inverse_regime_results/CONCLUSION.md). Optimasi terakhir48simulasi selesai; belum ada kandidat lolos. AFL aktif belum diganti.

## Environment Codex Cloud

Nama yang disarankan: `Ngulik AI Analysis`.
Repository: `saevan/ngulik-ai-analysis`, branch `main`.
Python3.11; install/setup command: `bash scripts/setup.sh`.
Tidak membutuhkan secrets untuk backtest lokal. Instalasi memerlukan akses package manager; data sudah tersedia di repository.

Di Codex web: Work in > Cloud > Select environment > Create environment. Pilih repository ini, minta jalankan setup command, periksa hasil, lalu Publish. Konfigurasi repository ini belum berarti environment Codex sudah dipublikasikan.

Dokumentasi resmi: https://learn.chatgpt.com/docs/environments/cloud-environments

Sesudah environment siap, gunakan [PROMPT_LANJUTKAN.txt](PROMPT_LANJUTKAN.txt). File sudah berada dalam checkout; tidak perlu ekstrak/upload ZIP lagi.

## GitHub Codespaces (opsional)

Konfigurasi `.devcontainer/devcontainer.json` menyiapkan Python3.11 dan menjalankan setup yang sama saat Codespace dibuat. Tidak ada Codespace berbayar yang otomatis dinyalakan oleh snapshot ini.

## Verifikasi

20unit tests smoke lulus lokal Windows. Manifest mencakup1.875file snapshot penelitian asli; file konfigurasi repository tambahan berada di luar manifest. Setup Linux/cloud belum dijalankan di sesi asal. Beberapa skrip historis memiliki path Windows: lihat PORTABILITY_NOTES.md. Jangan menjalankan seluruh `test*.py` otomatis karena sebagian adalah runner eksperimen panjang.
