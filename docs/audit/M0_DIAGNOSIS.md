# M0 — diagnosis mart kosong

Dicatat 2026-09-09. Bagian awal merekam diagnosis baca-saja. Update terbaru: dua tes SQL M0 dan reproduksi terisolasi selesai, lalu recovery development sukses setelah disk dilonggarkan: loan/final 1.599.982 baris dan 9 tes pass. Lihat ../WORKLOG.md, M0_ISOLATED_TEST_REPORT.json dan M0_MART_RECOVERY_REPORT.json. Cakupan ingestion masih terbuka; tugas Agatha di bagian rencana lama ditunda ke latihan akhir.

## Bukti baru

Agatha mengirim output psql: database/user `creditlens`, host `localhost` (`::1`), port 5432; `SHOW transaction_read_only;` menghasilkan `on`. Ini memverifikasi koneksi dan pengaturan transaksi sesi tersebut saat diperiksa, bukan bukti isi tabel atau role yang permanen read-only.

Codex membaca source, `logs/dbt.log`, `target/manifest.json` dan `target/run_results.json`, tanpa menjalankan dbt. Ekstrak log dengan nomor baris dan checksum disimpan di [M0_DBT_LOG_EVIDENCE.json](M0_DBT_LOG_EVIDENCE.json), karena artifact target dapat ditimpa eksekusi berikutnya.

| Bukti historis | Lokasi log | Arti |
|---|---|---|
| loan_features SELECT 1599982 | logs/dbt.log:3718 | Ada catatan build berisi 1.599.982 baris |
| final_features SELECT 1599982 | logs/dbt.log:3786 | Build final juga pernah menghasilkan baris |
| loan_features SELECT 0 | logs/dbt.log:5703 | Eksekusi berikutnya dalam urutan file membuat hasil kosong |
| SQL COMMIT dan status COMMIT | logs/dbt.log:5678,5686 | Hasil kosong ini di-commit menurut log |
| macro_features SELECT 954 | logs/dbt.log:5707 | Cabang makro pada run tersebut tetap berisi data |
| final_features SELECT 0 | logs/dbt.log:5775 | Final mengikuti cabang loan yang kosong |
| PASS=3 ERROR=0 | logs/dbt.log:5797 | dbt run sukses secara eksekusi dengan hasil kosong |
| PASS=24 ERROR=0 | logs/dbt.log:6954 | Run tes sesudahnya melaporkan 24 pass |

Run build kosong memiliki invocation `b783edf8-7fbf-4963-9cb2-6f13a934a93a`, profile creditlens/target dev dan SQL destination `creditlens.mart.loan_features__dbt_tmp`. Run tes berikutnya memiliki invocation `9fe064ea-f8f2-474c-ab85-d03a66ccbf2f`, sama dengan metadata run_results yang generated_at `2026-08-03T08:55:13.706930Z`.

Log hanya menampilkan jam, bukan tanggal. Tanggal artifact tes tidak boleh dianggap tanggal pasti semua run sebelumnya. Nama database/profile tidak membuktikan server/volume yang sama dengan koneksi kini. Tidak ada snapshot data atau commit yang terikat pada run tersebut.

## Diagnosis sementara

Hipotesis umum “dbt belum pernah dijalankan” tidak cocok dengan log yang tersedia. Ada bukti dbt pernah membuat tabel kosong dan menganggap eksekusinya berhasil. Source loan_features hanya memproyeksikan/menghitung fitur dari staging, tanpa WHERE atau JOIN pengurang baris. Ini mendukung dugaan input yang terlihat oleh run itu kosong. Mengapa input tersebut kosong belum terbukti: urutan ingestion/build, database/volume berbeda, perubahan source lama, atau operasi pengosongan tetap perlu dibedakan.

Staging adalah view: pembacaan berikutnya dapat melihat raw yang telah berubah. Mart adalah tabel: hasil build lama tetap tersimpan sampai ada operasi yang mengubahnya. Karena itu raw/staging yang kemudian terisi dapat berdampingan dengan mart hasil build kosong. Ini mekanisme yang konsisten dengan bukti, bukan kronologi ingestion yang sudah terbukti.

Tes unique/not_null memeriksa pelanggaran pada baris yang ada, sehingga tabel kosong dapat lolos. Tes accepted_values juga tidak menjamin adanya baris. `rows_affected=1` pada adapter_response tes bukan jumlah loan; query tes menghasilkan baris agregat hasil pemeriksaan. Kita memerlukan kontrak nonempty dan rekonsiliasi jumlah baris.

## Langkah berikutnya dan pembagian kerja

1. Agatha menjalankan COUNT staging dan mart pada sesi psql yang sudah terverifikasi. Output live belum diterima; angka 8 September tetap snapshot historis.
2. Codex menautkan hasil itu ke log dan mempersiapkan reproduksi kecil terisolasi. Tidak memakai perubahan target.schema saja sebagai isolasi: macro generate_schema_name saat ini mengembalikan custom schema secara langsung, sehingga model tetap menargetkan staging/mart.
3. Sebelum mutation, dokumentasikan lokasi database isolasi, dataset kecil, perintah, dampak, cleanup dan verifikasi target. Jangan menjalankan rebuild di database aktif sebagai percobaan pertama.
4. Agatha menulis tes SQL nonempty pada tahap berikutnya; Codex menyiapkan wiring dan review setelah percobaan. Tes harus gagal pada fixture kosong dan lulus pada fixture berisi data. Belum ada solusi tes yang dipasang.

## Pekerjaan sesi ini

Pembacaan Git/source/log/artifact; penyimpanan ekstrak bukti; pembaruan checkpoint dan HTML latihan. Tidak ada query COUNT pengganti Agatha, koneksi database baru oleh Codex, perubahan data/source aplikasi, instalasi, training, dbt run/test, commit atau push. Validasi dokumen/HTML dilaporkan terpisah dari tes aplikasi.
