from sqlalchemy import create_engine, text
from config import DATABASE_URL


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


def test_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Koneksi database berhasil!")
            print(result.fetchone())

    except Exception as e:
        print("Koneksi database gagal!")
        print(e)


if __name__ == "__main__":
    test_connection()