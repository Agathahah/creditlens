# V4 — riwayat pinjaman dan kalibrasi pada cohort lebih baru

14 Oktober 2026. Hash protokol `config/research/freddie_experiment_v4.json`:
`2b034c94ca49445793a9c5e3f1d598cdbbdd9f45aa12070b2fc544051202535b`.
Dikunci sebelum membaca outcome sampel 2021/2022 atau fit, berdasarkan kelanjutan
riset lokal dan keputusan teknis berbatas sumber daya yang telah didelegasikan.
Ini bukan tanda tangan pemilik atas hash atau izin scoring/public model distribution.

## Data, grain dan waktu

Studi tetap hipotek retrospektif privat. Checksum dan byte size dua ZIP baru cocok
dengan receipt lokal; nama member origination/performance sesuai. Metadata directory
ZIP tidak membuktikan layout record, cutoff aktual atau checksum penerbit. Layout
31/35 kolom, keys, bounds, CRC saat streaming dan cutoff harus lulus sebelum fit.
Binding Release47 tetap diinferensikan untuk riset privat, bukan publisher attestation.
Ketentuan pribadi yang diterima sebelumnya berlaku sebagai batas scope; operational
point-in-time availability serta penggunaan layanan fintech belum dibuktikan.

| Role | Vintage | As-of | Outcome paling akhir | Pemisahan identitas |
|---|---:|---|---|---|
| Train | 2018 | Jan2019–Sep2020 | Des2020 | Source berbeda |
| Calibration | 2021 | Jan–Des2023 | Mar2024 | Hash loan bucket0 |
| Validation | 2021 | Apr–Des2024 | Mar2025 | Hash loan bucket1 |
| Frozen test | 2022 | Apr–Des2025 | Mar2026 | Vintage baru; seluruh isi disegel |

Calendar dipilih dari tahun origination dan cutoff resmi Mar2026, sebelum outcome
baru diperiksa. Label tiga bulan harus selesai sebelum role berikutnya dimulai.
Hash SHA256 memakai salt tetap `creditlens-freddie-v4-calibration-20261014`, modulo2;
seluruh bulan satu pinjaman mengikuti bucket yang sama. Identitas lintas-role dicek.
2021 ditetapkan **development** sebelum akses pertama, sehingga tidak menjadi
ujian independen pada versi berikutnya. Vintage2020 tetap consumed dan tidak dibaca.
2019 tetap bukti pengembangan sebelumnya; tidak dipakai untuk selection v4.

Eligibility tetap pinjaman current dengan UPB positif dan tanpa zero-balance event.
Label positif: 90+ hari delinquent/REO teramati dalam tiga bulan kalender ke depan.
Negatif memerlukan ketiga bulan lengkap. Unknown/gap/terminasi menjadi censored NULL,
bukan nol. Counts eligible, labeled, censored dan reason direkonsiliasi per bulan.
Policy top1% dievaluasi pada labeled cohort; ini simulasi penelitian, bukan bukti alert
atas seluruh traffic termasuk observasi yang belum matang/censored.

## Fitur dan estimator

Sepuluh fitur v3 dipertahankan, ditambah sembilan kandidat audit development:
worst_dq_6, dq_months_6, complete_status_6, worst_dq_12, dq_months_12,
complete_status_12, months_since_known_dq_12, upb_change_ratio_3, upb_change_ratio_12.
[Kontrak audit](FREDDIE_DEVELOPMENT_HISTORY_AUDIT.md) mendefinisikan NULL, kalender dan
stock change. Hanya bulan sebelum as-of dipakai untuk history; UPB as-of masuk perubahan
stok. Prior_dq memakai exact calendar lookup, tidak sekadar row offset.

Perubahan cohort dan fitur dilakukan bersama; perbedaan hasil bukan causal ablation.
Tidak dijanjikan recall meningkat. Riwayat yang lebih panjang dapat menyimpan pemulihan
setelah tunggakan; completeness membedakan riwayat tidak tersedia dari tidak ada kejadian.
Snapshot terkoreksi tetap tidak membuktikan kapan informasi pertama kali tersedia.

Constant train prevalence, Logistic Regression dan HGB kecil dibandingkan pada cohort
sama. Parameter/80iter/depth3 tetap dari v3, tanpa search/oversampling/class weighting.
Median+missing indicators di-fit hanya pada train; scaling hanya untuk LR. Base dibekukan
ketika sigmoid di-fit pada calibration. Kandidat dengan calibrated validation AP tertinggi
dipilih; exact tie memilih LR. Raw predictions bersifat diagnostic, bukan jalan mengganti
kandidat setelah melihat validation. Input dan preprocessing menggunakan float32 untuk
mengurangi memori, dan dtype itu juga wajib di jalur evaluasi/test.

## Gate, sumber daya dan ujian

Gate v3 tidak diturunkan: unique adverse loans train≥50/calibration≥50/validation-test≥30;
AP/prevalence≥2, loan-bootstrap95% lower>1, Brier skill positif terhadap constant train dan
calibration, recall monthly top1%≥20%, precision lift≥2, valid probabilities dan alerts.
Bootstrap1.000 resample by-loan menjaga seluruh loan-month bersama; interval conditional
pada kandidat tetap, bukan seluruh ketidakpastian fit atau common-calendar shocks.

Budget tetap dua thread/15menit/RSS2GiB. Reader streaming dan preallocated float32 arrays
menghindari ekstraksi ZIP/SQLite baru. Guard disk minimal2GiB berlaku untuk riset kecil,
terpisah dari8GiB untuk build Docker lokal. Tidak menghapus source/model/evidence lama.
Attempt, source/code snapshot, laporan resource dan hasil ditulis privat tanpa overwrite.

Jika support/validation gagal, vintage2022 tetap disegel. Jika semua gate validation
lulus, checker independen merekalkulasi evidence; contract test mengikat kandidat/report,
protocol/source/schema/code/runtime sebelum akses. Ledger konsumsi global vintage2022
harus dibuat sebelum member dibuka. Ujian sekali tidak fit, recalibrate atau mengubah
policy. Penolakan/abort membuat vintage terpakai; tidak dipindah window atau di-reset.
Bahkan PASS_RESEARCH_TEST tidak mempromosikan layanan scoring fintech.

## Dasar teknis dan batas klaim

[SFLLD resmi](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset) memberikan
monthly performance/cutoff serta batas source. [Dokumentasi calibration sklearn](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV)
mensyaratkan fit base dan calibrator memakai data terpisah. Kajian
[Sirignano, Sadhwani & Giesecke](https://arxiv.org/abs/1607.02470) memodelkan dinamika
risiko hipotek dengan loan-specific/macroeconomic information; arXiv ini bukan bukti
bahwa sembilan fitur atau window v4 optimal. Pilihan fitur/model ringan adalah desain
CreditLens yang harus diuji sendiri, bukan reproduksi deep learning dari kajian tersebut.

Kualitas riset, availability, usage rights, immutable bundle, HTTP parity, auth/HTTPS,
beban, actual monitoring dan rollback tetap gerbang berbeda. Profil mortgage, model,
source manifest, notebook dan penjelasan belajar tetap di luar GitHub/BI publik.

## Hasil penerapan — diperbarui 15 Oktober 2026

Training v4 dan development validation nyata selesai dalam budget; HGB terkalibrasi
terpilih berdasarkan calibrated AP dan lulus semua gate. Checker terpisah merekalkulasi
validation sebelum contract ujian dikunci:
`2d75ed29d0b955c1e6642d800b28d879051886c84b32b41e6f3ecc888f480899`.
Contract mengikat source/candidate/report/schema/runtime dan logic executor melalui
normalized-code hash (hanya literal hash contract dinormalisasi untuk menghindari cycle).

Ujian vintage2022 telah dilakukan sekali, tanpa fitting/reselection; seluruh gate
terpenuhi: **PASS_RESEARCH_TEST**. Ledger dibuat sebelum member access, source manifest
mencatat consumption dan mempertahankan bytes sebelumnya. Seluruh vintage2022 consumed,
termasuk bulan yang tidak digunakan. Vintage2020 tidak dibuka kembali. Angka mortgage,
model, predictions dan resource reports tetap privat. Ini hasil penelitian pada cohort
berlabel lengkap; dampak operasional/ROI dan ketidakpastian recall population belum dibuktikan.

### Bundle dan HTTP riset privat

`src.research.freddie_shadow_api` menyediakan aplikasi terpisah pada127.0.0.1, menggunakan
manifest lokal owner-only dan bearer token dari file privat (tidak dicetak). Verifikasi
mengikat protocol/validation/test/candidate, schema19fitur, float32 dan versi library;
validation dan test gates direkalkulasi sebelum own trusted weights dimuat.

Request menerima **fitur domain yang telah dibentuk**, bukan loan ID/raw monthly records.
Model training/calibrator tidak di-fit oleh API. Exact keys, finite/domain ranges dan
completeness/missing rules diperiksa. Maksimal8.192byte aktual per request dan60request
terautentikasi per menit per process; auth diperiksa sebelum parsing input. Pemrosesan
prediksi diserialisasi dan dibatasi dua thread. Validation error tidak mengulang nilai
input, termasuk NaN; tidak ada approved/tier keputusan kredit. OpenAPI/docs publik dan
access log default dinonaktifkan. Scope/research readiness dan production HOLD terpisah.

Smoke HTTP loopback nyata dengan input fitur sintetis menghasilkan skor identik dengan
offline/reloaded pipeline dan memverifikasi401unauthenticated,422invalid-domain/NaN,
413oversized. Server sementara dihentikan setelah uji. Fixtures terpisah menguji429rate
limit. Ini bukan load/SLO, HTTPS, multi-worker/distributed rate limit, token lifecycle,
raw history adapter, prospective data availability atau operating rollback acceptance.
API utama LendingClub tetap menolak model yang belum diterima; API mortgage lokal ini
bukan aktivasi endpoint fintech lama. Tidak ada API publik, belanja hosting, tag atau merge.
