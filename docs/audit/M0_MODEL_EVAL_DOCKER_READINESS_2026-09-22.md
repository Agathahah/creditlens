# M0 — kesiapan evaluasi model dan image API

Pemeriksaan 22 September 2026. Ini audit kode dan prasyarat lokal, bukan hasil evaluasi model atau uji image.

Pembaruan setelah pemeriksaan: `.dockerignore` allowlist ditambahkan pada worktree Codex dan disalin ke checkout `~/Documents/creditlens` atas permintaan pengguna. Isinya membatasi konteks ke `pyproject.toml`, `README.md`, `src/` dan Dockerfile API, dengan pengecualian tambahan untuk berkas Python terbangun dan `.env` di bawah `src/`. Docker daemon belum berjalan, jadi perilaku build nyata belum diuji. Tabel berikut mencatat kondisi **sebelum** perbaikan tersebut.

Pembaruan uji lokal berikutnya: Docker Desktop melaporkan server 29.0.1. Build image `creditlens:m0-smoke-20260922` dari checkout `~/Documents/creditlens` berhasil pada arsitektur `arm64`; konteks yang ditransfer 221,13 kB dan ukuran image menurut `docker image inspect` 966.707.006 byte. Container uji hanya dibuka pada `127.0.0.1:18000`, tanpa model/DB. `GET /health` memberi HTTP 200 dengan `model_loaded=false`, `explainer_loaded=false`; `POST /predict` memberi HTTP 503 dengan pesan `No scoring model is loaded.` Container telah dihentikan dan dihapus, image uji masih lokal. Build memasang versi dependensi terbaru sesuai rentang `pyproject.toml` dan menarik paket besar termasuk `nvidia-nccl-cu13`; hasil ini adalah uji kemasan, bukan evaluasi atau bukti kesiapan rilis. Keterangan daemon pada paragraf sebelumnya adalah kondisi sebelum uji ini.

Setelah melihat ruang host turun dari sekitar 16 GiB menjadi 8,6 GiB, image uji tersebut dihapus. Cache build yang tercatat 0 B sebelum uji dibersihkan dengan `docker builder prune --force`; penggunaan Docker kembali ke 17 image dan cache 0 B seperti sebelum build. Ruang host terbaca sekitar 11 GiB segera sesudah pembersihan; tidak ada image lama, container lain, atau volume proyek yang dihapus. Pernyataan "image uji masih lokal" pada paragraf di atas mencatat keadaan **sebelum** pembersihan ini.

## Bukti

| Pemeriksaan | Hasil | Implikasi |
|---|---|---|
| Model lokal | Tidak ada `models/*.joblib` di worktree Codex maupun checkout `~/Documents/creditlens` | `make eval` dan evaluator bawaan belum memiliki artefak untuk dimuat |
| Input evaluator | `src/ml/evaluate.py` memuat `models/xgboost_credit.joblib`, lalu membaca seluruh `mart.final_features` dari PostgreSQL | Perintah evaluasi memerlukan model dan database yang cocok; belum ada snapshot/test manifest berversi |
| Preprocessing | `src/features/features.py` menghitung median dan kode kategori pada seluruh data sebelum split train/test; fitur mencakup variabel yang belum dibuktikan tersedia pada waktu prediksi | Metrik dari jalur lama belum layak menjadi bukti mutu rilis |
| CI | `eval-gate` hanya berjalan setelah push ke `main`, tetapi job itu tidak mengambil artefak model atau menyediakan data/database evaluasi | Kelulusan PR tidak membuktikan gate model; push ke `main` saat ini berisiko menghasilkan gate gagal |
| Image API | `infra/docker/Dockerfile.api` memasang kode dan dependensi serta menetapkan `MODEL_PATH`, tetapi tidak menyalin model | Build image saja tidak membuat scoring siap |
| Kesiapan API | `GET /health` mengembalikan HTTP 200 dengan `model_loaded=false` jika model tidak ada; `POST /predict` membalas 503 | Pemeriksaan status HTTP saja dapat memberi kesan keliru bahwa API siap |
| Build context | Tidak ada `.dockerignore` pada kedua checkout; `.gitignore` tidak membatasi Docker build context | Jangan menjalankan `docker build .` dari checkout yang berisi data mentah, backup dan `.env` sebelum context dibatasi |
| Docker lokal | CLI tersedia, daemon tidak tersambung saat pemeriksaan | Build lokal belum dapat dijalankan |
| Kapasitas | Sekitar 16 GiB tersedia pada volume data saat pemeriksaan | Penggunaan disk build/dependensi perlu dipantau; angka ini bukan bukti cukup untuk seluruh pipeline |

## Keputusan operasional saat ini

Belum menjalankan `make eval`, training penuh, `docker build`, `docker compose up`, atau tag/release. Audit ini berada dalam lingkup diagnosis M0. Dataset tetap privat, dan kecocokan hash file tidak menyelesaikan hak penggunaan atau tanggal snapshot outcome.

Perintah baca-saja yang dapat dijalankan dari terminal awal:

```sh
cd ~/Documents/creditlens
pwd
git status -sb
df -h .
find models -maxdepth 1 -name '*.joblib' -print
test -f .dockerignore && echo 'Docker context dibatasi' || echo 'Docker context belum dibatasi'
docker info --format '{{.ServerVersion}}'
```

Saat ini `find` diperkirakan tidak menampilkan model dan `docker info` gagal sampai Docker Desktop dijalankan. Keduanya pemeriksaan, bukan instruksi untuk memulai training/build sekarang.

## Gerbang sebelum evaluasi dan build yang bermakna

1. Tutup keputusan hak penggunaan demo publik atau pilih data lain; batasi klaim pada outcome retrospektif jika as-of tidak dapat dibuktikan.
2. Tetapkan cohort dan whitelist fitur berdasarkan ketersediaan pada waktu penggunaan; catat denominator, exclusion, term/vintage dan prevalensi.
3. Bekukan train/validation/test manifest sebelum tuning; fit transform hanya pada train dan simpan bersama model dalam bundle berversi. Pisahkan test dari pemilihan model/threshold.
4. Evaluasi kandidat pada input eksplisit yang identik dengan bundle; simpan checksum, metrik, kalibrasi, analisis galat dan batas klaim. Jangan memakai ambang PR-AUC lama sebagai satu-satunya bukti.
5. Buat `.dockerignore`; ikat image ke bundle yang dievaluasi dan ubah readiness agar gagal bila bundle hilang, rusak atau tidak kompatibel. Uji score fixture yang sama pada batch dan HTTP, termasuk image baru dan rollback.
6. Setelah semua gerbang lulus dan implementasi tahap berikutnya disetujui, susun perintah rilis yang menunjuk manifest, model dan image digest konkret. Jangan menganggap build atau HTTP 200 pada `/health` sebagai penerimaan rilis.

9Router adalah proxy/routing untuk permintaan model bahasa dari alat coding dan provider AI eksternal. API CreditLens yang diperiksa melakukan inferensi model lokal melalui `CreditPredictor`; ia tidak memanggil 9Router. Komponen itu tidak diperlukan untuk evaluasi model, build image, atau endpoint scoring saat ini.
