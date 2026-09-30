# CreditLens — jalur demo dan kesiapan produksi

Tanggal keputusan/persiapan: 29 September 2026. Permintaan melanjutkan proyek menuju produksi
mencakup persiapan lokal API, demo agregat dan kriteria rilis berikut. Ini belum menjadi bukti
model valid atau layanan sudah dioperasikan. Eksperimen M1 baru mengikuti scope yang telah disetujui.

## Status push yang diverifikasi

GitHub PR #14 menerima head `61c960c` dan checkout lokal cocok (0/0). Pada
[run 36535113262](https://github.com/Agathahah/creditlens/actions/runs/36535113262), lint/typecheck
lulus dan application tests melaporkan 146 passed, 4 skipped, 7 warnings. Coverage agregat 89%
termasuk file tes src. Model Evaluation Gate dan Build Docker Image lama skipped. PR tetap
draft/open. Penambahan job Docker dashboard selanjutnya belum dipush/diuji remote.
Runbook pilot: [DASHBOARD_RELEASE_RUNBOOK.md](DASHBOARD_RELEASE_RUNBOOK.md).

## Produk yang dapat ditampilkan sekarang

Dashboard Streamlit baca-saja memperlihatkan agregat dari laporan M1 yang sudah dipublikasikan:
cohort/vintage, distribusi label, pembanding validation, hasil test historis, dan keterbatasan.
Snapshot memiliki tanggal laporan dan asal angka. Tidak memuat loan ID, data borrower, credential,
model joblib, prediksi baru atau sambungan database. Menampilkan angka tersimpan tidak membuka
ulang frozen test. Halaman ini belum merupakan monitoring layanan aktif.

Pilih Streamlit untuk demo Python inti. Tableau/Power BI merupakan opsi untuk analisis bisnis,
bukan syarat lulus model/API. Grafana yang ada lebih sesuai untuk monitoring operasional setelah
request/model_version dan label tertunda tercatat. Tidak ada kebutuhan LLM pada alur scoring
numerik saat ini. Ops Copilot berbasis dokumen memerlukan desain terpisah dan sumber terverifikasi.

## Tahap, prasyarat, dan bukti selesai

| Tahap | Pekerjaan | Bukti penerimaan | Status |
|---|---|---|---|
| Demo riset lokal | Dashboard agregat bertanggal; disclosure kandidat gagal | UI dapat dijalankan; interaksi split dan disclosure diuji; tidak ada data mentah | Implementasi lokal disiapkan |
| Persiapan API | `/live`, `/ready`, penolakan scoring bundle belum terverifikasi | Missing/legacy/incomplete → 503; fixture sintetis terverifikasi → 200; Docker probe memakai `/ready` | Implementasi lokal disiapkan |
| M1 sumber | Provenance, hak penggunaan, as-of, event/outcome timing, maturity dan fitur sebelum pricing | Manifest intake diterima; independensi loan ID dari seluruh split lama diperiksa | Tertahan: belum ada sumber diterima |
| M1 evaluasi baru | Kunci split, budget dan protokol sebelum fit; validation untuk pemilihan | Kandidat lulus gate yang dikunci; hasil/uncertainty/prevalence tersimpan; test baru dibuka sekali | Belum dimulai |
| M2 bundle | Simpan preprocessing + model + schema + library version + checksum + identitas laporan rilis | Validator artefak hilang/rusak/tidak kompatibel; raw→save→reload→HTTP parity; kategori baru/missing/invalid; probability-only contract | Belum selesai |
| M3 packaging/rilis | Dependency khusus API, transitive lock, image digest, model/data input CI eksplisit | Build reproducible; release terikat artefak evaluasi; invalid candidate gagal gate; dependency audit | Belum selesai |
| M3 staging | Target hosting, akses, batas biaya, resource, HTTPS dan secret; staging smoke/load/rollback | Bukti p50/p95/p99, error rate, resource; pemulihan image+bundle yang terukur | Target dan biaya belum dipilih |
| M4 operasi | Event inference berisi run/model_version, metrics/drift dan delayed-label join | Dashboard menunjukkan traffic nyata; alert dan recovery diuji; retention ditetapkan | Belum selesai |
| Pilot publik | Review semua bukti; demo pendidikan terbatas dengan batas penggunaan yang jelas | URL aktif dan smoke eksternal, logs/monitoring, rencana rollback; tanpa keputusan kredit otomatis | Belum dirilis |

Tidak menurunkan gate model berdasarkan hasil test yang gagal. Tidak menggunakan current/unresolved
sebagai label 0. Tidak menganggap dataset tahun terbit baru pasti snapshot outcome baru. Tidak
menganggap model retrospektif sebagai PD origination 36 bulan yang telah tervalidasi.

## Kontrak kesiapan API yang diimplementasikan

- `/live`: HTTP 200 saat proses dapat menjawab.
- `/health`: kompatibilitas status artefak, dapat 200 ketika model tidak ada.
- `/ready`: HTTP 503 kecuali predictor tersedia, schema fitur ada, dan bundle ditandai terverifikasi
  oleh jalur internal yang terpercaya. Explain opsional memiliki ketersediaan sendiri.
- `/predict` dan `/explain`: menolak dengan 503 bila kontrak bundle belum dipenuhi.
- Loader artefak legacy **tidak** mengesahkan bundle: `bundle_verified` tetap false. Saat ini hanya
  tes menyuntikkan fixture sintetis terverifikasi. Tidak tersedia model real yang dilayani.

Flag internal tersebut adalah pengaman transisi, bukan validator bundle lengkap. Implementasi M2
harus memverifikasi manifest, checksum, schema, runtime compatibility, transform parity dan bukti
kelulusan evaluasi sebelum menandai registry siap. Test sintetis membuktikan kontrak software saja.
Kontrak API lama masih memuat `approved` dan tier; rilis demo mendatang perlu endpoint probability-only
sesuai keputusan tidak memakai threshold keputusan kredit. Tidak mengaktifkan endpoint lama untuk
keputusan pinjaman nyata.

## Menjalankan dashboard lokal

Dari root proyek, gunakan environment khusus agar paket UI tidak mengubah Conda base:

```bash
python -m venv .local-backups/dashboard-venv
.local-backups/dashboard-venv/bin/python -m pip install \
  -r infra/docker/requirements.dashboard.txt pytest
.local-backups/dashboard-venv/bin/python -m pytest tests/test_dashboard.py -q
.local-backups/dashboard-venv/bin/python -m streamlit run src/dashboard/app.py \
  --server.address=127.0.0.1 --browser.gatherUsageStats=false
```

Buka `http://localhost:8501`. Hentikan dengan Ctrl+C. Dependensi UI langsung dipin pada versi yang
diuji; lock transitive dan pin base-image digest masih menjadi pekerjaan rilis. Data snapshot yang
ditampilkan bertanggal 23 September 2026; status database/API terkini tidak diambil otomatis.

## Docker dashboard: setelah kapasitas cukup

Pemeriksaan 29 September menemukan sekitar **4,8 GiB** bebas. Tidak dilakukan build Docker baru.
Kapasitas minimal 8 GiB berikut adalah aturan operasional lokal untuk smoke, bukan kebutuhan
production atau jaminan seluruh stack cukup. Periksa pemakaian lebih dulu:

```bash
df -h .
open -a Docker
docker info --format '{{.ServerVersion}}'
docker system df
lsof -nP -iTCP:8501 -sTCP:LISTEN
```

Jika Docker masih menyalakan engine, tunggu dan ulangi `docker info`. Jangan menjalankan build saat
kapasitas belum cukup. Jangan hapus volume, backup, dataset atau direktori PostgreSQL untuk membuat
ruang. Setelah ruang memadai dan port 8501 kosong:

```bash
docker build -f infra/docker/Dockerfile.dashboard -t creditlens-dashboard:research .
docker run --rm -d --name creditlens-dashboard-smoke \
  -p 127.0.0.1:8501:8501 creditlens-dashboard:research
docker logs creditlens-dashboard-smoke
curl -i http://127.0.0.1:8501/_stcore/health
docker inspect --format '{{.State.Health.Status}}' creditlens-dashboard-smoke
```

Health probe dapat awalnya `starting`; tunggu sebelum memeriksa ulang. HTTP 200 probe memeriksa
server Streamlit; validitas angka/disclosure diuji melalui tes aplikasi. Buka halaman dan periksa
ketiga tab, lalu hentikan hanya container smoke ini:

```bash
docker stop creditlens-dashboard-smoke
```

Dockerfile dashboard menjalankan user non-root dan hanya menyalin kode UI serta snapshot agregat.
Allowlist konteks tidak mengikutkan data raw, backup atau notebook. Docker build/dashboard container
belum diuji pada perubahan ini; jangan menyebutnya lulus sampai perintah tersebut berhasil.

## Sebelum merge/tag/deployment

CI tag lama masih memanggil `/health` dan belum memeriksa manifest release. Gate main lama belum
memiliki input model/data eksplisit. Kedua jalur perlu diperbaiki dan tes negatif ditambahkan sebelum
mengandalkan release otomatis. Keberhasilan dua job PR bukan izin melewati dependensi tersebut.

Demo dashboard dapat dirilis terpisah dari model setelah review disclosure, hak publikasi ringkasan,
hosting, biaya dan artefak konkret. Layanan scoring publik tetap menunggu bukti model dan bundle.
