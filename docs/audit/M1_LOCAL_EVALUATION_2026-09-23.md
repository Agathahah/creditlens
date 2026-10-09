# Laporan evaluasi M1 lokal — 23 September 2026

## Status keputusan

Implementasi dan evaluasi M1 lokal berbatas sumber daya telah selesai dalam ruang lingkup yang
disetujui. Kandidat **gagal gate rilis** dan tidak boleh disebut production ready. Frozen test 2015
sudah dibuka satu kali dan tidak boleh dipakai lagi untuk memilih fitur, model atau threshold.

## Cohort dan split

Populasi dibatasi ke pinjaman accepted tenor 36 bulan dengan `issue_date` 2011–2015. Target
retrospektif: Fully Paid=0, Charged Off/Default=1, status lain tanpa label.

| Split | Rentang issue | Semua baris | Eligible | Non-adverse | Adverse | Prevalence |
|---|---|---:|---:|---:|---:|---:|
| Train | 2011–2013 | 157.993 | 157.993 | 138.213 | 19.780 | 12,520% |
| Validation | 2014 | 162.570 | 162.570 | 140.255 | 22.315 | 13,726% |
| Frozen test | 2015 | 283.173 | 283.024 | 240.893 | 42.131 | 14,886% |

Exclusion terdiri dari 147 outcome unresolved dan dua `annual_inc <= 0`. Kedua pendapatan tidak
valid juga memiliki `dti` kosong. Checksum SHA-256 membership privat:
`fa4f814b3d434675c8c75cc1733f7fa8825e64c8efea251877ff358d298a9078`.

## Implementasi

- Split dibuat sebelum fit preprocessing.
- Median dan RobustScaler numerik serta one-hot encoder kategori hanya di-fit pada train.
- Kategori baru ditangani dengan `handle_unknown="ignore"`.
- Whitelist tidak memuat ID, outcome/status, pembayaran, recovery, pricing, grade atau tanggal mentah.
- Kandidat: prediktor konstan, Logistic Regression dan satu XGBoost kecil dengan maksimal dua thread.
- Artefak lokal berhasil disimpan, dimuat ulang dan menghasilkan skor probe yang identik.
- Enam tes kontrak M1 lulus. Ruff dan Black check lulus. `mypy` dan `isort` tidak tersedia pada
  environment Conda yang dipakai. Collection seluruh `src/ml/tests` tertahan karena dependency
  deklaratif `email-validator` belum terpasang pada environment tersebut.
- Warning `fork()` pada run pengguna berasal dari `n_jobs=2` pada Logistic Regression. Parameter
  yang tidak diperlukan itu dihapus; enam tes M1 kemudian lulus tanpa warning.

## Hasil validation

| Kandidat | Average precision | ROC-AUC | Brier |
|---|---:|---:|---:|
| Konstan | 0,1373 | 0,5000 | 0,1186 |
| Logistic Regression | 0,2016 | 0,6291 | 0,1158 |
| XGBoost kecil | 0,2046 | 0,6356 | 0,1155 |

Aturan pemilihan yang dikunci memilih AP validation tertinggi, dengan Brier lebih rendah sebagai
pemecah seri. XGBoost kecil terpilih, tetapi kenaikan AP terhadap Logistic Regression hanya sekitar
0,0030 dan belum membenarkan tambahan kompleksitas production.

## Frozen test

| Ukuran | Nilai | Interval bootstrap baris 95% |
|---|---:|---:|
| Average precision | 0,2197 | 0,2164–0,2221 |
| ROC-AUC | 0,6343 | 0,6315–0,6367 |
| Brier | 0,1241 | 0,1232–0,1249 |

Gate historis average precision minimal 0,25 gagal. Threshold 0,4829 dipilih pada validation karena
mencapai precision 100%, tetapi hanya didukung satu predicted-positive. Pada frozen test threshold
tersebut menghasilkan TN=240.893, FP=0, FN=42.131 dan TP=0. Operating point ini gagal dan ditolak.
Kode threshold untuk eksperimen berikutnya kini mensyaratkan minimal 100 predicted-positive dan 0,5%
baris validation. Perbaikan ini belum dievaluasi pada frozen test 2015 karena test tersebut sudah
terpakai.

## Batas kesimpulan

- Dataset hanya mencakup pinjaman accepted; selection bias terhadap aplikasi rejected tetap ada.
- Outcome as-of dan horizon belum diketahui, sehingga hasil bukan backtest origination point-in-time.
- Seluruh `member_id` kosong; overlap borrower dan bootstrap berkelompok tidak dapat diuji.
- Hak penggunaan publik artefak masih belum diselesaikan.
- Model lokal bukan model bundle API, bukan Docker release dan bukan keputusan kredit.

## Tindak lanjut wajib

1. Tetapkan prediction time, outcome-as-of dan horizon yang dapat dibuktikan.
2. Gunakan threshold dengan minimum support dan biaya false positive/false negative yang disetujui.
3. Sediakan holdout independen baru; test 2015 sudah consumed.
4. Lakukan error/drift analysis tanpa menyesuaikan keputusan pada test 2015.
5. Mulai M2 parity API/bundle hanya setelah kandidat baru memenuhi gate yang disetujui.
