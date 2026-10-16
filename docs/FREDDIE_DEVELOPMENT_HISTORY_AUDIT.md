# Audit riwayat sebelum bulan prediksi

13 Oktober 2026. Scope: development 2018/2019 pada sumber hipotek retrospektif privat
yang telah diterima. Audit ini tidak melatih model, menghitung label masa depan,
membuka vintage ujian atau menghasilkan bundle scoring. V3 tetap REJECT_TEST.

## Implementasi dan kontrak

`src.research.freddie_history_audit` membaca ZIP secara streaming, satu riwayat pinjaman
pada satu waktu. Kalender dan loan partition mengikuti bagian **development** dari
protokol v3 yang immutable. Audit tidak mengubah protokol tersebut atau mengesahkan
fit baru. Seluruh vintage 2020 tetap consumed; 2021/2022 belum menjadi input audit.

Grain agregasi adalah observasi pinjaman lancar × bulan laporan di window development.
Observasi dengan follow-up yang kelak censored tetap masuk audit; tidak diperlukan
outcome masa depan untuk menilai kelengkapan fitur. Counts audit harus direkonsiliasi
dengan eligible observations development yang telah dicatat, bukan hanya labeled rows.

| Kandidat | Definisi kalender | Nilai hilang dan batas interpretasi |
|---|---|---|
| observed_months_6/12 | Jumlah record pada tepat 6/12 bulan sebelum as-of | Bulan absen bukan bulan lancar |
| known_status_months_6/12 | Jumlah status yang diketahui pada window tersebut | Status unknown tidak diisi nol |
| complete_status_6/12 | Semua slot kalender mempunyai status diketahui | 0 menunjukkan riwayat tidak lengkap, bukan risiko nol |
| worst_dq_6/12 | Maksimum kode delinquency historis pada window lengkap | NULL bila tidak lengkap; RA memakai kode ordinal 100 dari reader, bukan 100 bulan tunggakan |
| dq_months_6/12 | Jumlah bulan dengan delinquency >0, pada window lengkap | NULL bila tidak lengkap; ini jumlah observasi, bukan jumlah kejadian independen |
| months_since_known_dq_12 | Jarak kalender dari tunggakan diketahui terdekat sebelum as-of | NULL bila tidak ada kejadian diketahui; completeness diperlukan untuk membedakan unknown |
| upb_change_ratio_3/6/12 | (UPB as-of − UPB tepat k bulan sebelumnya) / UPB sebelumnya | NULL bila record/balance pembanding tidak tersedia atau nonpositif; bukan nilai cash payment |

Semua slot riwayat memakai bulan **strictly before as-of**, bukan offset baris. Saldo
as-of hanya dipakai untuk perubahan stok UPB. Identitas pinjaman harus sama dan bulan
harus unik serta meningkat. Fungsi fitur mengabaikan current/future entries dalam map
riwayat. Reader development tetap membaca berkas historis lengkap untuk validasi
struktur, tetapi tidak menggunakan future status/outcome untuk perhitungan fitur.

## Sumber, privasi dan sumber daya

- Dua vintage, nama archive, checksum sumber yang diterima dan hash protokol terikat
  sebelum archive dibaca. Frozen-test entry tidak di-stat, di-hash atau dibuka.
- Consumption test tidak menghalangi audit development. Fungsi ini **bukan** jalan
  melewati admission training atau mengaktifkan kembali executor v3.
- Output harus di luar repository, directory baru tanpa overwrite; file owner-only.
  Tidak ada loan identifier, record sumber atau nilai sampel dalam laporan agregat.
- Count, missingness, min/max, mean dan population standard deviation dihitung persis
  sampai presisi floating point. Quantile bersifat **perkiraan** dari reservoir maksimal
  2.000 nilai non-null per fitur/role, seed 42; nilai reservoir tidak disimpan.
- Supervisor yang sama membatasi worker: dua thread, 15 menit, RSS 2 GiB. Pengukuran
  RSS setiap 250 ms bukan jaminan maksimum instan seluruh sistem. Kegagalan monitor
  atau budget menghentikan worker dan mempertahankan bukti kegagalan.

## Validasi dan keputusan berikutnya

Tes memakai fixtures sintetis untuk gap kalender, unknown status, delinquency/recency,
perubahan saldo, invariansi terhadap future record, duplicate/mixed identity, reservoir
terbatas dan penolakan source selain development sebelum source read.

Audit menyediakan bukti completeness/distribution. Ia tidak menunjukkan peningkatan
recall, kontribusi kausal fitur atau operational point-in-time availability. Whitelist
baru belum dipilih. Langkah sesudahnya adalah intake metadata holdout baru dan protokol
fit/evaluasi baru yang terkunci sebelum fit/test; kriteria rilis tidak diturunkan.

Definisi sumber mengacu [SFLLD](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset)
dan [general user guide](https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf).
Dokumentasi kode ini dapat dipublikasikan. Profil numerik mortgage, notebook, manifest,
model dan catatan belajar tetap privat. [Urutan penerimaan layanan](FREDDIE_NEXT_RESEARCH_AND_SERVICE.md)
memisahkan kualitas model, hak penggunaan, availability, bundle/API dan operasi.
