# Review M0 — pemulihan ingestion dan tabel analitik

Pembaruan 12 September 2026: penerapan label pada tiga relasi pinjaman dan pemulihan bila gagal telah disetujui. Pemeriksaan disk menemukan hanya sekitar 185–217 MiB tersedia, sehingga pekerjaan berhenti sebelum penulisan database aktif. Checksum backup dan hash source sesuai bukti simulasi. Salinan cluster pengujian 4,3 GiB sudah dipastikan berhenti; pembersihan belum dijalankan. Sediakan sedikitnya 8 GiB sebelum preflight dilanjutkan. Rincian: [rencana penerapan](../M0_LABEL_ROLLOUT.md). Bagian review sebelumnya di bawah mempertahankan bukti historis.

Tanggal review: 11 September 2026. Commit yang diperiksa: `0acd49a9aefc22c4facd73b78a00d5b329d36a33`.

## Hasil review

Bukti yang tersedia mendukung keberhasilan pemulihan data dalam lingkup M0. Ingestion adalah proses memasukkan data sumber ke database. Setelah pemulihan, tabel raw (data hasil impor), staging (data yang dibersihkan), dan kedua mart (tabel analitik) masing-masing berisi 2.260.668 record pinjaman.

Pada perubahan kode aplikasi yang diperiksa, tidak ditemukan masalah tambahan yang menghalangi perbaikan ingestion tersebut. Pemeriksaan ini terbatas pada perubahan yang disebutkan di bawah; bukan pemeriksaan menyeluruh seluruh aplikasi atau semua skrip pemulihan yang diarsipkan.

**PR belum direkomendasikan untuk digabung ke main.** Konfigurasi evaluasi model setelah penggabungan belum menyediakan input yang dibutuhkan. Asal data dan waktu ketersediaan fitur juga belum selesai diputuskan. Pembaruan setelah review commit: kontrak label sudah disetujui, diperbaiki pada SQL lokal dan diuji terisolasi; database aktif belum direbuild. Implementasi M1, training penuh, dan penerimaan rilis memerlukan keputusan tersendiri.

## Apa yang sudah diperiksa

| Bagian | Bukti dan maknanya | Batas kesimpulan |
|---|---|---|
| Repo dan PR | Commit lokal sama dengan PR #14. Status OPEN, masih draft, dan MERGEABLE | MERGEABLE berarti GitHub tidak menemukan konflik penggabungan; bukan jaminan aplikasi benar atau siap rilis |
| CI, yaitu pemeriksaan otomatis | [Run 34556669746](https://github.com/Agathahah/creditlens/actions/runs/34556669746) lulus pemeriksaan gaya kode/tipe dan tes aplikasi | Jumlah tes serta coverage terperinci tidak diambil untuk run ini. Evaluasi model dan build Docker dilewati |
| Status pinjaman utuh | Migrasi, pemetaan tabel Python (ORM), dan SQL inisialisasi memakai TEXT. Parser mempertahankan teks status lengkap | Log lama menunjukkan mekanisme kegagalan yang cocok dengan batas VARCHAR(50), tetapi belum membuktikan identitas proses impor terakhir |
| Migrasi skema | View staging dibuat ulang dalam satu transaksi. DROP RESTRICT menolak penghapusan bila ada view lain yang bergantung padanya. Pengembalian ke VARCHAR(50) ditolak jika akan memotong data | View dengan hak akses atau metadata khusus memerlukan penanganan tersendiri. Tes database terisolasi belum menjadi bagian CI |
| Melanjutkan impor | Mode insert-missing melewati ID yang sudah ada. ON CONFLICT DO NOTHING mencegah penimpaan saat terjadi konflik. Kegagalan penulisan membatalkan batch yang sedang berjalan | Batch yang sebelumnya berhasil tetap tersimpan. Daftar ID yang dimuat ke memori bertambah mengikuti ukuran data |
| Memperbarui data lama | Mode upsert memperbarui status dan field pembayaran tertentu hanya jika nilainya berubah. Impor ulang tanpa perubahan mempertahankan loaded_at | Tidak menyimpan riwayat setiap perubahan pinjaman dan tidak menyinkronkan semua field sumber |
| Tes mart | Tes nonempty menolak tabel kosong. Rekonsiliasi jumlah baris mendeteksi perbedaan jumlah antar-layer dan melengkapi tes ID unik | Jumlah sama belum menjamin ID atau seluruh nilai sama. Perbandingan ID sumber dengan raw merupakan pemeriksaan terpisah |
| Pemulihan | Catatan raw/staging/loan/final menunjukkan masing-masing 2.260.668 baris; selisih ID sumber/raw nol; pemulihan backup dalam lingkup yang ditetapkan berhasil | Pemeriksaan seluruh CSV dan database tidak dijalankan ulang dalam review kode ini |
| Target model | SQL pada commit yang direview masih memasukkan Late (31–120 days) sebagai label positif; perubahan lokal berikutnya memperbaiki mapping dan lulus tes terisolasi | Database aktif belum direbuild; penerapan aktif memerlukan keputusan tersendiri |

Kode yang diperiksa: `src/ingestion/lending_club.py`, `scripts/load_data.py`, `migrations/versions/4b7d2a91c608_expand_loan_status.py`, `src/common/orm_models.py`, `scripts/init_db.sql`, serta dua tes baru dalam `tests/dbt/`. Tes parser dan skrip verifikasi PostgreSQL/dbt terisolasi dibaca bersama laporan hasil sebelumnya.

## P1 — evaluasi setelah merge belum memiliki input

P1 berarti masalah berprioritas tinggi yang perlu ditangani sebelum alur terkait diandalkan. Merge adalah penggabungan perubahan branch PR ke branch tujuan, dalam kasus ini main. Masalah berikut sudah ada sebelum perubahan M0.

1. `.github/workflows/ci.yml` menjalankan pekerjaan `eval-gate` setelah push ke main. Pekerjaan ini hanya mengambil kode, memasang Python/dependensi, lalu menjalankan evaluator.
2. `src/ml/evaluate.py` mengharapkan file model `models/xgboost_credit.joblib`. File itu tidak ada dalam kode yang dilacak Git dan workflow tidak memiliki langkah mengambil artefak model. Artefak adalah file hasil training yang diperlukan untuk menghitung prediksi.
3. Setelah memuat model, evaluator membaca fitur dari database. Pekerjaan evaluasi juga belum menyediakan database atau snapshot data evaluasinya. PostgreSQL pada pekerjaan tes terpisah tidak otomatis tersedia untuk pekerjaan evaluasi.
4. Dengan konfigurasi tersebut, lingkungan baru yang hanya mengambil kode repo tidak dapat menyelesaikan evaluasi model. Kesimpulan ini berasal dari pemeriksaan kode dan workflow; belum dilakukan merge atau evaluasi data nyata untuk memicu kegagalan.
5. Pembuatan image Docker berjalan saat tag versi dibuat dan bergantung pada tes aplikasi, belum pada keberhasilan evaluasi model. Karena itu, image belum terikat pada bukti evaluasi model yang akan digunakan.

### Usulan perbaikan CI — belum diterapkan

| Perubahan yang diusulkan | Tujuan | Kriteria berhasil |
|---|---|---|
| Pertahankan tes software pada PR dan main | Memeriksa perubahan kode secara otomatis | Kesalahan kode atau tes gagal tetap menggagalkan pemeriksaan |
| Tambahkan tes PostgreSQL/dbt dengan data sintetis kecil yang dapat berjalan di CI | Membuktikan pemulihan ingestion dan deteksi mart rusak dapat diulang di luar laptop | Status panjang, pembatalan batch gagal, impor ulang, tabel kosong dan jumlah baris tidak cocok diuji |
| Pisahkan evaluasi kandidat model dengan input berversi yang eksplisit | Memastikan jelas model dan data mana yang dievaluasi | Model atau data hilang/tidak cocok harus gagal; hasil di bawah ambang mutu juga gagal |
| Hubungkan rilis dengan hasil evaluasi kandidat yang sama | Mencegah model yang berbeda dari hasil evaluasi ikut dirilis | Identitas versi/checksum model, data, dan image sesuai catatan rilis; ketidaksesuaian menolak rilis |

Data sintetis adalah data buatan untuk menguji perilaku software. Kelulusan tes sintetis tidak membuktikan kualitas model pada data pinjaman nyata. Usulan ini tidak mengizinkan penurunan ambang mutu, training penuh, atau deployment.

## Verifikasi jumlah kandidat target

Hasil query baca-saja terhadap `raw.lc_loans` dilaporkan sesuai dengan angka pada audit sebelumnya. Query mengelompokkan status dengan CASE; tidak mengubah kolom is_default atau menghapus record.

| Kelompok usulan | Jumlah | Makna |
|---|---:|---|
| Fully Paid → kandidat label 0 | 1.076.751 | Pinjaman tercatat lunas |
| Charged Off/Default → kandidat label 1 | 268.599 | Pinjaman tercatat pada status outcome negatif yang dipilih |
| Status lain → di luar target utama | 915.318 | Tetap disimpan dalam raw; tidak otomatis menjadi label 0 |
| Total | 2.260.668 | Sama dengan jumlah record raw yang tercatat |

Konfirmasi ini merupakan hasil yang dilaporkan, bukan eksekusi database baru oleh reviewer. Bukti angka terperinci sebelumnya tersedia di [analisis kelayakan label](M0_LABEL_FEASIBILITY.json). **Kesesuaian jumlah tidak sama dengan persetujuan definisi target.** Sebanyak 1.345.350 kandidat berlabel masih perlu pemeriksaan waktu dan fitur sebelum menjadi dataset training.

## Profil tahun dan tenor: hasil agregat terverifikasi

Sumber pemeriksaan ini adalah keluaran query psql sebanyak 21 baris yang disampaikan untuk review. Penjumlahan dihitung ulang dari keluaran tersebut; database tidak diakses ulang untuk menghasilkan profil ini. Pada setiap baris, total sama dengan kandidat 0 + kandidat 1 + di luar target. Jumlah seluruh kelompok adalah 2.260.668, dengan 1.076.751 kandidat 0, 268.599 kandidat 1 dan 915.318 di luar target, sesuai agregat sebelumnya.

| Tahun | Tenor (bulan) | Total | Kandidat 0 | Kandidat 1 | Di luar target | % di luar target |
|---|---:|---:|---:|---:|---:|---:|
| 2007 | 36 | 603 | 206 | 45 | 352 | 58,37% |
| 2008 | 36 | 2.393 | 1.315 | 247 | 831 | 34,73% |
| 2009 | 36 | 5.281 | 4.122 | 594 | 565 | 10,70% |
| 2010 | 36 | 9.156 | 7.624 | 842 | 690 | 7,54% |
| 2010 | 60 | 3.381 | 2.425 | 645 | 311 | 9,20% |
| 2011 | 36 | 14.101 | 12.602 | 1.499 | 0 | 0,00% |
| 2011 | 60 | 7.620 | 5.822 | 1.798 | 0 | 0,00% |
| 2012 | 36 | 43.470 | 37.567 | 5.903 | 0 | 0,00% |
| 2012 | 60 | 9.897 | 7.156 | 2.741 | 0 | 0,00% |
| 2013 | 36 | 100.422 | 88.044 | 12.378 | 0 | 0,00% |
| 2013 | 60 | 34.392 | 25.736 | 8.646 | 10 | 0,03% |
| 2014 | 36 | 162.570 | 140.255 | 22.315 | 0 | 0,00% |
| 2014 | 60 | 73.059 | 41.686 | 18.847 | 12.526 | 17,15% |
| 2015 | 36 | 283.173 | 240.894 | 42.132 | 147 | 0,05% |
| 2015 | 60 | 137.922 | 58.848 | 33.672 | 45.402 | 32,92% |
| 2016 | 36 | 323.495 | 186.241 | 46.120 | 91.134 | 28,17% |
| 2016 | 60 | 110.912 | 38.612 | 22.132 | 50.168 | 45,23% |
| 2017 | 36 | 320.419 | 102.817 | 25.734 | 191.868 | 59,88% |
| 2017 | 60 | 123.160 | 27.335 | 13.435 | 82.390 | 66,90% |
| 2018 | 36 | 344.671 | 35.804 | 5.468 | 303.399 | 88,03% |
| 2018 | 60 | 150.571 | 11.640 | 3.406 | 135.525 | 90,01% |

Persentase menggunakan jumlah seluruh pinjaman pada masing-masing baris sebagai pembagi, bukan jumlah kandidat berlabel. Angka dibulatkan menjadi dua desimal.

### Interpretasi dan batasnya

- Pada 2015, proporsi di luar target adalah 0,05% untuk tenor 36 bulan dan 32,92% untuk 60 bulan. Pada 2018, proporsinya mencapai 88,03% dan 90,01%. Mengambil hanya kandidat berlabel akan menyisakan bagian yang sangat berbeda dari setiap kelompok.
- Pola ini konsisten dengan perbedaan lama pengamatan, tetapi tabel agregat belum membuktikan penyebab atau tanggal snapshot. Di luar target juga mencakup status di luar kebijakan kredit; tidak semuanya dapat disebut pinjaman berjalan.
- Tahun 2007–2010 memiliki total 2.749 record di luar target. Rincian status lanjutan di bawah mengonfirmasi semuanya berasal dari dua status di luar kebijakan kredit (1.988 + 761), bukan status Current atau terlambat.
- Tanpa tanggal snapshot dan kapan outcome diketahui, label dari pinjaman tahun lama dapat memuat informasi yang baru tersedia sesudah tanggal pemisahan yang diusulkan. Karena itu, belum ditetapkan cutoff train/test atau klaim pengujian prospektif.
- Kelompok dengan nol record di luar target tidak otomatis bebas dari bias seleksi, kebocoran fitur atau keterlambatan ketersediaan label. Pemilihan pinjaman dengan outcome yang sudah diketahui dapat lebih banyak menyertakan pelunasan atau kegagalan yang terjadi lebih cepat.

Rincian status per periode sudah diterima dan dijumlahkan pada bagian berikut. Verifikasi sumber/tanggal snapshot masih terbuka. Query operasional tersedia dalam [panduan pemeriksaan](../M0_TERMINAL_CHECK.md). Mapping label sudah disetujui dan lulus tes terisolasi; pembagian dataset tetap berupa usulan.

## Rincian status di luar target

Sumber: sepuluh baris keluaran query baca-saja yang disampaikan untuk review. Penjumlahan dihitung ulang dari keluaran itu, tanpa eksekusi database baru oleh reviewer.

| Periode | Status sumber | Jumlah |
|---|---|---:|
| 2007–2010 | Does not meet the credit policy. Status:Fully Paid | 1.988 |
| 2007–2010 | Does not meet the credit policy. Status:Charged Off | 761 |
| 2011–2015 | Current | 55.224 |
| 2011–2015 | Late (31-120 days) | 1.696 |
| 2011–2015 | In Grace Period | 813 |
| 2011–2015 | Late (16-30 days) | 352 |
| 2016–2018 | Current | 823.093 |
| 2016–2018 | Late (31-120 days) | 19.771 |
| 2016–2018 | In Grace Period | 7.623 |
| 2016–2018 | Late (16-30 days) | 3.997 |

Subtotal periode: 2.749 + 58.085 + 854.484 = **915.318**. Agregat status juga cocok dengan audit sebelumnya: Current 878.317; Late (31-120 days) 21.467; In Grace Period 8.436; Late (16-30 days) 4.349; dua status di luar kebijakan 2.749. Seluruh kelompok yang diharapkan terjelaskan; tidak ada selisih hitung pada keluaran yang diberikan.

Ada dua alasan pengeluaran yang berbeda: status di luar kebijakan (2.749), serta status Current/terlambat/masa tenggang yang tidak digunakan sebagai label pada usulan target (912.569). Pinjaman di luar kebijakan sudah memiliki status Fully Paid/Charged Off, sehingga pengeluarannya adalah keputusan cakupan populasi. Pinjaman Current belum boleh dianggap lunas hanya karena belum tercatat gagal; status terlambat juga belum sama dengan Charged Off/Default pada kontrak yang diusulkan.

Profil status awal selesai. Mapping target kemudian disetujui dan implementasi SQL lokal lulus tes terisolasi; rancangan fitur dan kelayakan dataset masih perlu review. Masalah waktu snapshot dan ketersediaan outcome tetap terbuka; ringkasan ini tidak menetapkan kapan hasil pinjaman diketahui.

## Langkah berikutnya untuk menutup M0

### Hasil verifikasi ulang dan pemeriksaan database aktif

Laporan /private/tmp/creditlens-m0-f8181l6x/report.json dibaca langsung: passed, cluster_stopped=true, lima model dan 27 tes lulus. Hash cocok dengan file sebelum penambahan opsi versi PostgreSQL berikutnya.

Preflight baca-saja mengonfirmasi database aktif memakai PostgreSQL 14.22, migrasi 4b7d2a91c608, dan raw/staging/dua mart masing-masing berisi 2.260.668 record. Staging dan kedua mart masih memiliki 290.066 label positif serta 21.467 ketidaksesuaian terhadap kontrak baru. Pemeriksaan tidak mengubah database.

Karena tes awal memakai PostgreSQL 16, skrip diberi opsi --pg-bin untuk memilih versi terpasang. Tes penuh diulang pada cluster privat PostgreSQL 14.22 dan lulus: lima model, 27 tes, kemudian cluster dihentikan. Bukti: [tes versi 14](M0_LABEL_PG14_REPORT.json).

Backup ingestion lama memuat 1.599.982 record sehingga tidak dipakai sebagai baseline perubahan label. Backup terbaru kemudian dibuat dan diuji sebagaimana pembaruan berikut. Lingkup, dependensi macro dan batas pemulihan dijelaskan dalam [rencana penerapan](../M0_LABEL_ROLLOUT.md).

### Pemulihan backup terbaru dan simulasi label lengkap

Backup before.dump terbaru berukuran 416.630.843 byte dengan SHA-256 060527b72cd4eea7aeb416ec0840284b8c7986051cca4618c25031801bd18fb3. Checksum cocok dan arsip berhasil dipulihkan pada cluster privat PostgreSQL 14.22. Seluruh operasi tulis berikut hanya dilakukan pada salinan sementara.

| Bukti | Hasil dan makna |
|---|---|
| Baseline pemulihan | 2.260.668 record pada raw dan setiap layer pinjaman, sesuai backup terbaru |
| Build label | Tiga model/12 tes dbt lulus; label 0=1.076.751, 1=268.599, NULL=915.318 pada ketiga layer |
| Pemeriksaan per record | ID tetap unik dan lengkap; seluruh kolom selain label dibandingkan per ID, tanpa perbedaan |
| Input raw/macro | Jumlah dan sidik agregat tetap sama; sidik agregat bukan bukti kesamaan bebas benturan hash |
| Rollback | Pemulihan kembali ke kondisi lama berhasil; nol perbedaan seluruh record termasuk label, definisi view sama dengan baseline |
| Penghentian server | Cluster privat berhasil dihentikan |

Rollback berarti mengembalikan keadaan sebelum perubahan bila penerapan bermasalah. Bukti ini menguji pemulihan data/struktur; owner dan ACL (hak akses) tidak dipulihkan pada simulasi. Metadata target harus diverifikasi lagi sebelum perubahan aktif. Laporan: [M0_LABEL_RESTORE_REPORT.json](M0_LABEL_RESTORE_REPORT.json); skrip: scripts/verify_m0_label_restore.py.

Penerapan aktif belum dijalankan. Usulan konkret di rencana penerapan membatasi perubahan pada staging dan dua mart pinjaman, memeriksa ulang baseline serta disk, dan mensyaratkan penghentian penggunaan downstream selama build/pemulihan. dbt tidak menjamin seluruh rangkaian model dikembalikan otomatis bila gagal. Source dan hasil simulasi masih lokal; CI pada commit lama tidak memvalidasi perubahan ini. Persetujuan rebuild aktif merupakan keputusan berikutnya, terpisah dari training, CI dan rilis.

### Perbaikan startup PostgreSQL pada lingkungan Terminal

Eksekusi lanjutan gagal sebelum tes SQL berjalan: initdb berhasil, tetapi start gagal. Log PostgreSQL memuat `postmaster became multithreaded during startup` dan menyarankan menetapkan `LC_ALL` ke locale yang valid. Locale adalah pengaturan bahasa/format lingkungan proses. Nilai persis locale Terminal saat gagal tidak direkam, sehingga tidak diasumsikan nilainya.

Skrip sebelumnya hanya memberikan `--locale=C` kepada initdb untuk membuat database; proses pg_ctl/postgres berikutnya masih mewarisi lingkungan Terminal. Perbaikan menetapkan `LC_ALL=C` dan `LANG=C` dalam salinan environment untuk proses anak skrip. Pengaturan shell global dan database aktif tidak diubah. Pesan kegagalan startup kini menunjukkan start.log serta postgres.log agar penyebab server lebih mudah ditemukan.

Pengujian regresi menjalankan skrip dari environment induk yang sengaja memakai locale tidak valid. Startup berhasil, lima model dan 27 tes pada build akhir lulus, seluruh kasus negatif tetap terdeteksi, dan cluster sementara dihentikan. Pemeriksaan Black/isort/Ruff/mypy pada skrip juga lulus. Bukti versi terbaru: [M0_DBT_STARTUP_FIX_REPORT.json](M0_DBT_STARTUP_FIX_REPORT.json). Laporan label sebelumnya dipertahankan sebagai bukti historis, bukan ditimpa dengan hash skrip baru.

### Pembaruan implementasi label lokal

Kontrak retrospektif disetujui untuk SQL dan tes terisolasi. Perubahan lokal mengeluarkan Late (31-120 days) dari label 1; semua status di luar tiga string yang disetujui menghasilkan NULL. Deskripsi skema diperbaiki agar jelas bahwa record berlabel NULL tetap disimpan pada warehouse.

| Pemeriksaan | Hasil | Makna |
|---|---|---|
| Tes baru pada SQL lama | Gagal dengan 3 pelanggaran | Satu kasus keterlambatan salah dilabeli pada staging dan dua mart; tes dapat menangkap perilaku yang hendak diperbaiki |
| Fixture label pada SQL baru | Lulus untuk 11 kasus status, termasuk kosong dan tidak dikenal | 13 record sintetis termasuk dua record awal tetap memiliki ID/status/label sesuai pada ketiga layer; build tidak mengubah raw |
| Label Current=0 dan Late=1 sengaja ditulis pada mart tes | Tes mendeteksi 2 pelanggaran | Status di luar target tidak boleh memperoleh label sembarang |
| Label Fully Paid sengaja dikosongkan pada mart tes | Tes mendeteksi 1 pelanggaran | Perbandingan label aman terhadap NULL; kesalahan tidak lolos diam-diam |
| Status sumber kosong | Tes kualitas sumber menolak 1 record, sesuai harapan | Aman dipetakan menjadi label NULL tidak berarti input memenuhi syarat kualitas sumber |
| Full build setelah fixture negatif dipulihkan | 5 model dan 27 tes lulus, tanpa kegagalan | Pemeriksaan akhir memakai 12 record sintetis setelah satu fixture sumber kosong dihapus secara sengaja |
| Penghentian cluster privat | Berhasil | Server database sementara telah dihentikan |
| Regresi ingestion dan migrasi | Delapan pemeriksaan terisolasi lulus | Perubahan definisi view tetap kompatibel dengan migrasi, pemulihan view, resume dan penjaga downgrade; cluster tes dihentikan |

Saat awal pengujian, sandbox membatasi shared memory PostgreSQL. Eksekusi tes yang diizinkan kemudian memakai socket privat dan TCP dimatikan. Percobaan pertama sesudah perbaikan label menemukan konflik fixture NULL dengan aturan kualitas sumber; aturan itu dipertahankan, penolakannya diuji secara eksplisit, lalu fixture negatif dipulihkan. Bukti dan hash source: [M0_LABEL_ISOLATED_REPORT.json](M0_LABEL_ISOLATED_REPORT.json).

Hasil ini berlaku untuk perubahan lokal, belum untuk CI commit baru atau database aktif. Database aktif belum direbuild. Training, perubahan CI, merge dan deployment belum dilakukan. Syarat persetujuan berikut tetap berlaku:

| Urutan | Pekerjaan | Alasan |
|---|---|---|
| 1 | Tetapkan sumber unduhan, versi, izin penggunaan dan waktu snapshot outcome, atau catat ketidakpastian serta batas penggunaan yang sesuai | Nama file dan tanggal pembayaran terakhir tidak cukup untuk membuktikan asal atau tanggal snapshot |
| 2 | [Kontrak target](../M0_LABEL_DECISION_DRAFT.md) disetujui; SQL lokal lulus tes terisolasi, penerapan aktif belum dilakukan | Retrospektif berarti mempelajari hasil pinjaman yang tercatat dalam snapshot; belum membuktikan prediksi default dalam horizon tetap |
| 3 | Profil awal tahun/tenor/status selesai; gunakan hasilnya untuk rancangan kelayakan dataset | Pemilihan hanya kandidat berlabel mengubah komposisi kelompok, terutama tahun baru dan tenor panjang; belum cukup untuk menetapkan cutoff waktu |
| 4 | Tentukan fitur yang tersedia pada waktu penggunaan dan aturan pembagian train/validation/test | Mencegah informasi yang baru diketahui kemudian masuk ke model dan membuat hasil evaluasi tampak lebih baik dari kenyataan |
| 5 | Sepakati penanganan CI sebelum merge | Pemeriksaan sesudah merge dan rilis perlu input serta kriteria yang jelas |

Tanggal pemisahan data belum ditetapkan. Angka kandidat tidak digunakan untuk memulai training. Implementasi M1, training penuh, merge, deployment dan perubahan riwayat Git tetap mengikuti persetujuan lingkup yang berlaku.

Bukti pendukung: [CI](M0_PR14_CI_REPORT.json), [tes ingestion terisolasi](M0_INGESTION_ISOLATED_REPORT.json), [rebuild dbt](M0_POST_INGESTION_DBT_REPORT.json), [asal dan cakupan data](../DATA_PROVENANCE.md).
