# Learning log

v0.2 · Log aktif · diperbarui 2026-09-09.

## Sesi awal: audit dan rancangan mentoring

**Agatha:** menetapkan tujuan pembelajaran/interview, batas audit baca-saja, prioritas core ML dan larangan mengambil alih latihan. Belum ada percobaan kode/SQL/tes oleh Agatha pada sesi ini. Tidak ada klaim kompetensi baru yang telah didemonstrasikan.

**Bantuan Codex:** membaca lampiran, aturan/source/tes/config/workflow dan catatan lama; memeriksa Git/GitHub; query database read-only; menelusuri record CSV→raw→staging; menyusun draft dokumen dan rencana atribusi. Tidak mengimplementasikan perbaikan atau menjalankan training/tes aplikasi. Tidak membuat commit atau mengubah setting Git.

**Bukti:** PROJECT_STATUS dan AUDIT_FINDINGS; HEAD 9f24144, remote main 1a097c5, tree identik. Raw/staging 1.599.982 versus loan/final mart kosong; model standar absen. CI historis 117 pass/4 skipped; bukan hasil tes sesi ini. Kontribusi kode Agatha dan Codex di repo selama audit: tidak ada.

## Klarifikasi arah belajar

Agatha menegaskan proyek dikerjakan mandiri, tanpa reviewer staging, dan ingin memahami end-to-end untuk DS/AI/ML Engineer. Codex merevisi draft agar staging dapat diuji Agatha sendiri dan menambahkan checkpoint kemampuan menjalankan, mengubah, debugging dan menjelaskan sistem. Tidak ada implementasi/commit baru; belum ada latihan yang diselesaikan atau kemampuan tambahan yang boleh diklaim.

## Pemasangan dokumen dan persetujuan M0

Agatha menyetujui arah v0.2, M0 dengan pola mentoring, pemasangan dokumen dan identitas Git noreply lokal. Codex memasang dokumen, memperbarui README/catatan transisi CLAUDE, membuat branch codex/m0-mentoring, dan memverifikasi author/committer efektif. Perubahan belum di-commit. Belum ada latihan Agatha yang diterima, tes aplikasi baru, training, perubahan SQL/data, atau klaim pemahaman yang lulus.

Checkpoint aktif: M0 reproduksi/tes dan recovery mart selesai oleh Codex; cakupan ingestion dan kontrak label masih terbuka. Sesuai arahan terbaru, latihan HTML ditunda sampai akhir dan tidak menjadi gate pekerjaan. Lihat [WORKLOG](docs/WORKLOG.md).

## Rencana latihan pertama — sebelum percobaan

Tujuan: memahami mengapa tes unique/not_null dapat lulus pada tabel kosong dan menelusuri titik hilangnya record. Agatha menulis query rekonsiliasi jumlah loan per layer, mengusulkan satu hipotesis, lalu menambahkan tes SQL nonempty yang gagal pada kondisi tersebut. Codex belum menulis query/test latihan finalnya. Hasil query audit disediakan sebagai bukti awal; Agatha mengerjakan implementasi tes dan menjelaskan alasan assert.

Contoh format perintah untuk sesi praktik nanti, belum ditugaskan untuk dijalankan sekarang:

```bash
cd /Users/agathasilalahi/Documents/creditlens
```

Lokasi: terminal Agatha. Tujuan: masuk repo yang diaudit. Dampak: hanya mengubah direktori shell. Output diharapkan: prompt berada di creditlens; jika “No such file”, cek path sebelum melanjutkan. Perintah kedua hanya diberikan setelah scope dan lokasi environment isolasi disepakati; tidak memakai make setup yang langsung install/start services.

## Percobaan M0.1 dan review — 2026-09-09

**Kontribusi Agatha dalam percakapan:** menyebut model sumber `lc_loans_clean`; menulis `select count(*) from lc_loans_clean`; hipotesis: “karna data belum ditarik dan dipanggil”. Tidak ada output eksekusi atau perubahan file SQL yang dikirim.

**Review Codex:** identifikasi model benar; bentuk SELECT COUNT(*) benar. Koreksi: relasi database ditulis `staging.lc_loans_clean` agar tidak bergantung pada search_path; semicolon digunakan untuk mengeksekusi query interaktif. Backslash pada pesan diperlakukan sebagai escape Markdown, bukan SQL untuk disalin. Interpretasi hipotesis yang dapat diuji: data belum dimaterialisasikan dari staging ke mart. Data raw/staging sudah terisi saat audit sebelumnya; penyebab mart kosong belum terbukti.

**Batas bukti pemahaman:** sudah menunjukkan kemampuan awal mengenali ref dan merancang COUNT. Pemahaman schema, materialization, serta bukti penyebab masih perlu demonstrasi; belum mengklaim penguasaan end-to-end.

**Langkah M0.2:** Agatha menjalankan corrected COUNT staging dan menyesuaikan nama tabel menjadi mart.loan_features melalui psql read-only; mengirim output/error serta menilai apakah hasil counts membuktikan dbt belum pernah dijalankan. Codex hanya menyiapkan instruksi, tidak menjalankan query tugas. Tidak ada tes aplikasi/training/rebuild/commit baru.

## Klarifikasi dasar dan prompt — 2026-09-09

**Percobaan/laporan Agatha:** mencoba koneksi read-only, melihat `creditlens->`, dan mempertanyakan password serta istilah staging, mart, dbt dan psql. Tidak mengirim password, error autentikasi atau hasil COUNT.

**Review/bantuan Codex:** menjelaskan perbedaan shell dengan psql, database/schema/tabel/view, staging data dengan staging deployment, serta dbt model dengan model ML. Pada prompt standar psql `->` berarti input belum diterminasi; dugaan salah password belum didukung bukti. Password koneksi adalah milik role PostgreSQL, bukan otomatis password login Mac. Instruksi pemulihan: Control+C, kemudian `\conninfo` dan `SHOW transaction_read_only;`. Tugas COUNT ditunda, bukan diselesaikan Codex.

**Pekerjaan dan batas bukti:** membaca definisi SQL dan dokumentasi resmi PostgreSQL/dbt; memperbarui panduan/checkpoint dokumen. Tidak mengubah source, data, password atau konfigurasi layanan; tidak menjalankan tes aplikasi, training atau rebuild. Status koneksi/read-only Agatha belum terverifikasi. Pemahaman konsep menunggu penjelasan kembali.

## M0.2a selesai dan penyesuaian cara belajar — 2026-09-09

**Bukti Agatha:** output `\conninfo` menyebut database/user creditlens, localhost (::1), port 5432; `SHOW transaction_read_only;` menghasilkan on. Escape Markdown dalam pesan tidak dianggap SQL literal karena output sukses diterima. Bukti ini memverifikasi sesi saat diperiksa, bukan pembatasan permanen role atau pemahaman seluruh konsep.

**Arahan pengguna terbaru:** lanjutkan proses proyek dengan pencatatan tiap proses dan HTML latihan/penulisan query beserta materi ringkas; Agatha ikut menjalankan perintah dan menerima penjelasan langkah. Codex melanjutkan diagnosis independen tanpa menunggu setiap jawaban konsep. Batas M0 dan persetujuan deployment/training/rewrite tidak berubah.

**Pekerjaan Codex:** memeriksa Git (branch codex/m0-mentoring, HEAD tetap 9f24144), membaca source/log/manifest/run_results, menemukan build loan/final berisi data lalu build kosong yang sukses dan di-commit, menyimpan ekstrak/checksum, menyusun diagnosis dan HTML latihan. Tidak menjalankan COUNT tugas Agatha atau mengubah database/source aplikasi. Materi SQL praktik disediakan Codex; jangan mengklaim Agatha menulis contoh itu mandiri.

**Hasil dan batas:** hipotesis dbt belum pernah berjalan tidak cocok dengan log yang tersedia; penyebab input build kosong tetap terbuka. Log jam saja tidak menjamin tanggal/identitas server. Lihat docs/audit/M0_DIAGNOSIS.md. Langkah Agatha berikutnya: dua COUNT, lalu latihan rancangan SQL/tes nonempty. Belum ada klaim bug data selesai, tes aplikasi baru, training, atau commit.

## Template catatan setiap checkpoint

Tanggal / milestone / dokumen-versi disetujui; pertanyaan konsep; tugas Agatha; hipotesis; percobaan dan output; hint/bantuan AI; file/diff/commit; tes beserta environment; penjelasan kembali; batas yang belum dipahami; latihan berikutnya. Menyalin solusi bukan otomatis menguasai konsep.

## Kerangka interview 3–5 menit, belum merupakan klaim prestasi

Indonesia: masalah dan scope publik (30 detik) → keputusan label/waktu fitur (45 detik) → kontribusi SQL/test Agatha dengan file nyata (60 detik) → evaluasi dan hasil yang telah diukur (45 detik) → satu bug/hipotesis/fix/test (45 detik) → keterbatasan dan bantuan AI (30 detik).

English: “I am developing a public-data credit-risk pilot with AI-assisted engineering. My verified contributions are [files/tests/decisions after completion]. I evaluated [cohort and metric with actual results]. One failure I investigated was [evidence → hypothesis → fix → regression test]. The current limitations are [documented limits].” Placeholder hanya diganti setelah ada bukti.

Latihan lintas milestone: SQL join cardinality/window functions; why split-before-fit; calibration versus ranking; feature availability versus missingness; artifact compatibility/readiness; traceback-driven hypothesis; gate versus deployment; monitoring drift versus delayed performance. Semua dikaitkan ke kode yang Agatha review/ubah sendiri.

## Lanjut teknis dan latihan ditunda — 2026-09-09

Agatha meminta latihan HTML di akhir, penjelasan alur dalam tabel, dan proyek dilanjutkan dahulu. Codex mengambil alih COUNT serta implementasi tes M0 sesuai arahan tersebut; tidak mengklaim Agatha penulis kode tes ini. Kontribusi Agatha yang sudah dibuktikan tetap identifikasi sumber, rancangan query awal, verifikasi koneksi/read-only, dan keputusan tujuan/scope.

Codex memverifikasi snapshot read-only baru, menulis dua tes dbt dan script cluster privat, membuktikan tes lama 24 pass pada kosong, nonempty/reconciliation gagal sesuai harapan, lalu 26 tes pass pada fixture terisi. Server fixture dihentikan. Black/Ruff script lulus. Rebuild development berhenti di preflight disk sekitar 1,9 GiB sebelum backup/data mutation; tidak ada training/deploy/commit/push. Detail tiap langkah dan error tercatat di docs/WORKLOG.md.

Bantuan AI mencakup penulisan seluruh dua tes dan script reproduksi, eksekusi serta dokumentasi/alasan kandidat model. Latihan akhir harus menguji variasi masalah dan penjelasan mandiri agar pemahaman tidak disimpulkan hanya dari membaca solusi. M0 dan klaim production readiness belum selesai.

## Disk dilonggarkan dan mart pulih — 2026-09-09

Agatha melaporkan disk telah dilonggarkan dan meminta kelanjutan serta perintah terminal yang diperlukan. Codex memverifikasi ruang, mencadangkan dua mart, menjalankan build terarah dan memeriksa dua model sukses/9 tes pass. Counts staging/loan/final kini 1.599.982. Backup disimpan lokal di luar pelacakan Git; pemulihan backup belum diuji.

Codex juga memprofilkan CSV dan membandingkan ID: 660.686 ID kandidat sumber belum dimuat ke raw. Record audit kini ditemukan pada final mart. Ini kemajuan alur data, bukan bukti model siap atau seluruh ingestion selesai. Tidak ada latihan baru diwajibkan; panduan COUNT opsional di docs/M0_TERMINAL_CHECK.md. Eksekusi SQL/recovery adalah bantuan Codex, sementara pengguna menyelesaikan hambatan kapasitas disk. Tidak mengklaim pengguna menulis kedua tes atau sudah menguasai debugging end-to-end.

## 10 September 2026 — data pulih, target belum diputuskan

Agatha menyatakan hasil COUNT sudah sesuai dan meminta pekerjaan dilanjutkan; dicatat sebagai konfirmasi pengguna, tanpa mengarang output terminal yang tidak dilampirkan. Latihan tetap ditunda sampai akhir.

Codex menemukan mekanisme ingestion terhenti pada status 51 karakter dalam kolom VARCHAR(50). Perbaikan mempertahankan teks sumber utuh, memakai migration yang menjaga dependency staging, dan menyediakan insert-missing agar record lama tidak tertimpa. Tujuh unit tests dan delapan pemeriksaan PostgreSQL privat lulus, seluruh CSV lolos dryrun. Backup raw/view/mart berhasil direstore dalam cluster privat sebelum mutation. Gagal awal socket path terlalu panjang diatasi dengan path pendek; tidak menyentuh server aktif saat perbaikan drill.

Hasil aktif: 660.686 record ditambahkan; raw/staging/loan/final kini 2.260.668. Record lama mempertahankan count/fingerprint seluruh field. Rebuild dua model dan sembilan tes dbt lulus. Ini keberhasilan data pipeline, belum keberhasilan model. Status late tidak otomatis default; current tidak otomatis aman; as-of bukan loaded_at atau last payment maksimum. Draft keputusan berikutnya ada di docs/M0_LABEL_DECISION_DRAFT.md.

Bahan latihan akhir: membaca semicolon/prompt psql; membedakan raw/view/mart; menulis tes nonempty/rekonsiliasi; reproduksi input status panjang dan transaksi rollback; membuktikan resume tidak menimpa data; menjelaskan bias status belum final, target leakage, split waktu, dan alasan Logistic Regression baseline sebelum XGBoost. Gunakan variasi fixture/requirement baru agar Agatha benar-benar menulis dan menjelaskan perubahan sendiri. Jangan mengklaim kode/tes yang ditulis Codex sebagai kontribusi mandiri Agatha.

## 10 September 2026 — verifikasi COUNT dan persiapan Git/PR

Agatha mengirim output nyata `SELECT COUNT(*) FROM mart.final_features;` → `2260668`, satu row hasil. Ini bukti ia menjalankan query verifikasi hasil pemulihan. COUNT menghitung record, bukan membuktikan semua fitur/label benar atau bahwa model valid.

Arahan terbaru: Agatha ingin ikut menjalankan operasi dan menerima perintah terminal untuk commit/push/PR. Codex menyiapkan perubahan, review, bukti tes dan panduan; operasi commit/push/pembuatan PR disisakan untuk dijalankan Agatha. Ini pembagian pekerjaan yang diminta, bukan gate persetujuan baru. Latihan konsep/HTML lengkap tetap di akhir; tidak ada merge/deployment otomatis.
