"""
Uji keamanan dasar untuk aplikasi ini (hanya dijalankan terhadap aplikasi
lokal milik sendiri, lewat test client Flask).

Jalankan dari folder utama proyek:

    set DATABASE_URL=sqlite:///demo/sinar_jaya.db      (Windows)
    python -m scripts.uji_keamanan
"""

import base64
import os
import re
import secrets
import sqlite3
import time

os.environ.setdefault("DATABASE_URL", "sqlite:///demo/sinar_jaya.db")

import app as a  # noqa: E402

c = a.app.test_client()

HEADERS = [
    "Content-Security-Policy", "X-Frame-Options", "X-Content-Type-Options",
    "Strict-Transport-Security", "Referrer-Policy", "Permissions-Policy",
]


def bagian(judul):
    print(f"\n== {judul}")


r = c.get("/")
bagian("1. Header keamanan")
ada = 0
for h in HEADERS:
    nilai = r.headers.get(h)
    ada += bool(nilai)
    print(f"  {h:28} {'ADA' if nilai else 'TIDAK ADA'}")
print(f"  Terpasang: {ada} dari {len(HEADERS)}")
print("  app.debug (mode WSGI):", a.app.debug)

bagian("2. XSS refleksi (4 payload)")
kasus_xss = [
    ("start_date", '"><script>alert(1)</script>'),
    ("category", '"><script>alert(1)</script>'),
    ("category", "<img src=x onerror=alert(1)>"),
    ("end_date", '2026-09-30"onfocus="alert(1)'),
]
lolos = 0
for param, p in kasus_xss:
    html = c.get("/", query_string={param: p}).data.decode()
    lolos += (
        "<script>alert(1)" in html
        or "<img src=x" in html
        or 'onfocus="alert' in html
    )
print(f"  Payload yang lolos mentah ke HTML: {lolos} dari {len(kasus_xss)}")

bagian("3. SQL injection (3 payload)")
kasus_sqli = [
    ("category", "' OR '1'='1"),
    ("category", "Cat'; DROP TABLE produk;--"),
    ("start_date", "2026-01-01' OR 1=1--"),
]
for param, p in kasus_sqli:
    code = c.get("/", query_string={param: p}).status_code
    print(f"  {param}={p[:28]!r:32} HTTP {code}")
baris = sqlite3.connect("demo/sinar_jaya.db").execute(
    "select count(*) from produk"
).fetchone()[0]
print("  Baris tabel produk setelah uji:", baris)

bagian("4. Error dan akses file")
print("  GET /admin ->", c.get("/admin").status_code)
print("  POST /     ->", c.post("/").status_code)
print("  GET /static/../config.py ->", c.get("/static/../config.py").status_code)

bagian("5. Beban per permintaan")
t = time.time()
for _ in range(5):
    r = c.get("/")
print(f"  rata-rata {(time.time() - t) / 5 * 1000:.0f} ms, respons {len(r.data) / 1024:.0f} KB")

bagian("6. Autentikasi opsional (kredensial uji acak, tidak disimpan)")
user, pw = "uji", secrets.token_urlsafe(8)
a.DASHBOARD_USER, a.DASHBOARD_PASSWORD = user, pw
benar = base64.b64encode(f"{user}:{pw}".encode()).decode()
salah = base64.b64encode(f"{user}:salah".encode()).decode()
print("  tanpa kredensial ->", c.get("/").status_code)
print("  kredensial salah ->", c.get("/", headers={"Authorization": "Basic " + salah}).status_code)
print("  kredensial benar ->", c.get("/", headers={"Authorization": "Basic " + benar}).status_code)
a.DASHBOARD_USER, a.DASHBOARD_PASSWORD = "", ""
