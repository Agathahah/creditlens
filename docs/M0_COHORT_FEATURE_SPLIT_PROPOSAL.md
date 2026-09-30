# M0 — usulan cohort, fitur dan split evaluasi lokal

Disusun 22 September 2026 dari agregat baca-saja pada database lokal `creditlens`. Ini **usulan desain** untuk evaluasi retrospektif, belum cohort final, test yang dikunci, izin training, atau klaim kesiapan produksi. Tidak ada model yang dilatih dan tidak ada baris mentah yang disalin ke dokumen ini.

## Pertanyaan yang dapat dijawab data sekarang

Pada pinjaman **accepted**, tenor 36 bulan, terbit 2011–2015, seberapa baik atribut sumber yang tersedia dalam satu snapshot membedakan status akhir **Fully Paid** dari **Charged Off/Default** yang tercatat? Status lain tetap di denominator audit, tetapi tidak diberi label 0. Hasil hanya berlaku bagi cohort terpilih; belum probabilitas gagal bayar semua pemohon, belum PD horizon 12/24/36 bulan, dan belum uji prospektif pada waktu pengajuan.

Alasan memilih tenor dan vintage ini:

1. Tenor 36 bulan mengurangi perbedaan lama pengamatan terhadap tenor 60 bulan. Pada 2015, hanya 147 dari 283.173 pinjaman 36 bulan belum berstatus final (0,052%), sedangkan 45.402 dari 137.922 pinjaman 60 bulan belum final (32,919%). Ini **mengurangi**, bukan menghapus, seleksi akibat outcome yang belum teramati.
2. Tahun 2011–2015 menyediakan tiga blok waktu dengan kelas 0 dan 1 yang cukup besar. Tahun 2007–2010 mengandung dua status panjang di luar kebijakan kredit yang tidak termasuk target utama. Pada 2016–2018, bagian tanpa label final pada tenor 36 bulan meningkat tajam: 91.134/323.495, 191.868/320.419, dan 303.399/344.671.
3. Satu tenor membuat perbandingan baseline lebih sederhana; `term_months` menjadi konstan dan tidak perlu masuk model. Pilihan ini membatasi generalisasi ke pinjaman 60 bulan.

## Profil split yang diusulkan

Sumber: `raw.lc_loans` untuk tanggal terbit, tenor, status dan nilai kosong; agregat silang terhadap `mart.final_features` cocok pada hitungan tahun/tenor/label. Filter tenor menggunakan angka 36 yang diparse dari `term`. Transaksi SQL `BEGIN READ ONLY` dan `statement_timeout` 120 detik.

| Bagian berdasarkan `issue_date` | Semua | Fully Paid (0) | Charged Off/Default (1) | Status lain | Kandidat berlabel | Prevalensi label 1 |
|---|---:|---:|---:|---:|---:|---:|
| Train: 2011–2013 | 157.993 | 138.213 | 19.780 | 0 | 157.993 | 12,520% |
| Validation: 2014 | 162.570 | 140.255 | 22.315 | 0 | 162.570 | 13,726% |
| Test: 2015 | 283.173 | 240.894 | 42.132 | 147 | 283.026 | 14,886% |
| Total | 603.736 | 519.362 | 84.227 | 147 | 603.589 | 13,954% |

Prevalensi meningkat antarblok; hasil model harus dilaporkan per vintage dan dibandingkan dengan prediktor konstan berdasarkan prevalensi **train**. Angka test dilihat pada tahap desain untuk menilai cakupan label; setelah protokol disetujui, test tidak boleh digunakan untuk memilih model, transform, kalibrasi, fitur atau ambang keputusan. Jika protokol direvisi berdasarkan kinerja test, test itu dianggap sudah terpakai.

**Batas utama:** `issue_date` tidak menunjukkan waktu label tersedia. Satu snapshot status dapat mengandung outcome train yang baru diketahui setelah tanggal penerbitan test. Karena tanggal snapshot outcome dan event yang tervalidasi belum ada, split ini adalah *holdout menurut vintage penerbitan* untuk analisis retrospektif, bukan simulasi deployment historis yang bebas informasi masa depan. Semua `member_id` kosong, sehingga pemisahan peminjam antarbagian tidak dapat dijamin.

## Fitur awal yang diusulkan untuk diperiksa, belum disahkan

Prioritaskan atribut yang tampak berkaitan dengan aplikasi/riwayat kredit sebelum outcome: `annual_inc`, sumber `dti`, `revol_bal`, sumber `revol_util`, `total_acc`, `open_acc`, umur riwayat dari `earliest_cr_line` dan `issue_date`, sumber `delinq_2yrs`, `pub_rec`, `inq_last_6mths`, `home_ownership`, dan `purpose`. Nama dan nilainya ada pada snapshot, tetapi waktu tersedianya untuk setiap pinjaman belum dibuktikan. Karena itu, daftar ini hanya kandidat eksperimen retrospektif.

- Gunakan nilai sumber `dti`/`revol_util` atau bawa indikator missing secara eksplisit. SQL staging saat ini mengubah NULL menjadi 0. Dalam cohort usulan, raw menunjukkan dua `dti` kosong pada blok test dan nol pada train/validation. Imputasi harus dipelajari dari train, bukan dari test.
- Ada dua `annual_inc <= 0` berlabel pada blok test dan nol pada train/validation. Putuskan validasi nilai tersebut sebelum evaluasi; jangan menyamakan rasio nol buatan dengan rasio nyata. Jumlah dua kelompok ini tidak diasumsikan berasal dari pinjaman yang sama.
- `loan_amnt` dan `term_months` dikeluarkan dari baseline awal: arti jumlah diminta versus jumlah yang disetujui belum dipastikan, sementara tenor sudah konstan. `int_rate`, `installment`, rasio installment/income, `grade`, `sub_grade` dan `verification_status` menunggu bukti tahap ketersediaan atau definisi scoring setelah penawaran.
- `addr_state` dipakai untuk pemeriksaan error/slice, belum sebagai prediktor awal karena merupakan proxy geografis. FRED belum punya vintage/publikasi yang sah untuk nilai as-of; SEC tidak punya join borrower. `loan_status`, `is_default`, pembayaran, recoveries, ID dan tanggal yang membocorkan outcome dilarang menjadi fitur.

## Pekerjaan sebelum M1 dapat dieksekusi

1. Putuskan cakupan penggunaan dataset untuk demo publik atau pilih sumber lain. Catat bahwa hak dari data asal dan tanggal snapshot outcome belum terverifikasi; file mentah tetap privat.
2. Tinjau definisi fitur sumber dan waktu tersedia. Jika ingin klaim prediksi pada tahap aplikasi, cari data dengan rekam waktu fitur dan outcome yang dapat membuktikannya; jika tidak tersedia, pertahankan klaim retrospektif terbatas.
3. Bekukan aturan eligibility, pengecualian, pilihan fitur dan split ini dalam manifest yang memuat hash sumber, versi SQL, ID/hash anggota per bagian, rentang tanggal, denominator, label counts dan prevalensi. Uji ID unik dan bagian saling lepas.
4. Implementasi M1, bila disetujui terpisah, harus membagi data **sebelum** `fit` preprocessing, membandingkan baseline konstan/Logistic Regression/XGBoost pada data sama, memakai validation untuk pemilihan dan mengunci test sampai keputusan selesai. Evaluasi akhir melaporkan diskriminasi, kalibrasi, uncertainty dan kesalahan menurut vintage/slice; hasil tidak boleh dipresentasikan sebagai rekomendasi kredit nyata.

Prinsip pemisahan sebelum preprocessing selaras dengan [panduan kebocoran data scikit-learn](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage). Pemilihan tahun, tenor dan batas klaim di atas adalah inferensi dari data CreditLens, bukan aturan dari sumber tersebut.
