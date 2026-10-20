# Intake sumber untuk eksperimen M1 berikutnya

Diperiksa 29 September 2026. Scope eksperimen disetujui; status intake saat ini
**MISSING_SOURCE**. Belum ada sumber yang diakui memenuhi target aplikasi 36 bulan.

## Hasil seleksi sumber

| Sumber | Bukti | Keputusan intake |
|---|---|---|
| File CreditLens 2007–2018 yang sudah tersedia | Identitas byte diverifikasi dalam audit sebelumnya; snapshot outcome dan timing kejadian belum terverifikasi | Tidak menjadi holdout baru; frozen test 2015 sudah terpakai |
| [Zenodo 11295916](https://zenodo.org/records/11295916) | Turunan data 2007–2018, outcome final dan status transisi sudah difilter; terbit Mei 2024 | Belum memenuhi kontrak holdout independen dan outcome 36 bulan; tanggal publikasi bukan bukti tanggal snapshot |
| [Mendeley wb3ndt69gf/3](https://data.mendeley.com/datasets/wb3ndt69gf/3) | Sumber 2008–2019 dan lisensi CC BY 4.0 tercatat; publikasi metode menyatakan BADLOAN=1 untuk overdue/default/charged-off, 0 untuk current/repaid | Label yang disediakan tidak sesuai kontrak; perlu sumber outcome asli dan timing sebelum dipertimbangkan |
| [Freddie Mac](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset) | Data origination dan performa bulanan mortgage tersedia melalui pendaftaran dan syarat penggunaan | Populasi/produk berbeda; bukan holdout Lending Club. Memerlukan keputusan perubahan scope |
| [Endpoint unduhan historis LendingClub](https://www.lendingclub.com/info/download-data.action) | Tidak dapat diakses melalui alat riset pada pemeriksaan ini | Akses dan file aktual belum terverifikasi; kegagalan akses alat tidak membuktikan data tidak tersedia |

Definisi BADLOAN dan pengolahan sumber tambahan didukung oleh
[publikasi penulis dataset](https://pmc.ncbi.nlm.nih.gov/articles/PMC8649212/).
Audit ini menilai dokumentasi; tidak mengunduh atau memeriksa record sumber eksternal.
Tidak ditemukan sumber yang sudah lolos seluruh gerbang dalam pencarian terbatas ini.

## Pemeriksaan yang dapat dijalankan sekarang

Jalankan dari root checkout CreditLens:

```bash
python -m scripts.inspect_m1_source
```

Secara default hanya folder privat `Documents/creditlens-private/holdout` yang diperiksa.
Script tidak menelusuri Downloads, mengunduh file, mengakses PostgreSQL atau melatih model.
Jika folder kosong, laporan JSON menyatakan `MISSING_SOURCE` dan exit code 2. Ini adalah status
data belum tersedia, bukan kerusakan environment.

Untuk memeriksa file nyata, gunakan opsi `--file` dengan jalur file yang sudah ada. Terminal macOS
dapat menerima jalur dengan menyeret file dari Finder setelah argumen `--file` diketik.
Jangan memakai ulang alamat contoh `/absolute/path/...`.

## Arti hasil pemeriksaan file

| Status | Exit code | Makna |
|---|---:|---|
| MISSING_SOURCE | 2 | Tidak ada CSV/CSV gzip di folder privat |
| CANDIDATES_FOUND | 0 | Ada calon file; belum dipilih atau divalidasi |
| INVALID_SOURCE | 1 | File hilang, format/header tidak sesuai atau kompresi bermasalah |
| KNOWN_OLD_SNAPSHOT | 2 | Byte file sama dengan snapshot CreditLens lama |
| FILE_INSPECTED_PENDING_REVIEW | 0 | Checksum, ukuran dan header tercatat; bukti ilmiah sumber masih menunggu audit |

Exit code 0 hanya berarti operasi inspeksi selesai. Semua hasil tetap menyatakan
`ready_for_training=false`. Checksum baru tidak membuktikan loan ID independen, snapshot baru,
hak penggunaan atau target horizon yang sah. `last_pymnt_d`, tanggal file dan tanggal publikasi
tidak otomatis menjadi tanggal default atau as-of outcome.

Pemeriksaan memakai buffer 1 MiB untuk hash file, kemudian membaca header. Script tidak menghitung
baris, menilai missingness record, memvalidasi keseluruhan gzip/CSV atau membaca outcome test.
Profil record dan rekonsiliasi ID dilakukan setelah provenance sumber cukup untuk tahap tersebut.

## Bukti yang harus dilengkapi

1. Asal dan hak penggunaan sumber, tanggal outcome as-of, serta definisi event bertanggal.
2. Fitur yang tersedia saat aplikasi, tenor/horizon dan aturan missing/censored.
3. Tanggal cutoff, gap outcome availability, membership dan checksum split yang dikunci.
4. Rekonsiliasi loan ID terhadap train/validation/test historis. Memperbarui label test 2015 tidak
   membuat loan yang sama independen kembali. Keterbatasan borrower overlap harus tetap dilaporkan.
5. Protokol kandidat, calibration, metrik, gate dan batas sumber daya sebelum test dibuka.

Laporan dengan lokasi file pribadi tetap di `.local-backups/` dan di luar Git.
Hanya source code, tes, keputusan dan bukti agregat yang aman menjadi perubahan PR.
Lihat [scope yang disetujui](M1_NEXT_EXPERIMENT_SCOPE.md).
