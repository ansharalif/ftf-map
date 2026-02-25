import os
from io import StringIO
from pathlib import Path

import pandas as pd
import streamlit as st
import folium
from folium import IFrame

try:
    from streamlit_folium import st_folium
    HAS_ST_FOLIUM = True
except Exception:
    HAS_ST_FOLIUM = False

st.set_page_config(page_title="FTF Country Status Map+", page_icon="🗺️", layout="wide")

STATUS_COLORS = {"belum": "#d73027", "draft": "#fdae61", "final": "#1a9850"}
REGION_ORDER = ["Asia", "MENA", "Eropa", "Amerika Utara", "Afrika", "Oseania", "Lainnya"]
DEFAULT_DATA = Path(__file__).parent / "data" / "ftf_country_status_sample_extended.csv"

# Kolom inti (wajib)
REQUIRED_COLS = [
    "country", "iso2", "region", "status_review", "last_reviewed",
    "tema_dominan", "catatan_singkat", "lat", "lon", "ftf_hub_url", "brief_internal_url"
]

# Kolom tambahan (opsional) yang bisa diambil dari telaah FTF Hub / matriks internal
OPTIONAL_NUMERIC_COLS = [
    "total_departed",
    "total_returned",
    "total_repatriated",
    "total_detainees",
    "total_prosecuted",
    "total_convicted",
    "women_returned",
    "children_returned",
]
OPTIONAL_TEXT_COLS = [
    "last_ftf_data_update",
    "data_confidence",
    "sumber_data_ringkas",
    "catatan_kebijakan",
    "measures_criminal",
    "measures_administrative",
    "program_rehabilitasi",
    "program_reintegrasi",
    "catatan_ham",
]

SAMPLE_CSV_EMBEDDED = """country,iso2,region,status_review,last_reviewed,tema_dominan,catatan_singkat,lat,lon,ftf_hub_url,brief_internal_url,total_departed,total_returned,total_repatriated,total_detainees,total_prosecuted,total_convicted,women_returned,children_returned,last_ftf_data_update,data_confidence,sumber_data_ringkas,catatan_kebijakan,measures_criminal,measures_administrative,program_rehabilitasi,program_reintegrasi,catatan_ham
Indonesia,ID,Asia,final,2026-02-20,repatriasi;rehabilitasi;koordinasi,Brief internal tersedia dan perlu update triwulan berikutnya.,-6.2088,106.8456,https://www.foreignterroristfighters.info/country/id,,1500,600,120,200,300,180,40,80,2026-02-15,sedang,FTF Hub + sumber terbuka pendukung,Fokus pembelajaran pada repatriasi & reintegrasi,Ya,Ya,Terbatas/Terdapat program,Terbatas/Tahap evaluasi,Perlu kehati-hatian interpretasi angka
Malaysia,MY,Asia,draft,2026-02-18,penegakan_hukum;prevention,Perlu review tambahan pada bagian kebijakan pencegahan.,3.1390,101.6869,https://www.foreignterroristfighters.info/country/my,,350,180,20,70,120,80,8,15,2026-02-10,sedang,FTF Hub,Perlu validasi update kebijakan terbaru,Ya,Ya,Ada,Terbatas,Data angka dapat berubah
Singapore,SG,Asia,belum,2026-02-01,prevention;rehabilitasi,Belum mulai review detail; baru inventarisasi sumber.,1.3521,103.8198,https://www.foreignterroristfighters.info/country/sg,,0,0,0,0,0,0,0,0,,rendah,Inventarisasi awal,Belum diisi,Belum,Belum,Belum,Belum,Belum ditelaah
Turkey,TR,MENA,draft,2026-02-12,border_control;returnees,Perlu penajaman catatan peran wilayah transit.,39.9334,32.8597,https://www.foreignterroristfighters.info/country/tr,,2000,900,60,500,450,250,25,90,2026-02-11,sedang,FTF Hub + literature,Catatan transit dan returnees perlu dipisah,Ya,Ya,Ada,Ada,Interpretasi lintas sumber
Belgium,BE,Eropa,final,2026-02-08,prosecution;reintegrasi,Siap dipakai komparasi dengan negara Eropa lainnya.,50.8503,4.3517,https://www.foreignterroristfighters.info/country/be,,500,130,35,60,220,160,18,40,2026-02-08,tinggi,FTF Hub,Komparasi prosecution-reintegration,Ya,Ya,Ada,Ada,Perlu konteks legal nasional
United Kingdom,GB,Eropa,final,2026-02-21,prosecution;prevention;returnees,Final dan sudah disinkronkan ke matriks komparatif.,51.5074,-0.1278,https://www.foreignterroristfighters.info/country/gb,,900,420,55,140,380,260,22,70,2026-02-20,tinggi,FTF Hub + update resources,Siap untuk knowledge sharing,Ya,Ya,Ada,Ada,Perlu update periodik
Australia,AU,Oseania,final,2026-02-14,returnees;anak_perempuan;rehabilitasi,Siap sebagai contoh komparasi kebijakan keluarga/anak.,-35.2809,149.1300,https://www.foreignterroristfighters.info/country/au,,250,110,30,35,95,60,14,28,2026-02-14,sedang,FTF Hub,Fokus keluarga/anak dan returnees,Ya,Ya,Ada,Ada,Asesmen risiko berbasis kasus
United States,US,Amerika Utara,belum,2026-02-05,prosecution;border_control,Belum diprioritaskan untuk batch saat ini.,38.9072,-77.0369,https://www.foreignterroristfighters.info/country/us,,300,120,10,90,210,150,4,9,2026-02-01,sedang,FTF Hub,Masuk batch berikutnya,Ya,Ya,Ada,Terbatas,Perlu verifikasi silang
South Africa,ZA,Afrika,belum,2026-02-03,prevention;legal_framework,Belum ada review mendalam.,-25.7479,28.2293,https://www.foreignterroristfighters.info/country/za,,40,15,2,6,10,5,1,3,2026-01-30,rendah,FTF Hub,Belum ditelaah mendalam,Terbatas,Terbatas,Terbatas,Terbatas,Data awal
"""

def _to_numeric_if_exists(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def _validate_and_standardize(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Kolom wajib belum ada: {missing}")

    df = df.copy()
    df["status_review"] = df["status_review"].astype(str).str.strip().str.lower()
    df["region"] = df["region"].astype(str).str.strip()
    df["last_reviewed"] = pd.to_datetime(df["last_reviewed"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "last_ftf_data_update" in df.columns:
        df["last_ftf_data_update"] = pd.to_datetime(df["last_ftf_data_update"], errors="coerce").dt.strftime("%Y-%m-%d")

    for c in ["tema_dominan", "catatan_singkat", "brief_internal_url", "ftf_hub_url"]:
        if c in df.columns:
            df[c] = df[c].fillna("")

    for c in OPTIONAL_TEXT_COLS:
        if c in df.columns:
            df[c] = df[c].fillna("")

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = _to_numeric_if_exists(df, OPTIONAL_NUMERIC_COLS)
    df = df.dropna(subset=["lat", "lon"])

    valid_status = {"belum", "draft", "final"}
    df["status_review"] = df["status_review"].apply(lambda x: x if x in valid_status else "belum")
    return df

@st.cache_data
def load_data(file_obj=None):
    if file_obj is not None:
        return _validate_and_standardize(pd.read_csv(file_obj)), "upload"
    if DEFAULT_DATA.exists():
        return _validate_and_standardize(pd.read_csv(DEFAULT_DATA)), "local_sample"
    return _validate_and_standardize(pd.read_csv(StringIO(SAMPLE_CSV_EMBEDDED))), "embedded_sample"

def status_badge_html(status: str) -> str:
    color = STATUS_COLORS.get(status, "#6c757d")
    return f'<span style="display:inline-block;padding:4px 10px;border-radius:999px;background:{color};color:white;font-weight:600;font-size:12px;">{status.upper()}</span>'

def _fmt_num(v):
    if pd.isna(v):
        return "-"
    try:
        return f"{int(v):,}".replace(",", ".")
    except Exception:
        return str(v)

def make_popup_html(row):
    brief_link = str(row.get("brief_internal_url", "")).strip()
    ftf_link = str(row.get("ftf_hub_url", "")).strip()
    brief_html = f'<a href="{brief_link}" target="_blank">Buka brief internal</a>' if brief_link else '<span style="color:#666;">Brief internal belum ditautkan</span>'
    ftf_html = f'<a href="{ftf_link}" target="_blank">Buka FTF Hub</a>' if ftf_link else '<span style="color:#666;">Link FTF Hub kosong</span>'

    # Optional FTF data block
    rows_stats = []
    labels = {
        "total_departed": "Total departed",
        "total_returned": "Total returned",
        "total_repatriated": "Total repatriated",
        "total_detainees": "Total detainees",
        "total_prosecuted": "Total prosecuted",
        "total_convicted": "Total convicted",
        "women_returned": "Women returned",
        "children_returned": "Children returned",
    }
    for c, label in labels.items():
        if c in row.index and not pd.isna(row[c]):
            rows_stats.append(f"<tr><td style='vertical-align:top;'><b>{label}</b></td><td>{_fmt_num(row[c])}</td></tr>")
    stats_html = ""
    if rows_stats:
        stats_html = f"""
        <hr style="margin:8px 0;">
        <div style="font-weight:700; margin-bottom:4px;">Data FTF (ringkas)</div>
        <table style="width:100%; border-collapse:collapse;">{''.join(rows_stats)}</table>
        """

    html = f"""
    <div style="font-family:Arial,sans-serif; font-size:13px; line-height:1.45; width: 300px;">
      <h4 style="margin:0 0 8px 0;">{row['country']}</h4>
      <div style="margin-bottom:6px;">{status_badge_html(row['status_review'])}</div>
      <table style="width:100%; border-collapse:collapse;">
        <tr><td style="vertical-align:top; width:120px;"><b>Region</b></td><td>{row['region']}</td></tr>
        <tr><td style="vertical-align:top;"><b>Last reviewed</b></td><td>{row.get('last_reviewed','') or '-'}</td></tr>
        <tr><td style="vertical-align:top;"><b>Tema dominan</b></td><td>{row.get('tema_dominan','') or '-'}</td></tr>
        <tr><td style="vertical-align:top;"><b>Catatan</b></td><td>{row.get('catatan_singkat','') or '-'}</td></tr>
      </table>
      {stats_html}
      <hr style="margin:8px 0;">
      <div style="display:flex; gap:12px; flex-wrap:wrap;">
        {ftf_html}
        {brief_html}
      </div>
    </div>
    """
    return html

def build_map(df, tile_style):
    m = folium.Map(location=[15, 10], zoom_start=2, tiles=tile_style, control_scale=True, prefer_canvas=True)

    for status in ["belum", "draft", "final"]:
        sub = df[df["status_review"] == status]
        fg = folium.FeatureGroup(name=f"Status: {status.title()}", show=True)
        for _, row in sub.iterrows():
            color = STATUS_COLORS.get(status, "#6c757d")
            tooltip_parts = [str(row["country"]), row["status_review"].upper()]
            if "last_reviewed" in row.index and str(row["last_reviewed"]) != "nan":
                tooltip_parts.append(f"Last: {row['last_reviewed']}")
            if "tema_dominan" in row.index and str(row["tema_dominan"]).strip():
                tooltip_parts.append(f"Tema: {row['tema_dominan']}")
            if "total_repatriated" in row.index and not pd.isna(row["total_repatriated"]):
                tooltip_parts.append(f"Repatriated: {_fmt_num(row['total_repatriated'])}")
            tooltip_text = " | ".join(tooltip_parts)

            iframe = IFrame(html=make_popup_html(row), width=340, height=310)
            popup = folium.Popup(iframe, max_width=350)
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
            ).add_to(fg)
        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m

def aggregate_sum(df, col):
    return int(df[col].fillna(0).sum()) if col in df.columns else None

def main():
    st.title("🗺️ Peta Interaktif FTF Knowledge Hub — Country Status Map+")
    st.caption("Versi enhanced: mendukung data FTF tambahan (mis. total repatriasi/returned/departed/detainees/prosecution) dari matriks internal hasil telaah FTF Knowledge Hub.")

    with st.sidebar:
        st.header("⚙️ Filter & Data")
        uploaded = st.file_uploader("Unggah CSV matriks internal (opsional)", type=["csv"])
        tile_style = st.selectbox("Gaya peta", ["CartoDB Positron", "OpenStreetMap", "CartoDB Voyager"], index=0)

        st.markdown("**Kolom inti (wajib):**")
        st.code(", ".join(REQUIRED_COLS), language="text")
        st.markdown("**Kolom tambahan (opsional):**")
        st.code(", ".join(OPTIONAL_NUMERIC_COLS + OPTIONAL_TEXT_COLS), language="text")

        st.download_button(
            "📥 Download Template CSV (extended)",
            data=SAMPLE_CSV_EMBEDDED.encode("utf-8"),
            file_name="ftf_country_status_template_extended.csv",
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

    # Sidebar filters lanjutan
    with st.sidebar:
        st.markdown("---")
        regions = sorted(df["region"].dropna().unique().tolist(), key=lambda x: REGION_ORDER.index(x) if x in REGION_ORDER else 999)
        selected_regions = st.multiselect("Filter wilayah", regions, default=regions)
        selected_statuses = st.multiselect("Filter status review", ["belum", "draft", "final"], default=["belum", "draft", "final"])
        theme_keywords = sorted({t.strip() for items in df["tema_dominan"].fillna("").astype(str) for t in items.split(";") if t.strip()})
        selected_theme = st.selectbox("Filter tema dominan (opsional)", ["(semua)"] + theme_keywords)
        search_text = st.text_input("Cari negara / catatan / tema")

    filtered = df[df["region"].isin(selected_regions) & df["status_review"].isin(selected_statuses)].copy()
    if selected_theme != "(semua)":
        filtered = filtered[filtered["tema_dominan"].str.contains(selected_theme, case=False, na=False)]
    if search_text:
        patt = search_text.strip()
        filtered = filtered[
            filtered["country"].str.contains(patt, case=False, na=False) |
            filtered["catatan_singkat"].astype(str).str.contains(patt, case=False, na=False) |
            filtered["tema_dominan"].astype(str).str.contains(patt, case=False, na=False)
        ]

    # KPI baris 1: status review
    a, b, c, d = st.columns(4)
    a.metric("Negara (filter)", int(len(filtered)))
    b.metric("Belum", int((filtered["status_review"] == "belum").sum()) if len(filtered) else 0)
    c.metric("Draft", int((filtered["status_review"] == "draft").sum()) if len(filtered) else 0)
    d.metric("Final", int((filtered["status_review"] == "final").sum()) if len(filtered) else 0)

    # KPI baris 2: agregat FTF data (jika kolom ada)
    kpi_cols = [("total_repatriated", "Total Repatriasi"), ("total_returned", "Total Returned"),
                ("total_departed", "Total Departed"), ("total_detainees", "Total Detainees")]
    cols = st.columns(4)
    for ui_col, (col_name, label) in zip(cols, kpi_cols):
        agg = aggregate_sum(filtered, col_name)
        ui_col.metric(label, f"{agg:,}".replace(",", ".") if agg is not None else "-")

    if filtered.empty:
        st.warning("Tidak ada data yang cocok dengan filter.")
        st.stop()

    left, right = st.columns([2.1, 1.1], gap="large")

    with left:
        st.subheader("🌍 Peta Interaktif")
        m = build_map(filtered, tile_style=tile_style)
        if HAS_ST_FOLIUM:
            _ = st_folium(m, width=None, height=620, returned_objects=["last_object_clicked_tooltip"])
        else:
            st.warning("`streamlit-folium` belum terpasang. Peta tetap tampil statis.")
            st.components.v1.html(m._repr_html_(), height=640, scrolling=False)

        # Simple charts if optional cols exist
        st.subheader("📊 Visualisasi Ringkas (berdasarkan filter)")
        chart_candidates = [c for c in ["total_repatriated", "total_returned", "total_departed", "total_detainees"] if c in filtered.columns]
        if chart_candidates:
            chart_col = st.selectbox("Pilih indikator untuk bar chart", chart_candidates, index=0)
            plot_df = filtered[["country", chart_col]].copy().dropna().sort_values(chart_col, ascending=False).head(15)
            if plot_df.empty:
                st.info("Belum ada nilai numerik untuk indikator ini pada data yang sedang difilter.")
            else:
                st.bar_chart(plot_df.set_index("country"))
        else:
            st.info("Tambahkan kolom numerik opsional (mis. total_repatriated / total_returned) untuk menampilkan grafik.")
    with right:
        st.subheader("📋 Tabel Ringkas")
        base_cols = ["country", "region", "status_review", "last_reviewed", "tema_dominan"]
        opt_show = [c for c in ["total_repatriated", "total_returned", "total_departed", "total_detainees"] if c in filtered.columns]
        st.dataframe(filtered[base_cols + opt_show + ["catatan_singkat"]], use_container_width=True, hide_index=True, height=420)

        st.subheader("🧩 Kolom terdeteksi")
        detected_optional = [c for c in OPTIONAL_NUMERIC_COLS + OPTIONAL_TEXT_COLS if c in filtered.columns]
        st.write(f"**Opsional aktif ({len(detected_optional)}):**")
        st.code(", ".join(detected_optional) if detected_optional else "(tidak ada)")

        st.subheader("📥 Export")
        st.download_button("Download data hasil filter (CSV)", data=filtered.to_csv(index=False).encode("utf-8"),
                           file_name="ftf_country_status_filtered_extended.csv", mime="text/csv")

        with st.expander("Petunjuk input data (singkat)", expanded=True):
            st.markdown("""
            - **Kolom inti** wajib diisi agar peta bisa tampil.  
            - Tambahkan **kolom numerik** seperti `total_repatriated`, `total_returned`, `total_departed`, `total_detainees` untuk KPI & grafik.  
            - Angka sebaiknya hasil **telaah matriks internal** dari FTF Knowledge Hub (sumber terbuka), bukan scraping otomatis mentah.  
            - Cantumkan **catatan/konteks** karena definisi dan periode data antarnegara bisa berbeda.
            """)

    st.markdown("---")
    st.markdown("### Saran pengembangan lanjutan")
    st.markdown("""
    - Tambahkan **halaman detail negara** (tabs: data, kebijakan, resources, timeline update).  
    - Tambahkan **metadata sumber** per angka (tahun/periode + catatan definisi).  
    - Tambahkan **indikator kualitas data** (`data_confidence`, kelengkapan kolom, tanggal update).  
    """)

if __name__ == "__main__":
    main()
