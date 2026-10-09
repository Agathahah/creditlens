# M0 — persiapan penerapan label pada database aktif

Status 11 September 2026: kontrak label, tes sintetis, backup terbaru, pemulihan backup, simulasi label dan rollback terisolasi selesai. Penerapan pada database aktif kemudian disetujui pada 12 September 2026; status pelaksanaan terbaru ada di bawah.

## Kondisi yang telah diperiksa

| Bagian | Hasil |
|---|---|
| Target baca-saja | Database creditlens, pengguna creditlens, localhost port 5432; transaction_read_only=on |
| Server aktif | PostgreSQL 14.22 Homebrew |
| Migrasi | 4b7d2a91c608 |
| Raw / staging / dua mart | Masing-masing 2.260.668 record |
| Label pada staging dan kedua mart | 0: 1.076.751; 1: 290.066; NULL: 893.851 |
| Ketidaksesuaian dengan kontrak baru | 21.467 pada masing-masing layer, sesuai kelompok Late (31-120 days) |
| Kapasitas filesystem repo/backup saat pemeriksaan | Sekitar 17,2 GiB tersedia; perlu diperiksa ulang sebelum backup/restore/rebuild |
| Backup ingestion terdahulu | Memuat 1.599.982 record sebelum ingestion selesai; tidak cocok sebagai baseline perubahan label terbaru |
| Tes pada versi server yang sama | Cluster privat PostgreSQL 14.22: lima model dan 27 tes lulus, cluster dihentikan |

Bukti: [preflight baca-saja](audit/M0_LABEL_PREFLIGHT_REPORT.json), [tes PostgreSQL 14](audit/M0_LABEL_PG14_REPORT.json). Lokasi fisik data_directory tidak dapat dibaca oleh role aplikasi; angka ruang disk di atas adalah filesystem repo/backup, bukan bukti pemeriksaan seluruh volume database. Statistik sesi juga dibatasi hak akses dan tidak menjamin ketiadaan semua writer.

## Membuat backup baru

Jalankan pada Terminal dari folder repo. Perintah membaca database, mengambil lock baca yang diperlukan untuk dump, dan membuat file lokal. Tidak mengubah label, menjalankan training atau melakukan rebuild. Direktori unik mencegah penimpaan backup sebelumnya dan berada di .local-backups yang diabaikan Git. mktemp membuat direktori privat; file hasil juga diatur hanya dapat dibaca/ditulis pemiliknya.

```bash
cd /path/to/creditlens
mkdir -p .local-backups
label_backup_dir=$(mktemp -d "$PWD/.local-backups/m0-label-XXXXXX")
```

```bash
LC_ALL=C LANG=C PGOPTIONS='-c default_transaction_read_only=on' \
/opt/homebrew/opt/postgresql@14/bin/pg_dump \
  -h localhost -p 5432 -U creditlens -d creditlens \
  -Fc --lock-wait-timeout=5s \
  -t raw.lc_loans -t staging.lc_loans_clean \
  -t mart.loan_features -t mart.final_features \
  -t mart.macro_features \
  -f "${label_backup_dir:?}/before.dump" && \
chmod 600 "$label_backup_dir/before.dump" && \
/opt/homebrew/opt/postgresql@14/bin/pg_restore \
  --list "$label_backup_dir/before.dump" > "$label_backup_dir/toc.txt" && \
shasum -a 256 "$label_backup_dir/before.dump"
```

Jika diminta password, gunakan password pengguna PostgreSQL creditlens. Jangan menaruh password dalam perintah atau laporan. Operator && menghentikan langkah lanjutan bila langkah sebelumnya gagal. Hasil akhir yang diharapkan adalah checksum SHA-256 dan path before.dump. Jika dump gagal, arsip yang mungkin terbentuk tidak boleh dianggap valid atau dipakai untuk restore.

Backup ini mencakup raw pinjaman, view staging, dua mart pinjaman dan mart.macro_features sebagai input join final_features. Ini bukan backup seluruh database, seluruh role/konfigurasi server, sumber raw FRED, SEC atau monitoring. Raw pinjaman dan mart macro dicadangkan sebagai input untuk simulasi; rencana perubahan label tidak mengubah kedua relasi itu.

pg_restore --list hanya memastikan daftar isi archive dapat dibaca; belum membuktikan data dapat dipulihkan. Ukuran file, daftar objek, checksum dan hasil restore harus diperiksa pada tahap berikutnya. Arsip dan data mentah tidak dipublikasikan.

## Urutan setelah backup tersedia

1. Catat checksum, ukuran file, versi pg_dump/server dan ruang tersisa. Pastikan daftar isi mencakup lima relasi yang ditetapkan. Periksa tidak ada ingestion atau penulisan paralel saat persiapan penerapan.
2. Pulihkan arsip pada cluster PostgreSQL 14 sementara dengan socket privat. Verifikasi jumlah, ID, label lama dan dependensi view. Restore tanpa owner/ACL hanya membuktikan data/struktur; hak akses pada target aktif perlu dicatat tersendiri.
3. Uji perubahan label pada salinan pemulihan tersebut, dengan hanya lc_loans_clean, loan_features dan final_features sebagai model yang dibangun. Gunakan mart.macro_features dari arsip yang sama sebagai input join; jangan menjalankan rebuild macro dari sumber raw FRED yang tidak termasuk backup ini.
4. Pastikan jumlah/ID/kolom selain label dipertahankan, raw tidak berubah, jumlah label sesuai kontrak, dan tes lulus. Verifikasi pengembalian ketiga relasi yang berubah ke kondisi semula pada salinan terisolasi.
5. Susun tindakan aktif yang dapat direview: sumber SQL/hash, objek yang berubah, backup teruji, ruang kerja, timeout/lock, pemeriksaan sebelum/sesudah dan langkah pemulihan bila gagal. Minta persetujuan penerapan berdasarkan hasil konkret itu.

Pada snapshot yang tidak berubah, hasil aktif yang diharapkan adalah label 0=1.076.751, label 1=268.599, NULL=915.318 pada ketiga layer dan nol pelanggaran loan_label_contract. Jumlah baris tetap 2.260.668. dbt build tidak menjamin rollback seluruh rangkaian ketika tes gagal, sehingga prosedur pemulihan harus diuji sebelum penerapan aktif.

Jangan menjalankan skrip recovery ingestion lama: guard jumlah dan revisinya ditujukan pada keadaan sebelum pemulihan ingestion.

## Bukti backup, simulasi dan rollback

Backup lokal .local-backups/m0-label-s7PGVD/before.dump berukuran 416.630.843 byte, dibuat dengan PostgreSQL 14.22. SHA-256 yang dihitung ulang cocok dengan hasil pembuatan arsip:

```text
060527b72cd4eea7aeb416ec0840284b8c7986051cca4618c25031801bd18fb3
```

Skrip scripts/verify_m0_label_restore.py memulihkan arsip pada cluster PostgreSQL 14.22 yang baru, menggunakan socket privat dan TCP dimatikan. Skrip tidak membaca kredensial proyek atau menghubungi database aktif. Bukti agregat dan hash source disimpan dalam [laporan simulasi](audit/M0_LABEL_RESTORE_REPORT.json); arsip dan salinan data tetap lokal.

| Pemeriksaan pada salinan backup | Hasil |
|---|---|
| Pemulihan lima relasi | Berhasil; raw serta tiga layer pinjaman masing-masing 2.260.668 record; macro 954 record |
| Build terbatas | Tepat tiga model dan 12 tes dbt lulus |
| Label 0 / 1 / NULL sesudah build | 1.076.751 / 268.599 / 915.318 pada setiap layer |
| ID unik dan jumlah record | Tetap 2.260.668 pada setiap layer |
| Perbandingan per ID, seluruh kolom selain is_default | Nol perbedaan pada staging dan kedua mart |
| Input raw dan macro | Jumlah dan sidik agregat baris tetap sama; sidik agregat adalah bukti pendukung, bukan pembuktian kesamaan tanpa kemungkinan benturan hash |
| Rollback, yaitu pemulihan kondisi sebelum build | Berhasil memulihkan label lama, definisi view dan seluruh nilai record; nol perbedaan per ID termasuk label |
| Server sementara | Dihentikan; ruang tersisa sekitar 12,5 GiB pada filesystem pengujian saat selesai |

Tes 12 kasus dbt pada salinan lengkap berbeda dari 27 tes pada fixture sintetis: salinan lengkap hanya membangun tiga model pinjaman, sedangkan fixture membangun lima model termasuk macro. Keduanya merupakan bukti lokal, belum hasil CI untuk perubahan yang belum dikomit.

Restore memakai --no-owner dan --no-privileges sehingga belum menguji pemulihan ownership atau ACL (hak akses). Pemeriksaan baca-saja pada target saat persiapan menemukan pemilik ketiga relasi creditlens, tanpa ACL, opsi relasi atau komentar khusus, dan role memiliki hak CREATE pada schema terkait. Metadata tersebut harus diperiksa kembali sebelum penerapan. Backup ini bukan pemulihan seluruh server. Direktori cluster sementara yang sudah berhenti masih menyimpan data privat dan tidak boleh dipublikasikan.

## Tindakan aktif yang diajukan untuk persetujuan

Usulan hanya membangun ulang staging.lc_loans_clean, mart.loan_features dan mart.final_features pada localhost:5432/creditlens memakai source yang hash-nya tercatat di laporan simulasi. Raw dan mart.macro_features menjadi input; tidak dijalankan rebuild macro. Dampak yang diharapkan pada snapshot yang sama adalah 21.467 record Late (31-120 days) berubah dari label 1 menjadi NULL pada setiap layer, tanpa perubahan ID atau kolom lain.

Sebelum menulis, verifikasi ulang target, migrasi 4b7d2a91c608, hash source dan arsip, jumlah/label serta sidik input terhadap backup, ownership/dependensi/hak akses dan kapasitas disk. Perubahan data atau metadata dari baseline menghentikan penerapan dan memerlukan backup serta penilaian ulang. Pastikan tidak ada ingestion, rebuild atau proses pembaca yang membutuhkan konsistensi ketiga layer selama pekerjaan berlangsung. Statistik sesi role aplikasi saja tidak cukup untuk memastikan keadaan ini.

Pelaksanaan setelah persetujuan menggunakan profile target yang diperiksa, threads=1, lock_timeout=5s dan statement_timeout=300s pada koneksi dbt; batasi proses build hingga 600 detik. Pemilihan model sama dengan simulasi: lc_loans_clean loan_features final_features dengan --indirect-selection cautious. Timeout dan penghentian proses harus dikonfirmasi telah menghentikan sesi penulis sebelum pemulihan dimulai.

Kriteria berhasil: tiga model dan 12 tes lulus; jumlah/ID unik tetap; label sesuai tabel; perbandingan per ID terhadap baseline membuktikan semua kolom selain label tetap sama; raw/macro tidak berubah menurut pemeriksaan input; metadata target tetap sesuai. Simpan laporan hasil aktual sebelum menyatakan penerapan selesai.

dbt menjalankan beberapa model secara bertahap, sehingga kegagalan dapat meninggalkan sebagian layer dengan label baru. Jika build, tes atau verifikasi gagal, hentikan pemakaian downstream, simpan bukti kegagalan, lalu pulihkan hanya ketiga relasi yang berubah dari arsip teruji. Seleksi rollback dan urutannya telah diuji dalam skrip simulasi. Verifikasi seluruh record/label lama serta definisi view sebelum membuka kembali pemakaian database. Rollback terhadap baseline lama hanya berlaku jika input tetap sama dan tidak ada penulisan paralel.

Persetujuan yang diminta terbatas pada penerapan label tersebut dan pemulihan bila gagal. Training, perubahan CI, M1, merge, deployment serta rewrite riwayat tidak tercakup. Keberhasilan simulasi ini belum menyatakan proyek siap produksi.

## Pembaruan 12 September 2026 — persetujuan dan kendala kapasitas

Penerapan label terbatas pada staging.lc_loans_clean, mart.loan_features dan mart.final_features, termasuk pemulihan bila gagal, telah disetujui. Persetujuan ini tidak mencakup training, CI, M1, merge atau deployment. Persetujuan tetap berlaku setelah kendala kapasitas diselesaikan.

Branch codex/m0-mentoring dan HEAD 0acd49a tetap sama. Checksum backup dan hash source terhadap laporan simulasi cocok; laporan privat dan salinan laporan repo juga sama. Filesystem repo hanya memiliki sekitar 185 MiB tersedia pada pemeriksaan Python, sementara pemeriksaan df sebelumnya menunjukkan 217 MiB. Kapasitas berubah selama sistem digunakan. Pemeriksaan dihentikan sebelum query berat atau penulisan database aktif.

Salinan cluster simulasi /private/tmp/m0-label-8r_3kzkh/pgdata menggunakan sekitar 4,3 GiB. pg_ctl status memastikan server tidak berjalan dan tidak ada postmaster.pid. Direktori pgdata ini dapat dibuat ulang dari backup terverifikasi; log, report.json dan before.dump tetap dipertahankan. Belum ada pembersihan yang dijalankan pada pemeriksaan ini.

Sediakan sedikitnya 8 GiB ruang bebas sebelum melanjutkan preflight. Ini batas operasional konservatif untuk rebuild terbatas, bukan kebutuhan training atau jaminan kapasitas seluruh volume database. Menghapus salinan simulasi saja diperkirakan belum mencapai batas tersebut. Setelah kapasitas tersedia, periksa ulang target, baseline data, metadata, aktivitas, source dan disk sebelum penerapan. Belum ada hasil penerapan aktif yang dapat dilaporkan.

## Pembaruan 22 September 2026 — pemeriksaan parsial

Ruang bebas pada filesystem data PostgreSQL sekitar 4,2 GiB, masih di bawah batas 8 GiB. Direktori cluster simulasi yang disebut pada pembaruan 12 September sudah tidak ada; tidak ada pembersihan yang dilakukan dalam pemeriksaan ini. Arsip privat tetap ada dan SHA-256-nya cocok dengan laporan restore. Seluruh hash source SQL/tes yang tercatat dalam laporan restore juga cocok.

Listener PostgreSQL menerima koneksi; sesi baca-saja memastikan database `creditlens`, role `creditlens`, dan server PostgreSQL 14.22. Akses socket dari sandbox Codex ditolak oleh sistem, sehingga hasil `pg_isready` tanpa akses lokal yang sesuai tidak dapat dipakai untuk menyimpulkan layanan mati. Ini belum menggantikan preflight lengkap: jumlah/label/ID, sidik input, migrasi, metadata, penulis lain dan ruang disk harus diperiksa ulang sesudah kapasitas mencukupi. Tidak ada build atau pemulihan pada database aktif. Bukti terstruktur: [laporan kendala](audit/M0_LABEL_2026-09-22_BLOCKER.json).

## Pembaruan 22 September 2026 — penerapan aktif selesai

Setelah operator mengosongkan ruang disk dan memastikan tidak ada workload CreditLens lain, preflight baca-saja lulus pada PostgreSQL 14.22: target, migrasi, backup, hash source, jumlah/ID/label baseline, sidik input, definisi view dan metadata cocok dengan simulasi. Arsip yang sama telah diuji restore dan rollback secara terisolasi; tidak diperlukan backup baru karena baseline aktif tidak berubah.

Build dibatasi pada `lc_loans_clean`, `loan_features` dan `final_features`, memakai satu thread, `lock_timeout=5s`, `statement_timeout=300s` dan batas proses 600 detik. Ketiga model dan 12 tes lulus. Pada setiap layer, 2.260.668 record dan ID unik tetap; label 0=1.076.751, label 1=268.599, NULL=915.318, dan nol pelanggaran kontrak. SHA-256 atas aliran baris berurutan menurut ID, tanpa kolom label, cocok sebelum/sesudah pada ketiga layer. Raw/macro mempertahankan jumlah dan sidik agregat; metadata relasi tidak berubah. Autovacuum PostgreSQL terlihat sesudah build sebagai proses perawatan pada final_features, bukan workload pengguna lain. Ruang tersisa sekitar 16 GiB pada pemeriksaan akhir; rollback aktif tidak diperlukan.

[Laporan penerapan aktif](audit/M0_LABEL_ACTIVE_ROLLOUT_REPORT.json) menyimpan hasil dan batas bukti. Perubahan ini tidak menetapkan as-of/cohort, tidak menjalankan training atau mengubah CI/deployment, dan belum membuktikan kesiapan produksi.
