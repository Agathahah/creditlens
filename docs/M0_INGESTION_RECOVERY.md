# M0 — pemulihan ingestion yang terhenti

2026-09-09. Diagnosis dan pemulihan ingestion lokal M0; tidak mengubah kontrak label atau menjalankan training.

## Diagnosis terverifikasi

Raw cocok persis dengan ID valid pada 16 chunk pertama CSV (masing-masing chunk sumber 100.000 record, total valid 1.599.982). Tidak ada ID raw di luar prefix atau ID prefix yang hilang. Log historis berhenti setelah 16 batch dengan StringDataRightTruncation VARCHAR(50). Hanya loan_status yang melampaui batas string schema: 761 record bernilai `Does not meet the credit policy. Status:Charged Off`, panjang 51, pertama kali muncul pada chunk 17.

Ini bukti kuat kegagalan mekanisme ingestion. Tanggal log Juli berbeda dari loaded_at Agustus, sehingga jangan mengklaim file log tersebut membuktikan identitas instance/eksekusi terakhir. Bukti rinci: audit/M0_INGESTION_DIAGNOSIS.json.

## Keputusan perbaikan

| Keputusan | Alasan | Batas |
|---|---|---|
| loan_status menjadi TEXT | Raw mempertahankan nilai sumber secara utuh; pemotongan akan mengubah makna/status | Tidak otomatis mengubah label ML; status out-of-policy tetap terpisah sampai kontrak label disetujui |
| Sinkronkan migration, ORM dan init SQL | Database lama dan instalasi baru harus mendukung kontrak sama | Downgrade harus menolak bila ada teks >50, bukan memotong data |
| Parsing tanggal per kolom, insert secara batch | Loader lama memparse setiap field per record dan menulis satu SQL per loan | Tetap mempertahankan transform legacy; kebijakan missing value ML diperbaiki pada milestone evaluasi |
| Mode insert-missing dengan ON CONFLICT DO NOTHING | Memulihkan ID yang belum ada tanpa menulis ulang 1.599.982 record yang sudah tersimpan | Gunakan snapshot CSV terverifikasi; bukan mekanisme update snapshot outcome |
| Commit per chunk + laporan count | Dapat melanjutkan sesudah gangguan dengan melewati ID tersimpan; terlihat berapa record dilewati/dimasukkan | Bukan transaksi tunggal seluruh file; kegagalan dilaporkan dan batch gagal di-rollback |

## Pengujian sebelum data aktif

Gunakan cluster PostgreSQL privat, socket unik, TCP nonaktif, fixture buatan. Buktikan kolom lama gagal menyimpan status 51 karakter dan batch di-rollback; migration menerima status utuh; mode insert-missing menjaga nilai record yang sudah ada; pengulangan menambah nol baris; input field wajib kosong dihitung sebagai exclusion. Uji guard downgrade ketika teks panjang ada. Unit tests menilai mapping tanggal/null dan pilihan operasi, bukan performa model.

## Data lokal, backup dan verifikasi

1. Target eksplisit localhost:5432/creditlens; catat revision/schema/counts dan ruang disk. Source checksum harus sama dengan manifest M0. Periksa state sebelum mutation agar perubahan pengguna tidak ditimpa.
2. Simpan pg_dump custom-format untuk raw.lc_loans serta dua mart saat ini di .local-backups privat/diabaikan Git, berikut checksum dan TOC. Ini backup scoped, bukan backup seluruh server. Uji restore pada cluster privat bila memungkinkan sebelum perubahan data aktif; keterbatasan owner/ACL dicatat.
3. Terapkan migration yang sesuai revision aktif. Jangan stamp revision atau mengulang initial migration tanpa verifikasi. Jangan mengubah source/status yang sudah ada untuk sekadar melewati error.
4. Jalankan insert-missing dengan batch kecil dan satu koneksi. Simpan report agregat tanpa parameter/record pribadi; periksa ruang disk sebelum fase besar. Jangan log password atau payload borrower.
5. Setelah sukses, bandingkan ID dengan CSV lagi, count raw/staging, lalu rebuild dua mart saja menggunakan salinan dbt project/profile eksplisit. Pastikan nonempty, uniqueness dan rekonsiliasi lulus.
6. Bila batch gagal, hentikan dan diagnosis; batch sebelumnya tetap tercatat. Bila dibutuhkan pemulihan, gunakan backup scoped setelah review keadaan; tidak menghapus schema dengan CASCADE. Jangan otomatis menurunkan guard disk atau memotong data.

Kriteria selesai: semua ID kandidat sumber tercakup atau exclusion valid terurai, status panjang tersimpan utuh, tes/resume terbukti, dan mart konsisten. Hasil aktual harus dicatat sesudah eksekusi. Angka 2.260.668 adalah cakupan kandidat ingestion, bukan ukuran dataset training yang sudah disepakati.

## Hasil 10 September 2026

- Tujuh unit tests parsing lulus. Delapan pemeriksaan PostgreSQL privat lulus, termasuk rollback, resume/no-op, update outcome default, guard downgrade dan perlindungan dependency view.
- Detail yang ditemukan selama verifikasi: PostgreSQL menolak perubahan tipe kolom yang masih dipakai view. Migration kini menyimpan definisi staging, DROP VIEW RESTRICT, mengubah tipe, lalu membuat view dalam satu transaksi. Metadata custom (owner berbeda, ACL, options, comments/security labels) membuat migration berhenti agar tidak dibuang. Downstream view tak dikenal diblokir tanpa CASCADE. Definisi hasil PostgreSQL menormalkan cast text/array; tes membandingkan SQL setelah normalisasi cast dan memeriksa nilai/label fixture.
- Backup raw + staging view + dua mart berukuran 293.338.379 byte. Restore privat sukses: setiap relasi 1.599.982 baris, lima indeks raw kembali. Owner/ACL tidak dipulihkan dalam drill. Percobaan awal server uji gagal karena socket path >103 byte; path diperpendek, bukan membuka TCP.
- Dryrun semua CSV lulus: 2.260.701 dibaca, 2.260.668 valid, 33 tanpa field wajib, 761 status >50 karakter. Tidak ada pemotongan status atau perubahan mapping label.
- Database lokal berhasil upgrade e9827ae898f0 → 4b7d2a91c608. Resume: 660.686 inserted, 1.599.982 skipped, 33 excluded, 14 batch committed. Jumlah dan fingerprint agregat seluruh field record lama, termasuk loaded_at, tidak berubah. Ini cek agregat row-hash, bukan bukti byte-for-byte backup.
- Rekonsiliasi set ID sumber/raw: selisih dua arah nol. Raw/staging/loan/final 2.260.668; dua model dbt sukses dan 9 tes pass. Dataset training belum disepakati.
- Disk sesudah raw 4,250 GiB, sesudah rebuild 3,747 GiB. Backup lama tetap disimpan; hanya salinan database restore buatan script yang dihapus setelah lulus dan server berhenti.

Bukti: [fixture](audit/M0_INGESTION_ISOLATED_REPORT.json), [dryrun](audit/M0_INGESTION_DRYRUN.json), [backup](audit/M0_INGESTION_BACKUP.json), [restore](audit/M0_INGESTION_RESTORE_REPORT.json), [resume](audit/M0_INGESTION_RECOVERY_REPORT.json), [dbt](audit/M0_POST_INGESTION_DBT_REPORT.json), [ID](audit/M0_ID_RECONCILIATION.json). Script satu kali diarsipkan di audit/m0_ingestion_scripts; bukan instruksi untuk menjalankan ulang mutation. Entry point loader mendukung --insert-missing; shell yang benar memakai `python -m scripts.load_data` dari root.

Subtugas pemulihan ingestion selesai. M0 keseluruhan belum ditutup: provenance, as-of dan [keputusan target](M0_LABEL_DECISION_DRAFT.md) masih perlu disepakati.
