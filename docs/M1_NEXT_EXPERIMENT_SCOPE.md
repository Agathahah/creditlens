# Scope intake data dan eksperimen M1 berikutnya

Status 23 September 2026: **arah disetujui; eksekusi training belum dimulai**.

Dokumen ini menerjemahkan keputusan holdout berikutnya menjadi gerbang kerja yang dapat diaudit.
Tujuannya adalah mendapatkan evaluasi temporal independen setelah frozen test 2015 terpakai.

## Tujuan dan batas penggunaan

- Produk adalah demo pendidikan/portfolio berbasis data publik.
- Prediksi dibuat pada saat aplikasi, sebelum grade, pricing dan keputusan kredit.
- Target adalah outcome buruk dalam 36 bulan untuk pinjaman tenor 36 bulan.
- Output utama adalah probabilitas risiko dan bukti evaluasi. Tidak ada keputusan approve/reject.
- Tidak ada training baru sampai sumber data lolos seluruh gerbang intake di bawah.

## Gerbang 1 — intake sumber privat

Sumber baru disimpan di luar Git. Manifest aman untuk publik hanya boleh memuat metadata berikut:

- nama logis dan versi/snapshot sumber;
- URL atau rujukan asal yang dapat diverifikasi;
- lisensi/hak penggunaan untuk demo;
- tanggal snapshot/as-of outcome;
- ukuran byte, SHA-256, jumlah baris dan jumlah kolom;
- rentang issue date dan daftar kolom yang diperlukan;
- metode mendapatkan data, tanpa token, cookie atau jalur lokal pribadi.

Gerbang gagal bila as-of, hak penggunaan, checksum atau timing outcome tidak dapat dibuktikan.

## Gerbang 2 — kontrak outcome dan fitur

- Outcome 36 bulan harus berasal dari tanggal kejadian atau history yang cukup; status akhir tanpa
  timing tidak otomatis membuktikan kapan outcome terjadi.
- Setiap fitur harus tersedia saat aplikasi. Grade, sub-grade, suku bunga, installment, payment,
  recovery dan status setelah originasi tetap dilarang.
- Baris unresolved tidak boleh dibuang berdasarkan pengetahuan masa depan. Aturan maturity ditentukan
  dari as-of dan horizon sebelum melihat performa model.
- Grain satu pinjaman dan rekonsiliasi loan ID harus lulus tanpa mempublikasikan data mentah.

## Gerbang 3 — split temporal yang dikunci

Tahun konkret ditentukan setelah profil sumber baru tersedia:

1. vintage fully mature paling baru menjadi frozen test baru;
2. vintage mature tepat sebelumnya menjadi validation;
3. vintage mature yang lebih awal menjadi train;
4. membership, alasan exclusion, jumlah label dan checksum disimpan sebelum training;
5. tidak boleh ada overlap loan ID atau fit preprocessing di luar train.

Frozen test tidak boleh dibuka untuk pemilihan fitur, model, calibration atau threshold.

## Gerbang 4 — protokol model dan evaluasi

- Constant baseline dan Logistic Regression wajib dijalankan pada cohort yang sama.
- XGBoost tetap kandidat kecil berbatas sumber daya; dipertahankan hanya bila peningkatan validation
  konsisten dan dilaporkan bersama ketidakpastian.
- Metrik utama pemeringkatan adalah average precision dengan prevalence sebagai konteks. ROC-AUC,
  Brier score, log loss, calibration dan confidence interval tetap dilaporkan.
- Karena produk belum memiliki biaya bisnis, tidak ada threshold approve/reject. Validation boleh
  menampilkan kurva precision/recall dan operating point dengan minimum support `max(100, 0,5%)`.
- Kandidat, preprocessing, calibration dan laporan harus terikat pada satu manifest versi sebelum
  frozen test dibuka satu kali.

## Gerbang 5 — keputusan setelah evaluasi

Hasil test dapat menghasilkan salah satu keputusan berikut:

- `REJECT`: validitas data atau gate model gagal;
- `RESEARCH_ONLY`: valid untuk pembelajaran, belum memenuhi release gate;
- `M2_CANDIDATE`: memenuhi gate yang telah dikunci dan dapat diajukan untuk scope bundle/API.

Status `M2_CANDIDATE` bukan izin deployment, merge atau keputusan kredit. M2 memerlukan persetujuan
scope terpisah dan bukti training-serving parity.

## Bukti yang harus dihasilkan

- laporan intake/provenance tanpa data mentah;
- profil maturity dan outcome per vintage;
- feature availability matrix;
- manifest train/validation/test dan checksum membership;
- hasil baseline/candidate pada validation;
- bundle manifest sebelum test;
- laporan frozen-test satu kali dan keputusan gerbang.

## Langkah berikutnya

Langkah aktif berikutnya adalah memperoleh atau menunjuk dataset/snapshot baru. Setelah file privat
tersedia, jalankan pemeriksaan checksum dan metadata terlebih dahulu. Jangan memasukkan data ke
database aktif dan jangan menjalankan `scripts/run_m1_local.py` pada frozen test 2015.
