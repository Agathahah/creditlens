# Dashboard riset — packaging dan pilot publik

Disiapkan 29 September 2026. Scope: dashboard baca-saja berisi agregat riset yang sudah ada pada
repository. Tidak mengaktifkan scoring, keputusan kredit, database publik atau training baru.

## Bukti dasar

Remote PR #14 pada `61c960c` sudah cocok dengan checkout lokal. Pada
[run 36535113262](https://github.com/Agathahah/creditlens/actions/runs/36535113262), lint/typecheck
lulus dan tes melaporkan 146 passed, 4 skipped, 7 warnings; coverage agregat 89% turut mencakup file
tes dalam src. Model Evaluation Gate dan Build Docker Image lama skipped. Hasil ini mendahului
penambahan job Docker dashboard di bawah; packaging baru belum diuji oleh runner sampai push.

## Kriteria penerimaan packaging

1. Tes UI membaca snapshot historis, merender disclosure gagal gate dan dapat mengganti cohort.
2. Image dashboard berhasil dibuild dan server HTTP health mengembalikan 200.
3. Container health menjadi healthy dalam 60 detik; user runtime bukan root.
4. Path `/app/data`, `/app/models`, `/app/.git`, `/app/.env`, `/app/.local-backups` tidak ada.
5. Agregat cohort direkonsiliasi; snapshot tetap menunjukkan model gagal dan test consumed.
6. Laporan smoke mencatat image ID dan code revision, serta model_release_passed=false.

Tes shell negatif memakai command fixture untuk membuktikan container unhealthy tidak menghasilkan
laporan sukses dan hanya container milik tes yang dibersihkan. Tes ini bukan pengganti Docker nyata.

Job **Dashboard Docker Smoke** menjalankan build dan skrip pada runner setelah lint/tests lulus.
Job tidak push image, deploy layanan atau mempromosikan model. Artifact
`dashboard-packaging-<revision>` menyimpan dashboard-smoke.json. Checkout PR GitHub dapat memakai
merge revision sementara; lihat code_revision pada artifact, bukan menganggap selalu SHA head PR.

## Verifikasi lokal yang ringan

```bash
cd /Users/agathasilalahi/Documents/creditlens
.local-backups/dashboard-venv/bin/python -m pytest \
  tests/test_dashboard.py tests/test_dashboard_packaging.py -q
.local-backups/dashboard-venv/bin/python -m streamlit run src/dashboard/app.py \
  --server.address=127.0.0.1 --browser.gatherUsageStats=false
```

Jika environment belum tersedia, buat mengikuti PRODUCTION_READINESS_ROADMAP.md. Buka
http://localhost:8501, periksa semua tab dan disclosure, lalu Ctrl+C. `width="stretch"` dipakai
untuk menghindari parameter tabel Streamlit yang sudah deprecated.

## Docker lokal atau runner CI

Pemeriksaan saat persiapan menunjukkan sekitar 7,2 GiB ruang host, Docker 29.0.1, tanpa cache build.
Batas operasional lokal smoke tetap minimal 8 GiB. `docker system df` juga memuat resource proyek
lain; jangan menghapusnya secara massal. CI runner memungkinkan packaging diverifikasi tanpa
memakai disk laptop untuk build baru.

Setelah tersedia ≥8 GiB, perintah lokal opsional:

```bash
docker build -f infra/docker/Dockerfile.dashboard -t creditlens-dashboard:research .
mkdir -p .local-backups/dashboard-release
bash scripts/smoke_dashboard_image.sh creditlens-dashboard:research \
  ".local-backups/dashboard-release/smoke-$(date +%Y%m%d-%H%M%S).json"
```

Skrip memakai port loopback acak untuk menghindari bentrok 8501 dan menghapus hanya container yang
dibuatnya. Image tetap tersedia. Jangan gunakan prune volume/database. Jalur laporan harus baru
agar bukti lama tidak tertimpa. Kegagalan smoke bukan bukti model gagal/berhasil: ini gate packaging.

## Pilot dashboard di Streamlit Community Cloud

Community Cloud dipilih sebagai usulan hosting demo pendidikan dengan biaya layanan Rp0 menurut
[dokumentasi resmi](https://docs.streamlit.io/deploy/streamlit-community-cloud). Ini bukan target
produksi layanan scoring atau klaim high availability.

Dependency file `src/dashboard/requirements.txt` mengacu pada dependency UI yang terpisah.
Community Cloud mencari file dependency pada direktori entrypoint lebih dulu; lihat
[aturan dependency](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).
Dengan demikian pyproject proyek yang memuat ML/Feast tidak menjadi dependency instalasi UI.
Versi langsung dipin; lock transitive dan base-image digest tetap pekerjaan reproducibility rilis.

Setelah push terbaru dan tiga job lint/test/dashboard-smoke lulus, operator dapat menyiapkan pilot:

| Pengaturan | Nilai |
|---|---|
| Repository | Agathahah/creditlens |
| Branch pilot | codex/m0-mentoring |
| Main file path | src/dashboard/app.py |
| Python | 3.12 |
| Secrets | Tidak diperlukan oleh dashboard ini |
| Dataset/model upload | Tidak diperlukan |
| Visibility | Publik untuk dashboard agregat yang telah direview |

Buka https://share.streamlit.io dan pilih pembuatan app dari repository GitHub. Operator melakukan
login, meninjau akses GitHub dan persyaratan layanan, kemudian mengisi koordinat tersebut.
Jika UI menampilkan izin repository privat yang lebih luas, tinjau kebutuhan itu; kode demo berada
pada repository publik. Jangan memasukkan POSTGRES_URL, token API, password database atau private
backup pada pengaturan app ini. Panduan platform:
[deploy app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy),
[status dan batasan](https://docs.streamlit.io/deploy/streamlit-community-cloud/status).

Deploy dari branch pengembangan adalah pilot yang dapat berubah setiap push. Catat head Git sebelum
menekan Deploy dan simpan URL yang benar-benar diberikan platform; jangan mengarang URL dari nama
proyek. Setelah diterapkan, branch tetap tidak boleh dipakai untuk mempublikasikan data pribadi.
Pilot ini tidak memerlukan merge/tag model. Stable dashboard release branch/tag menjadi keputusan
berikutnya setelah uji publik; jangan menggunakan tag v* karena workflow API lama masih terbuka.

## Verifikasi setelah URL tersedia

1. Buka URL sebenarnya dari jendela browser yang tidak login ke dashboard.
2. Ketiga tab dan selector cohort berfungsi; tidak ada traceback.
3. Judul/status menyatakan riset historis, model gagal dan test consumed.
4. Angka merujuk snapshot 23 September, bukan traffic layanan langsung.
5. Link laporan sumber dapat dibuka.
6. Tidak ada upload borrower, score button atau permintaan credential database.
7. Periksa logs setelah smoke; simpan timestamp, URL, revision dan hasil secara privat.

HTTP health/halaman saja tidak membuktikan semua UI bekerja; periksa interaksi nyata. Screenshot
untuk berbagi harus diambil sesudah UI berjalan dan menunjukkan tanggal/batasan. Dashboard cloud
menjalankan Streamlit sendiri; keberhasilan Docker CI merupakan bukti portability terpisah, bukan
bukti image Docker yang sama dijalankan Community Cloud.

## Rollback pilot

Jika app tidak merender setelah suatu push, hentikan publikasi tautan sampai perbaikan tervalidasi.
Pertahankan commit terakhir yang lolos. Gunakan commit revert terarah pada perubahan yang diketahui,
bukan reset/force-push. Uji kembali dan push hanya perubahan rollback yang direview; platform akan
mengambil versi source terbaru. Catat source revision sebelum/sesudah dan uji publik kembali.
Pemulihan dengan dependency yang belum terkunci penuh belum menjamin environment identik; jangan
menyebut rollback rehearsal lulus sebelum benar-benar dilakukan.

## Batas kesiapan model/API

Holdout baru masih MISSING_SOURCE. Kandidat AP 0,2197 tetap gagal gate 0,25 dan frozen test 2015
sudah consumed. Agar scoring dirilis, sumber baru harus lolos provenance/rights/as-of/event timing,
split dikunci dan kandidat lulus evaluasi independen. Setelah itu bundle validator/parity,
probability-only API, release manifest, CI model, dependency lock API, smoke/load, monitoring dan
rollback perlu dibuktikan. Tidak mengubah protokol atau menurunkan gate demi publikasi portfolio.
