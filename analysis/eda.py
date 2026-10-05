import os

import numpy as np
import pandas as pd
import plotly.express as px
from sqlalchemy import text

from database import engine


# =========================================================
# KONFIGURASI
# =========================================================

OUTPUT_DIR = "output"
CSV_DIR = os.path.join(OUTPUT_DIR, "csv")
CHART_DIR = os.path.join(OUTPUT_DIR, "charts")

# Aturan restock
STOK_MINIMUM = 10     # stok <= nilai ini selalu dianggap perlu restock
RESTOCK_HARI = 21     # stok diperkirakan habis dalam <= nilai ini (hari)

os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)


# =========================================================
# 1. MENGAMBIL DATA DARI DATABASE
# =========================================================

def load_sales_data():

    query = text("""
        SELECT
            t.id_transaksi,
            t.id_pelanggan,
            t.tanggal_transaksi,
            t.total AS total_transaksi,
            t.status,

            p.id_produk,
            p.nama_produk,
            p.harga AS harga_produk,
            p.stok,

            k.id_kategori,
            k.nama_kategori,

            dt.id_detail,
            dt.jumlah,
            dt.harga AS harga_transaksi,
            dt.subtotal

        FROM transaksi t

        INNER JOIN detail_transaksi dt
            ON t.id_transaksi = dt.id_transaksi

        INNER JOIN produk p
            ON dt.id_produk = p.id_produk

        INNER JOIN kategori k
            ON p.id_kategori = k.id_kategori

        WHERE t.status = 'selesai'

        ORDER BY t.tanggal_transaksi
    """)

    with engine.connect() as connection:
        df = pd.read_sql(query, connection)

    return df


def load_product_data():
    """Master produk + stok terkini, termasuk produk yang belum pernah terjual."""

    query = text("""
        SELECT
            p.id_produk,
            p.nama_produk,
            p.stok,
            k.nama_kategori

        FROM produk p

        INNER JOIN kategori k
            ON p.id_kategori = k.id_kategori
    """)

    with engine.connect() as connection:
        df = pd.read_sql(query, connection)

    df["stok"] = pd.to_numeric(df["stok"], errors="coerce").fillna(0)

    return df


# =========================================================
# 2. DATA CLEANING
# =========================================================

def clean_data(df):

    df = df.copy()

    if df.empty:
        return df

    # Konversi tanggal
    df["tanggal_transaksi"] = pd.to_datetime(
        df["tanggal_transaksi"],
        errors="coerce"
    )

    # Konversi kolom numerik
    numeric_columns = [
        "total_transaksi",
        "harga_produk",
        "stok",
        "jumlah",
        "harga_transaksi",
        "subtotal"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # Hapus baris yang tidak mempunyai tanggal
    df = df.dropna(
        subset=["tanggal_transaksi"]
    )

    # Jumlah dan subtotal tidak boleh negatif
    df = df[
        (df["jumlah"] > 0) &
        (df["subtotal"] >= 0)
    ]

    # Hilangkan duplikasi detail transaksi
    df = df.drop_duplicates(
        subset=["id_detail"]
    )

    # Membuat kolom waktu
    df["tanggal"] = df["tanggal_transaksi"].dt.normalize()

    df["bulan"] = (
        df["tanggal_transaksi"]
        .dt.to_period("M")
        .astype(str)
    )

    df["tahun"] = (
        df["tanggal_transaksi"]
        .dt.year
    )

    return df


# =========================================================
# 3. KPI UTAMA
# =========================================================

def calculate_kpis(df):

    if df.empty:
        return {
            "total_omzet": 0,
            "jumlah_transaksi": 0,
            "jumlah_pelanggan": 0,
            "jumlah_produk": 0,
            "rata_rata_transaksi": 0
        }

    total_omzet = df["subtotal"].sum()

    jumlah_transaksi = df[
        "id_transaksi"
    ].nunique()

    jumlah_pelanggan = df[
        "id_pelanggan"
    ].nunique()

    jumlah_produk = df[
        "id_produk"
    ].nunique()

    rata_rata_transaksi = (
        total_omzet / jumlah_transaksi
        if jumlah_transaksi > 0
        else 0
    )

    return {
        "total_omzet": total_omzet,
        "jumlah_transaksi": jumlah_transaksi,
        "jumlah_pelanggan": jumlah_pelanggan,
        "jumlah_produk": jumlah_produk,
        "rata_rata_transaksi": rata_rata_transaksi
    }


# =========================================================
# 4. PRODUK TERLARIS
# =========================================================

def analyze_best_selling_products(df):

    result = (
        df.groupby(
            ["id_produk", "nama_produk"],
            as_index=False
        )
        .agg(
            jumlah_terjual=("jumlah", "sum"),
            omzet=("subtotal", "sum")
        )
        .sort_values(
            "jumlah_terjual",
            ascending=False
        )
    )

    return result


# =========================================================
# 5. PRODUK DENGAN OMZET TERBESAR
# =========================================================

def analyze_top_revenue_products(df):

    result = (
        df.groupby(
            ["id_produk", "nama_produk"],
            as_index=False
        )
        .agg(
            jumlah_terjual=("jumlah", "sum"),
            omzet=("subtotal", "sum")
        )
        .sort_values(
            "omzet",
            ascending=False
        )
    )

    return result


# =========================================================
# 6. PENJUALAN BERDASARKAN KATEGORI
# =========================================================

def analyze_categories(df):

    result = (
        df.groupby(
            ["id_kategori", "nama_kategori"],
            as_index=False
        )
        .agg(
            jumlah_terjual=("jumlah", "sum"),
            omzet=("subtotal", "sum")
        )
        .sort_values(
            "omzet",
            ascending=False
        )
    )

    return result


# =========================================================
# 7. TREN PENJUALAN BULANAN
# =========================================================

def analyze_monthly_sales(df):

    result = (
        df.groupby(
            "bulan",
            as_index=False
        )
        .agg(
            omzet=("subtotal", "sum"),
            jumlah_terjual=("jumlah", "sum"),
            jumlah_transaksi=("id_transaksi", "nunique")
        )
        .sort_values("bulan")
    )

    return result


# =========================================================
# 8. ANALISIS STOK
# =========================================================

def analyze_stock(products, df, period_days):
    """
    products    : master produk + stok terkini (dari load_product_data)
    df          : data penjualan yang SUDAH terfilter
    period_days : lama periode penjualan (hari), untuk hitung laju jual harian
    """

    sales = (
        df.groupby("id_produk", as_index=False)
        .agg(jumlah_terjual=("jumlah", "sum"))
    )

    result = products.merge(
        sales,
        on="id_produk",
        how="left"
    )

    result["jumlah_terjual"] = result["jumlah_terjual"].fillna(0)

    period_days = max(int(period_days), 1)

    result["rata_harian"] = result["jumlah_terjual"] / period_days

    # Perkiraan stok cukup untuk berapa hari
    result["hari_stok"] = np.where(
        result["rata_harian"] > 0,
        result["stok"] / result["rata_harian"],
        np.inf
    )

    # Restock: stok tipis (<= batas minimum) ATAU diperkirakan habis dalam
    # RESTOCK_HARI hari bila laju penjualan tetap
    result["status_stok"] = np.where(
        (result["stok"] <= STOK_MINIMUM) |
        (result["hari_stok"] <= RESTOCK_HARI),
        "Perlu Restock",
        "Aman"
    )

    median_stok = result["stok"].median()
    median_penjualan = result["jumlah_terjual"].median()

    result["status_pergerakan"] = np.where(
        (result["stok"] >= median_stok) &
        (result["jumlah_terjual"] <= median_penjualan),
        "Slow Moving",
        "Normal"
    )

    return result.sort_values("stok", ascending=False)


# =========================================================
# 9. MEMBUAT VISUALISASI
# =========================================================

def create_charts(
    best_products,
    revenue_products,
    categories,
    monthly_sales,
    stock_analysis
):

    # -----------------------------------------
    # Grafik 1
    # Tren omzet
    # -----------------------------------------

    fig = px.line(
        monthly_sales,
        x="bulan",
        y="omzet",
        markers=True,
        title="Tren Omzet Penjualan"
    )

    fig.update_layout(
        xaxis_title="Bulan",
        yaxis_title="Omzet (Rp)"
    )

    fig.write_html(
        os.path.join(
            CHART_DIR,
            "tren_omzet.html"
        )
    )

    # -----------------------------------------
    # Grafik 2
    # Produk terlaris
    # -----------------------------------------

    top_products = best_products.head(10)

    fig = px.bar(
        top_products,
        x="jumlah_terjual",
        y="nama_produk",
        orientation="h",
        title="10 Produk Terlaris"
    )

    fig.update_layout(
        xaxis_title="Jumlah Terjual",
        yaxis_title="Produk"
    )

    fig.write_html(
        os.path.join(
            CHART_DIR,
            "produk_terlaris.html"
        )
    )

    # -----------------------------------------
    # Grafik 3
    # Produk omzet terbesar
    # -----------------------------------------

    top_revenue = revenue_products.head(10)

    fig = px.bar(
        top_revenue,
        x="omzet",
        y="nama_produk",
        orientation="h",
        title="10 Produk dengan Omzet Terbesar"
    )

    fig.update_layout(
        xaxis_title="Omzet (Rp)",
        yaxis_title="Produk"
    )

    fig.write_html(
        os.path.join(
            CHART_DIR,
            "produk_omzet_terbesar.html"
        )
    )

    # -----------------------------------------
    # Grafik 4
    # Penjualan kategori
    # -----------------------------------------

    fig = px.pie(
        categories,
        names="nama_kategori",
        values="omzet",
        hole=0.4,
        title="Omzet Berdasarkan Kategori"
    )

    fig.write_html(
        os.path.join(
            CHART_DIR,
            "penjualan_kategori.html"
        )
    )

    # -----------------------------------------
    # Grafik 5
    # Stok vs penjualan
    # -----------------------------------------

    fig = px.scatter(
        stock_analysis,
        x="stok",
        y="jumlah_terjual",
        text="nama_produk",
        title="Hubungan Stok dan Penjualan"
    )

    fig.update_traces(
        textposition="top center"
    )

    fig.update_layout(
        xaxis_title="Stok Saat Ini",
        yaxis_title="Jumlah Terjual"
    )

    fig.write_html(
        os.path.join(
            CHART_DIR,
            "stok_vs_penjualan.html"
        )
    )

    print("\n5 visualisasi berhasil dibuat.")


# =========================================================
# 10. FORMAT BANTUAN
# =========================================================

HARI_ID = {
    0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
    4: "Jumat", 5: "Sabtu", 6: "Minggu"
}

BULAN_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}


def rp(value):
    """Format rupiah: 1234567 -> Rp1.234.567"""
    return "Rp" + f"{value:,.0f}".replace(",", ".")


def nama_bulan(periode):
    """'2026-08' -> 'Agustus 2026'"""
    tahun, bulan = periode.split("-")
    return f"{BULAN_ID[int(bulan)]} {tahun}"


def _daftar(names, limit=3):
    names = list(names)[:limit]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " dan " + names[-1]


# =========================================================
# 11. JAWABAN EDA (8 PERTANYAAN) + INTERPRETASI
# =========================================================

def build_eda_answers(
    df,
    kpis,
    best_products,
    revenue_products,
    categories,
    monthly_sales,
    stock_analysis
):
    """
    Mengembalikan list dict {pertanyaan, jawaban, interpretasi}
    untuk 8 pertanyaan EDA yang diminta tugas.
    """

    if df.empty:
        return []

    answers = []

    total_omzet = kpis["total_omzet"]
    total_unit = df["jumlah"].sum()

    # ---- 1. Produk paling banyak terjual -------------------------------
    top = best_products.head(3)
    p1 = top.iloc[0]
    share_unit = p1["jumlah_terjual"] / total_unit * 100

    answers.append({
        "pertanyaan": "Produk apa yang paling banyak terjual?",
        "jawaban": (
            f"{p1['nama_produk']} ({p1['jumlah_terjual']:.0f} unit). "
            f"Berikutnya: {_daftar(top['nama_produk'].iloc[1:])}."
        ),
        "interpretasi": (
            f"Produk ini menyumbang {share_unit:.1f}% dari seluruh unit terjual. "
            f"Produk dengan perputaran tinggi seperti ini perlu dijaga "
            f"ketersediaannya agar tidak kehilangan penjualan."
        )
    })

    # ---- 2. Produk omzet terbesar --------------------------------------
    r1 = revenue_products.iloc[0]
    share_omzet = r1["omzet"] / total_omzet * 100
    rank_unit = int(
        (best_products["jumlah_terjual"] > r1["jumlah_terjual"]).sum() + 1
    )

    if rank_unit > 3:
        catatan = (
            f"Produk ini hanya peringkat {rank_unit} dari sisi jumlah unit, "
            f"tetapi harga satuannya tinggi sehingga omzetnya besar. "
            f"Artinya produk terlaris belum tentu penyumbang omzet terbesar."
        )
    else:
        catatan = (
            "Produk ini kuat di jumlah unit sekaligus omzet, "
            "sehingga menjadi produk andalan toko."
        )

    answers.append({
        "pertanyaan": "Produk apa yang menghasilkan omzet terbesar?",
        "jawaban": (
            f"{r1['nama_produk']} dengan omzet {rp(r1['omzet'])} "
            f"({share_omzet:.1f}% dari total omzet)."
        ),
        "interpretasi": catatan
    })

    # ---- 3. Kategori penjualan tertinggi -------------------------------
    c1 = categories.iloc[0]
    share_cat = c1["omzet"] / total_omzet * 100
    top3_share = categories["omzet"].head(3).sum() / total_omzet * 100

    answers.append({
        "pertanyaan": "Kategori apa yang memiliki penjualan tertinggi?",
        "jawaban": (
            f"{c1['nama_kategori']} dengan omzet {rp(c1['omzet'])} "
            f"({share_cat:.1f}% dari total)."
        ),
        "interpretasi": (
            f"Tiga kategori teratas menguasai {top3_share:.0f}% omzet, "
            f"sehingga stok dan promosi sebaiknya difokuskan pada kategori tersebut."
            if len(categories) > 3 else
            f"Kategori ini menjadi sumber omzet utama pada periode yang dipilih."
        )
    })

    # ---- 4. Periode penjualan tertinggi --------------------------------
    best_month = monthly_sales.loc[monthly_sales["omzet"].idxmax()]
    rata_bulan = monthly_sales["omzet"].mean()

    weekday = (
        df.assign(hari=df["tanggal"].dt.dayofweek)
        .groupby("hari")["subtotal"].sum()
    )
    hari_top = HARI_ID[int(weekday.idxmax())]

    if len(monthly_sales) > 1:
        selisih = (best_month["omzet"] / rata_bulan - 1) * 100
        interp_period = (
            f"Omzet bulan puncak {selisih:.0f}% di atas rata-rata bulanan "
            f"({rp(rata_bulan)}). Hari dengan omzet terbesar adalah {hari_top}. "
            f"Pola ini dapat dipakai untuk menyiapkan stok sebelum periode ramai."
        )
    else:
        interp_period = (
            f"Hanya satu bulan pada data terfilter. "
            f"Hari dengan omzet terbesar adalah {hari_top}."
        )

    answers.append({
        "pertanyaan": "Kapan periode penjualan tertinggi?",
        "jawaban": (
            f"{nama_bulan(best_month['bulan'])} "
            f"dengan omzet {rp(best_month['omzet'])}."
        ),
        "interpretasi": interp_period
    })

    # ---- 5. Stok tinggi, penjualan rendah ------------------------------
    slow = stock_analysis[
        stock_analysis["status_pergerakan"] == "Slow Moving"
    ].sort_values("stok", ascending=False)

    if not slow.empty:
        s_top = slow.head(3)
        detail = "; ".join(
            f"{r.nama_produk} (stok {r.stok:.0f}, terjual {r.jumlah_terjual:.0f})"
            for r in s_top.itertuples()
        )
        jawaban5 = f"{len(slow)} produk, antara lain {detail}."
        interp5 = (
            "Stok yang menumpuk mengikat modal dan ruang gudang. "
            "Pertimbangkan promo, bundling, atau tunda pembelian ulang "
            "untuk produk-produk ini."
        )
    else:
        jawaban5 = "Tidak ada produk yang terindikasi slow moving."
        interp5 = "Perputaran stok relatif sehat pada periode ini."

    answers.append({
        "pertanyaan": "Produk apa yang memiliki stok tinggi tetapi penjualannya rendah?",
        "jawaban": jawaban5,
        "interpretasi": interp5
    })

    # ---- 6. Perlu restock ----------------------------------------------
    restock = stock_analysis[
        stock_analysis["status_stok"] == "Perlu Restock"
    ].sort_values("hari_stok")

    if not restock.empty:
        detail = "; ".join(
            (
                f"{r.nama_produk} (stok {r.stok:.0f}, habis ±{r.hari_stok:.0f} hari)"
                if np.isfinite(r.hari_stok)
                else f"{r.nama_produk} (stok {r.stok:.0f})"
            )
            for r in restock.head(5).itertuples()
        )
        jawaban6 = f"{len(restock)} produk: {detail}."
        interp6 = (
            f"Restock diprioritaskan dari yang paling cepat habis. "
            f"Aturan: stok ≤ {STOK_MINIMUM} unit atau diperkirakan habis "
            f"dalam ≤ {RESTOCK_HARI} hari pada laju penjualan periode ini."
        )
    else:
        jawaban6 = "Belum ada produk yang perlu segera di-restock."
        interp6 = "Seluruh stok masih cukup untuk laju penjualan saat ini."

    answers.append({
        "pertanyaan": "Produk apa yang perlu segera dilakukan restock?",
        "jawaban": jawaban6,
        "interpretasi": interp6
    })

    # ---- 7. Rata-rata nilai transaksi ----------------------------------
    per_trx = df.groupby("id_transaksi")["subtotal"].sum()
    rata = per_trx.mean()
    median = per_trx.median()

    if rata > median * 1.2:
        interp7 = (
            "Rata-rata lebih tinggi dari median, artinya sebagian kecil "
            "transaksi bernilai sangat besar menarik angka rata-rata naik. "
            "Median lebih mewakili transaksi pelanggan pada umumnya."
        )
    else:
        interp7 = (
            "Rata-rata dan median berdekatan, artinya nilai transaksi "
            "cukup merata antar pelanggan."
        )

    answers.append({
        "pertanyaan": "Berapa rata-rata nilai transaksi?",
        "jawaban": (
            f"{rp(rata)} per transaksi (median {rp(median)}, "
            f"terbesar {rp(per_trx.max())})."
        ),
        "interpretasi": interp7
    })

    # ---- 8. Perkembangan penjualan -------------------------------------
    if len(monthly_sales) >= 2:
        first = monthly_sales.iloc[0]
        last = monthly_sales.iloc[-1]
        x = np.arange(len(monthly_sales))
        slope = np.polyfit(x, monthly_sales["omzet"].values, 1)[0]
        slope_pct = slope / rata_bulan * 100

        if slope_pct > 3:
            arah = "cenderung naik"
        elif slope_pct < -3:
            arah = "cenderung turun"
        else:
            arah = "relatif stagnan"

        perubahan = (
            (last["omzet"] / first["omzet"] - 1) * 100
            if first["omzet"] > 0 else 0
        )

        cv = monthly_sales["omzet"].std() / rata_bulan * 100
        fluktuasi = (
            "Fluktuasi antar bulan cukup besar, sehingga perencanaan stok "
            "tidak bisa hanya bertumpu pada satu bulan sebelumnya."
            if cv > 20 else
            "Fluktuasi antar bulan kecil, penjualan tergolong stabil."
        )

        answers.append({
            "pertanyaan": "Bagaimana perkembangan penjualan dari waktu ke waktu?",
            "jawaban": (
                f"Secara umum {arah}. Dari {nama_bulan(first['bulan'])} "
                f"({rp(first['omzet'])}) ke {nama_bulan(last['bulan'])} "
                f"({rp(last['omzet'])}) berubah {perubahan:+.0f}%."
            ),
            "interpretasi": (
                f"Garis tren linear menunjukkan perubahan omzet sekitar "
                f"{slope_pct:+.1f}% dari rata-rata bulanan setiap bulan. "
                f"{fluktuasi}"
            )
        })
    else:
        answers.append({
            "pertanyaan": "Bagaimana perkembangan penjualan dari waktu ke waktu?",
            "jawaban": "Data terfilter hanya mencakup satu bulan.",
            "interpretasi": "Perluas rentang tanggal untuk melihat tren."
        })

    return answers


# =========================================================
# 12. CATATAN INTERPRETASI UNTUK TIAP GRAFIK
# =========================================================

def build_chart_notes(
    best_products,
    revenue_products,
    categories,
    monthly_sales,
    stock_analysis
):
    notes = {}

    if len(monthly_sales) >= 2:
        hi = monthly_sales.loc[monthly_sales["omzet"].idxmax()]
        lo = monthly_sales.loc[monthly_sales["omzet"].idxmin()]
        notes["sales"] = (
            f"Omzet tertinggi terjadi pada {nama_bulan(hi['bulan'])} "
            f"({rp(hi['omzet'])}) dan terendah pada {nama_bulan(lo['bulan'])} "
            f"({rp(lo['omzet'])}). Pantau bulan-bulan rendah untuk mencari "
            f"penyebabnya, misalnya stok kosong atau musim sepi."
        )

    if not best_products.empty:
        notes["products"] = (
            f"{best_products.iloc[0]['nama_produk']} paling laku berdasarkan "
            f"jumlah unit. Produk di daftar ini adalah prioritas ketersediaan stok."
        )

    if not revenue_products.empty:
        notes["revenue"] = (
            f"{revenue_products.iloc[0]['nama_produk']} menyumbang omzet "
            f"terbesar. Bandingkan dengan grafik terlaris: produk berharga "
            f"tinggi bisa unggul di omzet meski unitnya lebih sedikit."
        )

    if not categories.empty:
        share = categories.iloc[0]["omzet"] / categories["omzet"].sum() * 100
        notes["category"] = (
            f"Kategori {categories.iloc[0]['nama_kategori']} memberi "
            f"{share:.0f}% omzet. Kategori berporsi kecil adalah kandidat "
            f"untuk promosi atau evaluasi ragam produk."
        )

    if not stock_analysis.empty:
        notes["stock"] = (
            "Produk di kanan bawah (stok besar, penjualan kecil) adalah "
            "slow moving. Produk di kiri atas (stok kecil, penjualan besar) "
            "paling berisiko kehabisan."
        )

    return notes


# =========================================================
# 13. MEMBUAT INSIGHT
# =========================================================

def generate_insights(
    kpis,
    best_products,
    revenue_products,
    categories,
    monthly_sales,
    stock_analysis
):

    insights = []

    if best_products.empty:
        return insights

    total_omzet = kpis["total_omzet"]

    # 1. Produk terlaris vs omzet terbesar
    p = best_products.iloc[0]
    r = revenue_products.iloc[0]

    if p["id_produk"] != r["id_produk"]:
        insights.append(
            f"{p['nama_produk']} paling laku ({p['jumlah_terjual']:.0f} unit), "
            f"tetapi omzet terbesar justru dari {r['nama_produk']} "
            f"({rp(r['omzet'])}). Produk berharga tinggi layak mendapat "
            f"perhatian khusus walau volumenya lebih kecil."
        )
    else:
        insights.append(
            f"{p['nama_produk']} unggul di jumlah unit ({p['jumlah_terjual']:.0f}) "
            f"sekaligus omzet ({rp(r['omzet'])}), sehingga menjadi produk "
            f"andalan yang stoknya harus selalu aman."
        )

    # 2. Konsentrasi omzet
    top5_share = revenue_products["omzet"].head(5).sum() / total_omzet * 100
    insights.append(
        f"Lima produk teratas menyumbang {top5_share:.0f}% dari total omzet "
        f"({rp(total_omzet)}). Omzet toko cukup bergantung pada produk-produk ini."
    )

    # 3. Kategori
    if not categories.empty:
        c = categories.iloc[0]
        share = c["omzet"] / total_omzet * 100
        insights.append(
            f"Kategori {c['nama_kategori']} memimpin dengan {rp(c['omzet'])} "
            f"({share:.0f}% omzet). Kategori dengan kontribusi terkecil "
            f"adalah {categories.iloc[-1]['nama_kategori']}."
        )

    # 4. Periode
    if len(monthly_sales) >= 2:
        hi = monthly_sales.loc[monthly_sales["omzet"].idxmax()]
        lo = monthly_sales.loc[monthly_sales["omzet"].idxmin()]
        gap = (hi["omzet"] / lo["omzet"] - 1) * 100 if lo["omzet"] > 0 else 0
        insights.append(
            f"Penjualan tertinggi pada {nama_bulan(hi['bulan'])} "
            f"({rp(hi['omzet'])}), {gap:.0f}% lebih besar daripada bulan "
            f"terendah ({nama_bulan(lo['bulan'])}). Siapkan stok lebih "
            f"sebelum periode ramai."
        )

    # 5. Slow moving
    slow = stock_analysis[
        stock_analysis["status_pergerakan"] == "Slow Moving"
    ].sort_values("stok", ascending=False)

    if not slow.empty:
        insights.append(
            f"{len(slow)} produk terindikasi slow moving, antara lain "
            f"{_daftar(slow['nama_produk'])}. Stoknya tinggi tetapi "
            f"penjualannya rendah, pertimbangkan promo atau tunda pembelian ulang."
        )

    # 6. Restock
    restock = stock_analysis[
        stock_analysis["status_stok"] == "Perlu Restock"
    ].sort_values("hari_stok")

    if not restock.empty:
        first = restock.iloc[0]
        extra = (
            f", diperkirakan habis dalam ±{first['hari_stok']:.0f} hari"
            if np.isfinite(first["hari_stok"]) else ""
        )
        insights.append(
            f"{len(restock)} produk perlu restock. Paling mendesak: "
            f"{first['nama_produk']} (stok {first['stok']:.0f}{extra}). "
            f"Daftar lengkap ada di tabel stok rendah."
        )

    # 7. Nilai transaksi
    insights.append(
        f"Rata-rata nilai transaksi {rp(kpis['rata_rata_transaksi'])} dari "
        f"{kpis['jumlah_transaksi']} transaksi. Menaikkan nilai per transaksi "
        f"(bundling, paket proyek) adalah cara paling cepat menambah omzet."
    )

    return insights


# =========================================================
# 14. SIMPAN HASIL ANALISIS
# =========================================================

def save_results(
    df,
    best_products,
    revenue_products,
    categories,
    monthly_sales,
    stock_analysis
):

    df.to_csv(
        os.path.join(
            CSV_DIR,
            "sales_data.csv"
        ),
        index=False
    )

    best_products.to_csv(
        os.path.join(
            CSV_DIR,
            "produk_terlaris.csv"
        ),
        index=False
    )

    revenue_products.to_csv(
        os.path.join(
            CSV_DIR,
            "produk_omzet_terbesar.csv"
        ),
        index=False
    )

    categories.to_csv(
        os.path.join(
            CSV_DIR,
            "penjualan_kategori.csv"
        ),
        index=False
    )

    monthly_sales.to_csv(
        os.path.join(
            CSV_DIR,
            "tren_penjualan.csv"
        ),
        index=False
    )

    stock_analysis.to_csv(
        os.path.join(
            CSV_DIR,
            "analisis_stok.csv"
        ),
        index=False
    )


# =========================================================
# 15. MAIN
# =========================================================

def main():

    print("=" * 60)
    print("EDA TOKO BANGUNAN SINAR JAYA")
    print("=" * 60)

    print("\n[1] Mengambil data dari database...")

    df = load_sales_data()

    if df.empty:

        print(
            "Data transaksi tidak ditemukan."
        )

        return

    print(
        f"Data berhasil diambil: "
        f"{len(df)} baris"
    )

    print("\n[2] Membersihkan data...")

    df = clean_data(df)

    print(
        f"Data setelah cleaning: "
        f"{len(df)} baris"
    )

    print("\n[3] Menghitung KPI...")

    kpis = calculate_kpis(df)

    print(
        f"Total omzet          : "
        f"Rp{kpis['total_omzet']:,.0f}"
    )

    print(
        f"Jumlah transaksi     : "
        f"{kpis['jumlah_transaksi']}"
    )

    print(
        f"Jumlah pelanggan     : "
        f"{kpis['jumlah_pelanggan']}"
    )

    print(
        f"Jumlah produk        : "
        f"{kpis['jumlah_produk']}"
    )

    print(
        f"Rata-rata transaksi  : "
        f"Rp{kpis['rata_rata_transaksi']:,.0f}"
    )

    print("\n[4] Menganalisis produk terlaris...")

    best_products = analyze_best_selling_products(df)

    print(
        best_products.head(10).to_string(
            index=False
        )
    )

    print("\n[5] Menganalisis omzet produk...")

    revenue_products = analyze_top_revenue_products(df)

    print(
        revenue_products.head(10).to_string(
            index=False
        )
    )

    print("\n[6] Menganalisis kategori...")

    categories = analyze_categories(df)

    print(
        categories.to_string(
            index=False
        )
    )

    print("\n[7] Menganalisis tren penjualan...")

    monthly_sales = analyze_monthly_sales(df)

    print(
        monthly_sales.to_string(
            index=False
        )
    )

    print("\n[8] Menganalisis stok...")

    products = load_product_data()
    period_days = (df["tanggal"].max() - df["tanggal"].min()).days + 1
    stock_analysis = analyze_stock(products, df, period_days)

    print(
        stock_analysis.to_string(
            index=False
        )
    )

    print("\n[9] Membuat visualisasi...")

    create_charts(
        best_products,
        revenue_products,
        categories,
        monthly_sales,
        stock_analysis
    )

    print("\n[10] Membuat insight...")

    insights = generate_insights(
        kpis,
        best_products,
        revenue_products,
        categories,
        monthly_sales,
        stock_analysis
    )

    print("\n" + "=" * 60)
    print("HASIL INSIGHT")
    print("=" * 60)

    for number, insight in enumerate(
        insights,
        start=1
    ):
        print(
            f"{number}. {insight}"
        )

    print("\n[11] Menyimpan hasil analisis...")

    save_results(
        df,
        best_products,
        revenue_products,
        categories,
        monthly_sales,
        stock_analysis
    )

    print(
        "\nEDA selesai."
    )


if __name__ == "__main__":
    main()