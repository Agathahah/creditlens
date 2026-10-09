# Persiapan admission dan rilis riset hipotek

Tanggal: 9 Oktober 2026. Status: **protokol eksperimen lokal disetujui per hash; penerimaan sumber belum lengkap**.
Scoring LendingClub tetap HOLD. Dokumen ini tidak mengizinkan training penuh, membuka test,
merge, tag, deployment atau penggunaan model hipotek pada pinjaman fintech.

## Metadata resmi yang telah ditemukan

[Release Notes Freddie](https://www.freddiemac.com/fmac-resources/research/pdf/release_notes.pdf)
mencatat Release 47, tanggal 29 Juli 2026, origination dan performance cutoff 31 Maret 2026.
[Halaman dataset](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset) juga
menyatakan cutoff kinerja tersebut dan bahwa data historis dapat berubah. Layout Juli 2026
dan periode maksimum berkas pengembangan lokal konsisten dengan release ini. Konsistensi
tersebut merupakan **inferensi**, bukan verifikasi hubungan byte arsip lokal dengan release resmi:
portal/receipt pemilik belum dicatat sebagai bukti hubungan tersebut. Tidak ada checksum resmi
Freddie untuk arsip lokal dalam bukti yang tersedia.

[Ketentuan SFLLD efektif November 2025](https://capitalmarkets.freddiemac.com/crt/docs/pdfs/fre_terms_conditions_sflld.pdf)
menyebut tujuan pribadi/internal untuk riset kinerja hipotek serta kondisi khusus untuk publikasi
riset nonkomersial yang tidak mengungkap atau memungkinkan rekonstruksi data. Pemilik perlu
mencatat ketentuan yang benar-benar diterima saat akses. Admission eksperimen lokal tidak
mengizinkan publikasi baris, panel, bobot model atau API publik. Tanggal release baru tidak
membuktikan informasi tersedia pada setiap bulan observasi historis.

## Tiga keputusan terpisah

1. **Admission training riset:** identitas arsip, intake, review ketentuan/release, pengakuan batas
   snapshot terkoreksi, dan persetujuan hash protokol sebelum validation outcome ditinjau.
2. **Kelulusan model riset:** evaluasi pada kandidat terkunci, baseline, support, uncertainty,
   kalibrasi dan operating policy. Test yang dipakai untuk revisi tetap dianggap terpakai.
3. **Penerimaan layanan:** bundle real, parity, akses, beban, monitoring, rollback dan scope
   penggunaan. Tidak otomatis terjadi setelah dua keputusan sebelumnya.

`src.research.freddie_preflight` hanya menilai prasyarat pertama. CLI membaca JSON dan hash byte
ZIP tanpa mengekstrak atau membuka member frozen test. Exit 2 menunjukkan prasyarat belum
lengkap; exit 0 berarti **eligible for review**, bukan izin train otomatis atau scoring PASS.
Acknowledgement dan intake pada manifest adalah pernyataan tercatat, bukan tanda tangan atau
sertifikasi independen. CLI tidak mengubah registry/API atau membuktikan kelulusan model.

## Protokol yang dapat ditinjau

Konfigurasi: [freddie_experiment_v1.json](../config/research/freddie_experiment_v1.json).
Status konfigurasi tetap PROPOSED_NOT_APPROVED. Persetujuan harus menyebut hash byte konfigurasi
tersebut; setiap perubahan membuat review lama tidak cocok. Review disimpan di manifest privat,
bukan dengan mengubah nilai status pada konfigurasi setelah hash disetujui.

- Target/split/fitur tetap mengikuti [protokol panel](FREDDIE_MONTHLY_RESEARCH_PROTOCOL.md).
- Estimasi **retrospektif** pada snapshot terkoreksi; bukan backtest point-in-time atau skor kredit.
- Constant memakai prevalence train; Logistic Regression C=1, maksimum 1.000 iterasi; satu
  HistGradientBoosting maksimum 80 iterasi/depth 3. Tanpa pencarian hyperparameter.
- Median/missing indicators dan scaling model linear fit hanya train. Loan ID/label/tanggal
  event tidak masuk fitur. Distribusi validation tidak mengubah transform train.
- Tidak ada calibrator pasca-fit pada v1. Reliability dan Brier wajib dilaporkan; jika kalibrasi
  tidak memadai, kandidat ditahan. Penambahan calibrator memerlukan protokol pengembangan baru
  sebelum frozen test dibuka, bukan fit pada test.
- Kandidat dipilih melalui AP validation; seri memilih model linear. Hanya kandidat terpilih
  boleh dinilai pada frozen test sekali setelah acceptance validation dan persetujuan pembukaan.
- Simulasi kapasitas: top 1% per bulan pada cohort berlabel, pembulatan jumlah alert ke atas,
  minimum satu alert bila cohort tidak kosong, ties memakai loan key privat secara deterministik.
  Ini evaluasi retrospektif pada subset berlabel; bukan volume alert operasional seluruh pinjaman.
- Budget usulan: dua thread, 15 menit, peak RSS 2 GiB, seed 42. Pelaksana berikutnya harus
  mengukur/menghentikan fit saat budget terlewati; konfigurasi ini belum menjalankan enforcement.

### Gate numerik usulan sebelum validation/test

| Gate | Usulan |
|---|---|
| Dukungan event unik | Train >=50, validation >=30, test >=30 pinjaman adverse |
| Ranking | AP/prevalence >=2; lower bound bootstrap 95% >1 |
| Probabilitas | Semua finite dan dalam [0,1]; Brier lebih baik daripada constant prevalence train |
| Simulasi kapasitas | Recall top 1% >=20%; precision/prevalence >=2; jumlah alert tidak nol |
| Ketidakpastian | 1.000 paired bootstrap per loan; semua loan-month pada loan yang disampling dipertahankan |
| Kualitas data | Laporkan denominators, label NULL/censoring dan hasil per bulan |

Angka tersebut adalah guardrail riset yang disetujui untuk eksperimen lokal, bukan standar industri atau kebutuhan
lender. Minimum support bukan power calculation. Interval yang lebar atau support tidak memadai
harus dilaporkan, bukan disamarkan oleh jumlah baris besar. Confidence interval yang tidak dapat
diestimasi membuat gate uncertainty gagal. AP bootstrap membandingkan AP dengan prevalence pada
resample yang sama; Brier dibanding constant train pada cohort evaluasi yang sama.

## Kontrol request yang diimplementasikan

- Envelope API menolak field tidak dikenal, >128 fitur dan applicant ID >128 karakter.
- Nilai fitur harus numerik finite; bool dan string numerik ditolak. Model schema menolak fitur
  tambahan, sehingga outcome masa depan tidak dapat diam-diam dibuang sambil request dianggap valid.
- Respons validation 422 tidak memantulkan raw input/ctx. NaN/Infinity tidak menyebabkan
  kegagalan serialisasi respons error.
- CORS default tertutup. `API_ALLOWED_ORIGINS` berisi origin HTTP(S) eksplisit dipisahkan koma;
  wildcard, credentials, path/query/fragment dan port invalid ditolak.
- Ini batas jumlah field, **bukan batas total byte payload/request**. CORS bukan autentikasi.
  Auth, HTTPS, byte/rate limits, bundle validator real, parity, monitoring dan rollback belum selesai.
  Input numerik praolah dan field approved API lama tidak cocok untuk kontrak hipotek; adapter/
  endpoint hipotek terpisah harus dirancang sebelum serving. Tidak ada model Freddie dimuat.

## Perintah lokal

Manifest privat dibuat di luar repo; jangan ubah acknowledgement menjadi true tanpa review nyata.

```bash
cd "$HOME/Documents/creditlens"
.venv/bin/python -m src.research.freddie_preflight \
  --manifest "$HOME/Documents/creditlens-private/freddie/release_preparation_20261009/source_manifest.json" \
  --protocol config/research/freddie_experiment_v1.json
.venv/bin/python -m pytest tests/test_freddie_preflight.py src/api/tests/test_input_controls.py src/api/tests/test_readiness.py -q
```

Preflight tidak menulis/mengubah file atau membuat label. Tes memakai fixture sintetis dan tidak
mengakses arsip privat. Hasil prasyarat saat persiapan ini: review release/terms
belum lengkap; training BLOCKED, model evaluation NOT_RUN, scoring HOLD. Bukti validasi software
ditambahkan ke WORKLOG sesudah tes, terpisah dari kelulusan model.

## Keputusan 9 Oktober 2026

Protokol dan batas klaim retrospektif disetujui untuk eksperimen lokal berbatas sumber daya,
terikat SHA-256 `c17999bce05357b4ef937eee474b0549702c811de91ccd43a8017a1f5eb696b7`.
Konfigurasi JSON adalah artefak proposal yang dibekukan; nilai status asalnya tidak diubah
agar persetujuan tetap terikat byte yang sama. Persetujuan aktual dicatat pada manifest
privat dan keputusan ini. Ini tidak memberi izin membuka test atau deployment.

Pemilik belum memeriksa metadata/ketentuan portal. Oleh karena itu dua prasyarat sumber
masih gagal: `release_binding_confirmed` dan `internal_research_terms_acknowledged`.
CLI tetap BLOCKED/HOLD; training dan evaluasi model tidak dijalankan.
