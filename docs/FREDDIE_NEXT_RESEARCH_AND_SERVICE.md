# Penelitian berikutnya dan urutan penerimaan layanan

13 Oktober 2026. V3 diterima pada development validation tetapi ditolak pada ujian
independen. Ini keputusan rilis model; source/terms yang sudah diterima tidak perlu
dikonfirmasi ulang. Data Freddie tetap riset hipotek retrospektif privat.

## Tahap penelitian berikutnya

1. **Audit fitur ke belakang pada development 2018/2019.** Kandidat fitur: worst/number
   of delinquency observations dalam 6/12bulan sebelumnya, waktu sejak tunggakan terakhir,
   completeness riwayat dan perubahan UPB. Semua menggunakan bulan sebelum/as-of yang
   terkunci; tidak memakai future status, recovery atau outcome. Whitelist, kalender,
   missingness dan availability harus dikunci sebelum fit. Ini usulan, belum implementasi
   atau bukti recall akan meningkat.
2. **Sediakan holdout baru.** Sample 2021/2022 SFLLD adalah kandidat intake berikutnya,
   belum ditemukan lokal. Simpan privat; hash sumber, layout, release/cutoff dan batas
   penggunaan harus tercatat. Jangan memakai outcome holdout untuk memilih fitur,
   model, calibrator, cohort atau policy. Tahun/month ujian baru ditetapkan dari metadata
   maturity sebelum fit. Seluruh vintage 2020 tetap consumed, tidak dialihkan menjadi
   ujian baru pada bulan lain.
3. **Kunci protokol dan fit terbatas.** Development validation tetap pengembangan,
   kalibrasi berbeda pinjaman/periode dan threshold/capacity terkunci. Gate sebelumnya
   tidak diturunkan untuk meluluskan v3. Bila operator ingin policy berbeda, kebutuhan
   biaya/kapasitas nyata harus ditetapkan sebagai use case baru sebelum evaluasi baru.
4. **Ujian independen sekali.** Kandidat yang lolos validation dikunci; ujian baru
   menggunakan candidate/source/schema/checksum yang sama, tanpa fitting/reselection.
   Penolakan membuat kandidat tidak dipromosikan dan holdout dianggap terpakai.

## Tahap layanan setelah model memenuhi kualitas

| Tahap | Bukti penerimaan yang harus dihasilkan | Status sekarang |
|---|---|---|
| Kesesuaian penggunaan | Produk/populasi/decision time dan hak penggunaan operator jelas | Freddie privat tidak mengesahkan scoring fintech |
| Point-in-time | feature_available_at, label availability, reporting lag dan riwayat koreksi | Snapshot terkoreksi; timestamp asli belum terbukti |
| Immutable bundle | Model+transform+calibrator+ordered schema/units/missing rules+versions+checksum | Candidate privat ada; tidak ada accepted serving bundle |
| Training-serving parity | Domain record → reload → actual HTTP score yang sama, invalid inputs ditolak | Save/reload penelitian ada; HTTP parity real belum selesai |
| Kontrol API | Auth/HTTPS, byte/rate limits, request/event IDs, akses dan audit tanpa raw input | Batas numerik/CORS/envelope ada; kontrol operasional belum lengkap |
| Beban dan packaging | Lingkungan/digest/model yang sama, p50/p95/p99, error/RSS, cold/warm dan concurrency | Docker dashboard smoke terpisah; bukan API model release |
| Monitoring | Actual inference, delayed labels, cohort/drift/quality per version dan prosedur respons | Prototype modul ada; belum bukti operasi layanan real |
| Rollback/pilot | Model+image sebelumnya, failure injection terisolasi dan recovery smoke | Belum dibuktikan pada layanan model yang diterima |

Rilis hanya mengacu lingkungan, beban dan scope yang benar-benar diuji. Tidak ada klaim
production atau regulatory compliance dari CI, jumlah baris, deployment dashboard atau
AP-lift saja. LendingClub dan Freddie tetap track berbeda; model hipotek tidak mengganti
model aplikasi LendingClub. Tidak ada pembelian hosting, aktivasi scoring atau merge.
