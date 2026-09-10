# M0 — identitas sumber dan cakupan ingestion

Snapshot awal 9 September dan pembaruan 10 September 2026. Pemulihan ingestion dilakukan dengan backup/restore teruji; training belum dijalankan.

| Item | Hasil verifikasi |
|---|---|
| File lokal | data/raw/accepted_2007_to_2018Q4.csv.gz |
| Ukuran terkompresi | 392.582.231 byte |
| SHA-256 file terkompresi | 55c16f75120f897683f02e7aabcf080d0e4a20c4832feb1d592cfa941bd62a2d |
| Jumlah record CSV | 2.260.701 |
| Record dengan ID numerik, amount numerik dan issue_d terisi | 2.260.668 |
| Record tanpa ID numerik/issue_d | 33; tidak dimasukkan perbandingan ID |
| ID duplikat dalam kandidat sumber | 0 |
| Rentang tahun kandidat CSV | 2007–2018 |
| ID raw sesudah recovery | 2.260.668, seluruhnya ditemukan dalam kandidat CSV |
| ID kandidat CSV yang belum ada di raw | **0**; sebelumnya 660.686, kini sudah dimasukkan |
| Rentang issue_date raw | Juni 2007–Desember 2018 setelah recovery; sebelumnya 2014–2018 |
| Source URL, pengunduh, waktu unduh | Belum terverifikasi; nama file bukan bukti provenance lengkap |
| Lisensi/izin penggunaan dataset | Belum terverifikasi; lisensi repo tidak otomatis berlaku pada data |
| Waktu snapshot outcome/as-of | Belum terverifikasi; loaded_at bukan waktu outcome diketahui |

Definisi kandidat di tabel hanya untuk rekonsiliasi dasar: ID/amount numerik dan issue_d ada. Ini belum aturan eligibility training, validasi seluruh field, parsing semua tanggal, atau kontrak label. Profil terperinci: [M0_CSV_PROFILE.json](audit/M0_CSV_PROFILE.json). Perbandingan set ID yang benar-benar dijalankan: [M0_ID_RECONCILIATION.json](audit/M0_ID_RECONCILIATION.json).

## Diagnosis dan pemulihan yang sudah terbukti

Raw lama cocok persis dengan prefix 16 chunk CSV. Log historis memperlihatkan kegagalan VARCHAR(50), sedangkan 761 status sumber panjangnya 51 karakter. Tanggal log berbeda dari loaded_at, sehingga bukti ini menunjukkan mekanisme yang cocok, bukan identitas run terakhir yang pasti. Bukti: audit/M0_INGESTION_DIAGNOSIS.json.

Schema kini memakai TEXT tanpa pemotongan. Setelah backup dan restore drill, insert-missing menambahkan 660.686 record serta menjaga fingerprint record lama. Seluruh 2.260.668 kandidat lolos normalisasi 37 field dan batas angka sebelum write. Raw/staging/loan/final kini masing-masing 2.260.668. Ini cakupan ingestion, belum eligibility training.

Jumlah 2,9 juta dalam komentar historis tidak cocok dengan CSV ini. Rejected tidak digabung sebagai label negatif. File tidak diunggah/redistribusikan; backup hanya lokal privat.

## Yang belum diketahui

Asal unduhan, izin penggunaan dan tanggal snapshot outcome belum terverifikasi. Pertanyaan asal data telah diajukan kepada Agatha. Last payment maksimum Maret 2019 hanya isi kolom; bukan bukti tanggal snapshot atau tanggal default. loaded_at adalah waktu ingestion, bukan tanggal outcome diketahui. Seluruh member_id NULL: evaluasi berbasis orang dan jaminan tidak ada borrower overlap belum dapat dibuat.

Keputusan berikutnya: [draft target/eligibility](M0_LABEL_DECISION_DRAFT.md), lalu manifest cohort/split setelah batas klaim dan ketersediaan waktu jelas. [Rekonsiliasi sebelum recovery](audit/M0_ID_RECONCILIATION_BEFORE_INGESTION.json) tetap disimpan agar sejarah diagnosis tidak ditimpa.
