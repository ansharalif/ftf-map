import os
from io import StringIO
from pathlib import Path

import pandas as pd
import streamlit as st
import folium
from folium import IFrame

# Optional dependency for bi-directional interaction in Streamlit
try:
    from streamlit_folium import st_folium
    HAS_ST_FOLIUM = True
except Exception:
    HAS_ST_FOLIUM = False

st.set_page_config(
    page_title="FTF Country Status Map",
    page_icon="🗺️",
    layout="wide"
)

STATUS_COLORS = {
    "belum": "#d73027",   # merah
    "draft": "#fdae61",   # kuning/oranye
    "final": "#1a9850",   # hijau
}

REGION_ORDER = ["Asia", "MENA", "Eropa", "Amerika Utara", "Afrika", "Oseania", "Lainnya"]

DEFAULT_DATA = Path(__file__).parent / "data" / "ftf_country_status_sample.csv"

SAMPLE_CSV_EMBEDDED = """country,iso2,region,status_review,last_reviewed,tema_dominan,catatan_singkat,lat,lon,ftf_hub_url,brief_internal_url
Indonesia,ID,Asia,final,2026-02-20,repatriasi;rehabilitasi;koordinasi,Brief internal tersedia dan perlu update triwulan berikutnya.,-6.2088,106.8456,https://www.foreignterroristfighters.info/country/id,
Malaysia,MY,Asia,draft,2026-02-18,penegakan_hukum;prevention,Perlu review tambahan pada bagian kebijakan pencegahan.,3.1390,101.6869,https://www.foreignterroristfighters.info/country/my,
Singapore,SG,Asia,belum,2026-02-01,prevention;rehabilitasi,Belum mulai review detail; baru inventarisasi sumber.,1.3521,103.8198,https://www.foreignterroristfighters.info/country/sg,
Philippines,PH,Asia,draft,2026-02-15,penindakan;rehabilitasi,Perlu validasi konsistensi istilah dalam matriks.,14.5995,120.9842,https://www.foreignterroristfighters.info/country/ph,
Turkey,TR,MENA,draft,2026-02-12,border_control;returnees,Perlu penajaman catatan peran wilayah transit.,39.9334,32.8597,https://www.foreignterroristfighters.info/country/tr,
Lebanon,LB,MENA,belum,2026-01-25,returnees;anak_perempuan,Belum ada brief internal.,33.8938,35.5018,https://www.foreignterroristfighters.info/country/lb,
Jordan,JO,MENA,final,2026-02-10,prosecution;prevention,Review final untuk knowledge sharing batch 1.,31.9539,35.9106,https://www.foreignterroristfighters.info/country/jo,
Belgium,BE,Eropa,final,2026-02-08,prosecution;reintegrasi,Siap dipakai komparasi dengan negara Eropa lainnya.,50.8503,4.3517,https://www.foreignterroristfighters.info/country/be,
France,FR,Eropa,draft,2026-02-22,prosecution;citizenship;reintegrasi,Perlu cek ulang tambahan resources terbaru.,48.8566,2.3522,https://www.foreignterroristfighters.info/country/fr,
Germany,DE,Eropa,belum,2026-01-30,rehabilitasi;prevention,Masuk prioritas review bulan depan.,52.5200,13.4050,https://www.foreignterroristfighters.info/country/de,
United Kingdom,GB,Eropa,final,2026-02-21,prosecution;prevention;returnees,Final dan sudah disinkronkan ke matriks komparatif.,51.5074,-0.1278,https://www.foreignterroristfighters.info/country/gb,
Canada,CA,Amerika Utara,draft,2026-02-17,prevention;rehabilitasi,Perlu standardisasi tag tema dominan.,45.4215,-75.6972,https://www.foreignterroristfighters.info/country/ca,
United States,US,Amerika Utara,belum,2026-02-05,prosecution;border_control,Belum diprioritaskan untuk batch saat ini.,38.9072,-77.0369,https://www.foreignterroristfighters.info/country/us,
Morocco,MA,MENA,draft,2026-02-16,rehabilitasi;prosecution,Catatan tambahan terkait program reintegrasi masih umum.,34.0209,-6.8416,https://www.foreignterroristfighters.info/country/ma,
South Africa,ZA,Afrika,belum,2026-02-03,prevention;legal_framework,Belum ada review mendalam.,-25.7479,28.2293,https://www.foreignterroristfighters.info/country/za,
Australia,AU,Oseania,final,2026-02-14,returnees;anak_perempuan;rehabilitasi,Siap sebagai contoh komparasi kebijakan keluarga/anak.,-35.2809,149.1300,https://www.foreignterroristfighters.info/country/au,
New Zealand,NZ,Oseania,draft,2026-02-11,returnees;rehabilitasi,Butuh update catatan setelah pembaruan resources.,-41.2865,174.7762,https://www.foreignterroristfighters.info/country/nz,
"""

REQUIRED_COLS = [
    "country", "iso2", "region", "status_review", "last_reviewed",
    "tema_dominan", "catatan_singkat", "lat", "lon", "ftf_hub_url", "brief_internal_url"
]

@st.cache_data
def load_data(file_obj=None):
    # 1) Prioritas data unggahan
    if file_obj is not None:
        df = pd.read_csv(file_obj)
        return _validate_and_standardize(df), "upload"

    # 2) File sample lokal jika tersedia
    if DEFAULT_DATA.exists():
        df = pd.read_csv(DEFAULT_DATA)
        return _validate_and_standardize(df), "local_sample"

    # 3) Fallback: sample embedded di kode
    df = pd.read_csv(StringIO(SAMPLE_CSV_EMBEDDED))
    return _validate_and_standardize(df), "embedded_sample"

def _validate_and_standardize(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Kolom wajib belum ada: {missing}")

    df = df.copy()
    df["status_review"] = df["status_review"].astype(str).str.strip().str.lower()
    df["region"] = df["region"].astype(str).str.strip()
    df["last_reviewed"] = pd.to_datetime(df["last_reviewed"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["tema_dominan"] = df["tema_dominan"].fillna("-")
    df["catatan_singkat"] = df["catatan_singkat"].fillna("-")
    df["brief_internal_url"] = df["brief_internal_url"].fillna("")
    df["ftf_hub_url"] = df["ftf_hub_url"].fillna("")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])

    valid_status = {"belum", "draft", "final"}
    df["status_review"] = df["status_review"].apply(lambda x: x if x in valid_status else "belum")
    return df

def status_badge_html(status: str) -> str:
    color = STATUS_COLORS.get(status, "#6c757d")
    label = status.upper()
    return f"""
    <span style="
        display:inline-block;padding:4px 10px;border-radius:999px;
        background:{color};color:white;font-weight:600;font-size:12px;
    ">{label}</span>
    """

def make_popup_html(row):
    brief_link = str(row.get("brief_internal_url", "")).strip()
    brief_html = f'<a href="{brief_link}" target="_blank">Buka brief internal</a>' if brief_link else '<span style="color:#666;">Brief internal belum ditautkan</span>'
    ftf_link = str(row.get("ftf_hub_url", "")).strip()
    ftf_html = f'<a href="{ftf_link}" target="_blank">Buka FTF Hub</a>' if ftf_link else '<span style="color:#666;">Link FTF Hub kosong</span>'

    html = f"""
    <div style="font-family:Arial,sans-serif; font-size:13px; line-height:1.45; width: 290px;">
      <h4 style="margin:0 0 8px 0;">{row['country']}</h4>
      <div style="margin-bottom:6px;">{status_badge_html(row['status_review'])}</div>
      <table style="width:100%; border-collapse:collapse;">
        <tr><td style="vertical-align:top; width:110px;"><b>Region</b></td><td>{row['region']}</td></tr>
        <tr><td style="vertical-align:top;"><b>Last reviewed</b></td><td>{row['last_reviewed'] or '-'}</td></tr>
        <tr><td style="vertical-align:top;"><b>Tema dominan</b></td><td>{row['tema_dominan']}</td></tr>
        <tr><td style="vertical-align:top;"><b>Catatan</b></td><td>{row['catatan_singkat']}</td></tr>
      </table>
      <hr style="margin:8px 0;">
      <div style="display:flex; gap:12px; flex-wrap:wrap;">
        {ftf_html}
        {brief_html}
      </div>
    </div>
    """
    return html

def build_map(df, tile_style, zoom_start=2):
    m = folium.Map(
        location=[15, 10],
        zoom_start=zoom_start,
        tiles=tile_style,
        control_scale=True,
        prefer_canvas=True
    )

    # Layer per status for easier toggling
    for status in ["belum", "draft", "final"]:
        sub = df[df["status_review"] == status]
        feature_group = folium.FeatureGroup(name=f"Status: {status.title()}", show=True)
        for _, row in sub.iterrows():
            color = STATUS_COLORS.get(status, "#6c757d")

            popup_html = make_popup_html(row)
            iframe = IFrame(html=popup_html, width=330, height=230)
            popup = folium.Popup(iframe, max_width=340)

            tooltip_text = (
                f"{row['country']} | {row['status_review'].upper()} | "
                f"Last: {row['last_reviewed'] or '-'} | Tema: {row['tema_dominan']}"
            )

            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=8,
                color=color,
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                tooltip=tooltip_text,
                popup=popup,
            ).add_to(feature_group)

        feature_group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Legend
    legend_html = """
    <div style="
        position: fixed; bottom: 20px; left: 20px; z-index: 9999;
        background: white; border: 1px solid #ccc; border-radius: 8px;
        padding: 10px 12px; font-size: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.15);
    ">
      <div style="font-weight:700; margin-bottom:6px;">Status Review</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#d73027;border-radius:50%;margin-right:6px;"></span>Belum</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#fdae61;border-radius:50%;margin-right:6px;"></span>Draft</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#1a9850;border-radius:50%;margin-right:6px;"></span>Final</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    return m

def main():
    st.title("🗺️ Peta Interaktif FTF Knowledge Hub — Country Status Map")
    st.caption("Prototype Latsar CPNS (Subdit Intelijen BNPT) — visualisasi status review internal berbasis matriks hasil telaah FTF Knowledge Hub (sumber terbuka).")

    with st.sidebar:
        st.header("⚙️ Filter & Data")
        uploaded = st.file_uploader("Unggah CSV matriks internal (opsional)", type=["csv"])
        tile_style = st.selectbox("Gaya peta", ["CartoDB Positron", "OpenStreetMap", "CartoDB Voyager"], index=0)

        st.markdown("**Struktur kolom CSV (wajib):**")
        st.code(
            "country, iso2, region, status_review, last_reviewed, tema_dominan, catatan_singkat, lat, lon, ftf_hub_url, brief_internal_url",
            language="text"
        )

        st.markdown("---")
        st.download_button(
            "📥 Download Template CSV",
            data=SAMPLE_CSV_EMBEDDED.encode("utf-8"),
            file_name="ftf_country_status_template.csv",
            mime="text/csv"
        )

    try:
        df, source_mode = load_data(uploaded)
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        st.stop()

    if source_mode == "upload":
        st.success("Menggunakan data dari file CSV yang diunggah.")
    elif source_mode == "local_sample":
        st.info(f"Menggunakan file sample lokal: {DEFAULT_DATA}")
    else:
        st.warning("File sample lokal tidak ditemukan. Aplikasi memakai sample data bawaan (embedded).")

    # Sidebar filters after data loaded
    with st.sidebar:
        st.markdown("---")
        regions = sorted(df["region"].dropna().unique().tolist(), key=lambda x: REGION_ORDER.index(x) if x in REGION_ORDER else 999)
        selected_regions = st.multiselect("Filter wilayah", regions, default=regions)

        statuses = ["belum", "draft", "final"]
        selected_statuses = st.multiselect("Filter status review", statuses, default=statuses)

        theme_keywords = sorted({t.strip() for items in df["tema_dominan"].fillna("").astype(str) for t in items.split(";") if t.strip()})
        selected_theme = st.selectbox("Filter tema dominan (opsional)", ["(semua)"] + theme_keywords)

        search_text = st.text_input("Cari negara / catatan")

    # Apply filters
    filtered = df[df["region"].isin(selected_regions) & df["status_review"].isin(selected_statuses)].copy()

    if selected_theme != "(semua)":
        filtered = filtered[filtered["tema_dominan"].str.contains(selected_theme, case=False, na=False)]

    if search_text:
        patt = search_text.strip()
        filtered = filtered[
            filtered["country"].str.contains(patt, case=False, na=False) |
            filtered["catatan_singkat"].str.contains(patt, case=False, na=False) |
            filtered["tema_dominan"].str.contains(patt, case=False, na=False)
        ]

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total negara (filter)", int(len(filtered)))
    c2.metric("Belum", int((filtered["status_review"] == "belum").sum()) if len(filtered) else 0)
    c3.metric("Draft", int((filtered["status_review"] == "draft").sum()) if len(filtered) else 0)
    c4.metric("Final", int((filtered["status_review"] == "final").sum()) if len(filtered) else 0)

    if filtered.empty:
        st.warning("Tidak ada data yang cocok dengan filter.")
        st.stop()

    left, right = st.columns([2.0, 1.0], gap="large")

    with left:
        m = build_map(filtered, tile_style=tile_style)

        if HAS_ST_FOLIUM:
            event = st_folium(m, width=None, height=620, returned_objects=["last_object_clicked_tooltip"])
            if event and event.get("last_object_clicked_tooltip"):
                st.info(f"Tooltip terakhir diklik: {event['last_object_clicked_tooltip']}")
        else:
            st.warning("`streamlit-folium` belum terpasang. Peta tetap tampil statis. Tambahkan dependency `streamlit-folium` untuk interaksi klik balik ke Streamlit.")
            st.components.v1.html(m._repr_html_(), height=640, scrolling=False)

    with right:
        st.subheader("📋 Tabel Ringkas")
        show_cols = ["country", "region", "status_review", "last_reviewed", "tema_dominan", "catatan_singkat"]
        st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True, height=420)

        st.subheader("📥 Export")
        st.download_button(
            "Download data hasil filter (CSV)",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="ftf_country_status_filtered.csv",
            mime="text/csv"
        )

        with st.expander("Petunjuk penggunaan singkat", expanded=True):
            st.markdown(
                """
                1. **Mulai dari data contoh** atau unggah CSV matriks internal.  
                2. Atur **filter wilayah / status / tema** di sidebar.  
                3. **Klik marker** pada peta untuk melihat ringkasan negara dan tautan FTF Hub / brief internal.  
                4. Gunakan tabel ringkas untuk cross-check cepat sebelum presentasi internal.  
                """
            )

    st.markdown("---")
    st.markdown("### Rekomendasi pengembangan lanjutan (opsional)")
    st.markdown(
        """
        - Tambahkan **halaman detail negara** (tabs: data kuantitatif, kebijakan, resources).  
        - Integrasikan **scoring coverage/quality review** (kelengkapan variabel, validasi tanggal, konsistensi tag).  
        - Tambahkan **riwayat pembaruan** (log reviewer, tanggal revisi, perubahan status).  
        """
    )

if __name__ == "__main__":
    main()
