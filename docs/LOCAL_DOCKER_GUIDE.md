# Panduan Docker lokal CreditLens

Status 23 September 2026: panduan ini memvalidasi packaging API tanpa menyatakan model siap
production. Kandidat M1 gagal gate rilis dan tidak boleh dipasang sebagai model API. Tanpa model,
`/health` tetap merespons HTTP 200 dengan `model_loaded=false`, sementara `/predict` harus 503.

## 1. Prasyarat

Jalankan dari root proyek:

```bash
cd /path/to/creditlens
docker info --format '{{.ServerVersion}}'
df -h .
```

Jika koneksi Docker gagal, buka Docker Desktop, tunggu status engine siap, lalu ulangi `docker info`.
Sisakan sedikitnya 8 GiB untuk smoke build. Kondisi terakhir menunjukkan sekitar 12 GiB kosong.

PostgreSQL Homebrew aktif memakai port 5432. Jangan menjalankan service `postgres` dari
`docker-compose.yml` secara bersamaan karena port akan bentrok. Stack lengkap juga memuat Airflow,
Grafana dan MLflow serta belum menjadi jalur rilis yang tervalidasi.

## 2. Pemeriksaan konteks build

`.dockerignore` memakai allowlist dan hanya mengirim metadata paket, source, serta Dockerfile API.
Dataset, `.git`, backup, notebook, model lokal dan credential tidak masuk build context.

```bash
test -f .dockerignore && echo 'Docker context dibatasi'
docker build --progress=plain \
  -f infra/docker/Dockerfile.api \
  -t creditlens-api:m1-smoke .
```

Build mengunduh base image dan dependency Python. Jangan menjalankan build jika ruang disk kembali
di bawah 8 GiB.

Smoke 23 September 2026 mengirim konteks 245,91 kB dan menghasilkan image 966.769.397 byte. Build
memerlukan sekitar sembilan menit karena `pip install .` memasang seluruh dependency proyek. Resolver
juga mengambil paket transitive besar termasuk NCCL. Untuk release, buat dependency set khusus API,
pin versi/lock file dan verifikasi ulang ukuran serta software bill of materials.

## 3. Smoke test API tanpa model

Pastikan port 8000 tidak sedang dipakai:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Jika tidak ada output, jalankan container:

```bash
docker run --rm -d \
  --name creditlens-api-smoke \
  -p 8000:8000 \
  creditlens-api:m1-smoke

docker logs creditlens-api-smoke
curl -sS http://localhost:8000/health | python -m json.tool
```

Hasil yang diharapkan saat ini:

```json
{
  "status": "ok",
  "model_loaded": false,
  "explainer_loaded": false
}
```

Verifikasi `/predict` menolak scoring tanpa model:

```bash
curl -i -sS -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"applicant_id":"smoke-local","features":{"annual_inc":60000}}'
```

Respons yang benar adalah HTTP 503 dengan pesan bahwa model belum dimuat. HTTP 200 dari `/health`
belum merupakan readiness model; perbaikan readiness adalah bagian desain M2/M3.

## 4. Hentikan dan bersihkan smoke test

```bash
docker stop creditlens-api-smoke
docker image inspect creditlens-api:m1-smoke --format '{{.Id}} {{.Size}}'
docker image rm creditlens-api:m1-smoke
docker builder prune --filter 'until=24h'
df -h .
```

Perintah `docker builder prune` hanya menghapus cache build yang tidak dipakai dan berumur lebih dari
24 jam. Jangan gunakan `docker system prune --volumes`; volume dapat menyimpan database lokal.

## 5. Tentang Docker Compose

Tinjau konfigurasi tanpa membuat container:

```bash
docker compose config --services
docker compose config > .local-backups/docker-compose-resolved.yml
```

Jangan menjalankan `docker compose up -d` pada kondisi sekarang karena:

1. service PostgreSQL meminta host port 5432 yang sudah dipakai PostgreSQL Homebrew;
2. database container baru tidak berisi dataset CreditLens aktif;
3. Airflow memerlukan setup database dan validasi terpisah;
4. Grafana memakai image `latest`, sehingga build belum reproducible;
5. model bundle yang lulus gate belum tersedia.

Compose baru dijalankan setelah dibuat override port/volume yang disetujui, image dipin ke digest atau
versi, secret dipindahkan dari default development, dan kebutuhan disk diperiksa ulang.

## 6. Urutan menuju API yang dapat melakukan scoring

1. Tetapkan outcome-as-of, horizon dan holdout independen baru.
2. Latih kandidat baru tanpa memakai test 2015 untuk pemilihan.
3. Luluskan gate model dan threshold dengan minimum support.
4. Buat bundle M2 berisi pipeline, schema, versi dan checksum.
5. Uji kesamaan skor raw → bundle → reload → HTTP.
6. Ubah readiness agar gagal bila bundle hilang/rusak/tidak kompatibel.
7. Build image yang mengacu pada bundle dan laporan evaluasi yang sama.
8. Jalankan smoke staging serta rollback sebelum deployment.

Sampai langkah tersebut selesai, Docker hanya membuktikan API dapat dipaketkan dan menolak scoring
ketika model tidak tersedia.
