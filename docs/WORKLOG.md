# Catatan pekerjaan CreditLens

## Sesi 2026-09-09 — lanjut teknis, latihan ditunda

| Langkah | Pelaksana dan tindakan | Mengapa | Hasil / batas |
|---|---|---|---|
| 1 | Agatha meminta latihan di akhir, tabel alur/status, dan catatan alasan | Menyesuaikan ritme belajar | Gate latihan dicabut; persetujuan deployment/training penuh/rewrite tetap terpisah |
| 2 | Codex membaca Git, aturan, milestone, evaluasi dan source training/dbt | Memastikan kondisi lokal dan scope | Branch codex/m0-mentoring, HEAD tetap 9f24144; perubahan lama dipertahankan |
| 3 | Codex mencoba koneksi read-only | Memperbarui counts sebelum tindakan | Sandbox menolak socket localhost; bukan error password. Akses lokal kemudian diizinkan melalui review eksekusi |
| 4 | Codex menjalankan COUNT dan agregat raw dalam transaksi read-only | Menentukan kondisi kini dan feasibility label | Raw/staging 1.599.982; loan/final mart 0; macro 954. Seluruh member_id NULL; issue_date 2014–2018. Bukti: audit/M0_LIVE_SNAPSHOT.json |
| 5 | Codex menulis rencana cluster PostgreSQL privat | Menguji mutation tanpa data aktif | Socket unik, TCP nonaktif, fixture sintetis, salinan dbt project dan cleanup otomatis |
| 6 | Codex menambahkan nonempty_required_models dan reconcile_loan_counts | Menangkap dua kelas kegagalan yang lolos tes kolom | SQL tes baru masuk tests/dbt; belum mengubah SQL fitur/label |
| 7 | Codex menulis scripts/verify_m0_dbt.py | Mengulang reproduksi memakai dbt/PostgreSQL sesungguhnya | Initdb pertama dibatasi shared memory sandbox; kemudian dijalankan dengan akses lokal yang diizinkan |
| 8 | Codex menguji input kosong | Membuktikan celah tes lama | Lima model build sukses, 24 tes lama pass, tes nonempty baru gagal dengan 3 relasi kosong |
| 9 | Codex menambah dua loan sintetis tanpa rebuild | Membuktikan view dan tabel dapat berbeda freshness | Staging 2, loan/final 0; tes rekonsiliasi gagal sesuai harapan |
| 10 | Codex membangun ulang fixture | Membuktikan jalur pemulihan dan tes positif | Lima model sukses, 26 tes pass, counts 2/2/2 |
| 11 | Codex menghapus satu final fixture lalu memulihkan | Memastikan rekonsiliasi juga memeriksa transisi loan→final | Tes gagal sesuai harapan lalu recovery lulus; cluster dihentikan otomatis |
| 12 | Codex memeriksa format/lint script | Mengikuti aturan repo | Black dan Ruff lulus untuk script baru; bukan seluruh suite aplikasi |
| 13 | Codex merencanakan backup dua mart lalu rebuild lokal | Memulihkan data development dari staging yang sudah terisi | Rencana M0_MART_RECOVERY.md dibuat; preflight state sesuai |
| 14 | Codex memeriksa disk sebelum backup/build | Menghindari pemulihan saat ruang terlalu sempit | Sekitar 1,9 GiB kosong, di bawah guard konservatif 2 GiB; berhenti sebelum backup atau mutation. Batas ini kebijakan kehati-hatian run, bukan hasil benchmark kebutuhan pasti |
| 15 | Codex memperbarui peta alur dan alasan kandidat model | Menjelaskan sudah/belum dan trade-off untuk interview | PROJECT_WALKTHROUGH.md dan MODEL_DECISIONS.md; belum ada training atau model pemenang |
| 16 | Codex memperbarui status, keputusan, learning log, dan status HTML draft | Mencegah sesi berikutnya kembali menunggu latihan | Latihan dirangkum/disempurnakan pada akhir; tidak ditugaskan sekarang |

## Lanjutan yang diperlukan

Status pada akhir sesi sebelumnya: pemulihan menunggu disk. Kendala tersebut kini teratasi; lihat sesi lanjutan di bawah. Backup/restore database dibedakan dari backup/rewrite Git.

Setelah mart pulih, selesaikan provenance/cakupan sumber dan kontrak label/waktu fitur sebelum perubahan preprocessing/evaluasi berikutnya. Training penuh, target deployment/biaya, dan rewrite Git tetap memiliki keputusan eksplisit tersendiri. Tidak ada commit/push sesi ini.

Tautan bukti: [snapshot](audit/M0_LIVE_SNAPSHOT.json), [reproduksi](audit/M0_ISOLATED_TEST_REPORT.json), [recovery preflight](audit/M0_MART_RECOVERY_REPORT.json), [diagnosis log historis](audit/M0_DIAGNOSIS.md).

## Sesi lanjutan 2026-09-09 — recovery setelah disk dilonggarkan

| Langkah | Tindakan dan alasan | Hasil |
|---|---|---|
| 1 | Agatha melonggarkan disk dan meminta tahap berikutnya | Codex memverifikasi sekitar 7,2 GiB kosong; Git/branch/HEAD tetap |
| 2 | Menyimpan laporan preflight gagal agar tidak ditimpa | M0_MART_RECOVERY_PREFLIGHT_REPORT.json menjadi arsip historis |
| 3 | Memeriksa kembali state lalu pg_dump dua mart | Staging terisi, loan/final masih kosong; backup custom-format 4.707 byte dan daftar isi valid |
| 4 | dbt build terarah pada salinan project dan profile eksplisit | Hanya loan_features/final_features dibangun; dua model sukses, 9 tes pass |
| 5 | Memeriksa counts dalam transaksi read-only | Staging/loan/final masing-masing 1.599.982; ruang disk setelah run 5,954 GiB |
| 6 | Menyalin backup dari temp ke .local-backups privat | Checksum cocok; .gitignore mencegah archive masuk Git. Backup sebelum build ini berisi state mart kosong, bukan hasil baru; restore drill belum diuji |
| 7 | Streaming profil accepted CSV dan checksum | 2.260.701 record; 2.260.668 memenuhi field dasar, 33 tidak; cakupan 2007–2018 |
| 8 | Membandingkan set ID CSV dengan raw secara baca-saja | 660.686 ID sumber belum dimuat, tidak ada ID raw di luar sumber; tidak mengulang ingestion |
| 9 | Memeriksa record 68407277 pada final mart | Ditemukan dengan nilai fitur yang diharapkan dari penelusuran sebelumnya; belum prediksi model |
| 10 | Memperbarui status dan panduan terminal | Pemeriksaan COUNT opsional, tidak perlu memanggil Codex/task baru; latihan akhir tetap ditunda |

Pelaksana backup/build/query/profiling dan dokumentasi: Codex. Kontribusi Agatha sesi ini: mengatasi kapasitas disk dan mengarahkan kelanjutan. Tidak ada training penuh, deployment, rewrite, commit atau push. Rebuild tidak mengubah raw/macro; tidak mengubah definisi label atau transform ML.

Lanjutan kini: tutup selisih cakupan ingestion/cohort yang terdefinisi sebelum menyatakan dataset siap evaluasi. Bukti: [recovery](audit/M0_MART_RECOVERY_REPORT.json), [profil CSV](audit/M0_CSV_PROFILE.json), [rekonsiliasi ID](audit/M0_ID_RECONCILIATION.json), [provenance](DATA_PROVENANCE.md).

## Sesi 10 September 2026 — ingestion lengkap dan keputusan target berikutnya

| Langkah | Tindakan dan alasan | Bukti / hasil |
|---|---|---|
| 1 | Agatha menyatakan COUNT sesuai harapan dan meminta lanjut | Dicatat sebagai konfirmasi pengguna; output mentah tambahan tidak tersedia |
| 2 | Codex memeriksa branch, HEAD dan identitas lokal | codex/m0-mentoring, 9f24144, noreply Agathahah; tidak commit/push |
| 3 | Diagnosis log, prefix ID dan panjang field sumber | Raw cocok 16 chunk; 761 loan_status panjang 51 melampaui VARCHAR(50), pertama chunk 17; tanggal log tidak mengidentifikasi run terakhir secara pasti |
| 4 | Menambahkan loader bulk, mode insert-missing, migration TEXT, ORM/init SQL dan unit tests | Status utuh, skip existing, rollback chunk, laporan agregat; tidak mengubah label ML |
| 5 | Tes fixture awal tanpa view lulus; memperluas fixture memakai SQL staging nyata | Menangani dependency view dalam migration; downstream tak dikenal diblokir RESTRICT, metadata custom membuat berhenti |
| 6 | Tes persamaan view awal gagal karena PostgreSQL menormalkan cast scalar/array | Diperiksa diff SQL; normalisasi cast pada assertion, pemeriksaan nilai/label tetap; delapan cek privat akhirnya lulus |
| 7 | Menjalankan dryrun seluruh CSV untuk parsing, field wajib dan batas numeric | 2.260.668 valid, 33 excluded, 761 status panjang, checksum tetap |
| 8 | Menyimpan backup raw/view/dua mart, memeriksa checksum dan TOC | Archive privat 293.338.379 byte, tidak masuk Git |
| 9 | Restore awal terhenti sebelum restore karena path socket terlalu panjang | Memindahkan cluster uji ke path pendek, mengulang: restore/count/index sukses; owner/ACL bukan cakupan drill |
| 10 | Menghentikan server restore, menghapus hanya pgdata salinan uji sesudah sukses | Backup dan laporan tetap disimpan, ruang disk pulih |
| 11 | Menerapkan migration lokal pada revision terverifikasi dan menjalankan insert-missing | 660.686 inserted, 1.599.982 skipped, 33 excluded, 14 commit batch |
| 12 | Membandingkan count dan fingerprint seluruh field record lama | Nilai agregat dua bagian MD5 per row dan count tidak berubah, termasuk loaded_at |
| 13 | Memeriksa set ID raw terhadap CSV | Tidak ada ID hilang/asing; kandidat sumber unik |
| 14 | Rebuild dua mart pada project dbt sementara dengan profile eksplisit | Dua model sukses, 9 tests pass; raw/staging/loan/final 2.260.668; disk 3,747 GiB sesudah build |
| 15 | Menghitung distribusi status/year/term serta ketersediaan waktu secara read-only | Late 31–120 masih masuk label lama; seluruh member_id NULL; last payment maks Maret 2019 bukan bukti as-of |
| 16 | Menulis draft label dan memperbarui status/alur/provenance | Kandidat mapping 1.345.350 sebelum eligibility waktu; belum persetujuan implementasi M1 |
| 17 | Memeriksa format, lint, type hints dan CLI help | Black/isort/Ruff untuk file baru/loader dan mypy modul+revision lulus; tujuh unit tests pass; bukan full suite aplikasi |
| 18 | Mengarsipkan script operasi dan bukti agar sesi bisa dilanjutkan | docs/audit/m0_ingestion_scripts dan laporan JSON; latihan HTML tetap ditunda |

Pelaksana perubahan kode, SQL migration, tes, backup/restore, ingestion, dbt dan dokumentasi: Codex. Agatha mengarahkan scope dan mengonfirmasi hasil COUNT, sebelumnya membuka ruang disk serta menjalankan koneksi read-only. Penguasaan mandiri/kontribusi kode Agatha masih akan dibuktikan lewat latihan akhir. Tidak ada training penuh, deployment, rewrite riwayat, commit atau push.

## Verifikasi pengguna dan persiapan publikasi M0 — 10 September 2026

| Langkah | Tindakan | Hasil / alasan |
|---|---|---|
| 1 | Agatha mengirim output COUNT final_features | 2260668, satu row hasil; verifikasi mandiri hasil recovery dicatat |
| 2 | Agatha meminta ikut menjalankan commit/push/PR | Operasi publikasi disisakan untuk Agatha; Codex menyiapkan hasil konkret dan panduan, bukan meminta izin ulang |
| 3 | Codex memeriksa Git, diff, identitas dan GitHub read-only | Branch/HEAD tetap; noreply Agathahah efektif; main terbaru 1a097c5; belum ada PR branch M0 |
| 4 | Codex membaca workflow dan branch protection | PR menjalankan lint/test; main meminta nol approving reviews, tidak punya required status checks; review/CI tetap dijadikan tahap sebelum merge |
| 5 | Codex memeriksa calon dokumen dan pengecualian data | Tidak ada kecocokan pola credential/token/private key pada dokumen; CSV/.env/backup ignored; empat konteks lama dipertahankan di luar paket |
| 6 | Codex menjalankan lint/typecheck dan suite aplikasi | Black/isort/Ruff pass; mypy 73 source files pass; 124 passed, 4 skipped, 7 warnings; tidak mengakses DB development atau training penuh |
| 7 | Codex menulis panduan tiga commit, push branch dan draft PR beserta body | Setiap blok menjelaskan lokasi/tujuan/dampak/expected output; belum dieksekusi pengguna pada checkpoint ini |

Bukti: audit/M0_PR_PREFLIGHT.json. Isi raw/PostgreSQL tidak ikut git push; hasil recovery lokal tetap bukti lokal. Belum ada merge, deployment, rewrite atau persetujuan M1 baru. URL PR dan commit akan dicatat setelah output Agatha diterima.

## 11 September 2026 — PR #14 terverifikasi, catatan Git pemula

| Langkah | Pelaksana/tindakan | Hasil / alasan |
|---|---|---|
| 1 | Agatha menyelesaikan tiga commit, push dan draft PR | a37fcbd, 79c7618, 7a859fe; PR https://github.com/Agathahah/creditlens/pull/14 |
| 2 | Codex memeriksa status lokal dan pesan/identitas commit | Hanya empat konteks lama untracked pada awal sesi; author/committer noreply Agatha, tanpa trailer Co-authored-by |
| 3 | Codex membaca status PR/run dan ringkasan log CI | Head sama 7a859fe, OPEN/draft, tidak ada konflik merge terdeteksi; lint/test success, eval/build skipped |
| 4 | Codex membedakan cakupan CI dari bukti lokal | 124 passed, 4 skipped, 8 warnings; coverage total 91% termasuk tes, ingestion 54%; runner PostgreSQL lokal belum masuk CI |
| 5 | Codex membuat catatan Git/PR pemula | Definisi, perintah/opsi/dampak, pager, alur PR yang sama, CI per commit, batas merge/produksi |
| 6 | Codex memperbarui status, indeks docs dan learning log | Memperbaiki ringkasan usang 1.599.982/belum push; mempertahankan laporan audit lama sebagai snapshot bertanggal |
| 7 | Codex menyiapkan instruksi commit/push catatan oleh Agatha | Enam file dokumentasi/evidence, tanpa mutation database/aplikasi; perubahan baru perlu CI untuk commit baru |

Hasil run 34504952839 tercatat dalam audit/M0_PR14_CI_REPORT.json. Repo belum merged/deployed; GitHub hanya dibaca oleh Codex pada sesi ini. Tidak menjalankan ulang tes aplikasi untuk perubahan dokumentasi saja; diff dan validitas JSON diperiksa. Pemberitahuan update gh bukan error atau prasyarat PR.
