import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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

    # Path SQLite relatif (sqlite:///demo/x.db) dihitung dari folder proyek,
    # bukan dari folder kerja server, supaya aman di hosting mana pun.
    _prefix = "sqlite:///"
    if DATABASE_URL.startswith(_prefix) and not DATABASE_URL.startswith("sqlite:////"):
        _path = DATABASE_URL[len(_prefix):]
        if _path and not os.path.isabs(_path) and ":" not in _path[:3]:
            DATABASE_URL = _prefix + os.path.join(BASE_DIR, _path).replace("\\", "/")
else:
    DATABASE_URL = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
