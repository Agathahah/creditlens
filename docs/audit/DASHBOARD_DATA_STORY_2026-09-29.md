# CreditLens — asal angka dan cerita data dashboard

Tanggal penyusunan: 29 September 2026. Profil database berasal dari pemeriksaan baca-saja pada
23 September 2026; label rollout berasal dari 22 September. Ini bukan refresh database live.

## Pertanyaan dan kegunaan

CreditLens menilai apakah data dan fitur pada tahap aplikasi cukup valid untuk mendukung model
risiko kredit. Dashboard menghubungkan cakupan data, kelengkapan outcome, rekonsiliasi warehouse,
evaluasi dan keputusan rilis. Tim data dapat melihat batas dataset; tim risiko dapat menilai
benchmark; tim engineering dapat menelusuri alasan suatu artefak boleh atau belum boleh digunakan.
Pengurangan kerugian, kenaikan approval dan ROI belum diukur. Tidak ada keputusan kredit di UI.

## Provenance dan populasi

`PORTFOLIO_RESEARCH_SNAPSHOT.json` mempertahankan hasil evaluasi M1 yang sudah dipublikasikan.
Penambahan `warehouse.vintages` dan `experiment_purposes` menyalin angka agregat dari output
profil PostgreSQL baca-saja 23 September 2026. Log profil lengkap tetap lokal; query untuk
mereproduksi agregat terdapat pada `scripts/sql/dashboard_aggregates.sql`. Query baru menambah
isolasi repeatable-read untuk membandingkan hasil dalam snapshot transaksi yang konsisten.
Query ini belum dijalankan ulang pada tanggal penyusunan; hasil database hari ini dapat berubah.

Total label dibandingkan dengan `M0_LABEL_ACTIVE_ROLLOUT_REPORT.json`, bagian `layers_after`.
Angka sumber 2.260.701 dan 33 pengecualian berasal dari laporan CSV/ingestion M0. Dua puluh satu
kombinasi vintage/tenor dijumlahkan dan cocok dengan 2.260.668 pinjaman, 1.076.751 label 0,
268.599 label 1 dan 915.318 label NULL. Tidak ada baris peminjam, ID, data raw atau model dalam
snapshot dashboard.

| Populasi | Denominator | Penggunaan |
|---|---:|---|
| Warehouse, 2007–2018, tenor 36/60 bulan | 2.260.668 | Volume, label dan heatmap vintage |
| Warehouse berlabel 0/1 | 1.345.350 | Adverse di antara outcome berlabel: 19,96% |
| Eksperimen M1, 36 bulan, 2011–2015, income positif, label 0/1 | 603.587 | Split dan distribusi tujuan pinjaman |
| Validation 2014 | 162.570 | Pemilihan kandidat/threshold historis |
| Frozen test 2015 eligible | 283.024 | Evaluasi historis, sudah terpakai |

Filter tahun/tenor hanya mengubah grafik dan KPI warehouse. Insight cakupan penuh, distribusi
tujuan M1, alur proyek dan metrik model diberi keterangan populasi tersendiri. Kombinasi tanpa data
menampilkan empty state, bukan tingkat risiko nol. Unduhan CSV hanya berisi agregat dalam filter.

## Temuan dan keputusan

1. **40,49% outcome belum/tidak definitif:** 915.318 / 2.260.668. Kontrak memberi NULL pada status
   selain Fully Paid, Charged Off dan Default. NULL tidak disamakan dengan pinjaman aman.
2. **Vintage baru belum otomatis matang:** 2018/36 bulan memiliki 303.399 / 344.671 = 88,03% NULL.
   Pola ini tidak membuktikan cohort tersebut lebih aman. Snapshot outcome/event timing belum
   terverifikasi; tenor tidak menetapkan horizon probabilitas gagal bayar.
3. **Eksperimen memakai subset yang eksplisit:** 147 outcome NULL dan 2 income tidak valid
   dikeluarkan pada test 2015. Train-only preprocessing dan whitelist mengurangi kebocoran
   informasi, tetapi label availability pada tanggal training historis masih harus dibuktikan.
4. **Kandidat gagal gate:** AP frozen test 0,2197 < 0,25; threshold lama menghasilkan nol prediksi
   positif. Test 2015 tidak boleh digunakan untuk seleksi ulang. Holdout independen baru diperlukan.
5. **Kualitas model dan packaging berbeda:** smoke lokal 29 September pada revisi `928acc6`
   mencatat container healthy, HTTP health 200, non-root dan lima path terlarang tidak ada.
   Image ID disalin dari laporan smoke lokal ke snapshot agregat. CI versi tersebut:
   [run 36538053231](https://github.com/Agathahah/creditlens/actions/runs/36538053231).
   Bukti ini mendahului desain UI baru; build/CI desain baru harus diperiksa setelah commit/push.
6. **Status publik pada 29 September belum diverifikasi:** saat itu tidak ada URL teruji.
   Pemeriksaan Cloud 30 September dicatat di bawah; deployment scoring tetap tertahan.

## Batas keamanan dan operasi

Halaman API menampilkan kontrak kode/tes, bukan probe endpoint langsung. Tes menggunakan fixture
sintetis untuk kasus readiness; belum ada bundle rilis dengan manifest/parity lengkap. Pemeriksaan
image terbatas pada `/app/data`, `/app/models`, `/app/.git`, `/app/.env`, `/app/.local-backups`.
Tidak ada klaim image bebas seluruh secret, CVE atau kerentanan. Autentikasi/rate limit/TLS,
pemindaian dependency, monitoring/rollback dan pengujian beban pada API aktif belum dibuktikan.

Data hanya mencakup pinjaman yang diterima. Independensi peminjam belum dapat ditetapkan karena
member_id tidak tersedia. Hak penggunaan raw/model publik masih perlu diselesaikan. Dashboard
memakai bukti agregat dan tidak memuat database, borrower upload, training atau scoring.

## Tambahan 30 September: sheet deskriptif dan pembanding model

`experiment_profile` menampilkan hanya agregat 603.587 pinjaman eligible M1 dari output
profil baca-saja 23 September. Median pendapatan tahunan 60.000 USD (p99 250.000, maksimum
9.000.000); median DTI 17,16 (p99 37,15, maksimum 999); median revolving utilization 54,5
(p99 98,2, maksimum 892,3) dalam satuan sumber. Nilai ekstrem menguatkan kebutuhan transformasi
train-only dan audit validitas input sebelum serving; angka ini tidak membuktikan imputation/scaling
sudah menyelesaikan semua anomali. Tabel profil juga memuat vintage 2011–2015 dan kategori
kepemilikan rumah, masing-masing berjumlah 603.587. Tidak ada catatan borrower/ID yang dipublikasikan.
Query agregat yang dapat mereproduksi tabel tersebut ditambahkan ke
`scripts/sql/dashboard_aggregates.sql`; query itu tidak dijalankan lagi dalam perubahan ini.

Halaman model sekarang membedakan cara kerja dan hasil **validation**: model konstan AP 0,1373
sebagai patokan prevalence 13,73%; Logistic Regression AP 0,2016 untuk hubungan linear yang
relatif mudah diaudit; bounded XGBoost AP 0,2046 untuk ambang/interaksi fitur. Kenaikan AP XGBoost
0,0030 dari Logistic Regression belum membuktikan manfaat operasional. Hanya kandidat terpilih
memiliki angka test pada laporan M1. Catatan keputusan rilis tersimpan di
`MODEL_RELEASE_DECISION_2026-09-30.md`.

Business problem yang dipakai adalah prioritas review manual pada tahap aplikasi. Success metrics
mencakup AP/prevalence, calibration, kualitas operating point, beban review, fairness dan operasi;
biaya kesalahan FP/FN serta dampak moneter belum tersedia. Dataset accepted-only tidak mewakili
semua pemohon dan tidak membuktikan performa prospektif. Dashboard publik adalah demo riset;
model/API scoring tetap tertahan.

## Verifikasi publik 30 September

Revisi dashboard `084e524` lulus lint, tes dan Docker smoke dalam
[CI run 36685936180](https://github.com/Agathahah/creditlens/actions/runs/36685936180).
URL [dashboard publik](https://creditlens-risk-evidence.streamlit.app/) berasal dari platform,
bukan localhost atau nama hasil tebakan. Sharing Cloud menyatakan public and searchable; sembilan
halaman dibuka pada situs hidup tanpa error aplikasi; permintaan HTTP anonim mengikuti redirect
cookie normal dan mendapat 200. Snapshot mencatat waktu `2026-09-30T08:03:29Z` dan revisi lengkap.
Ini hanya memverifikasi pilot agregat. Tidak ada model rilis atau API scoring aktif.
