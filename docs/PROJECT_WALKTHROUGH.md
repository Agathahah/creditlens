# CreditLens — alur, status, dan alasan pengerjaan

2026-09-10. Ringkasan untuk memahami proyek dan menyiapkan narasi DS/AI/ML Engineer. Angka/status membedakan pengujian terkini, kode yang tersedia, dan rencana. Latihan ditunda sampai akhir sesuai arahan terbaru. Pemulihan ingestion, backup/restore scoped dan rebuild mart kini lulus; M0 masih menunggu kontrak label/provenance.

## Tujuan layanan

Mengubah informasi pinjaman publik menjadi skor risiko yang dapat ditelusuri, dijelaskan, diuji, dan dioperasikan dalam scope layanan demonstrasi. Tujuan akhir bukan sekadar notebook dengan skor tinggi: data harus benar, model dievaluasi secara sah, API konsisten, dan rilis dapat dipantau/dipulihkan. Belum digunakan untuk keputusan kredit nyata. Label/horizon detail perlu keputusan tersendiri sebelum hasil disebut probability of default pada horizon tertentu.

## Alur dengan bahasa sederhana

| Tahap | Apa yang terjadi | Yang sudah terbukti | Yang belum selesai dan mengapa penting |
|---|---|---|---|
| 1. Data mentah | File pinjaman dimuat ke PostgreSQL raw | 2.260.668 loan, tanggal pinjaman 2007–2018; semua ID kandidat CSV tercakup | Asal unduhan, lisensi/as-of dan cohort evaluasi masih perlu ditetapkan |
| 2. Pembersihan | dbt staging menyeragamkan bentuk data dan menurunkan label | View staging terbaca dengan 2.260.668 loan; status panjang utuh | Kontrak label, null dan fitur yang benar-benar tersedia saat prediksi; view berisi data belum membuktikan label sah |
| 3. Fitur | SQL mart membuat rasio dan menggabungkan fitur | Pipeline berhasil pada fixture dan data aktif: mart loan/final masing-masing 2.260.668 | Selesaikan kontrak label; tabel terisi belum menjamin dataset evaluasi valid |
| 4. Tes kualitas data | Memeriksa apakah data memenuhi kontrak | Dua tes baru menangkap tabel kosong dan ketidakcocokan jumlah baris, dengan kasus gagal/lulus nyata | Sudah pass pada hasil recovery; integrasi CI berikutnya. Kesamaan counts belum menjamin seluruh isi/label benar |
| 5. Preprocessing | Mengubah null/kategori/angka menjadi input model | Kode ada | Saat ini preprocessing terjadi sebelum split dan transform tidak tersimpan; berisiko hasil terlalu optimistis dan input API berbeda |
| 6. Pembagian data | Memisahkan bahan belajar, pemilihan, dan ujian akhir | Kode memiliki pemisahan waktu train/test | Validation terpisah, maturity/as-of dan fitur tersedia; semua member_id kosong sehingga overlap borrower tidak dapat dijamin |
| 7. Training | Model belajar menghubungkan fitur dengan label | Implementasi Logistic Regression, XGBoost, LightGBM tersedia | Belum ada training penuh yang disetujui/diulang, artefak standar belum tersedia, model pemenang belum dipilih secara sah |
| 8. Evaluasi | Menguji urutan risiko, kualitas probabilitas dan threshold | Kode metrik/fairness tersedia | Evaluasi bebas leakage, baseline yang sama, calibration, error analysis dan threshold terkunci sebelum test |
| 9. Artefak | Menyimpan hasil training agar bisa dipakai ulang | Fungsi save/load estimator ada | Satu bundle preprocessing+model+schema+versi dan checksum; estimator saja tidak menjamin konsistensi |
| 10. API | Menerima input dan mengembalikan skor/penjelasan | Source FastAPI, predict/explain dan tes tersedia | Readiness harus gagal saat model tidak tersedia; parity input→bundle→HTTP belum dibuktikan pada artefak nyata |
| 11. CI dan deployment | Memeriksa perubahan dan merilis versi teruji | Workflow ada; CI historis unit tests pass, evaluasi gagal karena artefak hilang | Gate model, image/bundle yang sama, smoke, benchmark dan rollback; deployment memerlukan persetujuan tersendiri |
| 12. Monitoring | Mengamati traffic, error, perubahan input dan performa | Kode/tabel/dashboard tersedia | Event inference nyata, versi model, delayed-label join, alert/runbook dan recovery drill belum lengkap |
| 13. Ops Copilot | Membantu operator mencari bukti di dokumen/log | Desain backlog | Setelah core stabil; RAG dan satu loop agent harus punya evaluasi, batas tools dan alasan kebutuhan |

## Mengapa urutan ini dipilih

| Keputusan | Alasan | Risiko jika dilewati |
|---|---|---|
| Pulihkan kontrak data sebelum model | Model hanya belajar dari apa yang disediakan pipeline | Mengejar metrik dari data kosong/salah/tercemar |
| Pisahkan fixture software dari eksperimen real-data | Dua baris cukup untuk membuktikan bug tes; tidak cukup mengukur model | Menganggap tes software pass sebagai bukti prediksi berkualitas |
| Baseline sederhana sebelum kandidat kompleks | Kompleksitas harus memberi manfaat yang diukur | Memilih XGBoost hanya karena namanya populer |
| Satu transform tersimpan untuk training dan API | Input yang sama seharusnya diproses sama | Prediksi berubah hanya karena encoding/median berbeda |
| Rilis harus membawa artefak yang dievaluasi | Keputusan kualitas harus terikat pada versi yang berjalan | Model berbeda terdeploy walau laporan evaluasi hijau |
| Monitoring mengukur request sungguhan | Operasi perlu tahu sistem sedang dipakai dan bagaimana kegagalannya | Dashboard terlihat hidup dari data historis saja |

Alasan kandidat model serta bukti yang diperlukan ada di [MODEL_DECISIONS.md](MODEL_DECISIONS.md). Tidak ada klaim XGBoost terbaik sebelum perbandingan yang sah.

## Satu contoh alur pinjaman

Record publik 68407277 sudah ditelusuri saat audit: CSV → raw → staging. Nilai installment 123,03 dan income tahunan 55.000 menghasilkan rasio cicilan tahunan sekitar 0,02684 menurut formula source. Record yang sama kini benar-benar ditemukan di mart.final_features setelah recovery, dengan rasio 0,02684290909, revol_util_clean 0,297 dan label lama 0. Jalur CSV→raw→staging→mart sudah ditelusuri; model/API nyata masih menunggu artefak dan perbaikan evaluasi. Bukti: audit/M0_ID_RECONCILIATION.json.

## Bukti yang bernilai untuk interview

| Area pekerjaan | Cerita yang kelak bisa dibuktikan | Bukti saat ini |
|---|---|---|
| SQL/data engineering | Menemukan mengapa pipeline sukses tetapi data tidak layak | Log build kosong, dua tes baru, reproduksi gagal/lulus tersedia; kode ditulis Codex |
| Data science | Memilih label, menghindari leakage, membandingkan baseline, menganalisis kesalahan | Desain dan temuan sudah dicatat; evaluasi perbaikan belum dilakukan |
| ML engineering | Menyamakan batch/API, mengemas model, readiness dan rollback | Kode awal ada; bukti integrasi perbaikan masih pekerjaan berikutnya |
| AI engineering | Retrieval/agent dengan tool terbatas dan evaluasi berbasis bukti | Backlog, belum prestasi yang dapat diklaim |
| Ownership | Menjelaskan keputusan, batas klaim, debugging dan bantuan AI secara jujur | Agatha menetapkan tujuan/batas, mencoba query dan memverifikasi koneksi; latihan mendalam menyusul di akhir |

Kesiapan teknis dan pemahaman Agatha dinilai terpisah. Menunda latihan tidak menghilangkan kebutuhan demonstrasi sebelum mengklaim penguasaan saat interview. Proyek ini harus diceritakan lewat keputusan dan hasil nyata, tanpa menciptakan metrik bisnis/pengguna produksi atau menyamarkan bantuan AI.
