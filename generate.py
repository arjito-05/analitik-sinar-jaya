import random
from datetime import datetime, timedelta

from sqlalchemy import text

from database import engine


# =========================================================
# KONFIGURASI
# =========================================================

JUMLAH_TRANSAKSI = 300

TANGGAL_MULAI = datetime(2026, 4, 1)
TANGGAL_SELESAI = datetime(2026, 9, 30)


# =========================================================
# MENGAMBIL DATA DARI DATABASE
# =========================================================

def get_customers(connection):
    query = text("""
        SELECT id_pelanggan
        FROM pelanggan
    """)

    result = connection.execute(query)

    return [row[0] for row in result]


def get_products(connection):
    query = text("""
        SELECT
            id_produk,
            nama_produk,
            harga
        FROM produk
        WHERE harga IS NOT NULL
    """)

    result = connection.execute(query)

    products = []

    for row in result:
        products.append({
            "id_produk": row[0],
            "nama_produk": row[1],
            "harga": float(row[2])
        })

    return products


# =========================================================
# MEMBUAT TANGGAL RANDOM
# =========================================================

def random_date(start_date, end_date):

    total_days = (end_date - start_date).days

    random_days = random.randint(0, total_days)

    date = start_date + timedelta(days=random_days)

    hour = random.randint(8, 17)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return date.replace(
        hour=hour,
        minute=minute,
        second=second
    )


# =========================================================
# MENENTUKAN JUMLAH PRODUK
# =========================================================

def random_quantity():

    choices = [
        1, 1, 1,
        2, 2, 2,
        3, 3,
        5,
        10,
        20
    ]

    return random.choice(choices)


# =========================================================
# MEMBUAT TRANSAKSI
# =========================================================

def generate_transactions():

    with engine.begin() as connection:

        customers = get_customers(connection)
        products = get_products(connection)

        if not customers:
            print("Tidak ada data pelanggan.")
            return

        if not products:
            print("Tidak ada data produk.")
            return

        print(f"Jumlah pelanggan : {len(customers)}")
        print(f"Jumlah produk    : {len(products)}")

        for transaction_number in range(JUMLAH_TRANSAKSI):

            # ---------------------------------------------
            # PILIH PELANGGAN
            # ---------------------------------------------

            customer_id = random.choice(customers)

            transaction_date = random_date(
                TANGGAL_MULAI,
                TANGGAL_SELESAI
            )

            # ---------------------------------------------
            # BUAT TRANSAKSI UTAMA
            # ---------------------------------------------

            result = connection.execute(
                text("""
                    INSERT INTO transaksi
                    (
                        id_pelanggan,
                        tanggal_transaksi,
                        total,
                        status
                    )
                    VALUES
                    (
                        :id_pelanggan,
                        :tanggal_transaksi,
                        :total,
                        :status
                    )
                """),
                {
                    "id_pelanggan": customer_id,
                    "tanggal_transaksi": transaction_date,
                    "total": 0,
                    "status": "selesai"
                }
            )

            transaction_id = result.lastrowid

            # ---------------------------------------------
            # PILIH 1-4 PRODUK
            # ---------------------------------------------

            jumlah_jenis_produk = random.randint(1, 4)

            selected_products = random.sample(
                products,
                min(jumlah_jenis_produk, len(products))
            )

            total_transaksi = 0

            # ---------------------------------------------
            # DETAIL TRANSAKSI
            # ---------------------------------------------

            for product in selected_products:

                quantity = random_quantity()

                harga = product["harga"]

                subtotal = quantity * harga

                total_transaksi += subtotal

                connection.execute(
                    text("""
                        INSERT INTO detail_transaksi
                        (
                            id_transaksi,
                            id_produk,
                            jumlah,
                            harga,
                            subtotal
                        )
                        VALUES
                        (
                            :id_transaksi,
                            :id_produk,
                            :jumlah,
                            :harga,
                            :subtotal
                        )
                    """),
                    {
                        "id_transaksi": transaction_id,
                        "id_produk": product["id_produk"],
                        "jumlah": quantity,
                        "harga": harga,
                        "subtotal": subtotal
                    }
                )

            # ---------------------------------------------
            # UPDATE TOTAL TRANSAKSI
            # ---------------------------------------------

            connection.execute(
                text("""
                    UPDATE transaksi
                    SET total = :total
                    WHERE id_transaksi = :id_transaksi
                """),
                {
                    "total": total_transaksi,
                    "id_transaksi": transaction_id
                }
            )

            print(
                f"Transaksi {transaction_number + 1}/"
                f"{JUMLAH_TRANSAKSI} "
                f"-> Rp{total_transaksi:,.0f}"
            )

    print("\nData transaksi berhasil dibuat!")


if __name__ == "__main__":
    generate_transactions()