import os

# ---------------------------------------------------------
# Koneksi database
#
# Prioritas:
#   1. Variabel lingkungan DATABASE_URL (dipakai saat deploy, misalnya Render)
#      contoh SQLite : sqlite:///demo/sinar_jaya.db
#      contoh MySQL  : mysql+pymysql://user:pass@host:3306/dbname
#   2. Jika tidak ada, pakai MySQL lokal dari DB_USER / DB_PASSWORD / ...
# ---------------------------------------------------------

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "toko_sinar_jaya")

_env_url = os.getenv("DATABASE_URL")

if _env_url:
    # Beberapa penyedia hosting memakai awalan lama "postgres://"
    if _env_url.startswith("postgres://"):
        _env_url = _env_url.replace("postgres://", "postgresql://", 1)

    DATABASE_URL = _env_url
else:
    DATABASE_URL = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
