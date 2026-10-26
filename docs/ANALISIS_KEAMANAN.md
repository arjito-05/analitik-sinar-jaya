# Analisis Kerentanan dan Keamanan Website

Objek: Dashboard Analitik Toko Bangunan Sinar Jaya (Flask, Pandas, Plotly, SQLite).
Pengujian dilakukan pada salinan lokal aplikasi milik sendiri. Server hosting publik tidak diserang.

## 1. Ringkasan

Ditemukan **8 temuan**: 4 berkategori sedang dan 4 rendah. Tidak ada temuan kritis atau tinggi
pada pengujian yang dilakukan. Tingkat risiko adalah penilaian kualitatif berdasarkan
kemungkinan dan dampak, bukan skor CVSS resmi. Kategori mengacu pada OWASP Top 10 (edisi 2021).

## 2. Metode

1. **Tinjauan kode manual**: `app.py`, `config.py`, `database.py`, skrip ekspor, templat HTML.
2. **Uji dinamis lokal** lewat test client Flask: header HTTP, XSS refleksi (4 payload),
   SQL injection (3 payload), akses file, penanganan error, beban per permintaan.
   Dapat diulang dengan `python -m scripts.uji_keamanan`.
3. **Tinjauan konfigurasi dan repositori**: isi GitHub, berkas data, kredensial bawaan, dependensi.

Batasan: audit kerentanan paket (pip-audit) belum dijalankan karena memerlukan akses internet
pada saat analisis.

## 3. Daftar temuan

| No | Temuan | Bukti | Dampak | Tingkat | OWASP | Status |
|---|---|---|---|---|---|---|
| 1 | Dashboard tanpa autentikasi | `GET /` tanpa login: HTTP 200 dan menampilkan omzet | Data penjualan dan stok dapat dilihat siapa pun yang memiliki tautan | Sedang | A01 Broken Access Control | Mitigasi tersedia (HTTP Basic opsional) |
| 2 | Header keamanan HTTP belum ada | 0 dari 6 header terpasang | Clickjacking, MIME sniffing, tanpa batasan sumber skrip | Sedang | A05 Security Misconfiguration | Diperbaiki (5 dari 6; HSTS di hosting) |
| 3 | Mode debug tertulis permanen | `app.run(debug=True)`; di mode WSGI `app.debug = False` | Debugger Werkzeug dapat mengeksekusi kode bila dijalankan langsung dan terjangkau jaringan (laten) | Sedang | A05 Security Misconfiguration | Diperbaiki (variabel `FLASK_DEBUG`) |
| 4 | Kredensial database bawaan lemah | `DB_USER=root`, kata sandi kosong | Akses penuh ke database bila MySQL terjangkau jaringan | Sedang | A07 Identification and Authentication Failures | Rekomendasi |
| 5 | Skrip CDN tanpa SRI | Bootstrap dan Plotly tanpa atribut `integrity` | Skrip berbahaya bila CDN dikompromikan | Rendah | A08 Software and Data Integrity Failures | Rekomendasi |
| 6 | Tanpa pembatasan laju | 160 sampai 190 ms dan 66 KB per permintaan | Server gratis dapat terbebani | Rendah | A04 Insecure Design | Sebagian (parameter dibatasi 40 karakter) |
| 7 | Data demo di repositori publik | `.db` dan CSV di GitHub; data acak dari `generate.py` | Bukan data nyata; berisiko jika data riil (UU No. 27 Tahun 2022) | Rendah | A01 Broken Access Control | Sebagian (skrip ekspor tidak menyalin `admin` dan kontak pelanggan) |
| 8 | Dependensi belum diaudit | `gunicorn` tanpa versi; audit belum dijalankan | Paket usang atau rentan tidak terdeteksi | Rendah | A06 Vulnerable and Outdated Components | Rekomendasi |

## 4. Kontrol yang sudah aman

- **SQL injection**: 3 payload tidak berefek; tabel `produk` tetap 17 baris. Kueri bersifat tetap tanpa input pengguna dan penyaringan dilakukan di Pandas.
- **XSS**: 0 dari 4 payload lolos mentah ke HTML (Jinja2 autoescape dan validasi input).
- **Akses file**: `/static/../config.py` ditolak (HTTP 404).
- **Penanganan error**: rute tak dikenal 404 dan metode salah 405, tanpa jejak tumpukan.
- **Cookie dan CSRF**: aplikasi tidak memakai cookie atau sesi dan hanya menerima GET, sehingga CSRF tidak relevan.

## 5. Perbaikan yang sudah diterapkan

| Perbaikan | Berkas |
|---|---|
| Header keamanan (CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy, COOP) | `app.py` (`add_security_headers`) |
| Mode debug dikendalikan `FLASK_DEBUG`, bawaan mati | `app.py` |
| Autentikasi HTTP Basic opsional lewat `DASHBOARD_USER` dan `DASHBOARD_PASSWORD` | `app.py` (`require_basic_auth`) |
| Batas panjang parameter filter 40 karakter | `app.py` |
| Skrip ekspor hanya menyalin 5 tabel analitik, tanpa `admin` dan kontak pelanggan | `scripts/export_mysql_to_sqlite.py` |

Verifikasi: grafik tetap tampil di browser tanpa pelanggaran CSP, dan 5 skenario filter berjalan HTTP 200.
Catatan: CSP masih memakai `unsafe-inline` karena skrip grafik ditulis inline.

Mengaktifkan autentikasi di PythonAnywhere: tambahkan dua baris ini pada file WSGI (isi nilai sendiri, jangan dibagikan atau di-commit):

```python
os.environ["DASHBOARD_USER"] = "..."
os.environ["DASHBOARD_PASSWORD"] = "..."
```

## 6. Rekomendasi

**Segera**
- Aktifkan autentikasi bila data yang ditampilkan adalah data riil.
- Ganti pengguna MySQL `root` dengan pengguna khusus yang hanya memiliki izin `SELECT`, dan atur kata sandi lewat variabel lingkungan.
- Pastikan berkas `.db` publik tidak memuat tabel `admin`.

**Jangka pendek**
- Tambahkan atribut `integrity` (SRI) pada skrip CDN atau hosting aset sendiri.
- Kunci versi semua paket di `requirements.txt` dan jalankan `pip-audit` secara berkala.
- Terapkan pembatasan laju (mis. Flask-Limiter) atau caching hasil analisis.
- Aktifkan HSTS pada lapisan hosting.

**Jangka panjang**
- CSP berbasis nonce tanpa `unsafe-inline`.
- Simpan kata sandi dengan hashing kuat (bcrypt atau Argon2) bila halaman admin dibuat.
- Tambahkan pencatatan (logging) dan pemantauan aktivitas.
- Susun kebijakan pengelolaan data pribadi.

## 7. Keterbatasan

Analisis mencakup tinjauan kode dan uji lokal pada versi aplikasi saat ini. Tidak dilakukan uji penetrasi
terhadap server hosting, audit dependensi, maupun peninjauan konfigurasi internal penyedia hosting.
Hasil ini bukan jaminan bahwa tidak ada celah lain.
