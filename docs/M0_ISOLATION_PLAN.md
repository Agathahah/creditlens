# M0 — rencana reproduksi terisolasi

2026-09-09. Dalam izin M0. Arahan terbaru Agatha menunda latihan sampai akhir dan meminta Codex melanjutkan pekerjaan teknis; COUNT dan tes M0 kini dapat dikerjakan Codex dengan atribusi bantuan yang jelas.

## Tujuan dan batas

Buktikan mekanisme input kosong → mart kosong → tes lama pass, lalu tambahkan tes yang mendeteksi kegagalan dan buktikan lulus setelah build dari fixture terisi. Ini tes software/data pipeline kecil, bukan training model atau rebuild database development.

## Lingkungan

- Gunakan binary PostgreSQL 16 yang sudah terpasang, tanpa instalasi atau container download.
- Script membuat direktori unik `/private/tmp/creditlens-m0-*` dengan permission 0700, cluster PostgreSQL baru dan socket privat. `listen_addresses=''` menonaktifkan TCP. Database `creditlens_m0`, role `creditlens_m0`, port socket 55439; bukan database localhost:5432/creditlens.
- Cluster baru memakai trust hanya di direktori socket privat; tidak mengubah authentication server yang sudah ada. Role ini khusus fixture, bukan konfigurasi produksi.
- Salin dbt project, models, macros, dan tests/dbt ke direktori kerja sementara. Buat profiles.yml baru dengan target cluster tersebut; jangan membaca profile/.env aktif untuk koneksi. Telemetri dbt dinonaktifkan.
- Jangan memakai target.schema saja sebagai isolasi: macro repo memaksa schema staging/mart. Server terpisah memastikan nama yang sama tidak mengenai data aktif.
- Fixture sintetis kecil; tidak menyalin borrower atau data pribadi. Raw schema disiapkan dengan definisi kolom yang dibutuhkan source; keterbatasan fixture dicatat.

## Urutan dan hasil yang diharapkan

| Langkah | Perubahan di cluster sementara | Bukti yang diharapkan |
|---|---|---|
| 1 | Membuat raw kosong dan menjalankan source dbt staging/mart | Semua model berhasil dibangun, loan/final 0 |
| 2 | Menjalankan tes bawaan | Tes lama pass walau mart kosong |
| 3 | Menjalankan tes nonempty tambahan | Gagal karena tabel wajib kosong; kegagalan yang diharapkan |
| 4 | Memasukkan dua loan sintetis dan satu bulan makro, tanpa rebuild mart | Staging melihat 2 loan, mart tetap 0; tes rekonsiliasi gagal |
| 5 | Menjalankan dbt build pada salinan project | Mart 2 loan, tes nonempty/rekonsiliasi dan tes bawaan pass |
| 6 | Menghentikan cluster sementara | Tidak ada server tes tertinggal; log/report disimpan |

## Eksekusi, cleanup dan hasil

Perintah dari root repo: `.venv/bin/python scripts/verify_m0_dbt.py`. Script menyimpan ringkasan dan log ke direktori sementara yang dicetak; bukti ringkas dapat disalin ke docs/audit. `finally` menghentikan cluster, termasuk ketika langkah gagal. File sementara tetap tersedia untuk diagnosis dan tidak mengubah target/log dbt utama. Tidak menghapus folder di luar direktori yang dibuat script. Jika izin socket ditolak sandbox, akses eksekusi lokal dapat diminta untuk script yang sama; tidak mengubah target menjadi database aktif.

Hasil aktual ditambahkan setelah eksekusi. Fixture kecil membuktikan perilaku transformasi/tes, bukan kebenaran label, performa model, kelengkapan ingestion atau kronologi bug historis.

## Hasil aktual

Selesai: lima model berhasil dibangun, 24 tes lama lulus pada kosong, nonempty gagal pada tiga relasi wajib kosong. Setelah ingestion fixture tanpa rebuild, counts 2/0/0 dan rekonsiliasi gagal. Build terisi menghasilkan 2/2/2 dengan 26 tes pass. Penghapusan satu final fixture juga terdeteksi; rebuild final memulihkan 2/2/2. Cluster dihentikan. Bukti: audit/M0_ISOLATED_TEST_REPORT.json. Raw schema memakai bagian DDL raw dari scripts/init_db.sql, tidak menjalankan setup Airflow/monitoring di bagian awal file.
