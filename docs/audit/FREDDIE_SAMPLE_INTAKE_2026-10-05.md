# Freddie Mac SFLLD sample 2018 — pemeriksaan awal lokal

**Status:** arsip valid dan struktur dasar lulus; belum diterima untuk training atau publikasi data. Studi hipotek ini terpisah dari CreditLens LendingClub. Pemeriksaan bersifat baca-saja terhadap ZIP privat, tanpa ekstraksi permanen atau penerbitan baris pinjaman.

## Sumber dan identitas

- Sumber yang dilaporkan pemilik: tab **SFLLD Data** pada [Clarity/Freddie Mac](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset), `Standard Dataset Download by Year` → `2018` → `Sample File`.
- Arsip privat: `~/Documents/creditlens-private/freddie/sample_2018.zip`; ukuran **33.889.319 byte**; SHA-256 `87e4d7ecad71ab0ad536d18fc078f51201077f602e35f49eccb7ea70cf01b2a8`.
- ZIP CRC lulus `unzip -tq`. Dua member: `sample_orig_2018.txt` (**6.346.800 byte**) dan `sample_perf_2018.txt` (**234.307.548 byte**) setelah dekompresi. Ukuran total terdekompresi **240.654.348 byte**; file tidak perlu diekstrak untuk audit berikutnya.
- SHA-256 ini mengikat **berkas lokal**; belum dibandingkan dengan checksum yang diterbitkan Freddie Mac. Catat release ID, cutoff, dan syarat akses yang benar-benar diterima pemilik sebelum menetapkan manifest sumber final.

## Profil struktur baca-saja

| Pemeriksaan | Hasil |
|---|---:|
| Baris origination / ID unik | 50.000 / 50.000 |
| Baris performance / ID unik | 2.059.564 / 50.000 |
| Kolom per baris origination / performance | 31 / 35 |
| Periode performance minimum / maksimum | 2018-01 / 2026-03 |
| Lebar baris tidak sesuai, ID kosong, ID performance tanpa origination | 0 |
| ID origination tanpa performance, ID origination ganda | 0 |
| Periode tidak valid, saldo negatif/tidak numerik | 0 |
| Grup ID yang muncul kembali, periode tidak meningkat, celah bulan dalam satu riwayat | 0 |

Pemeriksaan memakai pemisah `|`, ID origination posisi 20, ID performance posisi 1, periode posisi 2, saldo posisi 3, dan status tunggakan posisi 4. Posisi ini cocok dengan [layout resmi efektif Juli 2026](https://www.freddiemac.com/fmac-resources/research/pdf/file_layout_july_2026.xlsx), tetapi mapping seluruh 31/35 field dan semantik missing value belum diaudit. Status `00` berarti lancar/kurang dari 30 hari menunggak, `03` berarti 90–119 hari, dan `RA` berarti REO acquisition menurut [ringkasan perubahan disclosure](https://www.freddiemac.com/fmac-resources/research/pdf/disclosure-changes-summary.pdf). Status dan *zero balance* tidak boleh langsung disamakan dengan label LendingClub.

## Batas dan gate berikutnya

1. Rekam release dan cutoff resmi, halaman ketentuan yang diterima pemilik, serta hak publikasi riset spesifik. [FAQ Freddie Mac](https://www.freddiemac.com/fmac-resources/research/pdf/faq.pdf) membedakan hasil riset nonkomersial dari distribusi data sumber.
2. Audit missing/sentinel tiap field, status dan kode terminasi, koreksi antar-release, dan tanggal informasi tersedia. Pemeriksaan format di atas belum membuktikan data *point-in-time* bebas kebocoran.
3. Sepakati populasi aktif pada `as_of`, kejadian yang ingin diperingatkan, horizon, penanganan pelunasan/terminasi (*censoring*), kapasitas analis, dan manfaat tindakan sebelum membuat label.
4. Setelah protokol dikunci, tentukan vintage tambahan dan split waktu independen. Sampel satu vintage belum merupakan train/validation/frozen test yang memadai. Jangan memakai frozen test LendingClub 2015 untuk pemilihan model Freddie.

**Keputusan saat ini: INTAKE AWAL LULUS; TRAINING DAN SCORING RELEASE TETAP HOLD.** Sampel hipotek AS tidak mengesahkan skor untuk pinjaman fintech dan tidak boleh digabung ke mart LendingClub.
