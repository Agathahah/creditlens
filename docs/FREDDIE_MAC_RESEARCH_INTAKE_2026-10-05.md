# Kandidat dataset baru: Freddie Mac SFLLD untuk studi hipotek terpisah

**Keputusan 5 Oktober 2026:** pengguna memilih studi riset hipotek terpisah. Ini tidak mengganti populasi LendingClub, tidak menjadi holdout bagi model M1 lama, dan tidak memberi izin rilis scoring CreditLens. Dataset Freddie Mac **belum diunduh, belum diaudit lokal, dan belum diterima untuk training**.

## Alasan memilih kandidat

[Single-Family Loan-Level Dataset (SFLLD)](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset) mencakup data origination dan kinerja bulanan pinjaman hipotek. Halaman resmi menyatakan kinerja tersedia sampai 31 Maret 2026, dan menyediakan sampel acak sekitar 50.000 pinjaman per vintage tahunan melalui akun Clarity. Format ini mendukung rancangan *loan-month* dengan tanggal observasi, saldo terutang dan status tunggakan, sehingga jauh lebih dekat dengan tujuan pemantauan setelah pencairan daripada status akhir tunggal di LendingClub. Ini tetap **hipotek AS**, bukan pinjaman konsumtif fintech Indonesia.

Kamus kolom resmi [Juli 2026](https://www.freddiemac.com/fmac-resources/research/pdf/file_layout_july_2026.xlsx) memuat `Loan Identifier` (posisi 20 di origination, posisi 1 di performance), `Period` (posisi 2), `Current Actual UPB` (posisi 3), `Current Loan Delinquency Status` (posisi 4), `Zero Balance Code` (posisi 9), dan `Zero Balance Effective Date` (posisi 10). Nama/posisi berasal dari dokumen, **belum diverifikasi terhadap file sampel**. Gunakan layout sesuai release yang benar-benar diunduh; jangan mengasumsikan header/format lama masih berlaku.

## Hak penggunaan dan batas publikasi

[Syarat SFLLD](https://capitalmarkets.freddiemac.com/crt/docs/pdfs/fre_terms_conditions_sflld.pdf) membolehkan penggunaan pribadi/internal untuk analisis kinerja hipotek dan hasil riset nonkomersial yang tidak mengungkap atau memungkinkan rekonstruksi data sumber. Distribusi dataset dan penggunaan/redistribusi komersial memerlukan perjanjian terpisah. Syarat juga melarang upaya identifikasi individu. Karena klausul distribusi *derived products* perlu ditafsirkan secara hati-hati, **jangan unggah baris sumber, ID pinjaman, ekstrak, atau turunan yang dapat direkonstruksi ke GitHub/Tableau/Streamlit**. Sebelum menerbitkan agregat hasil Freddie atau menjalankan layanan komersial, tinjau persyaratan lisensi untuk bentuk publikasi yang spesifik.

Pendaftaran Clarity dan penerimaan syarat dilakukan oleh pemilik akun sendiri. Jangan membagikan kredensial atau kode masuk. Fannie Mae menyediakan panel bulanan serupa, tetapi [syaratnya](https://capitalmarkets.fanniemae.com/credit-risk-transfer/fannie-mae-single-family-loan-performance-data) secara eksplisit membatasi distribusi dan penggunaan komersial eksternal; ini menjadi cadangan, bukan pilihan pertama. Data kompetisi Home Credit 2024 lebih dekat ke konsumen, tetapi [aturannya menyebut *Competition Use Only*](https://www.kaggle.com/c/home-credit-credit-risk-model-stability/rules), sehingga tidak cocok dijadikan dasar portfolio/API publik.

## Intake terbatas yang disarankan

1. Buka [halaman resmi Freddie Mac](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset) → **Access Historical Data** → daftar/masuk Clarity → baca dan setujui sendiri syaratnya → pilih tab **SFLLD Data**, bukan **CRT Data**. Bagian *Custom Download* dengan filter `Deal Name`, `Loss Type`, dan `Offering` berada di tab CRT dan bukan sumber studi ini. Pada **Standard Dataset Download by Year**, cari baris **2018** lalu klik **`sample_2018.zip`** pada kolom **Sample File**. Jangan pilih `historical_data_2018.zip` (Full Standard), `non_std_historical_data.zip`, atau `rpl_historical_data.zip` untuk intake awal. Sampel 2018 adalah satu vintage untuk uji format/kualitas, bukan train/validation/test yang sudah cukup.
2. Simpan ZIP di `~/Documents/creditlens-private/freddie/`, di luar Git. Catat URL resmi, release/cutoff, waktu unduh, nama file, byte size, SHA-256, dan syarat yang diterima. Jangan kirim file mentah ke chat.
3. Periksa nama member ZIP, format origination/performance, kolom dan tipe terhadap layout release tersebut; hitung ID unik, bulan pertama/akhir, duplikasi `(loan_id, period)`, missing periods, rentang delinquency/UPB, penutupan, serta perubahan data/koreksi. Jangan ekstrak semua file sebelum ukuran tak terkompresi diketahui.
4. Baru setelah intake lulus, tetapkan peristiwa target dan horizon bersama pemilik risiko. Rancangan awal yang **belum disetujui**: dari setiap loan-month aktif dengan status lancar pada `as_of`, peringatkan peralihan ke tunggakan berat dalam jendela berikutnya. Definisi tunggakan berat, horizon, satuan kapasitas analis dan kasus censoring belum final.
5. Siapkan split waktu baru dengan holdout independen dan aturan cutoff label, training preprocessing hanya dari train, baseline sederhana, kalibrasi, biaya false alert, serta audit subgroup. Jangan menggunakan test LendingClub 2015 atau modelnya sebagai kandidat Freddie.

## Perintah pemeriksaan awal setelah unduhan resmi

```bash
cd "$HOME/Documents/creditlens"
mkdir -p "$HOME/Documents/creditlens-private/freddie"
chmod 700 "$HOME/Documents/creditlens-private/freddie"
find "$HOME/Downloads" -maxdepth 1 -type f -iname 'sample_2018*.zip' -print
df -h "$HOME/Downloads"
```

Jika hasil `find` menunjukkan nama persis `sample_2018.zip`, pindahkan tanpa menimpa berkas yang sudah ada, lalu periksa metadata:

```bash
mv -n "$HOME/Downloads/sample_2018.zip" "$HOME/Documents/creditlens-private/freddie/"
export FREDDIE_SAMPLE="$HOME/Documents/creditlens-private/freddie/sample_2018.zip"
if [ -f "$FREDDIE_SAMPLE" ]; then
  df -h .
  stat -f '%N | %z bytes' "$FREDDIE_SAMPLE"
  shasum -a 256 "$FREDDIE_SAMPLE"
  unzip -l "$FREDDIE_SAMPLE" | tail -n 12
else
  echo 'File belum ditemukan; periksa nama/path'
fi
```

Perintah di atas hanya memeriksa metadata dan daftar isi ZIP. Menurut [FAQ resmi](https://www.freddiemac.com/fmac-resources/research/pdf/faq.pdf), sampel tahunan berisi satu file origination dan satu file kinerja bulanan untuk pinjaman yang sama. Jangan memaksa perintah pindah di atas bila nama unduhan berbeda, misalnya `sample_2018 (1).zip`; periksa dulu file yang sudah ada. Kirim hanya nama berkas, ukuran, SHA-256, release/cutoff dan daftar nama member ZIP; jangan kirim baris data pinjaman.

**Gate:** studi ini baru dapat menjadi *research prototype* setelah source intake dan hak penggunaan lulus. Scoring production untuk pinjaman fintech nyata tetap memerlukan panel milik operator, tujuan penggunaan yang sah, outcome bertanggal, evaluasi prospektif, integrasi API aman, monitoring, serta persetujuan bisnis/compliance.
