from flask import Flask, render_template, request
import pandas as pd
import plotly
import plotly.express as px
import json

from analysis.eda import (
    load_sales_data,
    load_product_data,
    clean_data,
    calculate_kpis,
    analyze_best_selling_products,
    analyze_top_revenue_products,
    analyze_categories,
    analyze_monthly_sales,
    analyze_stock,
    generate_insights,
    build_eda_answers,
    build_chart_notes
)


app = Flask(__name__)


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
def dashboard():

    # -----------------------------------------
    # Ambil parameter filter (tetap sebagai string untuk form)
    # -----------------------------------------

    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    selected_category = request.args.get("category", "").strip()

    filter_notes = []

    # -----------------------------------------
    # Load data
    # -----------------------------------------

    df = clean_data(load_sales_data())
    products = load_product_data()

    # -----------------------------------------
    # Data untuk pilihan kategori (diambil dari master produk,
    # bukan dari data yang terfilter)
    # -----------------------------------------

    categories_filter = sorted(
        products["nama_kategori"].dropna().unique().tolist()
    )

    if selected_category and selected_category not in categories_filter:
        filter_notes.append(
            f"Kategori '{selected_category}' tidak dikenal, filter kategori diabaikan."
        )
        selected_category = ""

    # -----------------------------------------
    # Filter tanggal
    # -----------------------------------------

    start_ts = pd.to_datetime(start_date, errors="coerce") if start_date else pd.NaT
    end_ts = pd.to_datetime(end_date, errors="coerce") if end_date else pd.NaT

    if start_date and pd.isna(start_ts):
        filter_notes.append("Format tanggal mulai tidak valid, filter diabaikan.")
        start_date = ""

    if end_date and pd.isna(end_ts):
        filter_notes.append("Format tanggal akhir tidak valid, filter diabaikan.")
        end_date = ""

    # Jika terbalik, tukar otomatis
    if pd.notna(start_ts) and pd.notna(end_ts) and start_ts > end_ts:
        start_ts, end_ts = end_ts, start_ts
        start_date, end_date = end_date, start_date
        filter_notes.append("Tanggal mulai lebih besar dari tanggal akhir, keduanya ditukar.")

    if pd.notna(start_ts):
        df = df[df["tanggal"] >= start_ts]

    if pd.notna(end_ts):
        # inklusif sampai akhir hari
        df = df[df["tanggal"] <= end_ts]

    # -----------------------------------------
    # Filter kategori (juga diterapkan ke master produk
    # agar analisis stok ikut terfilter)
    # -----------------------------------------

    if selected_category:
        df = df[df["nama_kategori"] == selected_category]
        products = products[products["nama_kategori"] == selected_category]

    # -----------------------------------------
    # Status data
    # -----------------------------------------

    filtered_rows = len(df)
    has_data = not df.empty

    # Lama periode untuk hitung laju penjualan harian
    if pd.notna(start_ts) or pd.notna(end_ts):
        first_day = start_ts if pd.notna(start_ts) else (
            df["tanggal"].min() if has_data else pd.Timestamp.today().normalize()
        )
        last_day = end_ts if pd.notna(end_ts) else (
            df["tanggal"].max() if has_data else first_day
        )
    else:
        first_day = df["tanggal"].min() if has_data else pd.Timestamp.today().normalize()
        last_day = df["tanggal"].max() if has_data else first_day

    period_days = (last_day - first_day).days + 1

    # -----------------------------------------
    # KPI
    # -----------------------------------------

    kpis = calculate_kpis(df)

    # -----------------------------------------
    # Analisis
    # -----------------------------------------

    best_products = analyze_best_selling_products(df)

    revenue_products = analyze_top_revenue_products(df)

    categories = analyze_categories(df)

    monthly_sales = analyze_monthly_sales(df)

    stock_analysis = analyze_stock(products, df, period_days)

    insights = generate_insights(
        kpis,
        best_products,
        revenue_products,
        categories,
        monthly_sales,
        stock_analysis
    )

    eda_answers = build_eda_answers(
        df,
        kpis,
        best_products,
        revenue_products,
        categories,
        monthly_sales,
        stock_analysis
    )

    chart_notes = build_chart_notes(
        best_products,
        revenue_products,
        categories,
        monthly_sales,
        stock_analysis
    ) if has_data else {}

    # =====================================================
    # VISUALISASI
    # =====================================================

    # -----------------------------------------
    # 1. Tren omzet
    # -----------------------------------------

    fig_sales = px.line(
        monthly_sales,
        x="bulan",
        y="omzet",
        markers=True,
        title="Tren Omzet Penjualan"
    )

    fig_sales.update_layout(
        xaxis_title="Bulan",
        yaxis_title="Omzet (Rp)",
        yaxis_tickprefix="Rp ",
        yaxis_tickformat=",.0f",
        separators=",.",
        template="plotly_white",
        margin=dict(
            l=20,
            r=20,
            t=50,
            b=20
        )
    )

    graph_sales = json.dumps(
        fig_sales,
        cls=plotly.utils.PlotlyJSONEncoder
    )

    # -----------------------------------------
    # 2. Produk terlaris
    # -----------------------------------------

    top_products = best_products.head(10)

    fig_products = px.bar(
        top_products,
        x="jumlah_terjual",
        y="nama_produk",
        orientation="h",
        title="Produk Terlaris"
    )

    fig_products.update_yaxes(autorange="reversed")

    fig_products.update_layout(
        xaxis_title="Jumlah terjual (unit)",
        yaxis_title="",
        template="plotly_white",
        margin=dict(
            l=20,
            r=20,
            t=50,
            b=20
        )
    )

    graph_products = json.dumps(
        fig_products,
        cls=plotly.utils.PlotlyJSONEncoder
    )

    # -----------------------------------------
    # 3. Produk omzet terbesar
    # -----------------------------------------

    top_revenue = revenue_products.head(10)

    fig_revenue = px.bar(
        top_revenue,
        x="omzet",
        y="nama_produk",
        orientation="h",
        title="Produk dengan Omzet Terbesar"
    )

    fig_revenue.update_yaxes(autorange="reversed")

    fig_revenue.update_layout(
        xaxis_title="Omzet (Rp)",
        xaxis_tickprefix="Rp ",
        xaxis_tickformat=",.0f",
        separators=",.",
        yaxis_title="",
        template="plotly_white",
        margin=dict(
            l=20,
            r=20,
            t=50,
            b=20
        )
    )

    graph_revenue = json.dumps(
        fig_revenue,
        cls=plotly.utils.PlotlyJSONEncoder
    )

    # -----------------------------------------
    # 4. Kategori
    # -----------------------------------------

    fig_category = px.pie(
        categories,
        names="nama_kategori",
        values="omzet",
        hole=0.45,
        title="Penjualan Berdasarkan Kategori"
    )

    fig_category.update_layout(
        template="plotly_white",
        margin=dict(
            l=20,
            r=20,
            t=50,
            b=20
        )
    )

    graph_category = json.dumps(
        fig_category,
        cls=plotly.utils.PlotlyJSONEncoder
    )

    # -----------------------------------------
    # 5. Stok vs penjualan
    # -----------------------------------------

    fig_stock = px.scatter(
        stock_analysis,
        x="stok",
        y="jumlah_terjual",
        text="nama_produk",
        title="Stok vs Penjualan"
    )

    fig_stock.update_traces(
        textposition="top center"
    )

    fig_stock.update_layout(
        xaxis_title="Stok saat ini (unit)",
        yaxis_title="Jumlah terjual (unit)",
        template="plotly_white",
        margin=dict(
            l=20,
            r=20,
            t=50,
            b=20
        )
    )

    graph_stock = json.dumps(
        fig_stock,
        cls=plotly.utils.PlotlyJSONEncoder
    )

    # =====================================================
    # TABEL
    # =====================================================

    # Produk stok rendah
    low_stock = stock_analysis[
        stock_analysis["status_stok"]
        == "Perlu Restock"
    ].copy()

    low_stock["hari_stok"] = (
        low_stock["hari_stok"]
        .replace([float("inf")], float("nan"))
        .round(0)
    )

    # Slow moving
    slow_moving = stock_analysis[
        stock_analysis["status_pergerakan"]
        == "Slow Moving"
    ].copy()

    # =====================================================
    # RENDER
    # =====================================================

    return render_template(
        "dashboard.html",

        kpis=kpis,

        graph_sales=graph_sales,
        graph_products=graph_products,
        graph_revenue=graph_revenue,
        graph_category=graph_category,
        graph_stock=graph_stock,

        low_stock=low_stock.to_dict(
            orient="records"
        ),

        slow_moving=slow_moving.to_dict(
            orient="records"
        ),

        insights=insights,
        eda_answers=eda_answers,
        chart_notes=chart_notes,

         # Filter
        categories_filter=categories_filter,
        selected_category=selected_category,
        start_date=start_date,
        end_date=end_date,

        filtered_rows=filtered_rows,
        has_data=has_data,
        filter_notes=filter_notes
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    app.run(
        debug=True
    )