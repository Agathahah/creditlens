# Arsip eksekusi M0 — 10 September 2026

Salinan script diagnosis/operasi yang dipakai untuk pemulihan lokal, disimpan agar langkah bisa diaudit sesudah direktori temp hilang. Ini arsip satu kali dengan guard state, bukan entry point operasional umum. Tidak memuat password: koneksi dibaca dari `.env` saat eksekusi, tidak dicetak. Jangan menjalankan ulang script mutation tanpa memeriksa prasyarat state; sebagian sengaja menolak state sesudah recovery. Backup raw dan payload tetap privat di `.local-backups`, tidak disalin ke sini.

Urutan: CSV dryrun → backup → restore drill → resume_live (migration dan insert-missing) → rebuild_after_ingestion → verify ID → label_feasibility. Verifikasi ID dijalankan bersamaan dengan rebuild; contoh mart di laporan ID bukan bukti timestamp rebuild terbaru. Laporan dbt menyatakan keberhasilan build secara terpisah.

Script restore yang diarsipkan memakai path socket pendek di `/private/tmp`; percobaan pertama memakai path terlalu panjang dan server gagal mulai. Perbaikan hanya pada lokasi cluster uji. Script menghentikan server dan menghapus hanya `pgdata` buatan script setelah restore sukses. Owner/ACL tidak diuji (`--no-owner --no-privileges`).

Untuk pengujian fixture yang dapat diulang, gunakan `scripts/verify_m0_ingestion.py`. Untuk impor terencana, entry point publik ialah `python -m scripts.load_data --source lending_club --csv-path <file> --insert-missing`, setelah skema/migration dan backup diverifikasi. Jangan ulang impor untuk memeriksa COUNT.
