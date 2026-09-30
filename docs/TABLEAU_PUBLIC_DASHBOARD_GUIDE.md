# Dashboard Tableau Public: kualitas portofolio CreditLens

## Tujuan dan status

Dashboard ini menceritakan kualitas data pinjaman yang sudah dicairkan sebelum membahas alert risiko. Tableau Public adalah kanal **visualisasi agregat historis** untuk portofolio profesional. Tidak ada data peminjam individual, monitoring langsung, model scoring yang dirilis, atau keputusan kredit. Sumber angka ialah `docs/audit/PORTFOLIO_RESEARCH_SNAPSHOT.json` dengan profil data 23 September 2026.

Jalankan `python scripts/export_tableau_aggregates.py` dari akar repositori untuk menghasilkan empat CSV di `outputs/tableau-public/`. Workbook `CreditLens_Tableau_Public_Aggregates.xlsx` berisi empat tabel yang sama dan lembar pembuka. Setiap sheet punya grain sendiri: **Vintage tenor** = satu tahun penerbitan × tenor; **Cohort M1** = satu split eksperimen; **Validation M1** = satu kandidat model; **Profil vintage M1** = satu tahun eligible. Jangan menggabungkan semua sheet menjadi satu tabel atau menjumlahkan `eligible` bersama `loans`.

## Rancangan dashboard publik

Judul: **CreditLens | Kualitas portofolio pinjaman historis**. Subjudul: *2,26 juta pinjaman diterima; profil vintage dan kelengkapan outcome; alert pinjaman aktif belum tersedia*. Susun satu halaman dengan urutan berikut:

1. **Kartu cakupan:** 2.260.668 pinjaman, 1.345.350 outcome definitif, 915.318 outcome belum/tidak definitif (40,49% dari seluruh warehouse). Hitung `SUM(loans)`, `SUM(labeled)`, `SUM(unresolved)` dari **Vintage tenor**. Jangan menambahkan filter sebelum menyebut denominator kartu.
2. **Peta vintage × tenor:** warna `SUM(unresolved) / SUM(loans)`; label/petunjuk jumlah pinjaman. Kolom `issue_year`, baris `term_months`, filter kedua dimensi. Judul *Kelompok yang lebih baru memiliki outcome lebih sedikit yang definitif*. Warna menunjukkan kelengkapan data, bukan risiko kredit.
3. **Garis perkembangan:** `issue_year` vs `SUM(loans)` atau `SUM(unresolved)/SUM(loans)` dari **Vintage tenor**. Jangan menyebut perubahan ini sebagai kenaikan default karena outcome terbaru belum matang.
4. **Perbandingan eksperimen lama:** tiga batang Average Precision di **Validation M1**: konstan 0,1373, Logistic Regression 0,2016, bounded XGBoost 0,2046. Tambahkan catatan terpisah: XGBoost frozen test 2015 AP 0,2197 < gate historis 0,25; threshold lama menghasilkan nol prediksi positif. Grafik ini bukan evaluasi model monitoring pinjaman aktif.
5. **Kesimpulan dan keputusan:** data engineering dan profil vintage sudah dapat diaudit; calon skor lama ditolak; langkah berikutnya ialah panel pinjaman berkala dengan `as_of`, outcome bertanggal, dan holdout independen. Tulis **Riset historis • scoring ditahan** pada footer bersama tanggal sumber.

Gunakan warna hijau gelap untuk cakupan, teal untuk data definitif, amber untuk outcome belum definitif, dan merah hanya untuk gate model yang gagal. Grafik harus menampilkan denominator pada tooltip. Hindari pie chart atas tabel dengan grain berbeda.

## Publikasi lewat browser

1. Masuk sendiri ke [Tableau Public](https://public.tableau.com/) di browser; jangan membagikan kata sandi atau kode ke percakapan.
2. Pilih **Create / Web Authoring** dan unggah workbook agregat lokal atau satu CSV per sumber. Jika hanya satu sumber per workbook yang didukung alur unggah, mulai dengan `vintage_tenor.csv`; tambahkan sheet model sebagai sumber terpisah setelahnya.
3. Buat visual sesuai urutan di atas dan simpan sebagai **CreditLens | Kualitas Portofolio Historis**. Beri deskripsi yang menyatakan data diterima historis, belum ada alert aktif, dan skor lama gagal gate.
4. Buka URL hasil dari jendela privat/tanpa login. Periksa nilai kartu, tooltip, filter, footer, serta kemampuan mengunduh data. Karena Tableau Public bersifat publik, unggah hanya tabel agregat yang sudah diaudit.
5. Catat URL, tanggal, sumber, dan revisi kode di status proyek setelah pemeriksaan publik selesai. URL Tableau belum boleh dinyatakan aktif sebelum langkah ini lulus.

Dashboard Streamlit tetap menjadi narasi teknis lengkap untuk lineage SQL/dbt, kontrak API, keamanan, deployment, dan batas model. Tableau menonjolkan analisis portofolio untuk recruiter dan audiens risiko; keduanya menautkan keputusan rilis yang sama.
