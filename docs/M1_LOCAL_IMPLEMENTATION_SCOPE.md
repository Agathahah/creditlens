# Usulan persetujuan implementasi M1 lokal

Status 23 September 2026: **disetujui untuk implementasi dan evaluasi lokal berbatas sumber daya**. Training penuh, deployment, merge, dan push tetap tidak termasuk. Dokumen ini menjadi batas pekerjaan M1 lokal; perubahan ruang lingkup memerlukan keputusan baru.

## Mengapa persetujuan terpisah diperlukan

`AGENTS.md` menetapkan lingkup yang saat ini diizinkan hanya diagnosis dan pemulihan M0. Implementasi M1–M5, training penuh, deployment, dan penulisan ulang riwayat memerlukan persetujuan eksplisit yang relevan. Deskripsi hasil M1 berada di `docs/MILESTONES_ADR.md`; protokol evaluasinya dijabarkan dalam `docs/EVALUATION_RELEASE_PLAN.md`; pilihan cohort/fitur/split yang diusulkan berada di `docs/M0_COHORT_FEATURE_SPLIT_PROPOSAL.md`.

## Cakupan M1 lokal yang diminta untuk disetujui

1. Membuat manifest cohort berversi untuk pinjaman accepted tenor 36 bulan, penerbitan 2011–2015, dengan target retrospektif Fully Paid=0 dan Charged Off/Default=1; status lain tetap dihitung tetapi tidak menjadi label 0.
2. Membagi berdasarkan `issue_date`: train 2011–2013, validation 2014, dan frozen test 2015. Membuktikan ID unik, antarbagian saling lepas, jumlah/label/prevalensi cocok, dan mencatat bahwa ini holdout vintage retrospektif, bukan backtest prospektif.
3. Menerapkan whitelist fitur awal yang disetujui serta aturan missing/invalid yang eksplisit. Split dilakukan sebelum `fit`; imputer, encoder dan scaler hanya belajar dari train. Validation/test memakai `transform` dari train.
4. Menambahkan tes kontrak untuk kebocoran preprocessing, batas tanggal split, status Late/Current tetap tanpa label, kolom outcome/ID tidak masuk fitur, kategori baru ditangani, dan urutan/schema fitur stabil setelah simpan/muat.
5. Membandingkan prediktor konstan dan Logistic Regression terlebih dahulu. XGBoost hanya dijalankan sebagai kandidat berbatas sumber daya setelah jalur baseline lulus. Semua kandidat memakai cohort/split yang sama.
6. Memakai validation untuk pilihan model, parameter, kalibrasi dan simulasi threshold. Frozen test dibuka satu kali setelah pilihan dikunci. Jika test memengaruhi revisi, tandai test telah terpakai.
7. Menyimpan laporan lokal yang berisi denominator, exclusions, prevalensi, ROC-AUC, trapezoidal PR-AUC dan average precision dengan nama yang benar, Brier/calibration, confusion matrix pada threshold terkunci, uncertainty yang didefinisikan, serta error analysis per vintage/slice yang memadai.
8. Membatasi eksekusi awal pada maksimum dua thread dan satu kandidat XGBoost kecil, tanpa Optuna sweep besar. Catat waktu, peak memory, versi paket, seed, commit/code revision dan checksum input/artefak.

## Belum termasuk dalam persetujuan M1 lokal

- Menyebut hasil sebagai probability of default horizon tertentu, backtest origination prospektif, atau rekomendasi keputusan kredit nyata.
- Memakai pinjaman 60 bulan, tahun 2016–2018, rejected applications sebagai non-default, FRED/SEC, grade/sub-grade, pricing, payment/recovery, atau fitur lain yang belum disetujui.
- Training penuh berulang, pencarian hyperparameter luas, membuka frozen test selama pengembangan, atau mengganti ambang agar test lulus.
- Implementasi bundle/API M2, perubahan CI/rilis M3, Docker release, deployment, monitoring pilot, biaya cloud, merge, force-push atau penulisan ulang riwayat Git.
- Menerbitkan dataset mentah, backup database, model lokal, rahasia, atau catatan belajar privat.

## Kriteria selesai M1 lokal

- Manifest cohort/split dapat direproduksi dan seluruh rekonsiliasi jumlah/ID lulus.
- Tes leakage menunjukkan perubahan validation/test tidak mengubah statistik transform train.
- Baseline konstan dan Logistic Regression dapat direproduksi; kandidat XGBoost hanya dipertahankan bila peningkatannya terukur dan batasnya dilaporkan.
- Frozen test tidak dipakai untuk pemilihan; laporan menyebut batas accepted-only, `member_id` kosong, hak penggunaan publik dan outcome as-of yang belum terverifikasi.
- Tidak ada klaim produksi, deploy, merge atau push otomatis.

## Bentuk persetujuan yang diberikan

Persetujuan diberikan untuk cakupan berikut:

> Saya menyetujui implementasi M1 lokal sesuai `docs/M1_LOCAL_IMPLEMENTATION_SCOPE.md`, termasuk training/evaluasi lokal berbatas sumber daya, tanpa training penuh, deployment, merge, atau push.

Persetujuan ini tidak otomatis mencakup langkah sesudah M1. Perubahan ruang lingkup harus dijelaskan dan disetujui tersendiri.
