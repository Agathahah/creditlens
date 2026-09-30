# CreditLens: fokus pemantauan portofolio setelah pencairan

**Keputusan 30 September 2026.** Tujuan produk untuk tahap berikutnya adalah membantu analis memantau pinjaman yang sudah dicairkan. Dashboard saat ini menunjukkan analisis **historis**, bukan alert langsung. Keputusan ini mengarahkan rancangan eksperimen berikutnya; tidak mengubah hasil atau protokol eksperimen M1 pada 23 September 2026 yang dibuat untuk fitur saat aplikasi.

## Masalah dan alur kerja

Tim risiko perlu menemukan kelompok dan pinjaman aktif yang layak ditinjau sebelum kualitas portofolio memburuk. Alur yang dituju: snapshot pinjaman berkala → pemeriksaan kualitas/kelengkapan → metrik vintage dan perubahan status → prioritas tinjauan oleh analis → pencatatan tindakan dan hasil. Tidak ada keputusan kredit otomatis. Saat ini hanya tahap profil historis, lineage data, dan kontrol penolakan API yang terbukti.

## Bukti yang tersedia

Warehouse memuat 2.260.668 pinjaman diterima historis; 915.318 outcome belum/tidak definitif. Eksperimen M1 memiliki 603.587 pinjaman eligible tenor 36 bulan dari 2011–2015, memakai fitur tahap aplikasi. Kandidat terpilih mendapat AP frozen test 0,2197 di bawah gate historis 0,25; threshold lama menghasilkan nol prediksi positif. Test 2015 sudah terpakai. Bukti ini **tidak** memvalidasi skor alert untuk pinjaman aktif.

## Kontrak data sebelum eksperimen pemantauan

1. Sumber baru yang dapat diaudit, hak penggunaan jelas, snapshot independen, dan tanggal ekstraksi/outcome diketahui. Jangan menganggap vintage yang lebih baru dalam file lama sebagai holdout baru.
2. Panel pinjaman aktif berkala dengan ID pinjaman stabil, tanggal observasi (`as_of`), tanggal pencairan, status/tunggakan pada tanggal observasi, saldo atau exposure, serta tanggal kejadian outcome dan pembaruan terakhir. Simpan hanya fitur yang benar-benar diketahui pada `as_of`; periksa late-arriving corrections.
3. Definisikan peristiwa yang ingin diperingatkan dan horizon ke depan bersama pemilik risiko **sebelum** membangun label. Jangan menyamakan status akhir retrospektif dengan kejadian 30/60/90 hari. Catat censoring, pinjaman lunas, dan kelengkapan label per vintage.
4. Pembagian waktu berdasarkan tanggal observasi dan jendela outcome; cegah satu pinjaman masuk ke train dan test secara melanggar protokol. Holdout baru dibekukan dan dipakai sekali untuk keputusan akhir. Frozen test 2015 tidak dipakai untuk memilih fitur, model, atau threshold lagi.

## Evaluasi dan syarat rilis

Tetapkan kapasitas analis, biaya false alert, jendela tindak lanjut, dan target bisnis sebelum memilih threshold. Ukur cakupan portofolio, tingkat peralihan status, recall/precision pada kapasitas alert tetap, kalibrasi, perbedaan antarsegmen, keterlambatan label, serta dampak tindakan yang benar-benar tercatat. Validasi pada waktu dan sumber independen; periksa parity preprocessing dan serving, manifest bundle, keamanan API, rollback, dan monitoring setelah rilis. Penilaian manfaat finansial memerlukan rancangan pengukuran terpisah.

**Keputusan rilis saat ini: HOLD.** Tidak ada data panel baru atau sumber independen yang diakui; model pemantauan belum dilatih atau divalidasi. Dashboard publik dan CI hanya membuktikan penyajian agregat serta kontrol yang diuji. API scoring tetap menolak bundle lama/tidak terverifikasi.

## Dashboard BI publik

Tableau Public dipilih untuk portofolio yang dapat dibuka recruiter melalui browser dan dibuat dari Mac. Sumbernya hanya agregat yang sudah dipublikasikan: vintage-tenor, cohort eksperimen, hasil validation, dan definisi metrik. Workbook publik tidak berisi baris pinjaman, ID, PII, database, atau backup. Semua visual wajib menampilkan grain, denominator, tanggal bukti, dan status riset historis. Jangan menjumlahkan metrik dari tabel dengan grain berbeda menjadi satu total.

Lihat [profil dashboard](audit/DASHBOARD_DATA_STORY_2026-09-29.md), [keputusan rilis model historis](audit/MODEL_RELEASE_DECISION_2026-09-30.md), dan [rencana evaluasi](EVALUATION_RELEASE_PLAN.md).
