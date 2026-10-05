# Tableau Public — dashboard kualitas portofolio CreditLens

Status 5 Oktober 2026: editor Tableau Public sudah memiliki koneksi Excel `CreditLens_Tableau_Public_Aggregates`. Kanvas data model masih kosong, tombol `Publish As...` masih tampil, dan **URL visualisasi publik belum ada/terverifikasi**. Dashboard ini menyajikan pinjaman historis yang sudah dicairkan. Alert untuk pinjaman aktif dan model scoring production belum tersedia. Data yang diunggah ke Tableau Public dapat dilihat orang lain; gunakan hanya tabel agregat di bawah, bukan data pinjaman, backup, atau artefak model.

## 1. Temukan berkas di Mac

Dari Terminal, jalankan dari akar repositori:

```bash
cd "$HOME/Documents/creditlens"
pwd
ls -lh outputs/tableau-public/*.csv
ls -lh .local-backups/outputs/creditlens_20260930_tableau/*.xlsx
```

Empat CSV agregat dibuat ulang dengan `python scripts/export_tableau_aggregates.py`. Workbook Excel lokal `CreditLens_Tableau_Public_Aggregates.xlsx` merangkum sumber dan definisinya. **Pada editor yang sudah terbuka, lanjutkan dari Excel yang telah tersambung; jangan unggah ulang.** Sheet Excel `Vintage tenor` sepadan dengan `vintage_tenor.csv` dan `Validation M1` sepadan dengan `m1_validation.csv`. CSV tetap tersedia bila Anda membuat workbook baru.

| Berkas/sheet | Satu baris berarti | Kegunaan |
|---|---|---|
| `vintage_tenor.csv` | Satu tahun penerbitan × tenor, seluruh pinjaman diterima dalam warehouse | KPI, heatmap, tren dan filter |
| `m1_cohorts.csv` | Satu split eksperimen lama | Tabel train/validation/test historis |
| `m1_validation.csv` | Satu kandidat model pada validation 2014 | Grafik tiga kandidat |
| `m1_vintage_profile.csv` | Satu vintage eligible eksperimen lama | Profil sampel M1, terpisah dari warehouse |

**Jangan membuat join** antara empat sumber itu. Populasi dan grain berbeda; join dapat menggandakan hitungan.

## 2. Hubungkan data di browser

1. Kembali ke tab **Edit | New Workbook**. Koneksi Excel `CreditLens_Tableau_Public_Aggregates` seharusnya sudah terlihat. Ini membuktikan koneksi file, belum membuktikan visualisasi sudah terbit.
2. Pada panel **Sheets** kiri, seret **Vintage tenor** ke area tengah bertuliskan **Drag tables here to create a data model**. Jangan seret sheet Excel lain ke model yang sama; grain dan populasi berbeda. Tunggu sampai pratinjau menunjukkan 21 baris dengan field `issue_year`, `term_months`, `loans`, `labeled`, `unresolved`, `adverse`, dan `non_adverse`. Jika Anda mulai dari workbook baru, gunakan **Connect to Data → Files → Upload from Computer** dan pilih `vintage_tenor.csv`.
3. Pastikan tipe data: `issue_year` dan `term_months` dapat diperlakukan sebagai *dimension* diskrit; kolom jumlah sebagai *number*. `evidence_date` adalah tanggal bukti, bukan tanggal tiap pinjaman.
4. Buka **Sheet 1** di bagian bawah. Ubah nama menjadi `01 | Cakupan portofolio`.

Tableau mendukung unggahan CSV/XLSX langsung melalui tab Files di web authoring. Editor Chrome sudah tampil saat pemeriksaan ulang. Jika nanti putih/kosong, jangan unggah berulang kali; coba muat ulang **hanya bila belum ada perubahan yang belum disimpan**. Jangan menganggap workbook editor sudah terpublikasi.

## 3. Buat empat visual

### A. Kartu cakupan

Pada sumber `vintage_tenor.csv`, gunakan `SUM(loans)`, `SUM(labeled)`, dan `SUM(unresolved)` sebagai tiga angka terpisah. Tanpa filter hasilnya harus **2.260.668**, **1.345.350**, dan **915.318**. Jika kartu tunggal sulit dibuat, buat tiga worksheet, masing-masing berisi satu measure di Marks → Text. Judul: *Jumlah pinjaman*, *Outcome definitif*, *Outcome belum definitif*.

### B. Heatmap vintage × tenor

Buat calculated field bernama `Proporsi outcome belum definitif`:

```text
SUM([unresolved]) / SUM([loans])
```

Format sebagai **Percentage, 1 decimal**. Tarik `issue_year` ke Columns, `term_months` ke Rows; pilih Marks → Square; taruh calculated field pada Color serta `SUM(loans)` pada Tooltip. Judul: *Kelengkapan outcome menurut tahun dan tenor*. Persentase ini mengukur kelengkapan label, **bukan tingkat gagal bayar**. Pada 2018/36 bulan, nilai referensi adalah 344.671 pinjaman dan 303.399 outcome belum definitif, sekitar 88,03%.

### C. Tren vintage

Tarik `issue_year` ke Columns dan `SUM(loans)` ke Rows; pilih Line. Tambahkan `term_months` sebagai filter. Judul: *Jumlah pinjaman historis menurut vintage*. Jika membuat garis kedua untuk proporsi belum definitif, beri sumbu dan judul terpisah agar jumlah dan persentase tidak tertukar. Data ini tidak menunjukkan jumlah pinjaman aktif saat ini.

### D. Hasil model historis

Klik **New Data Source**, pilih kembali koneksi Excel yang sama dan gunakan **Validation M1** sebagai satu-satunya tabel pada kanvas sumber kedua. Alternatif untuk workbook CSV: unggah `m1_validation.csv` sebagai sumber kedua. Buka worksheet baru; tarik `candidate` ke Rows dan `average_precision` ke Columns; pilih Bar dan tampilkan label angka empat desimal. Nilai validation 2014: Constant **0,1373**, Logistic Regression **0,2016**, bounded XGBoost **0,2046**. Tambahkan keterangan teks: *Kandidat XGBoost terpilih pada validation, tetapi AP frozen test 2015 = 0,2197 < gate historis 0,25; threshold lama menghasilkan nol prediksi positif. Ini bukan model alert pinjaman aktif.* Jangan mencampur angka test dengan batang validation.

## 4. Susun dan terbitkan dashboard

1. Klik **New Dashboard** di baris tab bagian bawah. Nama: `CreditLens | Kualitas Portofolio Historis`.
2. Tambahkan objek **Text** untuk judul dan subjudul: *2,26 juta pinjaman diterima; outcome belum definitif 40,49%; scoring aktif ditahan*.
3. Tarik kartu ke baris atas, heatmap dan tren ke tengah, hasil model dan kotak kesimpulan ke bawah. Bila ruang sempit, buat dua dashboard: `Portofolio` dan `Bukti Model`.
4. Tampilkan filter `issue_year` dan `term_months` hanya pada worksheet yang memakai sumber vintage-tenor. Setelah filter dipilih, kartu dan heatmap harus memakai denominator yang sama. Jangan menerapkan filter ini ke grafik model M1 karena populasinya berbeda.
5. Tambahkan footer: *Riset historis; profil 23 Sep 2026; pinjaman diterima saja; tidak ada skor pinjaman aktif. Sumber dan batas data: repository CreditLens.*
6. **Tahan tombol `Publish As...`** sampai hak publikasi agregat dari sumber LendingClub dipastikan. Halaman [Zenodo sumber yang ditelusuri](https://zenodo.org/records/11295916) belum menunjukkan lisensi yang cukup jelas untuk menyimpulkan izin redistribusi; unggahan Excel ke editor tidak menyelesaikan persoalan itu. Setelah hak penggunaan/publikasi dipastikan, periksa lagi bahwa workbook hanya berisi agregat dan tidak ada ID/baris pinjaman; kemudian terbitkan ke profil Tableau Public Anda. Tableau Public bersifat publik dan workbook/data dapat diunduh.

## 5. Verifikasi dari luar akun

Buka URL visualisasi yang dihasilkan dari jendela privat/tanpa login. Periksa judul, empat visual, filter 2018/36 bulan, angka referensi, footer, dan apakah data yang dapat diunduh hanya agregat. Catat URL serta tanggal pemeriksaan di `PROJECT_STATUS.md` **setelah** halaman publik benar-benar terlihat. Jangan menyebut Tableau sudah terbit hanya karena file Excel ada atau halaman editor terbuka.

Untuk cerita teknis yang lebih lengkap, tautkan [dashboard Streamlit](https://creditlens-risk-evidence.streamlit.app/) di deskripsi Tableau: Streamlit memaparkan raw → staging → mart, eksperimen model, kontrak API, keamanan, dan status deployment. Lihat juga [scope pemantauan portofolio](PORTFOLIO_MONITORING_SCOPE_2026-09-30.md).
