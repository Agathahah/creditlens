# Eksperimen hipotek v3: waktu, kalibrasi dan keputusan rilis

Tanggal 13 Oktober 2026. Riset retrospektif privat, tahap pengembangan. Protokol dikunci
sebelum membaca statistik cohort baru atau fit: SHA-256 `f4eef57a25e638f9a4c694a16f3d93d2bd8ee8f50440d5c9758cbd440eee0411`.
Otorisasi adalah kelanjutan riset terbatas dan keputusan teknis yang didelegasikan; bukan
klaim tanda tangan pemilik atas hash. Sumber/ketentuan privat yang diterima tetap berlaku.

## Perubahan untuk menjawab kegagalan v2

| Peran | Vintage | Bulan laporan | Outcome terakhir |
|---|---|---|---|
| Train | 2018 | Jan 2019–Sep 2020 | Des 2020 |
| Calibration | 2019, bucket loan 0 | Jan–Sep 2021 | Des 2021 |
| Development validation | 2019, bucket loan 1 | Apr–Des 2022 | Mar 2023 |
| Test terencana, masih tertutup | 2020 | Jul 2023–Mar 2024 | Jun 2024 |

Train mencakup periode sebelum/saat krisis agar bukan hanya periode rendah event.
Ini tidak menjamin generalisasi ke kondisi ekonomi baru. Calibration dan validation
menggunakan bucket hash pinjaman yang tetap, tanpa stratifikasi outcome; satu pinjaman
tidak dapat masuk keduanya. Label train selesai sebelum calibration; label calibration
selesai sebelum validation; label validation selesai sebelum test. Ada jeda kalender,
tetapi tidak ada klaim timestamp publikasi asli sudah diketahui pada data terkoreksi.

Test v1/v2 semula Jan–Sep 2021. Periode itu tidak lagi cocok sebagai ujian temporal
setelah calibration/validation digeser. Rencana test direvisi sebelum isi vintage 2020
pernah dibuka. Arsipnya tetap tertutup; tidak ada statistik test untuk memilih perubahan.
Validation baru tetap data pengembangan, bukan bukti ujian final yang independen.

## Model, kalibrasi dan gate

Fitur origination+bulanan dan dua model v2 tetap. Dua thread/15 menit/RSS worker 2 GiB.
Median/missing indicator/scaling fit hanya train. Setiap fitted base estimator dibekukan
lalu sigmoid calibrator fit hanya calibration, bukan validation/test. Raw probabilities
hanya pembanding diagnosis; tidak menjadi opsi selection pasca-hasil. Kandidat dipilih
melalui AP calibrated validation, dengan seri memilih Logistic Regression.

[Dokumentasi scikit-learn](https://scikit-learn.org/stable/modules/calibration.html)
mensyaratkan data fitting/calibration terpisah; sigmoid dipilih sebagai fungsi parametrik
terbatas pada masalah tidak seimbang. Ini tidak menjamin ranking/recall membaik.
[JMLR: Arrieta-Ibarra et al. (2022)](https://jmlr.org/beta/papers/v23/22-0658.html)
menjelaskan tradeoff resolusi/ketidakpastian diagram calibration berbasis bin; reliability
bins bersifat deskriptif, bukan tes formal kalibrasi.

Gate utama tetap: event unik train>=50, validation>=30, AP/prevalence>=2,
lower bound loan-bootstrap lift>1, Brier skill terhadap constant train>0,
recall top1%>=20%, precision lift>=2 dan nonzero alerts. Tidak dilonggarkan setelah v2.
Tambahan: calibration>=50 pinjaman positif unik dan Brier model harus mengungguli
constant prevalence calibration juga. Ini guardrail riset yang lebih ketat, bukan standar
industri atau power calculation. Hasil per bulan/censoring dan observed/mean prediction
wajib dilaporkan. Bootstrap tetap conditional pada fitted base+calibrator, bukan refit CI.

## Urutan menuju layanan

1. Jalankan v3 sekali; support/temporal/loan-disjoint diperiksa sebelum fit.
2. Jika gate validation gagal, simpan bukti dan jangan buka test/promosikan model.
3. Jika lulus, kunci candidate, schema dan checksum; buat kontrak ujian independen
   sebelum membangun panel test. Ini belum pengesahan operational scoring.
4. Setelah ujian model lulus: validasi bundle raw-feature→reload→HTTP, validitas
   point-in-time/hak penggunaan, auth/HTTPS, byte/rate limits, beban, monitoring delayed
   labels dan rollback pada lingkungan bernama. Scoring aktif hanya setelah acceptance.

Hasil aktual execution dicatat di bagian berikut. Data/prediksi/model/hasil numerik
privat tidak diunggah ke GitHub, Tableau Public atau Streamlit.

## Kontrak ujian independen setelah validation diterima

V3 nyata selesai dan checker menghitung ulang semua gate PASS. Kandidat HGB+sigmoid
terkunci. Kontrak execution SHA-256 `b79cd44176c05aac59159ee62cb6d5f19ae9dd936a716586797afdc280fc9726` mengikat model/report/protokol/sumber/window
dan budget yang sama sebelum akses ZIP2020. Ini otorisasi penelitian kondisional melalui
kelanjutan yang didelegasikan, bukan persetujuan layanan production.

Executor terpisah memeriksa checksum/quality sebelum akses, mencatat seluruh vintage 2020
terpakai sebelum member pertama dibaca, membangun panel privat, menguji overlap/layout/label,
dan melakukan predict saja. Tidak ada fit atau pemilihan ulang pada test; marker tidak
dihapus jika intake/ujian gagal. CLI pengembangan tetap menolak vintage 2020. Bukti numeric
ujian tetap privat. Setelah ujian, vintage ini tidak boleh dipakai untuk revisi/evaluasi baru.


## Hasil aktual dan keputusan

Training/calibration/validation v3 nyata selesai dalam 13,478 detik, worker RSS tersampel
sekitar 1,532 GiB. Support/temporal/loan-disjoint lulus; HGB+sigmoid terpilih dan seluruh
gate validation lulus. Raw-HGB Brier pada validation sedikit lebih baik dari calibrated;
mean probability calibrated lebih dekat dengan prevalence. Kalibrasi tidak dijamin
memperbaiki semua metrik. Perbandingan v2/v3 bukan ablation karena cohort/tanggal berbeda.

Ujian independen sekali selesai dalam 33,346 detik dengan worker RSS tersampel sekitar
656,4 MiB. ZIP layout/key/period dan label horizon diperiksa; test loan tidak overlap
sumber pengembangan. Kandidat hanya predict, tanpa fit model/transform/calibrator.
Semua gate kecuali recall pada kapasitas bulanan tetap lulus: **REJECT_TEST**. Model
belum dipromosikan. Vintage2020 seluruhnya terpakai dan tidak boleh dituning/retest.
Source manifest sebelum test dipertahankan; current manifests mencatat consumption.

Brier yang mengungguli constant tidak membuktikan probabilitas sudah terkalibrasi
memadai untuk operasi; reliability/observed-to-predicted tetap perlu ditinjau. Support
minimum bukan power calculation. Conditional AP-lift CI lebar; tidak ada klaim bahwa
recall populasi pasti di bawah gate melalui uji statistik. Penolakan mengikuti criterion
point estimate yang dikunci. Tidak ada klaim manfaat ekonomi atau kesiapan fintech.

Validasi software lokal: 237 passed, 4 skipped, 8 warnings (20,08 detik), black/isort/ruff
lulus dan mypy lulus 88 source files. Coverage total 88% termasuk src/tests; non-test src
83,31% (2.431/2.918 statements). Calibrated orchestration74%, independent executor66%;
gap terutama CLI, admission-failure/support-failure dan abort. Fixture end-to-end memakai
pinjaman sintetis dan tidak mengesahkan model real. Koleksi pytest sempat menganggap
nama fungsi worker sebagai test; fungsi diubah dan seluruh suite lulus. Tidak ada
pengulangan ujian real saat perbaikan software. Snapshot kode actual fit/test disimpan privat.

Checker validation sekarang menyatakan independent-test status NOT_ASSESSED_BY_VALIDATION_CHECKER:
ia menghitung ulang gate validation saja, bukan membaca keputusan ujian yang sudah selesai.
Scoring tetap HOLD. CI branch dan deployment publik dashboard belum diasumsikan lulus dari
local tests; bukti remote dicatat pada PR sesudah push.
