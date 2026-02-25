import pandas as pd
import plotly.express as px
from io import StringIO

# =========================================================
# Peta Interaktif FTF Knowledge Hub (Template + Sample Data)
# =========================================================
# Cara pakai:
# 1) Jalankan file ini untuk melihat contoh peta interaktif (sample data).
# 2) Ganti DATA_CSV dengan hasil ekstraksi manual dari country pages / PDF FTF Hub.
# 3) Simpan HTML output dan buka di browser.
#
# Catatan:
# - Data default di bawah ini adalah SAMPLE (subset) untuk demo visualisasi.
# - Gunakan ISO-3 country code agar pemetaan akurat.
# =========================================================

DATA_CSV = """country,iso3,region,last_updated,ftf_departed_min,ftf_departed_max,ftf_returned_min,ftf_returned_max,update_status,data_completeness,source_note
Tunisia,TUN,Africa,2025-12-01,3000,7000,970,1500,Updated,Q1 2026 snippet,Tunisia PDF snippet (search result)
Turkey,TUR,Europe/Asia,2025-08-01,5000,6581,600,600,Needs Update,Q1 2026 snippet,Turkiye PDF snippet (search result)
Australia,AUS,Oceania,2025-12-01,230,230,44,44,Updated,Q1 2026 snippet,Australia PDF snippet (search result)
Algeria,DZA,Africa,2025-12-01,785,500,87,150,Updated,Q1 2026 snippet,Algeria PDF snippet (range/order in snippet may need manual verification)
Indonesia,IDN,Asia,2024-02-01,,,,,Needs Review,Country page available,Country page found via FTF Hub search result
Germany,DEU,Europe,2024-02-01,,,,,Needs Review,Country page available,Country page found via FTF Hub search result
France,FRA,Europe,2024-02-01,,,,,Needs Review,Country page available,Country page found via FTF Hub search result
Netherlands,NLD,Europe,2024-02-01,,,,,Needs Review,Country page available,Country page found via FTF Hub search result
Sweden,SWE,Europe,2024-02-01,,,,,Needs Review,Country page available,Country page found via FTF Hub search result
Denmark,DNK,Europe,2024-02-01,,,,,Needs Review,Country page available,Country page found via FTF Hub search result
Saudi Arabia,SAU,Middle East,2024-02-01,,,,,Needs Review,Country page available,Country page found via FTF Hub search result
United Arab Emirates,ARE,Middle East,2024-02-01,,,,,Needs Review,Country page available,Country page found via FTF Hub search result
"""


def load_data() -> pd.DataFrame:
    df = pd.read_csv(StringIO(DATA_CSV))
    df["last_updated"] = pd.to_datetime(df["last_updated"], errors="coerce")

    # numeric coercion
    for c in ["ftf_departed_min", "ftf_departed_max", "ftf_returned_min", "ftf_returned_max"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # midpoint helper (for choropleth coloring)
    def midpoint(a, b):
        if pd.notna(a) and pd.notna(b):
            return (a + b) / 2
        if pd.notna(a):
            return a
        if pd.notna(b):
            return b
        return pd.NA

    df["departed_mid"] = [midpoint(a, b) for a, b in zip(df["ftf_departed_min"], df["ftf_departed_max"])]
    df["returned_mid"] = [midpoint(a, b) for a, b in zip(df["ftf_returned_min"], df["ftf_returned_max"])]
    df["has_quant"] = df["departed_mid"].notna()
    df["days_since_update"] = (pd.Timestamp.today().normalize() - df["last_updated"]).dt.days
    return df


def build_choropleth(df: pd.DataFrame):
    color_col = "departed_mid"

    # Hover text yang lebih informatif
    hover_cols = {
        "country": True,
        "region": True,
        "last_updated": True,
        "ftf_departed_min": True,
        "ftf_departed_max": True,
        "ftf_returned_min": True,
        "ftf_returned_max": True,
        "update_status": True,
        "data_completeness": True,
        "source_note": True,
        "departed_mid": ':.0f',
        "returned_mid": ':.0f',
    }

    fig = px.choropleth(
        df,
        locations="iso3",
        color=color_col,
        hover_name="country",
        hover_data=hover_cols,
        color_continuous_scale="YlOrRd",
        title="Peta Interaktif FTF Knowledge Hub (Sample/Template) — Estimasi FTF Departed (midpoint range)",
    )

    fig.update_geos(showcoastlines=True, coastlinecolor="gray", showframe=False, projection_type="natural earth")
    fig.update_layout(
        margin=dict(l=20, r=20, t=60, b=20),
        coloraxis_colorbar_title="Departed (mid)",
    )
    return fig


def build_status_scatter(df: pd.DataFrame):
    # Titik overlay untuk menunjukkan status pembaruan / kelengkapan data
    plot_df = df.copy()
    # Plotly scatter_geo butuh lat/lon; kita manfaatkan built-in country location via country names using locationmode='country names'
    fig = px.scatter_geo(
        plot_df,
        locations="country",
        locationmode="country names",
        color="update_status",
        symbol="has_quant",
        hover_name="country",
        hover_data={
            "region": True,
            "last_updated": True,
            "data_completeness": True,
            "days_since_update": True,
            "source_note": True,
            "has_quant": True,
        },
        title="Overlay Status Pembaruan & Ketersediaan Data Kuantitatif",
    )
    fig.update_geos(showcoastlines=True, coastlinecolor="gray", showframe=False)
    fig.update_layout(margin=dict(l=20, r=20, t=60, b=20))
    return fig


def export_html(fig, filename: str):
    fig.write_html(filename, include_plotlyjs="cdn")
    print(f"Saved: {filename}")


def main():
    df = load_data()
    print("Preview data:")
    print(df[["country", "iso3", "last_updated", "departed_mid", "returned_mid", "update_status", "has_quant"]].to_string(index=False))

    choropleth = build_choropleth(df)
    status_map = build_status_scatter(df)

    export_html(choropleth, "ftf_map_choropleth.html")
    export_html(status_map, "ftf_map_status_overlay.html")

    # Optional interactive window in notebook/local python
    # choropleth.show()
    # status_map.show()


if __name__ == "__main__":
    main()
