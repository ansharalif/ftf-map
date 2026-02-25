from io import StringIO
import sys
import pandas as pd

# =========================================================
# Peta Interaktif FTF Knowledge Hub (Template + Sample Data)
# Robust version with graceful fallback when plotly is unavailable
# =========================================================
# Solusi error umum di Streamlit Cloud:
# - Tambahkan `plotly` ke requirements.txt
# - Jika plotly belum tersedia, app tetap jalan dengan fallback tabel + ringkasan
# =========================================================

try:
    import plotly.express as px  # type: ignore
    PLOTLY_AVAILABLE = True
except ModuleNotFoundError:
    px = None
    PLOTLY_AVAILABLE = False

try:
    import streamlit as st  # optional if running as Streamlit app
    STREAMLIT_AVAILABLE = True
except ModuleNotFoundError:
    st = None
    STREAMLIT_AVAILABLE = False

DATA_CSV = """country,iso3,region,last_updated,ftf_departed_min,ftf_departed_max,ftf_returned_min,ftf_returned_max,update_status,data_completeness,source_note
Tunisia,TUN,Africa,2025-12-01,3000,7000,970,1500,Updated,Q1 2026 snippet,Tunisia PDF snippet (search result)
Turkey,TUR,Europe/Asia,2025-08-01,5000,6581,600,600,Needs Update,Q1 2026 snippet,Turkiye PDF snippet (search result)
Australia,AUS,Oceania,2025-12-01,230,230,44,44,Updated,Q1 2026 snippet,Australia PDF snippet (search result)
Algeria,DZA,Africa,2025-12-01,500,785,87,150,Updated,Q1 2026 snippet,Algeria PDF snippet (search result)
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
    num_cols = ["ftf_departed_min", "ftf_departed_max", "ftf_returned_min", "ftf_returned_max"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

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
    today = pd.Timestamp.today().normalize()
    df["days_since_update"] = (today - df["last_updated"]).dt.days
    return df


def build_choropleth(df: pd.DataFrame):
    if not PLOTLY_AVAILABLE:
        raise RuntimeError("plotly tidak tersedia")

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
        color="departed_mid",
        hover_name="country",
        hover_data=hover_cols,
        color_continuous_scale="YlOrRd",
        title="Peta Interaktif FTF (Sample/Template) — Estimasi FTF Departed (midpoint range)",
    )
    fig.update_geos(showcoastlines=True, coastlinecolor="gray", showframe=False, projection_type="natural earth")
    fig.update_layout(margin=dict(l=20, r=20, t=60, b=20), coloraxis_colorbar_title="Departed (mid)")
    return fig


def build_status_scatter(df: pd.DataFrame):
    if not PLOTLY_AVAILABLE:
        raise RuntimeError("plotly tidak tersedia")

    fig = px.scatter_geo(
        df,
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


def render_streamlit():
    st.set_page_config(page_title="FTF Interactive Map", layout="wide")
    st.title("Peta Interaktif FTF Knowledge Hub")
    st.caption("Template/sample untuk visualisasi data FTF per negara (semi-manual, dapat diisi bertahap).")

    df = load_data()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total negara", len(df))
    c2.metric("Negara dengan data kuantitatif", int(df["has_quant"].sum()))
    c3.metric("Perlu update/review", int(df["update_status"].isin(["Needs Update", "Needs Review"]).sum()))

    st.markdown("### Filter")
    region_opts = ["Semua"] + sorted(df["region"].dropna().unique().tolist())
    status_opts = ["Semua"] + sorted(df["update_status"].dropna().unique().tolist())
    colf1, colf2 = st.columns(2)
    with colf1:
        region_filter = st.selectbox("Region", region_opts)
    with colf2:
        status_filter = st.selectbox("Status Update", status_opts)

    filtered = df.copy()
    if region_filter != "Semua":
        filtered = filtered[filtered["region"] == region_filter]
    if status_filter != "Semua":
        filtered = filtered[filtered["update_status"] == status_filter]

    if PLOTLY_AVAILABLE:
        st.markdown("### Choropleth Map")
        st.plotly_chart(build_choropleth(filtered), use_container_width=True)

        st.markdown("### Status Overlay Map")
        st.plotly_chart(build_status_scatter(filtered), use_container_width=True)
    else:
        st.warning(
            "Module `plotly` belum tersedia di environment ini. "
            "Map interaktif tidak bisa ditampilkan, tapi tabel monitoring tetap tersedia. "
            "Tambahkan `plotly` ke requirements.txt."
        )

    st.markdown("### Tabel Data")
    show = filtered.copy()
    show["last_updated"] = show["last_updated"].dt.strftime("%Y-%m-%d")
    st.dataframe(show, use_container_width=True)

    st.markdown("### requirements.txt (untuk Streamlit Cloud)")
    st.code("pandas\nplotly\nstreamlit\n", language="text")


def render_cli():
    df = load_data()
    print("=== FTF Interactive Map Template (CLI fallback) ===")
    print(f"Plotly available: {PLOTLY_AVAILABLE}")
    print(df[["country", "iso3", "region", "update_status", "departed_mid", "has_quant"]].to_string(index=False))
    if not PLOTLY_AVAILABLE:
        print("\n[INFO] Install plotly untuk peta interaktif:")
        print("pip install plotly")


def export_html_files():
    if not PLOTLY_AVAILABLE:
        raise ModuleNotFoundError("plotly belum terpasang. Install dengan: pip install plotly")
    df = load_data()
    build_choropleth(df).write_html("ftf_map_choropleth.html", include_plotlyjs="cdn")
    build_status_scatter(df).write_html("ftf_map_status_overlay.html", include_plotlyjs="cdn")
    print("Saved: ftf_map_choropleth.html")
    print("Saved: ftf_map_status_overlay.html")


def _run_tests():
    df = load_data()
    assert len(df) >= 10, "Dataset sample minimal 10 negara"
    assert "departed_mid" in df.columns and "returned_mid" in df.columns
    # Algeria midpoint should be numeric after corrected range order
    dza = df[df["iso3"] == "DZA"].iloc[0]
    assert pd.notna(dza["departed_mid"]), "DZA departed_mid harus terisi"
    # Countries with no quant should be flagged False
    idn = df[df["iso3"] == "IDN"].iloc[0]
    assert bool(idn["has_quant"]) is False, "Indonesia sample belum punya data kuantitatif"
    # Plotly optional behavior
    if PLOTLY_AVAILABLE:
        fig = build_choropleth(df)
        assert fig is not None
    print("All tests passed.")


def main():
    if "--test" in sys.argv:
        _run_tests()
        return
    if "--export-html" in sys.argv:
        export_html_files()
        return

    if STREAMLIT_AVAILABLE:
        render_streamlit()
    else:
        render_cli()


if __name__ == "__main__":
    main()
