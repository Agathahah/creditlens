# Milestone dan ADR

> Pembaruan operasional 10 September 2026: ingestion dan rebuild lokal selesai; raw/staging/loan/final masing-masing 2.260.668, schema loan_status TEXT. Snapshot audit lama di bawah dipertahankan sebagai konteks; status aktif ada di PROJECT_STATUS.md. Kontrak label/M1 masih draft: lihat M0_LABEL_DECISION_DRAFT.md.


> Status pemasangan 2026-09-08: arah v0.2 dan M0 disetujui. Detail implementasi di luar M0 tetap draft; ini bukan izin training penuh, deployment, atau rewrite.

v0.2 · M0 aktif: reproduksi, tes dan recovery mart lulus; cakupan ingestion/label masih terbuka. Arahan terbaru 9 September menunda latihan sampai akhir; pembagian tugas latihan dalam tabel berikut kini menjadi backlog demonstrasi, bukan gate eksekusi. Codex mengerjakan dua tes M0 dengan atribusi jelas. Persetujuan deployment, training penuh, dan rewrite tetap terpisah.

| Milestone | Prasyarat persetujuan | Tugas Agatha yang disisakan | Tugas Codex setelah percobaan | Kriteria selesai |
|---|---|---|---|---|
| M0 — reproduksi dan kontrak awal | PRD v0.2, desain data/eval arah awal, lingkungan isolasi | Menulis query rekonsiliasi raw/staging/mart dan satu dbt test nonempty; mengajukan hipotesis mengapa mart kosong | Menyiapkan isolasi/snapshot aman, membantu membaca log dan review query; memfasilitasi data-as-of/label feasibility; reproduksi baseline software bersama | Penyebab/ketidakpastian terdokumentasi, test menangkap mart kosong, lingkungan reproducible, scope target/availability M1 siap disetujui |
| M1 — validitas preprocessing/evaluasi | Label/horizon/eligibility final, whitelist fitur dan evaluation protocol v0.2 | Menulis regression test yang mengubah nilai test ekstrem dan membuktikan transform train invariant; satu SQL label boundary | Review usaha Agatha, implementasi transform tersimpan bagian lain, baseline/validation metrics dan error analysis | Leakage tests dan split maturity lulus; baseline reproducible; threshold/calibrator tidak belajar dari test; Agatha menjelaskan leakage |
| M2 — bundle dan API | Kontrak fitur/bundle/API serta mode Feast disetujui | Menulis readiness absent/corrupt test atau parity assertion raw→HTTP; mengerjakan bagian key mapping SQL bila Feast masuk scope | Wiring bundle loader/schema, integrasi score/explain, Feast setelah key contract selesai | Satu record melewati jalur aktual, kategori dan missing valid, readiness tepat, probabilitas reload/HTTP konsisten |
| M3 — CI, release dan rollback | Desain release, target lingkungan, budget, benchmark disetujui | Menambah satu tes negatif evaluation gate dan assertion smoke rollback | Menghubungkan manifests, artifact/data input CI, image release, menjalankan recovery drill bersama | Eval mengikat artefak yang dirilis; gagal gate tidak release; rollback terbukti; approval deploy tersendiri |
| M4 — monitoring dan pilot | Schema event, akses/retention, SLO dan runbook disetujui | Mengganti/menulis SQL scoring volume dari event inference dan test delayed-label join | Wiring event/log sanitization, drift reference/current, dashboard/runbook, backup state dan restore drill sesuai scope | Dashboard mengukur traffic, alert bermakna, tidak auto-promote/retrain, evidence pilot dan biaya tersedia |
| M5 — review kesiapan dan interview | Acceptance scope pilot terakhir disetujui | Memperbaiki satu edge case/tes recovery dari review pilot dan memberi walkthrough ID/EN 3–5 menit | Meninjau bukti, menantang asumsi dalam mock interview, menyiapkan daftar keterbatasan | AC PRD dipenuhi pada lingkungan/beban yang disebut; kontribusi Agatha terbukti, tidak ada klaim pengguna/metrik rekaan |

Cara kerja terbaru: jelaskan tujuan → kerjakan langkah teknis yang diizinkan → verifikasi → catat hasil/keputusan/kontribusi → kumpulkan latihan HTML untuk akhir. Saat latihan akhir, gunakan percobaan mandiri, review dan penjelasan kembali; jangan mengklaim pemahaman sebelum demonstrasi.

Setiap instruksi terminal wajib singkat, berisi lokasi, tujuan, dampak, expected output dan diagnosis. Arahan terbaru mengizinkan Codex menjalankan pemeriksaan yang sebelumnya ditugaskan, dengan mencatat perubahan pelaksana. Milestone selesai dengan diff, test output, keputusan, keterbatasan, dan learning log; jumlah commit bukan ukuran kompetensi.

## Pemeriksaan pemahaman dan penerimaan mandiri

Setiap milestone memiliki dua syarat terpisah: sistem lolos bukti teknis dan Agatha mendemonstrasikan pemahaman. Ukuran belajar: dapat menjelaskan dengan kata sendiri, mengerjakan perubahan kecil tanpa solusi lengkap, memprediksi perilaku, dan mendiagnosis satu variasi bug baru. Jika belum bisa, lakukan latihan tambahan kecil; jangan otomatis menambah fitur.

Reviewer eksternal tidak diwajibkan. Agatha menjalankan checklist acceptance dan memutuskan rilis; Codex mengulas diff/hasil dan membantu mencari kelemahan, tidak mengklaim review independen manusia. Tes otomatis, laporan evaluasi terkunci, negative tests dan recovery drill melengkapi self-review. Staging tetap berguna untuk mencoba migrasi/config/model release dan rollback pada lingkungan terpisah meskipun dikerjakan sendirian.

Bukti untuk Data Scientist: SQL/cohort, target, leakage, baseline, calibration, error analysis dan batas interpretasi. Bukti untuk ML Engineer: kontrak data/model, serving, tests, CI, deployment, observability dan recovery. Bukti tambahan AI Engineer: setelah core stabil, Ops Copilot RAG/single-agent yang dievaluasi terhadap baseline dan memiliki batas tools/biaya; tidak dilabeli selesai sebelum dibuat dan diukur.

## ADR yang diajukan

| ADR | Status | Keputusan / alternatif / konsekuensi |
|---|---|---|
| ADR-008 | Proposed | Proyek mandiri: pilot publik retrospektif lokal → staging yang diuji Agatha → layanan demonstrasi yang siap dioperasikan setelah release gates. Alternatif origination credit decision ditunda karena label/time/permission belum cukup |
| ADR-009 | Pending M0 | Event Charged Off/Default versus Fully Paid di cohort eligible; Late/current terpisah. Fixed-horizon memerlukan bukti event/as-of; snapshot classifier memiliki batas klaim |
| ADR-010 | Proposed | Train-only pipeline dan immutable bundle; menggantikan batch median/category codes yang tidak tersimpan. Perlu kontrak schema dan uji raw→model |
| ADR-011 | Proposed | Validation untuk calibration/threshold; frozen temporal test untuk estimasi akhir. Membutuhkan pemisahan data dan manifest yang lebih ketat |
| ADR-012 | Proposed | Inline raw feature serving dulu; Feast milestone berikutnya hanya bila integrasi diverifikasi. Modul Feast tetap dipertahankan |
| ADR-013 | Proposed | Separate liveness/readiness dan candidate/promoted artifact; release fail-closed bila schema/model/data mismatch |
| ADR-014 | Proposed | Monitoring inference aktual + delayed labels; drift memicu review manusia |
| ADR-016 | Proposed | Self-review dengan Agatha sebagai release owner; bukti otomatis, negative tests, recovery drill dan teach-back menggantikan ketergantungan pada reviewer eksternal, tanpa klaim audit independen |
| ADR-015 | Proposed | Identitas repo-local manusia, bantuan AI dicatat naratif; metadata history cleanup membutuhkan pemetaan, backup, simulasi, review terpisah |

ADR-001–007 hanya tercantum sebagai ringkasan dalam CLAUDE.md lama. Pertahankan PostgreSQL/dbt, pilihan baseline/kandidat, temporal intent, PR metrics dan konteks explainability/Feast; jangan menyatakan semua ADR sudah terimplementasi penuh. ADR baru menjelaskan penyesuaian, bukan menghapus konteks lama.

## Tahap Ops Copilot, sesudah core stabil

Ajukan PRD/desain baru: RAG atas runbook, metadata deployment, metrik/log tersanitasi; satu agent memilih tools baca-saja dan menyusun diagnosis dengan kutipan untuk review manusia. Bandingkan baseline pencarian/runbook tanpa agent. Ukur retrieval relevance, ketepatan evidence/diagnosis, task success, unsupported claims, latency dan biaya. Desain ingestion/chunking/retrieval/citation, state/session isolation, tool permissions, stop conditions, timeout/retry/budget, tracing dan prompt injection sebelum implementasi. Tidak boleh retrain/promote/model-change/keputusan kredit otomatis.

Swarm/multi-agent hanya jika baseline menunjukkan kebutuhan dan keuntungan terukur. Hermes/Graphify tidak diperlukan otomatis. Graphify sudah meninggalkan instalasi/hook lokal, namun tidak dijalankan/diperluas pada audit ini. ERD adalah relasi data; workflow graph alur proses; Graphify peta kode; GraphRAG teknik retrieval—kebutuhannya berbeda.
