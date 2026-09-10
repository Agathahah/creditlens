# M0 — menjalankan commit, push dan draft PR bersama

10 September 2026. Paket siap untuk dijalankan Agatha; belum ada commit/push/PR pada checkpoint penulisan panduan. Codex sudah memeriksa diff, daftar file, identitas, GitHub dan tes. Latihan HTML lengkap tetap di akhir; langkah Git ini partisipasi operasional yang diminta Agatha.

## Apa yang berpindah ke GitHub

| Istilah | Arti dan dampak |
|---|---|
| Working tree | File yang sedang diedit di laptop; belum menjadi riwayat commit |
| git add / staging Git | Memilih perubahan untuk commit berikutnya. Ini berbeda dari schema staging PostgreSQL |
| Commit | Snapshot perubahan terpilih dengan pesan, author, committer dan parent; masih lokal |
| Push | Mengirim commit dan memperbarui branch tujuan di GitHub |
| Pull request / PR | Mengajukan perbandingan branch dengan main; ada ruang review dan hasil CI |
| Draft PR | PR yang belum dinyatakan siap digabung; tetap dapat menjalankan workflow PR |
| Merge | Menggabungkan perubahan ke main; langkah terpisah sesudah review/CI |
| Fetch | Memperbarui informasi branch remote tanpa mengubah file kerja |

Yang dikirim adalah source, tes, dokumentasi dan laporan agregat. Isi PostgreSQL serta model di laptop tidak ikut berpindah melalui git push. `.env`, CSV dan `.local-backups` diabaikan Git; empat dokumen konteks historis pengguna tetap untracked dan tidak ikut paket ini. Gunakan path eksplisit berikut, bukan `git add .`.

Kondisi diverifikasi: branch codex/m0-mentoring, HEAD 9f24144; GitHub main 1a097c5 (satu merge commit lebih maju, tree sama). Akun gh Agathahah memiliki akses push. Belum ada PR branch ini. Main protected, required approving reviews = 0, required status checks belum dikonfigurasi. Dengan aturan saat diperiksa, reviewer eksternal tidak diwajibkan; kita tetap menunggu CI/review sebelum merge. Aturan dapat berubah, jangan menganggap angka ini izin bypass pemeriksaan.

## 1. Keluar dari psql, masuk repo

Di prompt `creditlens=>` jalankan:

```text
\q
```

Tujuan/dampak: menutup sesi psql, bukan menghentikan server PostgreSQL. Prompt kembali menjadi shell Mac (`%` atau `$`). Semua perintah selanjutnya dijalankan di shell, bukan psql.

```bash
cd /Users/agathasilalahi/Documents/creditlens
git status --short
git branch --show-current
```

Harapan: branch `codex/m0-mentoring`; file M0 modified/untracked. Jika branch berbeda, berhenti dan kirim output sebelum commit agar perubahan tidak dicatat pada branch keliru.

## 2. Periksa identitas dan remote

```bash
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
git remote -v
git fetch origin
```

Harapan kedua identitas: `Agatha Silalahi <149786199+Agathahah@users.noreply.github.com>` diikuti timestamp. Remote origin harus repo Agathahah/creditlens. Fetch hanya mengunduh informasi/objek Git. Belum mengirim perubahan atau memodifikasi file kerja. Tidak perlu pull/rebase untuk dasar branch yang baru diperiksa; bila main berubah, periksa diff terbaru bersama sebelum merge.

Identitas email menghubungkan commit ke akun Agathahah; badge GitHub “Verified” adalah soal signature dan tidak otomatis muncul hanya karena noreply benar. Jangan mengubah author/committer lama. Bantuan AI dicatat naratif tanpa trailer AI otomatis.

## 3. Commit tes kelengkapan mart

```bash
git add -- tests/dbt scripts/verify_m0_dbt.py
git diff --cached --stat
git diff --cached --check
GRAPHIFY_SKIP_HOOK=1 git commit -m "test(dbt): detect empty and inconsistent loan marts"
```

`git add` memilih dua tes SQL dan runner reproduksi. `--stat` menunjukkan ringkasan tiga file; `--check` seharusnya tanpa output/error. Commit menyimpan perubahan lokal. Variabel GRAPHIFY_SKIP_HOOK=1 menggunakan opt-out hook yang sudah terpasang agar tidak membangun graph otomatis; tidak menonaktifkan CI atau menghapus hook. Harapan output commit SHA baru dan tiga file berubah.

## 4. Commit pemulihan ingestion

```bash
git add -- .gitignore scripts/init_db.sql scripts/load_data.py
git add -- src/common/orm_models.py src/ingestion/lending_club.py
git add -- src/ingestion/tests/test_lending_club.py scripts/verify_m0_ingestion.py
git add -- migrations/versions/4b7d2a91c608_expand_loan_status.py
git diff --cached --stat
git diff --cached --check
GRAPHIFY_SKIP_HOOK=1 git commit -m "fix(ingestion): preserve loan statuses and resume missing records"
```

Harapan delapan file terpilih: schema/ORM/migration, loader/helper, unit tests, runner dan ignore backup. Commit tidak menjalankan migration atau mengisi database; mutation lokal sebelumnya sudah selesai dan dilaporkan. Pemisahan commit membantu reviewer memahami alasan perubahan serta memungkinkan revert source per bagian. Revert Git tidak otomatis membatalkan migration/data aktif.

## 5. Commit dokumentasi dan bukti

```bash
git add -- AGENTS.md CLAUDE.md README.md PROJECT_STATUS.md LEARNING_LOG.md docs/
git diff --cached --stat
git diff --cached --check
GRAPHIFY_SKIP_HOOK=1 git commit -m "docs: record M0 recovery and mentoring evidence"
```

Harapan hanya dokumen/rencana, laporan agregat dan arsip script operasi yang sudah diperiksa. Isi draft PR dan panduan ini ikut tersimpan. Catatan bertanggal “belum push/PR” adalah snapshot persiapan, bukan pernyataan bahwa push tidak pernah terjadi kemudian. Setelah hasil dikirim, log akan diperbarui dengan commit/URL aktual.

## 6. Periksa tiga commit sebelum push

```bash
git log -3 --format=fuller
git status --short
git diff origin/main...HEAD --stat
```

Harapan: tiga commit baru dengan author/committer noreply Agatha, pesan tanpa trailer AI. Empat file *_CONTEXT.md lama tetap untracked; itu sengaja dan tidak menghalangi push. Tidak ada perubahan M0 tertinggal yang belum dicommit. Jangan menyalin seluruh email/password/token dari konfigurasi lain.

Pemeriksaan independen singkat opsional:

```bash
.venv/bin/python -m pytest src/ingestion/tests/test_lending_club.py -q
```

Lokasi root repo, hanya fixture unit, harapan tujuh tes pass. Tidak menyentuh database aktif. Suite src/tests yang lebih luas sudah dijalankan Codex: 124 passed, 4 skipped. Bukti ada di audit/M0_PR_PREFLIGHT.json.

## 7. Push branch yang sudah diperiksa

```bash
git push -u origin codex/m0-mentoring
```

Ini pertama kali langkah di panduan mengirim commit ke GitHub. `-u` menghubungkan branch lokal dengan origin/codex/m0-mentoring. Harapan pesan new branch dan upstream tracking. Main tidak berubah. Tidak memakai --force, tidak push semua branch, dan tidak menulis ulang history.

Jika ditolak/non-fast-forward, berhenti dan kirim pesan error yang tidak memuat rahasia. Jangan mencoba force-push. Jika autentikasi diminta, selesaikan melalui login GitHub lokal; password PostgreSQL tidak digunakan untuk GitHub.

## 8. Buat draft PR

```bash
gh pr create --repo Agathahah/creditlens \
  --base main --head codex/m0-mentoring --draft \
  --title "fix(data): restore resumable ingestion and enforce mart completeness" \
  --body-file docs/M0_PR_BODY.md
```

`gh` sudah tersedia dan akun Agathahah terverifikasi pada pemeriksaan ini. Perintah membuat PR publik di repo yang sama, memakai deskripsi yang bisa dibaca dahulu di docs/M0_PR_BODY.md. Harapan satu URL PR. Bila perintah melaporkan PR sudah ada, jangan membuat duplikat; lihat PR existing dengan perintah berikut.

```bash
gh pr view codex/m0-mentoring --repo Agathahah/creditlens --json number,url,state,isDraft
gh pr checks codex/m0-mentoring --repo Agathahah/creditlens
```

View menampilkan identitas PR. Checks membaca hasil CI; pada awalnya bisa belum tersedia/pending. Tidak ada perintah merge pada tahap ini. Workflow saat ini menjalankan lint/typecheck dan tes pada PR; evaluation gate hanya saat push main dan masih punya masalah artefak yang didokumentasikan. CI hijau di PR ini bukan bukti kualitas model atau kesiapan produksi.

## Setelah dijalankan

Kirim output `git log -3 --oneline`, URL PR dan hasil `gh pr checks` (atau error pertama). Codex memeriksa commit/diff/trailer dan CI aktual, mencatat kontribusi Agatha, lalu menyiapkan langkah berikutnya. Jalankan blok berurutan; jika suatu langkah gagal, jangan melanjutkan blok yang bergantung padanya.

M0 masih menunggu provenance/as-of serta keputusan label. Membuka PR M0 tidak otomatis menyetujui draft target M1, training penuh, deployment atau rewrite Git. Tujuan tahap ini adalah menyimpan dan mereview perbaikan yang sudah dibuktikan.
