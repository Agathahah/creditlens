# M0 — pemulihan mart development

2026-09-09. Melanjutkan pekerjaan M0 setelah pengguna menunda latihan sampai akhir. Bukan deployment, training penuh, atau perubahan metadata Git.

## Dasar tindakan

Snapshot read-only kini membuktikan staging 1.599.982, loan_features 0 dan final_features 0. Reproduksi PostgreSQL terisolasi lulus: build dari raw kosong → tes lama 24 pass, tes baru nonempty gagal; ingestion dua fixture tanpa rebuild → staging 2/mart 0; rebuild → seluruh 26 tes pass. Tes rekonsiliasi juga menangkap satu baris final yang sengaja dihapus di cluster sementara. Server tes sudah dihentikan. Lihat audit/M0_ISOLATED_TEST_REPORT.json.

## Scope dan urutan

1. Target harus `localhost:5432/creditlens` seperti snapshot; gunakan credential lokal tanpa menampilkannya. Periksa kembali counts sebelum mutation. Hentikan jika loan/final tidak lagi kosong atau staging kosong: state harus direview kembali.
2. Buat direktori privat unik `/private/tmp/creditlens-m0-recovery-*`. Simpan dump custom-format untuk **hanya** mart.loan_features dan mart.final_features sebelum rebuild, berikut checksum. Verifikasi daftar isi backup melalui pg_restore --list. Backup ini bukan backup seluruh database; raw tidak disentuh.
3. Salin dbt project, models, macros, tests ke direktori kerja itu. Profile baru menunjuk database yang diverifikasi dan mengambil password dari environment proses, bukan literal file. Gunakan satu thread, timeout statement terbatas, telemetri off. Target/log historis utama tidak ditimpa.
4. Jalankan `dbt build --select loan_features final_features` pada salinan tersebut. Ini mengganti dua hasil mart lokal dari staging/macro yang sudah ada; tidak menjalankan loader, FRED fetch, training, atau rebuild macro.
5. Verifikasi counts staging/loan/final sama dan nonzero serta tes yang dipilih pass. Simpan ringkasan results, log dan source hashes. Reproduksi sudah memverifikasi jumlah baris, bukan seluruh formula atau semua label/evaluasi.
6. Jika build gagal, simpan hasil/keadaan tanpa menghapus bukti. Backup dapat dipakai mengembalikan dua tabel ke kondisi sebelum perbaikan setelah meninjau keadaan parsial. Pemulihan memakai pg_restore --clean --if-exists hanya pada archive dua tabel tersebut; tidak pernah menjalankan DROP SCHEMA raw/CASCADE sebagai shortcut.

## Batas dan konsekuensi

Pembentukan tabel menggunakan ruang disk dan dapat mengambil lock singkat saat rename; periksa ruang cukup sebelum mulai. Belum ada traffic layanan yang diverifikasi, dan pengujian bukan beban produksi. dbt build yang gagal tes tidak otomatis rollback seluruh DAG; hasil build dan hasil tes harus dicatat terpisah. Backup sebelum tindakan melindungi keadaan sebelumnya, bukan jaminan restore drill sudah dilakukan. Runbook restore ini belum dianggap lulus sebelum benar-benar diuji.

Perbaikan ini memulihkan materialisasi dan menambahkan deteksi kegagalan. Ia tidak membuktikan kapan/mengapa ingestion historis mendahului atau mengikuti build, tidak memperbaiki preprocessing/label, serta tidak memberikan bukti performa model.

## Hasil percobaan 9 September

Percobaan pertama: state sesuai rencana, tetapi preflight disk gagal pada sekitar 1,9 GiB, di bawah guard konservatif 2 GiB. Berhenti sebelum backup/dbt build. Bukti historis: audit/M0_MART_RECOVERY_PREFLIGHT_REPORT.json.

Setelah Agatha melonggarkan disk, preflight 7,129 GiB lulus. Backup dua mart kosong dibuat (4.707 byte), daftar isi/checksum diverifikasi, lalu dua model dibangun dan 9 tes pass. Staging/loan/final masing-masing 1.599.982 baris; disk sesudah run 5,954 GiB. Backup disalin ke direktori privat .local-backups yang diabaikan Git; path/checksum ada di audit/M0_MART_RECOVERY_REPORT.json. Raw, macro dan definisi fitur/label tidak diubah. Restore drill terhadap archive belum dijalankan; jangan menyebutnya teruji hanya karena dump/TOC valid.
