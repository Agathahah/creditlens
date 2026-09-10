# M0 — diagnosis dan reproduksi dengan mentoring

v0.2 · 2026-09-09 · M0 aktif. **Arahan terbaru: latihan ditunda sampai akhir. Bagian latihan di bawah adalah arsip/draft, bukan tugas yang sedang ditunggu.** Codex telah menjalankan COUNT, menulis tes, membuktikan reproduksi dan memulihkan dua mart. Cakupan ingestion/label masih terbuka. Lihat [WORKLOG](WORKLOG.md) dan [pemeriksaan terminal opsional](M0_TERMINAL_CHECK.md).

Cara belajar aktif: Codex melanjutkan pekerjaan yang diizinkan, menjelaskan status/alasan dan mencatat hasil. [HTML awal](M0_LATIHAN.html) disimpan sebagai draft; latihan akhir akan memakai variasi kasus. Dua tes M0 ditulis Codex atas arahan pengguna terbaru, bukan kontribusi kode Agatha.

## Tujuan

Memahami jalur data raw → staging → mart; menyelidiki tabel mart kosong berdasarkan bukti; menulis tes kualitas data yang menangkap kegagalan tersebut. Kita belum mengetahui penyebab mart kosong. Angka audit 8 September adalah snapshot, bukan jaminan state sekarang.

Tahap awal memakai pembacaan source, tanpa mengubah database. Setelah review percobaan, Codex menyiapkan sesi koneksi read-only dan reproduksi terisolasi, lalu Agatha mengerjakan tes nonempty. Jangan menjalankan rebuild lebih dahulu atau langsung memuat ulang data.

## Penjelasan sebelum latihan

dbt memakai file SQL untuk membentuk suatu relasi database, berupa tabel atau view sesuai konfigurasi. `ref()` mengacu ke model dbt lain dan mencatat dependensinya. File SQL adalah definisi proses; keberadaan file tidak membuktikan tabel hasilnya sudah terisi.

Dalam debugging, bedakan observasi dengan hipotesis. “Tabel final berisi nol baris saat audit” adalah observasi. Penjelasan mengapa hal itu terjadi masih hipotesis sampai diuji.

## M0.1 — tugas Agatha

Di Terminal, masuk ke repo:

```bash
cd /Users/agathasilalahi/Documents/creditlens
```

Lokasi awal: direktori apa pun. Tujuan: memakai folder proyek yang benar. Dampak: hanya mengubah direktori shell; output normal biasanya kosong. Jika path tidak ditemukan, kirim error sebelum melanjutkan.

Baca definisi mart loan:

```bash
sed -n '1,90p' models/mart/loan_features.sql
```

Lokasi: root creditlens. Tujuan: membaca SQL beserta konfigurasi dan model sumbernya. Dampak: baca-saja, tidak menghubungi database. Output yang diharapkan: blok config, WITH/SELECT dan ref model. Jika file tidak ditemukan, periksa lokasi shell; jangan menjalankan setup.

Kirim tiga hal dengan kata-kata sendiri:

1. Nama model yang menjadi sumber langsung loan_features, berdasarkan ref pada file.
2. Satu query SQL rancangan Anda untuk menghitung baris pada relasi sumber tersebut. Query cukup dikirim di percakapan, belum perlu dieksekusi. Petunjuk pertama: gunakan SELECT, COUNT(*) dan FROM.
3. Satu hipotesis yang mungkin menjelaskan mengapa sumber berisi data tetapi tabel hasilnya kosong. Tidak harus benar; jelaskan bukti tambahan yang diperlukan untuk mengujinya.

Codex menunggu percobaan sebelum memberi solusi query atau mengambil alih debugging. Jika belum memahami COUNT/ref/materialized, Agatha dapat menyebut bagian yang membingungkan untuk memperoleh contoh kecil terpisah dari solusi latihan.

## Review M0.1

Model sumber `lc_loans_clean` benar. Query `select count(*) from lc_loans_clean` memiliki bentuk yang benar; gunakan schema eksplisit `staging.lc_loans_clean`, karena nama tanpa schema bergantung pada search_path koneksi. Akhiri query dengan semicolon pada psql. Tulis underscore dan tanda bintang tanpa backslash SQL.

Hipotesis Agatha: data belum ditarik/dipanggil. Kita memperjelas dugaan itu menjadi data belum dimaterialisasikan ke tabel mart. Raw/staging sudah terisi saat audit, sehingga belum ada alasan langsung mengunduh ulang sumber. Counts saat ini dapat menguji apakah ketimpangan antar-layer masih ada, tetapi belum membuktikan kapan/kenapa tabel mart kosong.

## M0.2a — dasar dan pemulihan prompt sebelum COUNT

- PostgreSQL: server pengelola database. Database `creditlens` memiliki schema seperti `raw`, `staging`, dan `mart`.
- Schema: kelompok bernama untuk objek database. `staging.lc_loans_clean` berarti objek `lc_loans_clean` dalam schema `staging`. Nama schema bisa dihilangkan jika search_path sesuai; gunakan eksplisit dalam latihan agar target jelas.
- Tabel: menyimpan baris dan kolom. View biasa: definisi query yang dibaca saat diakses, bukan salinan hasil yang disimpan seperti tabel.
- Data staging: lapisan pembersihan antara raw dan mart. Berbeda dengan environment staging untuk menguji aplikasi sebelum produksi; schema staging tidak otomatis mengisolasi deployment.
- Mart: data yang disiapkan untuk kebutuhan tertentu. Pada proyek ini `mart.loan_features` menyiapkan fitur pinjaman; nama mart tidak membuktikan kualitas/readiness.
- dbt: menjalankan transformasi SQL, mengelola dependensi dan tes. Model dbt adalah definisi transformasi seperti file SQL; berbeda dengan model machine learning terlatih.
- psql: aplikasi terminal untuk berkomunikasi dengan PostgreSQL. Shell (biasanya `%`/`$`) menjalankan program; prompt psql menerima SQL dan perintah psql.

Definisi repo: `models/staging/lc_loans_clean.sql` mengonfigurasi view staging dari raw; `models/mart/loan_features.sql` mengonfigurasi tabel mart dan memakai `ref('lc_loans_clean')`. Membaca SELECT tidak menjalankan dbt atau otomatis membangun tabel mart.

Laporan Agatha: melihat `creditlens->`. Pada prompt standar psql ini berarti input belum selesai, sering karena belum ada semicolon. `creditlens=>` siap menerima perintah baru. Jangan menambahkan semicolon pada buffer yang isinya tidak diketahui atau mengetik ulang password di sana.

1. Di prompt `creditlens->`, tekan **Control+C** untuk membatalkan input tertunda. Dampak: membuang input belum selesai; harapan prompt kembali `creditlens=>` (atau `creditlens=#` untuk superuser).
2. Masih di psql, ketik `\conninfo`, lalu Enter, tanpa semicolon. Dampak: menampilkan informasi koneksi. Harapan database/user creditlens, host localhost dan port 5432.
3. Ketik `SHOW transaction_read_only;`, lalu Enter. Dampak: membaca pengaturan transaksi. Harapan `on` untuk sesi yang dibuka dengan perintah di bawah. Jika `off`, berhenti di checkpoint ini dan laporkan; jangan mengubah tabel.

Password saat `Password for user creditlens:` adalah password role PostgreSQL `creditlens`, bukan otomatis password Mac. Input password biasanya tidak terlihat saat diketik. Salah password pada koneksi awal biasanya menampilkan error autentikasi; prompt `->` sendiri tidak menunjukkan itu. Jika ada error, kirim pesan error tanpa password atau isi .env; jangan reset password dulu.

Selesai: Agatha telah mengirim output database/user creditlens, localhost (::1):5432 dan read-only on. Lanjutkan COUNT di sesi yang sama. Untuk kembali ke shell, `\q` lalu Enter. Jalankan perintah pembuka psql berikut hanya dari shell jika belum berada di psql.

Rujukan: [psql dan prompt](https://www.postgresql.org/docs/16/app-psql.html), [schema/search_path](https://www.postgresql.org/docs/16/ddl-schemas.html), [dbt](https://docs.getdbt.com/docs/introduction).

## M0.2 — tugas eksekusi baca-saja setelah verifikasi M0.2a

Lokasi: Terminal Mac, dari folder repo. `psql` tersedia pada environment yang diperiksa. Buka koneksi ke localhost:5432, database creditlens, dengan default transaksi read-only:

```bash
PGOPTIONS='-c default_transaction_read_only=on' \
psql -X -h localhost -p 5432 -U creditlens -d creditlens
```

Tujuan: menjalankan pemeriksaan jumlah baris dengan query buatan Agatha. Dampak: membuka koneksi; pengaturan read-only hanya berlaku untuk sesi ini. `-X` menghindari perintah startup psqlrc. Output harapan: prompt `creditlens=>`. Bila diminta password, masukkan lokal dan jangan kirim password ke chat. Jika koneksi/otentikasi gagal, kirim pesan error tanpa credential; jangan menyalin isi .env.

Di dalam psql, jalankan query Anda yang telah dikoreksi:

```sql
SELECT COUNT(*) FROM staging.lc_loans_clean;
```

Tujuan: mengetahui jumlah baris sumber saat ini. Dampak: SELECT baca-saja; tidak mengubah tabel. Output harapan: satu angka count. Angka audit sebelumnya 1599982 adalah pembanding, bukan hasil yang dijamin sekarang.

Sesuai permintaan praktik terarah terbaru, jalankan juga `SELECT COUNT(*) FROM mart.loan_features;`. Kirim kedua count/error. Query ini disediakan Codex; bagian penulisan mandiri tersedia di HTML untuk final_features dan tes nonempty. Untuk keluar dari psql gunakan `\q` setelah selesai.

Codex telah menemukan bukti log dbt pernah membuat loan/final berisi 1.599.982 baris, lalu pada run lain membuat hasil kosong dan melaporkan sukses. Jadi jangan meminta Agatha membuktikan ulang hipotesis “belum pernah berjalan”; latih membedakan isi kini, riwayat build dan penyebab awal. [Diagnosis dan bukti](audit/M0_DIAGNOSIS.md).

Codex tidak menjalankan kedua query ini sebagai pengganti Agatha dan belum menyiapkan solusi tes nonempty. Tidak ada dbt run dalam checkpoint ini.

## Checkpoint selanjutnya

- Review query, model sumber, dan perbedaan observasi/hipotesis.
- Siapkan koneksi read-only dan lingkungan reproduksi terisolasi dengan lokasi serta dampak dijelaskan; jangan memakai DB aktif sebagai lingkungan tes yang melakukan mutation.
- Agatha menulis query rekonsiliasi dan tes dbt nonempty yang bermakna; Codex membantu wiring/isolasi setelah percobaan.
- Reproduksi kegagalan → hipotesis diuji → perubahan yang disetujui → tes → penjelasan kembali.
- Finalisasi feasibility label/horizon/data-as-of sebelum desain M1 disetujui.

## Bukti checkpoint

Percobaan M0.1: diterima dalam percakapan; identifikasi sumber dan rancangan COUNT benar dengan koreksi schema. Hipotesis masih diuji. Review: tercatat di LEARNING_LOG.md. Hasil runtime M0.2: belum diterima. Tes nonempty: belum ditulis. Commit: belum ada. M0 belum selesai.
