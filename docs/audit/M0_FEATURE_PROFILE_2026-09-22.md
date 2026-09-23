# M0 — profil nilai kosong kandidat fitur

Pemeriksaan baca-saja pada 22 September 2026 terhadap `raw.lc_loans` di PostgreSQL lokal. Transaksi `BEGIN READ ONLY` memakai batas waktu per pernyataan 120 detik. Hanya agregat yang dikeluarkan; tidak ada record mentah atau perubahan database.

Filter cohort untuk **profil awal saja**: `loan_status IN ('Fully Paid', 'Charged Off', 'Default')`. Jumlahnya **1.345.350**, sesuai kandidat berlabel pada [kontrak target](../M0_LABEL_DECISION_DRAFT.md). Filter ini belum menjadi eligibility training final.

| Kolom/keadaan sumber | Jumlah |
|---|---:|
| `dti IS NULL` | 376 |
| `annual_inc <= 0` | 361 |
| `annual_inc IS NULL` | 0 |
| `loan_amnt`, `term`, `revol_bal`, `revol_util`, `total_acc`, `open_acc`, `earliest_cr_line`, `delinq_2yrs`, `pub_rec`, `inq_last_6mths` kosong | 0 untuk setiap kolom |
| `home_ownership`, `purpose`, `addr_state` NULL/string kosong | 0 untuk setiap kolom |

Jumlah per baris tabel tidak harus saling lepas. Angka nol hanya berlaku pada cohort dan definisi kosong yang diuji; angka itu tidak membuktikan nilai valid, benar, tersedia saat prediksi, atau bebas kebocoran informasi.

`models/mart/loan_features.sql` saat ini menghasilkan `dti_eff = COALESCE(dti, 0.0)` dan `installment_to_income_ratio = 0.0` bila `annual_inc <= 0`. Dengan demikian, `dti_eff=0` dapat berarti DTI sumber benar-benar nol atau nilai yang kosong; rasio nol dapat berasal dari pendapatan tidak positif. Pipeline M1 perlu mempertahankan/menandai keadaan sumber tersebut sebelum imputasi, memutuskan eligibility untuk pendapatan tidak positif, dan memasang transform dari train saja. Keputusan ini belum dibuat. Ketersediaan waktu fitur, tanggal snapshot outcome, hak penggunaan publik dan desain split tetap terbuka.
