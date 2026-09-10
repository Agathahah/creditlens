# Git attribution plan

> Status pemasangan 2026-09-08: arah v0.2 dan M0 disetujui. Dokumen ini adalah snapshot audit/rencana atribusi historis, bukan persetujuan rewrite.

v0.1 rencana history; status diperbarui 2026-09-09. **Identitas Git repo-local sudah disetujui dan diterapkan. Pemetaan ulang, backup history, simulasi dan remote belum dieksekusi.** Bukti audit historis: [GIT_EVIDENCE.json](audit/GIT_EVIDENCE.json) dan [GIT_COMMIT_INVENTORY.md](audit/GIT_COMMIT_INVENTORY.md).

Identitas efektif sekarang: Agatha Silalahi / 149786199+Agathahah@users.noreply.github.com untuk author dan committer. Instruksi tanpa AI author/co-author otomatis dipasang di AGENTS/CLAUDE; setting CLI Claude terpisah belum diubah dan tidak dianggap sudah teruji. Periksa pesan/trailer setiap commit sebelum push. Konfigurasi/angka di bagian audit berikut menggambarkan keadaan sebelum pemasangan identitas.

## Arti setiap atribusi

| Konsep | Makna / temuan |
|---|---|
| Author | Identitas pembuat perubahan dalam objek commit; dapat berbeda dari orang yang menerapkan commit |
| Committer | Identitas yang mencatat/menerapkan objek commit; rebase/merge dapat mengubahnya |
| Co-authored-by | Trailer dalam pesan commit untuk kontributor tambahan; tidak sama dengan field author/committer |
| Pemilik PR | Akun pembuat PR di GitHub; PR 11/12 dimiliki Agathahah walau commit tertentu memakai author Claude |
| Collaborator | Akun dengan akses repo; membership/permission terpisah dari metadata commit; daftar collaborator belum diperiksa |
| Contributors | Tampilan yang dihitung GitHub dari kontribusi commit dengan aturan platform; bukan daftar izin akses, dan tidak otomatis membuktikan siapa menulis semua kode |

Git mengambil identitas dari konfigurasi/environment; perintah dapat menimpa identitas. Lihat [git commit](https://git-scm.com/docs/git-commit). GitHub mengaitkan commit berdasarkan email; repo-local setting dapat menimpa global tanpa memengaruhi repo lain. Lihat [commit email](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address). Merge/empty commits tidak dihitung pada contributors graph yang didokumentasikan: [GitHub contributors](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors).

## Identitas efektif dan penyebab

`git var GIT_AUTHOR_IDENT` dan `GIT_COMMITTER_IDENT` keduanya menunjukkan Agatha Silalahi / silalahiagatha15@gmail.com. Sumbernya global `/Users/agathasilalahi/.gitconfig`; tidak ditemukan override user lokal, author/committer config, commit template, custom hooksPath atau trailer setting dalam konfigurasi efektif yang diperiksa. Variabel GIT_AUTHOR/COMMITTER name/email dan override GIT_CONFIG standar tidak diset pada proses audit.

Akun gh terautentikasi: login Agathahah, id 149786199, nama Agatha Silalahi. Commit main GitHub memakai `149786199+Agathahah@users.noreply.github.com`, terhubung ke akun itu. API email menghasilkan HTTP 404 karena scope user tidak tersedia; **status verified Gmail belum dapat dikonfirmasi**. Tidak memperluas auth scope. GitHub `verification.verified=true` pada merge main menyatakan verifikasi signature commit GitHub tersebut, bukan bukti Gmail sudah verified atau semua commit lokal ditandatangani.

Hook executable Git yang ditemukan: post-commit dan post-checkout untuk rebuild Graphify. Tidak ditemukan prepare-commit-msg atau commit-msg hook aktif. Hook agent yang tercatat adalah Graphify guards dan GSD checks/guards; pencarian identitas/co-author pada skrip GSD lokal tidak menemukan penambahan atribusi. GSD validate-commit memeriksa format Conventional Commits. Setting attribution/includeCoAuthoredBy tidak diset di `.claude/settings.json`, `.claude/settings.local.json`, atau `~/.claude/settings.json` yang diperiksa.

Kesimpulan terbatas: metadata Claude pada commit lama terbukti; konfigurasi Git laptop saat ini bukan Claude. Trailer konsisten dengan commit yang dibuat dengan bantuan Claude, dan PR mencatat bantuan Claude. Exact environment/command yang menetapkan author dan committer pada sesi cloud lama tidak dapat direkonstruksi dari setting lokal kini. Ketiadaan override lokal bukan bukti sumber setiap trailer. Jangan menyalahkan hook Graphify sebagai penyebab atribusi; hook tersebut berfungsi rebuild graph.

## Commit berikutnya — rencana repo-local

1. Konfirmasi nama dan email. Rekomendasi konkret: `Agatha Silalahi <149786199+Agathahah@users.noreply.github.com>`, cocok dengan akun yang diverifikasi. Alternatif Gmail setelah pengguna memastikan verified di GitHub Settings/Emails.
2. Setelah disetujui, set `user.name` dan `user.email` **--local** pada CreditLens. Sebelum commit, periksa git var author/committer dan override lingkungan; konfigurasi saja tidak menghalangi override per perintah.
3. Codex tidak menambah AI author/co-author. Jika Claude Code akan dipakai lagi, verifikasi versi dan schema setting atribusi yang didukung, lalu isi konfigurasi commit attribution kosong dengan merge yang mempertahankan hooks/permissions. Dokumentasi settings Inggris saat audit merujuk reference baru yang gagal diambil oleh browser; detail versi lokal perlu diperiksa sebelum edit. Jangan mengubah semua hook atau memakai --no-verify sebagai solusi umum.
4. Review staged diff dan pesan/trailer, commit pekerjaan yang benar-benar direview, lalu audit author/committer/trailer sebelum push. Tidak membuat dummy commit. GitHub signing badge berbeda dari identitas akun; jangan menjanjikan badge Verified untuk unsigned local commit.
5. Karena user tidak menginginkan Graphify otomatis, dalam milestone Git yang disetujui gunakan opt-out hook yang sudah didukung (`GRAPHIFY_SKIP_HOOK=1`) pada operasi terkait, tanpa uninstall/menghapus hook. Tidak ada commit/checkout dilakukan pada sesi audit.

## Scope metadata yang terukur

| Reachability | Total | Claude author | Claude committer | Commit dengan trailer Claude | Union kandidat metadata |
|---|---:|---:|---:|---:|---:|
| HEAD lokal | 34 | 12 | 12 | 15 | 15 |
| main GitHub/cache yang identik SHA | 35 | 12 | 12 | 15 | 15 |
| Semua refs lokal yang diinventarisasi | 40 | 17 | 17 | 15 | 20 |

Angka kategori tumpang tindih dan tidak dijumlahkan. Lima author Claude tambahan ada pada branch `claude/alembic-import-conflict-mac-e6gw8x` di luar main. SHA penuh, identitas dan trailer tiap kandidat tersedia di GIT_COMMIT_INVENTORY.md; tanggal dan parents/tree/signature presence tersedia di GIT_EVIDENCE.json.

**Pemetaan calon, memerlukan persetujuan spesifik:**

- Field author dengan pasangan persis `Claude <noreply@anthropic.com>` → identitas Agatha yang dikonfirmasi, hanya pada commit allowlist.
- Field committer dengan pasangan persis sama → identitas Agatha yang dikonfirmasi, hanya pada commit allowlist.
- Hapus hanya trailer Co-authored-by yang bernilai persis salah satu: `Claude Opus 4.8 <noreply@anthropic.com>`, `Claude Fable 5 <noreply@anthropic.com>`, `Claude Opus 4.6 (1M context) <noreply@anthropic.com>`. Nama token dapat beda kapitalisasi sesuai parser trailer Git, isi identitas harus cocok allowlist.
- Semua author/committer manusia, committer GitHub, trailer manusia, subject/body selain trailer AI tersebut, lisensi dan kredit pihak ketiga dipertahankan. Jangan mengganti substring “Claude” di source, PR body atau seluruh history secara massal.
- Author/committer dates serta offset waktu dipertahankan. Pemetaan ini adalah koreksi metadata pengelolaan repo berbantuan AI, **bukan** klaim Agatha menulis seluruh kode lama secara manual.

## Ref remote yang terlihat saat audit

| refs/heads/ | SHA sebelum perubahan |
|---|---|
| main | 1a097c5e0254a09ddcaeebac8d7bd0fb4fe0093d |
| chore/fix-gitignore-cleanup | 9f241445ae75066cabda444b6a339d792c54b034 |
| feature/foundation | 985e905dfcdaeaf414c6d63644360543cfdecca1 |
| feature/ml-pipeline | a6902bb0b56cc6c3a9c4270d039dabf0dd148d65 |
| feature/ml-pipeline-impl | 985e905dfcdaeaf414c6d63644360543cfdecca1 |
| feature/api | 31c2f7c7c6a560d9006832e47772e90e8ae42093 |
| feature/airflow | 060370371af83e47517b8e1ef06d9fe3d9c02db0 |
| feature/feast-store | 6cf85e45d7b5287289f61dfc9db96d45e68de661 |
| feature/monitoring | 4d4c89000a1f46ec1e799d6dc49b8fbd2a54ba5f |
| feature/mlops-enhancements | 8654fd68f9a3b25ce4df2077e23213d4ebde1cac |
| feature/survival-analysis | ef479139d3abc4b7e5ab14ec7935d90f19874d6f |
| claude/explainability-fairness-16fto9 | fb2b713656013390abb161498f584b198c95a540 |
| claude/alembic-import-conflict-mac-e6gw8x | 21a8227456c47d0b68862a401396aef179054b24 |

Main protected; tags API kosong. Local heads, remote-tracking refs, serta ref internal Codex juga ada dalam inventory; **ref internal, stash/backup refs dan refs/pull bukan target push**. Daftar branch adalah inventaris, bukan izin mengubah semuanya.

Pilihan rencana: A) hanya cegah atribusi otomatis commit baru; B) koreksi main dengan 15 kandidat tetapi ref branch lain tetap menyimpan history lama; C) koreksi allowlist branch yang dipilih secara konsisten, termasuk 5 kandidat tambahan jika branch Alembic disertakan. Rekomendasi mulai A dan simulasi B; keputusan C baru sesudah dampak terlihat. Pekerjaan core tidak menunggu rewrite.

## Dampak konkret yang dihitung sebelum simulasi

Karena parent SHA ikut menentukan commit SHA, mengubah 15 kandidat pada main diperkirakan mengubah **34 dari 35 SHA** reachable. Ada **22 commit dengan signature** pada jalur yang akan berubah. Signature lama tidak dapat dipertahankan sebagai signature valid untuk objek baru. Simulasi harus mencatat pelepasan signature invalid; jangan menyalin signature seolah valid atau meniru tanda tangan manusia/GitHub. Opsi menandatangani ulang dengan kunci Agatha adalah keputusan terpisah dan bukan signature asli.

Pada seluruh refs lokal: 20 kandidat langsung, 39 dari 40 SHA berpotensi berubah, termasuk 27 signed commits. Ini hasil analisis ancestor, **bukan** hasil rewrite atau SHA pengganti. Tree ID file di setiap mapped commit harus tetap sama. PR/commit links, base perbandingan, CI records, clone lain dan fork dapat tetap menunjuk history lama. Contributors bisa terlambat dihitung; membersihkan metadata tidak menghapus semua jejak Claude.

## Backup lengkap setelah pemetaan disetujui

Koordinasikan freeze penulisan Git dan hentikan writer aplikasi yang relevan; jangan menghentikan layanan tanpa scope yang disetujui. Pilih direktori backup **di luar repo aktif**, misalnya direktori bertanggal yang pengguna setujui dengan ruang cukup.

Simpan bundle seluruh refs lokal yang relevan dan bundle/mirror remote terpisah, ref manifest, git config/hooks, reflog/object store yang dibutuhkan untuk recovery, index serta patch binary staged/unstaged. Bundle saja tidak memuat untracked/ignored files, working tree, config, hook, reflog dan state eksternal. Karena itu backup filesystem lengkap repo termasuk .git, empat dokumen untracked, data gzip, ignored artefak, konfigurasi lokal dan metadata/symlink; rahasiakan .env/credential-bearing config, tidak upload/push backup. Inventory ukuran dan checksum sebelum/sesudah. Backup state PostgreSQL/volumes bila menjanjikan recovery lingkungan lengkap; history rewrite sendiri tidak memerlukan mengubah database. Buat restore rehearsal di salinan terpisah sebelum menyebut backup valid.

## Simulasi terisolasi dan kriteria review

1. Gunakan clone/copy disposable dari backup terverifikasi, bukan worktree bersama object store repo aktif; hindari shared hardlink object writes. Matikan push URL dan hooks pada salinan simulasi. Jangan menginstall tool atau menjalankan filter sekarang.
2. Verifikasi tool rewrite dan versinya; gunakan callback berbasis allowlist commit+identitas, bukan regex penghapusan menyeluruh. Batasi refs yang dipilih; preserve merge topology, tanggal, isi file/mode dan trailer manusia.
3. Hasilkan old→new SHA map, ref map, before/after metadata diff dan signature report. Pastikan `tree(old)==tree(new)` **untuk setiap mapped commit dan setiap ref terkoreksi**, bukan hanya main tip; jumlah dan relasi parents identik setelah pemetaan.
4. Jalankan integritas object (fsck) dan check hash backup/working files. Verifikasi human identities/trailers unchanged; tiga trailer AI yang disetujui hilang hanya di scope; tidak ada field lain berubah kecuali parent IDs/signature handling yang disepakati.
5. Berikan tabel ref lama→baru, jumlah commit, tree equality, signatures hilang, serta batas dampak PR/clone/fork. Agatha review hasil konkret. Tidak ada remote mutation sebelum persetujuan khusus tersebut.

## Remote dan pemulihan, hanya setelah persetujuan akhir

Refresh advertised remote SHA tepat sebelum perubahan; jika ada perubahan baru, berhenti dan ulang dampak. Per-ref push eksplisit dengan lease terhadap SHA remote yang telah disetujui; jangan force tanpa lease, push --mirror, push --all, delete branches/tags, atau mass push backup refs. Jangan bypass protection main; perubahan aturan memerlukan persetujuan khusus tersendiri. Scope main-only meninggalkan old history pada branch lain dan itu harus diterima secara eksplisit.

Jika perlu pemulihan remote, review dan setujui ref+SHA backup tertentu lalu kembalikan per-ref dengan lease terhadap SHA rewrite yang benar; rollback remote juga penulisan history dan memerlukan koordinasi. Restore repo aktif dari backup hanya dengan persetujuan, mempertahankan pekerjaan baru sejak backup. Clone lain perlu instruksi rekonsiliasi/reclone dan penyelamatan perubahan lokal; tidak memerintahkan hard reset massal.

Pernyataan provenance yang dipertahankan: “CreditLens dikembangkan Agatha dengan bantuan AI, termasuk Claude dan Codex pada tahap berbeda. Kontribusi manual, review, keputusan dan latihan Agatha dicatat bersama bukti; koreksi metadata Git tidak menyatakan seluruh kode historis ditulis manual.”
