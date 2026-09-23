# Keputusan sebelum eksperimen model berikutnya

Status 23 September 2026: **menunggu keputusan pengguna**. Dokumen ini bukan izin training baru.
Frozen test 2015 sudah terpakai dan tidak boleh digunakan untuk memilih fitur, model atau threshold.

## Mengapa holdout baru diperlukan

Eksperimen M1 memilih model dan threshold memakai validation 2014, lalu membuka test 2015 satu kali.
Hasil test menunjukkan gate AP 0,25 gagal dan threshold tidak menghasilkan predicted-positive.
Perubahan setelah melihat hasil tersebut memerlukan evaluasi independen agar metrik tidak bias.

Vintage 2016–2018 pada snapshot saat ini tidak otomatis dapat menjadi holdout:

| Vintage | Tenor | Semua baris | Outcome unresolved | Unresolved |
|---|---:|---:|---:|---:|
| 2016 | 36 bulan | 323.495 | 91.134 | 28,172% |
| 2017 | 36 bulan | 320.419 | 191.868 | 59,880% |
| 2018 | 36 bulan | 344.671 | 303.399 | 88,026% |
| 2016 | 60 bulan | 110.912 | 50.168 | 45,232% |
| 2017 | 60 bulan | 123.160 | 82.390 | 66,897% |
| 2018 | 60 bulan | 150.571 | 135.525 | 90,007% |

Menghapus seluruh unresolved dan memakai hanya loan yang sudah selesai akan memilih outcome
berdasarkan masa depan. Itu dapat menghasilkan evaluasi yang tidak mewakili aplikasi pada waktu
originasi.

## Pilihan sumber holdout

### A. Dataset baru dengan snapshot dan hak penggunaan yang jelas — rekomendasi

Syarat:

- tanggal snapshot/as-of terdokumentasi;
- status outcome atau riwayat pembayaran cukup untuk horizon yang dipilih;
- fitur dapat dibuktikan tersedia pada prediction time;
- hak penggunaan lokal/demo jelas;
- loan ID dapat direkonsiliasi tanpa mempublikasikan data mentah.

Konsekuensi: pekerjaan lebih lambat, tetapi dapat menghasilkan test independen yang sah.

### B. Rekonstruksi outcome dari riwayat pembayaran

Syaratnya adalah data performa bulanan atau tanggal kejadian yang cukup. Snapshot CreditLens saat ini
belum membuktikan bahwa informasi tersebut lengkap. Perlu audit kolom dan provenance sebelum desain.

### C. Evaluasi internal tanpa klaim test independen

Gunakan train/validation temporal pada periode lama untuk pengembangan software dan analisis error.
Hasil harus disebut validation research; tidak dapat menggantikan release gate atau bukti production.

## Keputusan yang memerlukan keterlibatan pemilik proyek

1. **Tujuan prediksi:** outcome buruk dalam 12, 24 atau 36 bulan, atau lifetime observed outcome?
2. **Prediction time:** saat aplikasi diajukan, saat pinjaman disetujui, atau setelah pricing ditetapkan?
3. **Sumber holdout:** memperoleh snapshot/dataset baru, merekonstruksi history, atau tetap pada riset internal?
4. **Tujuan threshold:** biaya false negative dan false positive, serta minimum jumlah keputusan yang harus didukung?
5. **Penggunaan produk:** demo pendidikan, portfolio, atau persiapan pilot terbatas?

## Rekomendasi teknis awal

- Prediction time: saat aplikasi, sebelum grade/pricing/keputusan kredit.
- Horizon: 36 bulan untuk cohort tenor 36 bulan, hanya bila tanggal kejadian dapat direkonstruksi.
- Model awal: Logistic Regression tetap menjadi baseline; XGBoost dipertahankan hanya bila kenaikan
  validation cukup besar dan konsisten.
- Threshold: dipilih dari validation dengan minimum support; jangan memakai constraint precision yang
  hanya didukung sedikit kasus.
- Test: satu holdout independen baru, dibuka setelah seluruh keputusan dikunci.

Setelah keputusan di atas disetujui, buat scope eksperimen baru sebelum training atau M2 API bundle.
