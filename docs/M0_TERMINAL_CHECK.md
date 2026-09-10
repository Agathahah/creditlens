# Memeriksa hasil pemulihan mart

2026-09-10. Pemeriksaan opsional setelah Codex menyelesaikan recovery. Latihan mendalam tetap ditunda sampai akhir.

## Bila masih berada di psql

Lokasi: prompt `creditlens=>`. Tidak perlu keluar atau membuka koneksi baru. Jalankan:

```sql
SELECT COUNT(*) FROM mart.final_features;
```

Tujuan: memeriksa bahwa tabel akhir sudah terisi. Dampak: hanya membaca. Hasil yang diharapkan setelah ingestion dan rebuild 10 September: `2260668`. Angka sebelumnya `1599982` adalah hasil recovery mart sebelum ingestion dilengkapi. Jika hasil berbeda atau error, catat waktu dan output; jangan mengulang rebuild sebagai percobaan.

Untuk memeriksa pengaturan transaksi sebelum query: `SHOW transaction_read_only;`. Hasil yang diharapkan `on` pada koneksi audit. SQL menggunakan underscore dan tanda bintang biasa; jangan menyalin backslash escape Markdown.

## Bila berada di shell Terminal Mac

Prompt biasanya berakhir `%` atau `$`. Perintah pembuka koneksi bisa dijalankan dari direktori mana pun:

```bash
PGOPTIONS='-c default_transaction_read_only=on' psql -X -h localhost -p 5432 -U creditlens -d creditlens
```

Tujuan: masuk ke database yang diperbaiki dengan default transaksi baca-saja. Dampak: hanya membuka sesi koneksi. Harapan prompt `creditlens=>`, kemudian jalankan query di atas. Password bila diminta adalah password role database `creditlens`; masukkan lokal tanpa membagikannya.

Jika `psql: command not found`, gunakan executable yang sudah ditemukan pada Mac ini sebagai pengganti kata psql: `/opt/homebrew/opt/postgresql@16/bin/psql`. Tidak perlu instalasi ulang.

Untuk keluar dari psql gunakan `\q` lalu Enter. `creditlens->` berarti input belum selesai pada prompt standar; Control+C membatalkan input tertunda sebelum mencoba lagi.

## Apakah perlu memanggil Codex lagi?

Tidak selama bekerja pada task Codex Desktop ini. Kirim hasil/error atau instruksi lanjutan di percakapan yang sama. Jangan mengetik `codex`, `dbt build`, atau perintah shell di prompt psql. Recovery sudah dikerjakan; tidak perlu menjalankan ulang perintah mutation untuk memeriksa hasil.

Perintah pemeriksaan ini tidak menjadi syarat melanjutkan diagnosis Codex. Kontribusi menjalankan query bisa dicatat jika Agatha mengirim hasilnya; tidak otomatis dianggap penguasaan SQL.
