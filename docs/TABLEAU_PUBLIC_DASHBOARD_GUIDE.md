# Tableau Public — dashboard kualitas portofolio CreditLens

Status 6 Oktober 2026: workbook `creditlens` sudah diterbitkan dan halaman dashboard publik telah terlihat dari tautan Share. [Buka dashboard CreditLens di Tableau Public](https://public.tableau.com/app/profile/agatha.silalahi/viz/creditlens/CreditLensPortofoliodanBuktiModel). Verifikasi dilakukan pada browser yang sedang masuk akun; akses tanpa login belum diuji secara terpisah. Dashboard memuat enam worksheet: tiga KPI, heatmap kematangan outcome, tren vintage menurut tenor, dan AP validation 2014. Filter tahun/tenor diuji pada 2018/36 bulan lalu dikembalikan ke All. Hasilnya 344.671 pinjaman, 41.272 outcome definitif, 303.399 outcome belum definitif dan 88,0% pada heatmap. Sumber model adalah agregat terpisah tanpa join ke warehouse.

Dashboard ini menyajikan pinjaman historis yang sudah dicairkan. Alert untuk pinjaman aktif dan model scoring production belum tersedia. Publikasi dashboard tidak mengubah keputusan menahan scoring. Bukti lisensi/izin redistribusi sumber LendingClub masih perlu diselesaikan; status terbit tidak berarti persoalan hak penggunaan telah terverifikasi. Data publik pada workbook berupa agregat, tanpa baris/ID pinjaman atau artefak model.

## 1. Temukan berkas di Mac

Dari Terminal, jalankan dari akar repositori:

```bash
cd "$HOME/Documents/creditlens"
pwd
ls -lh outputs/tableau-public/*.csv
ls -lh .local-backups/outputs/creditlens_20260930_tableau/*.xlsx
```

Empat CSV agregat dibuat ulang dengan `python scripts/export_tableau_aggregates.py`. Workbook Excel lokal `CreditLens_Tableau_Public_Aggregates.xlsx` merangkum sumber dan definisinya. Mulai workbook baru dari halaman profil bila belum ada editor CreditLens yang tersimpan. Sheet Excel `Vintage tenor` sepadan dengan `vintage_tenor.csv` dan `Validation M1` sepadan dengan `m1_validation.csv`. CSV tetap tersedia bila unggahan Excel gagal. Jangan pilih berkas sementara Excel yang namanya diawali `~$`.

| Berkas/sheet | Satu baris berarti | Kegunaan |
|---|---|---|
| `vintage_tenor.csv` | Satu tahun penerbitan × tenor, seluruh pinjaman diterima dalam warehouse | KPI, heatmap, tren dan filter |
| `m1_cohorts.csv` | Satu split eksperimen lama | Tabel train/validation/test historis |
| `m1_validation.csv` | Satu kandidat model pada validation 2014 | Grafik tiga kandidat |
| `m1_vintage_profile.csv` | Satu vintage eligible eksperimen lama | Profil sampel M1, terpisah dari warehouse |

**Jangan membuat join** antara empat sumber itu. Populasi dan grain berbeda; join dapat menggandakan hitungan.

## 2. Hubungkan data di browser

1. Dari halaman profil seperti pada tangkapan layar, klik tombol biru **Create** di kanan, lalu pilih **Create a Viz** (nama menu dapat ditulis **Create a Viz** atau **Viz**). Menu **Create** pada bilah atas juga dapat digunakan. Ini membuka editor workbook baru; angka `Data Sources 0` pada profil tidak perlu diubah lebih dulu.
2. Pada dialog **Connect to Data**, buka tab **Files**, lalu klik **Upload from Computer**. Di jendela pemilih berkas Mac, tekan `Command`+`Shift`+`G`, tempel path lengkap berikut, tekan Return, lalu pilih **Open**:

   ```tex
   /Users/agathasilalahi/Documents/creditlens/.local-backups/outputs/creditlens_20260930_tableau/CreditLens_Tableau_Public_Aggregates.xlsx
   ```

   Lokasi `.local-backups` tersembunyi di Finder; path lengkap menghindari salah pilih. Jangan pilih `~$CreditLens_Tableau_Public_Aggregates.xlsx`, data mentah, database, atau backup. Jika editor langsung membuka kanvas tanpa dialog, gunakan **Connect to Data** atau **New Data Source** → **Files** → **Upload from Computer**.
3. Tunggu sampai halaman **Data Source** menampilkan nama workbook Excel dan daftar sheet di panel kiri. Nama sheet yang diharapkan: `Baca dulu`, `Vintage tenor`, `Cohort M1`, `Validation M1`, dan `Profil vintage M1`. Unggahan ini membuat sumber dalam editor; belum berarti visualisasi CreditLens sudah dipublikasikan.
4. Seret **Vintage tenor** saja ke area tengah bertuliskan **Drag tables here to create a data model**. Jangan seret sheet Excel lain ke model yang sama; grain dan populasi berbeda. Pratinjau seharusnya menunjukkan **21 baris data** dengan field `issue_year`, `term_months`, `loans`, `labeled`, `unresolved`, `adverse`, dan `non_adverse`. Jika unggahan Excel gagal, mulai workbook baru dengan **Connect to Data → Files → Upload from Computer** dan pilih `outputs/tableau-public/vintage_tenor.csv`.
5. Pastikan tipe data: `issue_year` dan `term_months` dapat diperlakukan sebagai *dimension* diskrit; kolom jumlah sebagai *number*. `evidence_date` adalah tanggal bukti, bukan tanggal tiap pinjaman.
6. Buka **Sheet 1** di bagian bawah. Ubah nama menjadi `01 | Cakupan portofolio`. Lanjutkan ke bagian 3 untuk visualnya.

Tableau mendukung unggahan CSV/XLSX langsung melalui tab Files di web authoring. Jika editor putih/kosong, jangan unggah berulang kali; coba muat ulang **hanya bila belum ada perubahan yang belum disimpan**. Jangan menganggap workbook editor sudah terpublikasi. Rujukan antarmuka: [panduan resmi Tableau untuk koneksi data di web](https://help.tableau.com/current/online/en-us/creator_connect.htm).

## 3. Buat empat visual

Layar acuan: worksheet sudah terbuka dan sumber `Vintage tenor` terlihat di panel **Data** kiri. Di Tableau, **Columns** menentukan arah mendatar, **Rows** arah tegak, dan kartu **Marks** mengatur warna, bentuk, teks, serta tooltip. Warna hijau berarti field **continuous**, bukan bukti bahwa field merupakan measure. Pada menu `Issue Year` yang ditunjukkan pada 6 Oktober 2026, opsi **Convert to Measure** membuktikan bahwa field sudah merupakan dimension. Pilih **Convert to Discrete** agar tahun tampil sebagai kategori; jangan memilih Convert to Measure. Periksa menu `Term Months` dengan cara sama: jika tertulis **Convert to Dimension**, pilih itu dahulu; jika tertulis **Convert to Measure**, dimension sudah benar. Jika tersedia **Convert to Discrete**, pilih untuk header kategori. Menu yang menawarkan **Convert to Continuous** berarti field sudah diskrit. Jangan ubah `Loans`, `Labeled`, atau `Unresolved` menjadi dimension.

### A. Kartu cakupan

Kartu cakupan adalah **tiga worksheet angka tunggal**, digabung sebagai satu kelompok pada dashboard:

1. Di worksheet yang terbuka, biarkan **Columns** dan **Rows** kosong. Pada kartu **Marks**, pilih **Text** dari menu `Automatic`, lalu tarik `Loans` dari panel kiri ke tombol **Text**. Pastikan pil menunjukkan `SUM(Loans)` dan tampil **2.260.668**. Klik dua kali **tab worksheet di bawah** untuk mengubah namanya menjadi `01a | Jumlah pinjaman`. Format angka sebagai bilangan bulat dengan pemisah ribuan jika masih tampil tanpa titik/koma.
2. Klik ikon **New Worksheet** di baris tab bawah (ikon lembar dengan tanda tambah). Pilih sumber `Vintage tenor` bila Tableau tidak memilihnya otomatis. Ulangi langkah tadi dengan `Labeled` → **Text**; judul `01b | Outcome definitif`; hasil **1.345.350**.
3. Buat worksheet ketiga dengan `Unresolved` → **Text**; judul `01c | Outcome belum definitif`; hasil **915.318**. Ketiga angka harus memenuhi `Labeled + Unresolved = Loans` saat belum ada filter.

Satu baris di sumber berarti **tahun penerbitan × tenor**, sehingga `SUM` menjumlahkan kelompok tanpa menghitung pinjaman dua kali. Angka ini jumlah pinjaman historis yang diterima, bukan portofolio aktif hari ini.

### B. Heatmap vintage × tenor

Buat **New Worksheet** bernama `02 | Kelengkapan outcome`. Tarik `Issue Year` ke **Columns** dan `Term Months` ke **Rows**. Keduanya harus menjadi header kategori, bukan `SUM(Issue Year)`/`SUM(Term Months)`. Pada menu `Automatic` di **Marks**, pilih **Square**. Lalu buka **Analysis → Create Calculated Field**, beri nama `Proporsi outcome belum definitif`, dan isi:

```text
SUM([unresolved]) / SUM([loans])
```

Klik **OK**, tarik field baru ke **Color**, serta `Loans` dan `Unresolved` ke **Tooltip**. Format field baru sebagai **Percentage** dengan 1–2 desimal. Kalkulasi menghasilkan pecahan 0–1; Tableau mengubah 0,880257 menjadi 88,03%. **Jangan** memakai `AVG(Unresolved Pct)` atau memformat kolom `Unresolved Pct` sebagai Percentage, sebab kolom itu sudah disimpan pada skala 0–100 dan rata-rata antarbaris tidak berbobot jumlah pinjaman. Judul yang dibaca audiens: *Kelengkapan outcome menurut tahun dan tenor*. Pada 2018/36 bulan, tooltip harus menunjukkan **344.671** pinjaman, **303.399** outcome belum definitif, dan sekitar **88,03%**. Warna ini menggambarkan outcome yang belum definitif, **bukan tingkat gagal bayar**.

### C. Tren vintage

Buat **New Worksheet** bernama `03 | Jumlah pinjaman menurut vintage`. Tarik `Issue Year` ke **Columns** dan `Loans` ke **Rows**; pastikan pil kedua menunjukkan `SUM(Loans)`. Pilih **Line** pada menu **Marks**. Satu titik berarti jumlah pinjaman pada satu tahun penerbitan, dijumlahkan lintas tenor. Jika garis tidak berurutan, urutkan `Issue Year` menaik. Jika label data diinginkan, buka **Marks → Label** dan aktifkan **Show mark labels**. Tambahkan `Term Months` ke **Filters** untuk melihat 36 atau 60 bulan. Grafik ini tidak menunjukkan jumlah pinjaman yang masih aktif hari ini.

### D. Hasil model historis

Grafik ini memakai **populasi dan sumber berbeda**. Buka menu **Data → New Data Source** (atau ikon sumber data bertanda tambah di toolbar) → **Files → Upload from Computer**. Unggah hanya CSV agregat berikut sebagai sumber kedua:

```text
/Users/agathasilalahi/Documents/creditlens/outputs/tableau-public/m1_validation.csv
```

Lalu buat **New Worksheet** bernama `04 | AP validation model` dan pastikan sumber `m1_validation` terpilih pada panel **Data** kiri. Tarik `Candidate` ke **Rows** dan `Average Precision` ke **Columns**; pil biasanya tampil `SUM(Average Precision)` karena ada satu baris per kandidat. Pilih **Bar** pada **Marks**, tarik `Average Precision` juga ke **Label**, dan format empat angka di belakang koma (bukan persen). Nilai validation 2014 harus: Constant **0,1373**, Logistic Regression **0,2016**, bounded XGBoost **0,2046**. Jika Tableau menampilkan 13,73%, 20,16%, 20,46%, formatnya persen; ubah ke angka desimal agar cocok dengan laporan.

Pada dashboard, tambahkan kotak teks terpisah: *XGBoost terpilih pada validation, tetapi AP frozen test 2015 = 0,2197 di bawah gate historis 0,25; threshold lama menghasilkan nol prediksi positif. Ini bukan model alert pinjaman aktif.* Jangan memasukkan angka frozen test sebagai batang keempat karena grafik ini khusus **validation**.

### Filter yang konsisten

Pada worksheet `02 | Kelengkapan outcome`, tarik `Issue Year` dan `Term Months` ke **Filters**; pilih semua nilai agar tampilan awal tidak mengecualikan baris. Dari menu tiap pil filter, pilih **Apply to Worksheets → All Using This Data Source**. Filter akan berlaku pada tiga kartu dan grafik tren yang memakai `Vintage tenor`, tetapi tidak pada grafik M1 yang memakai `m1_validation`. Di web authoring, kartu filter biasanya langsung tampil; bila tidak, pilih **Show Filter** dari menu pil. Untuk pemeriksaan, pilih 2018 dan 36 bulan: ketiga kartu harus menjadi **344.671**, **41.272**, **303.399**; heatmap sekitar **88,03%**. Kembalikan filter ke **All** sebelum menyusun dashboard utama.

## 4. Susun dan terbitkan dashboard

1. Klik ikon **New Dashboard** (ikon kisi dengan tanda tambah) pada baris tab bagian bawah; jika sulit ditemukan, gunakan menu **Dashboard → New Dashboard**. Ubah nama dashboard menjadi `CreditLens | Kualitas Portofolio Historis`.
2. Tambahkan objek **Text** untuk judul dan subjudul: *2,26 juta pinjaman diterima; outcome belum definitif 40,49%; scoring aktif ditahan*.
3. Pada panel **Sheets** kiri, seret `01a`, `01b`, dan `01c` ke baris atas; seret `02` dan `03` ke tengah; seret `04` dan kotak teks kesimpulan ke bawah. Jika satu sheet mengambil seluruh kanvas, seret sheet berikutnya sampai garis penempatan biru muncul di tepi sheet, lalu lepaskan. Bila ruang sempit, buat dua dashboard: `Portofolio` dan `Bukti Model`.
4. Tampilkan filter `issue_year` dan `term_months` hanya pada worksheet yang memakai sumber vintage-tenor. Setelah filter dipilih, kartu dan heatmap harus memakai denominator yang sama. Jangan menerapkan filter ini ke grafik model M1 karena populasinya berbeda.
5. Tambahkan footer: *Riset historis; profil 23 Sep 2026; pinjaman diterima saja; tidak ada skor pinjaman aktif. Sumber dan batas data: repository CreditLens.*
6. Di editor web, **Publish** menyimpan perubahan workbook publik; **Publish As...** membuat salinan baru. Workbook `creditlens` sudah diterbitkan pada 6 Oktober 2026. Gunakan tautan dashboard di awal panduan agar pengunjung langsung melihat dashboard lengkap, bukan worksheet angka tunggal. Periksa cakupan agregat dan hak publikasi setiap sumber sebelum menambahkan data baru. Halaman [Zenodo sumber yang ditelusuri](https://zenodo.org/records/11295916) belum memberikan bukti lisensi yang cukup jelas untuk menyimpulkan izin redistribusi. Workbook Tableau Public yang disembunyikan dari profil tetap dapat dilihat orang yang mengetahui URL. Lihat [FAQ Tableau Public](https://help.tableau.com/current/pro/desktop/en-us/public_faq.htm) dan [panduan simpan Tableau](https://help.tableau.com/current/pro/desktop/en-us/publish_workbooks_tableaupublic.htm).

## 5. Verifikasi dari luar akun

Buka URL visualisasi yang dihasilkan dari jendela privat/tanpa login. Periksa judul, empat visual, filter 2018/36 bulan, angka referensi, footer, dan apakah data yang dapat diunduh hanya agregat. Catat URL serta tanggal pemeriksaan di `PROJECT_STATUS.md` **setelah** halaman publik benar-benar terlihat. Jangan menyebut Tableau sudah terbit hanya karena file Excel ada atau halaman editor terbuka.

Untuk cerita teknis yang lebih lengkap, tautkan [dashboard Streamlit](https://creditlens-risk-evidence.streamlit.app/) di deskripsi Tableau: Streamlit memaparkan raw → staging → mart, eksperimen model, kontrak API, keamanan, dan status deployment. Lihat juga [scope pemantauan portofolio](PORTFOLIO_MONITORING_SCOPE_2026-09-30.md).
