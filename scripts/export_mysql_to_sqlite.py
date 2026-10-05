"""
Salin data yang dipakai dashboard dari MySQL lokal ke file SQLite agar bisa
di-deploy tanpa server database (misalnya di Render).

Jalankan dari folder utama proyek, saat MySQL lokal menyala dan
variabel DATABASE_URL TIDAK di-set:

    python -m scripts.export_mysql_to_sqlite

Hasil: demo/sinar_jaya.db

Catatan keamanan: hanya tabel yang dibutuhkan analitik yang disalin.
Tabel `admin` (berisi username dan password) TIDAK disalin, dan kolom
kontak pelanggan (no_telepon, email) dibuang karena database ini akan
ikut ter-publish.
"""

import os

from sqlalchemy import Column, MetaData, Table, create_engine

from config import DATABASE_URL

OUTPUT = "demo/sinar_jaya.db"

# Urutan mengikuti ketergantungan foreign key
TABLES = [
    "kategori",
    "pelanggan",
    "produk",
    "transaksi",
    "detail_transaksi",
]

# Kolom yang tidak ikut disalin
DROP_COLUMNS = {
    "pelanggan": {"no_telepon", "email"},
}


def generic_type(column_type):
    """Ubah tipe khusus MySQL menjadi tipe generik yang dikenal SQLite."""

    try:
        generic = column_type.as_generic()
    except NotImplementedError:
        generic = column_type

    # Collation MySQL (mis. utf8mb4_general_ci) tidak dikenal SQLite
    if hasattr(generic, "collation"):
        generic.collation = None

    return generic


def convert_table(source_table, target_metadata):
    """
    Bangun definisi tabel versi SQLite: tipe generik, tanpa server_default
    khusus MySQL (mis. current_timestamp()), tanpa kolom yang dibuang.
    """

    drop = DROP_COLUMNS.get(source_table.name, set())

    columns = []

    for col in source_table.columns:
        if col.name in drop:
            continue

        columns.append(
            Column(
                col.name,
                generic_type(col.type),
                nullable=col.nullable,
                primary_key=col.primary_key,
                autoincrement=col.autoincrement,
            )
        )

    return Table(source_table.name, target_metadata, *columns)


def main():
    if DATABASE_URL.startswith("sqlite"):
        raise SystemExit(
            "DATABASE_URL sudah SQLite. Hapus variabel DATABASE_URL "
            "agar skrip membaca dari MySQL lokal."
        )

    os.makedirs("demo", exist_ok=True)

    if os.path.exists(OUTPUT):
        os.remove(OUTPUT)

    source = create_engine(DATABASE_URL)
    target = create_engine(f"sqlite:///{OUTPUT}")

    source_metadata = MetaData()
    source_metadata.reflect(bind=source, only=TABLES)

    target_metadata = MetaData()

    for name in TABLES:
        convert_table(source_metadata.tables[name], target_metadata)

    target_metadata.create_all(target)

    with source.connect() as src, target.begin() as dst:
        for name in TABLES:
            source_table = source_metadata.tables[name]
            target_table = target_metadata.tables[name]

            keep = [c.name for c in target_table.columns]

            rows = [
                {k: row._mapping[k] for k in keep}
                for row in src.execute(source_table.select())
            ]

            if rows:
                dst.execute(target_table.insert(), rows)

            print(f"{name:<20} {len(rows)} baris")

    print(f"\nSelesai: {OUTPUT}")


if __name__ == "__main__":
    main()
