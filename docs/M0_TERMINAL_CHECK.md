# Verifikasi warehouse secara baca-saja

## Status SQL lokal dan database aktif

SQL lokal kini memakai kontrak label yang disetujui: Fully Paid=0, Charged Off/Default=1, status lain=NULL. Kontrak telah diuji pada PostgreSQL sementara. Database aktif belum direbuild; perubahan file SQL tidak otomatis mengubah view atau tabel yang sudah tersimpan. Karena itu, tes loan_label_contract pada database aktif dapat mendeteksi mapping lama sampai penerapan yang disetujui selesai.

Untuk mengulang tes terisolasi dari folder repo pada Terminal macOS (bukan prompt psql):

```bash
.venv/bin/python scripts/verify_m0_dbt.py
echo $?
```

Skrip membuat cluster sementara, memasukkan data sintetis kecil, memeriksa mapping dan kegagalan yang disengaja, lalu menghentikan cluster. Tidak membaca kredensial database aktif atau menjalankan training. Membutuhkan PostgreSQL 16 pada path Homebrew dan dbt dari .venv. Baris exit=1 expected=1 adalah penolakan yang sengaja diuji; hasil akhir yang sehat adalah exit proses 0, status passed pada report.json dan cluster_stopped true. Jangan menjalankan dbt build pada database aktif sebagai pengganti perintah ini.

## Pemeriksaan jumlah pada database aktif

Catatan troubleshooting tes terisolasi: jika startup gagal, baca start.log dan postgres.log pada direktori Report. Pesan postmaster became multithreaded during startup dengan petunjuk LC_ALL telah diperbaiki pada skrip dengan locale C khusus proses anak. Jalankan kembali perintah skrip yang sama; tidak perlu mengubah konfigurasi shell global. Setiap eksekusi membuat direktori sementara baru, sehingga log kegagalan lama tetap tersedia. Bukti regresi: [perbaikan startup](audit/M0_DBT_STARTUP_FIX_REPORT.json).

Hasil pemulihan lokal yang tercatat: raw, staging dan kedua mart pinjaman masing-masing berisi 2.260.668 baris.

Hubungkan psql menggunakan password pengguna database creditlens:

```bash
PGOPTIONS='-c default_transaction_read_only=on' psql -X -h localhost -p 5432 -U creditlens -d creditlens
```

Pada instalasi macOS yang sudah diperiksa, psql juga tersedia di /opt/homebrew/opt/postgresql@16/bin/psql.

```sql
SHOW transaction_read_only;
SELECT 'raw' AS layer, COUNT(*) FROM raw.lc_loans
UNION ALL SELECT 'staging', COUNT(*) FROM staging.lc_loans_clean
UNION ALL SELECT 'loan', COUNT(*) FROM mart.loan_features
UNION ALL SELECT 'final', COUNT(*) FROM mart.final_features;
```

Hasil yang diharapkan: transaction_read_only bernilai on dan keempat jumlah baris bernilai 2260668 pada snapshot yang tercatat. Jika berbeda, periksa sumber, filter dan build terakhir sebelum mengulang ingestion atau rebuild. Query ini belum membuktikan kesamaan seluruh nilai, kecukupan waktu pengamatan outcome, atau kualitas model. Rekonsiliasi ID sumber dan hasil terperinci tercatat di audit/M0_ID_RECONCILIATION.json.

## Profil kandidat menurut tahun dan tenor

Jalankan query berikut di psql. Query hanya membaca raw dan membuat ringkasan; tidak mengubah label SQL yang aktif. Tahun menunjukkan waktu pinjaman diterbitkan. Tenor adalah jangka waktu pinjaman. Pengelompokan ini membantu memeriksa apakah proporsi kandidat berlabel berbeda pada tahun dan tenor tertentu sebelum menentukan pembagian dataset model.

```sql
SELECT
    EXTRACT(YEAR FROM issue_date)::int AS tahun,
    COALESCE(NULLIF(TRIM(term), ''), 'tidak_diketahui') AS tenor,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE loan_status = 'Fully Paid') AS kandidat_0,
    COUNT(*) FILTER (
        WHERE loan_status IN ('Charged Off', 'Default')
    ) AS kandidat_1,
    COUNT(*) - COUNT(*) FILTER (
        WHERE loan_status IN ('Fully Paid', 'Charged Off', 'Default')
    ) AS di_luar_target
FROM raw.lc_loans
GROUP BY 1, 2
ORDER BY 1, 2;
```

Kriteria pemeriksaan:

- Pada setiap baris, total = kandidat_0 + kandidat_1 + di_luar_target. Status NULL juga masuk di_luar_target karena dihitung sebagai selisih dari seluruh record.
- Jumlah total seluruh kelompok diharapkan 2.260.668; kandidat_0 berjumlah 1.076.751, kandidat_1 berjumlah 268.599 dan di_luar_target berjumlah 915.318 pada snapshot yang sudah diperiksa.
- Catat kelompok tahun/tenor dengan banyak record di_luar_target. Kelompok tersebut mencakup beberapa jenis status, sehingga tidak semuanya dapat disebut pinjaman berjalan atau belum matang tanpa memeriksa rincian statusnya.
- Jangan menetapkan tanggal split atau menganggap evaluasi prospektif valid hanya dari tabel ini. Tanggal snapshot dan waktu outcome diketahui masih perlu bukti.

Profil 21 kelompok telah diterima dari keluaran psql dan diperiksa ulang penjumlahannya. Hasil dan batas interpretasi tercatat dalam [review M0](audit/M0_PR14_REVIEW.md). Database tidak diakses ulang oleh reviewer untuk menghasilkan profil tersebut.

## Rincian status di luar target per periode

Query baca-saja berikut menjelaskan isi kelompok di_luar_target. Periode 2007–2010, 2011–2015 dan 2016–2018 hanya kelompok pelaporan untuk diagnosis; bukan pembagian train/validation/test. Kolom status NULL tetap diperhitungkan melalui IS NOT TRUE.

```sql
SELECT
    CASE
        WHEN EXTRACT(YEAR FROM issue_date) BETWEEN 2007 AND 2010
            THEN '2007–2010'
        WHEN EXTRACT(YEAR FROM issue_date) BETWEEN 2011 AND 2015
            THEN '2011–2015'
        WHEN EXTRACT(YEAR FROM issue_date) BETWEEN 2016 AND 2018
            THEN '2016–2018'
        ELSE 'periode_lain'
    END AS periode,
    COALESCE(loan_status, '(NULL)') AS status,
    COUNT(*) AS jumlah
FROM raw.lc_loans
WHERE (loan_status IN ('Fully Paid', 'Charged Off', 'Default')) IS NOT TRUE
GROUP BY 1, 2
ORDER BY 1, jumlah DESC, 2;
```

Jumlah semua baris diharapkan 915.318 pada snapshot yang tercatat; subtotal periode 2007–2010 diharapkan 2.749 berdasarkan profil tahun/tenor. Distribusi per status belum diasumsikan. Bila subtotal tahun awal seluruhnya berasal dari status di luar kebijakan, kelompok itu tidak boleh dijelaskan sebagai pinjaman yang belum selesai. Untuk periode baru, periksa kontribusi Current, status keterlambatan dan status lain sebelum menyimpulkan penyebab pengeluaran dari target.
