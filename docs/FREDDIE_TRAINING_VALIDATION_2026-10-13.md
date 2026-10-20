# Training dan validation riset hipotek — 13 Oktober 2026

Status: **training lokal selesai; kandidat ditolak pada validation; scoring HOLD**.
Dokumen ini memperbarui keadaan 9 Oktober, ketika admission masih terblokir.
Bukti numerik, panel, prediksi, identitas pinjaman, model dan notebook hasil tetap privat.
Tidak ada evaluasi frozen test, promosi bundle, layanan scoring hipotek atau merge.

## Penerimaan sumber dan batas penggunaan

Ketentuan riset pribadi/internal hipotek telah diterima. Portal pemilik menampilkan cutoff
31 Maret 2026 dan populasi Standard SFLLD yang konsisten dengan
[Release Notes resmi](https://www.freddiemac.com/fmac-resources/research/pdf/release_notes.pdf).
Release 47 **diinferensikan** dari metadata tersebut, layout lokal dan sumber resmi;
nomor release tidak tampak pada screenshot dan tidak ada checksum penerbit yang
mengikat byte ZIP lokal ke release. Manifest privat mencatat batas ini secara eksplisit.
Penerimaan untuk riset retrospektif privat tidak membuktikan validitas point-in-time
atau memberi izin mendistribusikan data/model melalui layanan publik.

Freddie Mac adalah studi hipotek AS yang terpisah. LendingClub tetap analisis historis;
model M1 lama tetap ditolak, dan test 2015 yang sudah terpakai tidak dinilai ulang.
Skor hipotek tidak diadopsi untuk pinjaman fintech tanpa data operator dan evaluasi
populasi yang sesuai. Manfaat yang diteliti adalah prioritas pemeriksaan portofolio
setelah pencairan, bukan persetujuan kredit atau klaim penghematan kerugian aktual.

## Rancangan yang dijalankan

| Komponen | Implementasi |
|---|---|
| Grain | Satu pinjaman × bulan laporan; identitas pinjaman tidak menjadi fitur |
| Target | Pinjaman lancar/saldo positif menjadi 90+ hari/REO dalam tiga bulan kalender berikutnya |
| Negatif/censoring | Negatif memerlukan horizon lengkap; terminasi/data tidak lengkap menjadi NULL |
| Train | Vintage 2018; bulan laporan Januari–September 2019; outcome sampai Desember 2019 |
| Development validation | Vintage 2019; Januari–September 2020; outcome sampai Desember 2020 |
| Test terencana | Vintage 2020; Januari–September 2021; belum dibuka |
| Preprocessing | Median/missing indicator hanya fit train; scaling hanya model linear |
| Kandidat | Constant train prevalence, Logistic Regression, HistGradientBoosting terbatas |
| Pemilihan | AP validation; seri memilih Logistic Regression; tanpa pencarian hyperparameter |
| Budget | Dua thread, maksimum 15 menit dan RSS worker 2 GiB |
| Artefak | Pipeline/prediksi/report/code snapshot privat; checksum dan probe save–reload |

V1 mempertahankan byte protokol yang disetujui:
[freddie_experiment_v1.json](../config/research/freddie_experiment_v1.json), SHA-256
`c17999bce05357b4ef937eee474b0549702c811de91ccd43a8017a1f5eb696b7`.
Enam fitur memakai saldo pokok, umur/sisa tenor, bunga dan dua lag tunggakan.

Setelah v1 gagal pada development validation, v2 dikunci sebelum fit berdasarkan
otorisasi keputusan teknis riset terbatas:
[freddie_experiment_v2.json](../config/research/freddie_experiment_v2.json), SHA-256
`01f06de390b6b64503e23f5926f3f143d1d86cdcd3cee221e0dd9853c8f2c975`.
Ini bukan persetujuan pemilik atas hash v2 secara terpisah. V2 menambah credit score,
DTI, LTV dan CLTV origination. Mapping/sentinel memakai
[User Guide Freddie](https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf).
[Elul et al. (2010)](https://www.aeaweb.org/articles?id=10.1257/aer.100.2.490)
memberi alasan domain tentang equity/liquidity dan default hipotek, bukan jaminan
performa empat fitur pada sample lokal. Gate, split, model budget dan kapasitas
alert tetap sama. Tidak ada post-hoc calibrator pada kedua run.

## Metrik dan keputusan

- AP adalah Average Precision untuk ranking positif yang jarang. Motivasi PR pada
  data tidak seimbang didukung [Saito & Rehmsmeier (2015)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432).
  Perhitungan mengikuti [definisi AP scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html),
  bukan integrasi PR dengan interpolasi trapezoid. ROC AUC dilaporkan sebagai pelengkap.
- Brier skill membandingkan galat probabilitas dengan constant train pada cohort yang sama;
  Brier bukan ukuran kalibrasi murni. Reliability bins serta mean prediction/observed rate
  dilaporkan. Prinsip perlunya kalibrasi memakai [Van Calster et al. (2019)](https://doi.org/10.1186/s12916-019-1466-7),
  artikel metode klinis yang bukan validasi fintech.
- Kebijakan top 1% bulanan memakai cohort berlabel. Precision/recall memakai denominator
  loan-month; censoring dan event unik dilaporkan terpisah. Kapasitas ini simulasi riset,
  bukan persetujuan biaya atau kapasitas analis lender.
- Bootstrap 1.000 draw resample pinjaman dan mempertahankan seluruh bulan pinjaman tersebut.
  Prinsip cluster mengikuti [Deen & de Rooij (2020)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7148287/).
  Adaptasi di sini adalah CI cohort pada model tetap, bukan refit GLM pada paper tersebut.
  Interval tidak mencakup ketidakpastian training atau shock kalender bersama antarloan.

| Pemeriksaan kandidat terpilih | V1 | V2 |
|---|---|---|
| Event unik minimum validation | Lulus | Lulus |
| AP/prevalence minimum | Gagal | Lulus |
| Lower bound CI lift di atas baseline | Lulus | Lulus |
| Brier skill positif | Gagal | Gagal |
| Recall pada kapasitas alert tetap | Gagal | Gagal |
| Precision lift/nonzero alerts | Lulus | Lulus |
| Keputusan validation | REJECT_VALIDATION | REJECT_VALIDATION |
| Frozen test / promosi layanan | Belum dijalankan | Belum dijalankan |

Perbaikan ranking pada v2 tidak cukup untuk mengesahkan probabilitas atau prioritas alert.
Validation dipakai untuk pemilihan/revisi; hasil ini merupakan bukti pengembangan,
bukan evaluasi independen. Tidak ada klaim signifikansi perbedaan v1–v2 atau penyebab
kausal pergeseran distribusi. Gate tidak diturunkan setelah melihat hasil.

## Kontrol yang telah dijalankan

- Admission/source/protocol diperiksa sebelum panel dibaca dan hash sumber diperiksa ulang.
- Training hanya menerima hash protokol terkunci dan sumber riset yang diterima.
  Attempt marker mencegah run tidak sengaja diulang dengan protokol yang sama.
- Output harus di luar Git, tanpa overwrite, direktori/file privat 700/600.
- Supervisor memantau RSS worker setiap 250 ms serta wall time; menghentikan process group
  miliknya saat budget gagal. Monitor tidak tersedia membuat run gagal tertutup.
  RSS sampel bukan jaminan puncak memori instan; parent/anak lain tidak diukur sebagai total cgroup.
- Kedua run nyata selesai tanpa abort di bawah budget: v1 15,476 detik dan v2 13,647 detik;
  RSS worker tersampel sekitar 740,5 MiB dan 1.023,5 MiB. Ini bukan benchmark serving.
- Kandidat dibuat dan diperiksa checksum, lalu save–reload diuji pada probe validation.
  Ini belum parity preprocessing/API atau validator bundle layanan produksi.
- Checker kandidat membaca JSON/hash tanpa deserialisasi bobot, menghitung ulang gate,
  menolak keduanya dan tetap HOLD. Pernyataan operator bukan attestation kriptografis;
  checker bukan pengesah rilis scoring.

Preflight admission sekarang menyatakan `model_evaluation=NOT_ASSESSED_BY_PREFLIGHT`:
preflight tidak boleh menghapus fakta bahwa training sudah selesai atau menganggap
penerimaan sumber sebagai kelulusan model. API lama tetap gagal tertutup saat bundle
terverifikasi tidak tersedia. Dashboard hanya menampilkan status/methodology, bukan
membaca artefak Freddie privat.

## Validasi software

Suite lokal: **219 passed, 4 skipped, 8 warnings**, 22,63 detik. Black/isort/ruff dan
strict mypy lulus pada source/tests/scripts; mypy memeriksa 86 source files.
Coverage total 89% mencakup test files di src; dihitung ulang tanpa test files menjadi
84,45% (2.216/2.624 statements). Coverage bukan bukti kualitas model.
Coverage modul metrics 93%, origination 92%, panel 86%, admission 78%, release 72%, train 74%.
Gap termasuk jalur malformed-artifact, CLI dan resource/abort; test eksternal/opsional
terlewati, bukan diterjemahkan menjadi lulus. Real fit lokal adalah bukti terpisah dari
fixture sintetis. CI pada head baru dan deployment dashboard perlu diverifikasi tersendiri.

## Pekerjaan yang masih menentukan rilis

1. Rancang train yang mencakup variasi regime dan event unik memadai, dengan audit
   censoring dan availability. Jumlah baris negatif tidak menyelesaikan support event.
2. Tetapkan train/calibration/development-validation terpisah sebelum fit berikutnya;
   validasi yang sudah dipakai tetap pengembangan. Kalibrasi tidak boleh fit pada test.
3. Kunci kandidat yang lulus gate sebelum test sekali. Test vintage lama juga harus
   dinilai kecocokannya dengan populasi tujuan; belum bukti performa masa depan.
4. Untuk penggunaan aktif, buktikan point-in-time, hak penggunaan, acceptance bisnis,
   bundle/schema/parity, auth/HTTPS, batas byte/rate, beban, monitoring dan rollback.

Tahap training/validation privat yang disetujui selesai dengan keputusan penolakan.
Kualitas probabilitas/kapasitas serta validitas operasi adalah penghalang nyata rilis,
bukan review ketentuan yang perlu diulang. Tidak ada dasar untuk menyatakan production ready.
