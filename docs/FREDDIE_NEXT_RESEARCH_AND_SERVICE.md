# Penelitian berikutnya dan urutan penerimaan layanan

13 Oktober 2026. V3 diterima pada development validation tetapi ditolak pada ujian
independen. Ini keputusan rilis model; source/terms yang sudah diterima tidak perlu
dikonfirmasi ulang. Data Freddie tetap riset hipotek retrospektif privat.

## Status terbaru — 15 Oktober 2026

V4 kini lulus validation dan ujian independen sekali pada vintage2022. Sampel2021
menjadi development dan seluruh vintage2022 kini consumed. Tidak perlu mencari data
baru untuk mengulang kelulusan kandidat yang sama. Perubahan model di masa depan tetap
memerlukan ujian baru. [Kontrak v4](FREDDIE_V4_HISTORY_PROTOCOL.md) mendokumentasikan
fit terbatas, feature-only HTTP parity dan API riset loopback dengan token/rate/byte limits.
Numerik, model dan kredensial tetap privat. Scoring fintech production tetap HOLD.

Tahap berikutnya adalah adapter riwayat operasional dengan availability yang dapat
dibuktikan, kesesuaian penggunaan sumber/populasi, transport/akses operasional, image+bundle
parity/load, actual delayed-label monitoring dan rollback pada lingkungan yang dinyatakan.

## Urutan penelitian sebelumnya — konteks 13 Oktober

1. **Audit fitur ke belakang pada development 2018/2019.** Kandidat fitur: worst/number
   of delinquency observations dalam 6/12bulan sebelumnya, waktu sejak tunggakan terakhir,
   completeness riwayat dan perubahan UPB. Semua menggunakan bulan sebelum/as-of yang
   terkunci; tidak memakai future status, recovery atau outcome. Audit development
   kini diimplementasikan dengan [kontrak eksplisit](FREDDIE_DEVELOPMENT_HISTORY_AUDIT.md).
   Whitelist baru, kalender, missingness dan availability masih harus dikunci sebelum
   fit baru; audit bukan bukti recall akan meningkat.
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
| Immutable bundle | Model+transform+calibrator+ordered schema/units/missing rules+versions+checksum | Bundle riset privat terikat evidence; belum bundle operasi fintech |
| Training-serving parity | Domain record → reload → actual HTTP score yang sama, invalid inputs ditolak | Feature-only HTTP parity nyata lulus; adapter raw monthly records belum selesai |
| Kontrol API | Auth/HTTPS, byte/rate limits, request/event IDs, akses dan audit tanpa raw input | API riset: bearer/loopback/byte/rate teruji; HTTPS/event audit operasi belum lengkap |
| Beban dan packaging | Lingkungan/digest/model yang sama, p50/p95/p99, error/RSS, cold/warm dan concurrency | Docker dashboard smoke terpisah; bukan API model release |
| Monitoring | Actual inference, delayed labels, cohort/drift/quality per version dan prosedur respons | Prototype modul ada; belum bukti operasi layanan real |
| Rollback/pilot | Model+image sebelumnya, failure injection terisolasi dan recovery smoke | Belum dibuktikan pada layanan model yang diterima |

Rilis hanya mengacu lingkungan, beban dan scope yang benar-benar diuji. Tidak ada klaim
production atau regulatory compliance dari CI, jumlah baris, deployment dashboard atau
AP-lift saja. LendingClub dan Freddie tetap track berbeda; model hipotek tidak mengganti
model aplikasi LendingClub. Tidak ada pembelian hosting, aktivasi scoring atau merge.
