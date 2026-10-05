# Tableau Public — dashboard kualitas portofolio CreditLens

Status: rancangan dan sumber agregat tersedia; **URL Tableau belum diverifikasi**. Dashboard ini menyajikan pinjaman historis yang sudah dicairkan. Alert untuk pinjaman aktif dan model scoring production belum tersedia. Data yang diunggah ke Tableau Public dapat dilihat orang lain; gunakan hanya empat tabel agregat di bawah, bukan data pinjaman, backup, atau artefak model.

## 1. Temukan berkas di Mac

Dari Terminal, jalankan dari akar repositori:

```bash
cd "$HOME/Documents/creditlens"
pwd
ls -lh outputs/tableau-public/*.csv
ls -lh .local-backups/outputs/creditlens_20260930_tableau/*.xlsx
```

Empat CSV publik dibuat ulang dengan `python scripts/export_tableau_aggregates.py`. Workbook Excel lokal `CreditLens_Tableau_Public_Aggregates.xlsx` merangkum sumber dan definisinya. **Mulai Tableau dari `vintage_tenor.csv`** karena tabel ini menampung angka portofolio utama; `m1_validation.csv` ditambahkan nanti sebagai sumber data kedua. Bila browser meminta memilih file, gunakan path lengkap dari hasil `pwd`, lalu buka folder `outputs/tableau-public`.

| Berkas/sheet | Satu baris berarti | Kegunaan |
|---|---|---|
| `vintage_tenor.csv` | Satu tahun penerbitan × tenor, seluruh pinjaman diterima dalam warehouse | KPI, heatmap, tren dan filter |
| `m1_cohorts.csv` | Satu split eksperimen lama | Tabel train/validation/test historis |
| `m1_validation.csv` | Satu kandidat model pada validation 2014 | Grafik tiga kandidat |
| `m1_vintage_profile.csv` | Satu vintage eligible eksperimen lama | Profil sampel M1, terpisah dari warehouse |

**Jangan membuat join** antara empat sumber itu. Populasi dan grain berbeda; join dapat menggandakan hitungan.

## 2. Hubungkan data di browser

1. Masuk ke [Tableau Public](https://public.tableau.com/) dengan akun Anda, lalu buka **Create → Web Authoring**. Jika menu berubah, cari tindakan **Create a Viz** atau **New Workbook**.
2. Pada panel **Connect to Data → Files**, pilih **Upload from Computer** dan unggah `vintage_tenor.csv`. Tunggu sampai halaman Data Source menunjukkan 21 baris dengan field `issue_year`, `term_months`, `loans`, `labeled`, `unresolved`, `adverse`, dan `non_adverse`.
3. Pastikan tipe data: `issue_year` dan `term_months` dapat diperlakukan sebagai *dimension* diskrit; kolom jumlah sebagai *number*. `evidence_date` adalah tanggal bukti, bukan tanggal tiap pinjaman.
4. Buka **Sheet 1** di bagian bawah. Ubah nama menjadi `01 | Cakupan portofolio`.

Tableau mendukung unggahan CSV/XLSX langsung melalui tab Files di web authoring. Jika halaman **New Workbook** putih/kosong seperti yang terlihat pada Chrome saat pemeriksaan, jangan unggah berulang kali. Pastikan koneksi internet stabil, lalu coba muat ulang **hanya bila belum ada perubahan yang belum disimpan**; bila masih kosong, buka Tableau Public pada tab Chrome baru atau gunakan Tableau Desktop Public Edition resmi. Jangan menganggap workbook kosong itu sudah terpublikasi.

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

Tambahkan **data source baru** `m1_validation.csv`; buka worksheet baru. Tarik `candidate` ke Rows dan `average_precision` ke Columns; pilih Bar dan tampilkan label angka empat desimal. Nilai validation 2014: Constant **0,1373**, Logistic Regression **0,2016**, bounded XGBoost **0,2046**. Tambahkan keterangan teks: *Kandidat XGBoost terpilih pada validation, tetapi AP frozen test 2015 = 0,2197 < gate historis 0,25; threshold lama menghasilkan nol prediksi positif. Ini bukan model alert pinjaman aktif.* Jangan mencampur angka test dengan batang validation.

## 4. Susun dan terbitkan dashboard

1. Klik **New Dashboard** di baris tab bagian bawah. Nama: `CreditLens | Kualitas Portofolio Historis`.
2. Tambahkan objek **Text** untuk judul dan subjudul: *2,26 juta pinjaman diterima; outcome belum definitif 40,49%; scoring aktif ditahan*.
3. Tarik kartu ke baris atas, heatmap dan tren ke tengah, hasil model dan kotak kesimpulan ke bawah. Bila ruang sempit, buat dua dashboard: `Portofolio` dan `Bukti Model`.
4. Tampilkan filter `issue_year` dan `term_months` hanya pada worksheet yang memakai sumber vintage-tenor. Setelah filter dipilih, kartu dan heatmap harus memakai denominator yang sama. Jangan menerapkan filter ini ke grafik model M1 karena populasinya berbeda.
5. Tambahkan footer: *Riset historis; profil 23 Sep 2026; pinjaman diterima saja; tidak ada skor pinjaman aktif. Sumber dan batas data: repository CreditLens.*
6. Simpan/publikasikan ke profil Tableau Public Anda. Tableau Public bersifat publik dan workbook/data dapat diunduh; periksa isi sumber sebelum menekan Publish.

## 5. Verifikasi dari luar akun

Buka URL visualisasi yang dihasilkan dari jendela privat/tanpa login. Periksa judul, empat visual, filter 2018/36 bulan, angka referensi, footer, dan apakah data yang dapat diunduh hanya agregat. Catat URL serta tanggal pemeriksaan di `PROJECT_STATUS.md` **setelah** halaman publik benar-benar terlihat. Jangan menyebut Tableau sudah terbit hanya karena file Excel ada atau halaman editor terbuka.

Untuk cerita teknis yang lebih lengkap, tautkan [dashboard Streamlit](https://creditlens-risk-evidence.streamlit.app/) di deskripsi Tableau: Streamlit memaparkan raw → staging → mart, eksperimen model, kontrak API, keamanan, dan status deployment. Lihat juga [scope pemantauan portofolio](PORTFOLIO_MONITORING_SCOPE_2026-09-30.md).
