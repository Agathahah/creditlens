# Laporan smoke Docker API — 23 September 2026

## Ruang lingkup

Pengujian ini memeriksa packaging API tanpa memasang kandidat M1 yang gagal gate. Pengujian bukan
Docker release, deployment, benchmark beban atau bukti production readiness.

## Lingkungan dan hasil

| Pemeriksaan | Hasil |
|---|---|
| Docker Server | 29.0.1 |
| Dockerfile | `infra/docker/Dockerfile.api` |
| Build context | 245,91 kB; `.dockerignore` allowlist aktif |
| Image lokal | `creditlens-api:m1-smoke`, 966.769.397 byte |
| Waktu build | sekitar sembilan menit pada Mac ARM lokal |
| `GET /health` | HTTP 200; `model_loaded=false`, `explainer_loaded=false` |
| `POST /predict` | HTTP 503; `No scoring model is loaded.` |
| Cleanup | container dan image smoke dihapus; 3,705 GB build cache dihapus |
| Volume | tidak dihapus |

Hasil endpoint sesuai kondisi saat ini: aplikasi dapat dimulai tanpa artefak, health melaporkan model
tidak dimuat, dan scoring ditolak.

## Temuan packaging

`pip install .` memasang seluruh dependency proyek, termasuk training, dbt, monitoring, dashboard,
feature store dan explainability. Resolver mengambil versi terbaru yang memenuhi lower bounds serta
dependency transitive besar seperti NCCL. Akibatnya build lambat, image sekitar 967 MB, dan hasilnya
belum terkunci secara reproducible.

Sebelum release:

1. pisahkan dependency runtime API dari training/data tooling;
2. pin versi atau gunakan lock file serta base-image digest;
3. hasilkan software bill of materials dan scan dependency;
4. bind image ke model bundle/checksum yang sudah lulus gate;
5. ubah readiness agar gagal ketika bundle hilang, rusak atau tidak kompatibel;
6. ukur cold start, warm latency dan peak memory pada image final.

`docker-compose.yml` tidak dijalankan karena PostgreSQL Homebrew aktif memakai host port 5432 dan
stack lengkap belum tervalidasi. Tidak ada registry push atau deployment.
