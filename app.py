import os
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

st.set_page_config(page_title="FTF Country Status Map", page_icon="🗺️", layout="wide")

STATUS_COLORS = {"belum": "#d73027", "draft": "#fdae61", "final": "#1a9850"}
REGION_ORDER = ["Asia", "MENA", "Eropa", "Amerika Utara", "Afrika", "Oseania", "Lainnya"]
DEFAULT_DATA = Path(__file__).parent / "data" / "ftf_country_status_sample.csv"

@st.cache_data
def load_data(file_obj=None):
    df = pd.read_csv(file_obj) if file_obj is not None else pd.read_csv(DEFAULT_DATA)
    required_cols = ["country", "iso2", "region", "status_review", "last_reviewed", "tema_dominan", "catatan_singkat", "lat", "lon", "ftf_hub_url", "brief_internal_url"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Kolom wajib belum ada: {missing}")
    df["status_review"] = df["status_review"].astype(str).str.strip().str.lower()
    df["region"] = df["region"].astype(str).str.strip()
    df["last_reviewed"] = pd.to_datetime(df["last_reviewed"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["tema_dominan"] = df["tema_dominan"].fillna("-")
    df["catatan_singkat"] = df["catatan_singkat"].fillna("-")
    df["brief_internal_url"] = df["brief_internal_url"].fillna("")
    return df

def status_badge_html(status: str) -> str:
    color = STATUS_COLORS.get(status, "#6c757d")
    return f'<span style="display:inline-block;padding:4px 10px;border-radius:999px;background:{color};color:white;font-weight:600;font-size:12px;">{status.upper()}</span>'

def make_popup_html(row):
    brief_link = str(row.get("brief_internal_url", "")).strip()
    brief_html = f'<a href="{brief_link}" target="_blank">Buka brief internal</a>' if brief_link else '<span style="color:#666;">Brief internal belum ditautkan</span>'
    return f"""
    <div style=\"font-family:Arial,sans-serif; font-size:13px; line-height:1.45; width: 290px;\">
      <h4 style=\"margin:0 0 8px 0;\">{row['country']}</h4>
      <div style=\"margin-bottom:6px;\">{status_badge_html(row['status_review'])}</div>
      <table style=\"width:100%; border-collapse:collapse;\">
        <tr><td style=\"vertical-align:top; width:110px;\"><b>Region</b></td><td>{row['region']}</td></tr>
        <tr><td style=\"vertical-align:top;\"><b>Last reviewed</b></td><td>{row['last_reviewed'] or '-'}</td></tr>
        <tr><td style=\"vertical-align:top;\"><b>Tema dominan</b></td><td>{row['tema_dominan']}</td></tr>
        <tr><td style=\"vertical-align:top;\"><b>Catatan</b></td><td>{row['catatan_singkat']}</td></tr>
      </table>
      <hr style=\"margin:8px 0;\">
      <div style=\"display:flex; gap:12px; flex-wrap:wrap;\">
        <a href=\"{row['ftf_hub_url']}\" target=\"_blank\">Buka FTF Hub</a>
        {brief_html}
      </div>
    </div>
    """

def build_map(df, tile_style):
    m = folium.Map(location=[15, 10], zoom_start=2, tiles=tile_style, control_scale=True, prefer_canvas=True)
    for status in ["belum", "draft", "final"]:
        sub = df[df["status_review"] == status]
        fg = folium.FeatureGroup(name=f"Status: {status.title()}", show=True)
        for _, row in sub.iterrows():
            color = STATUS_COLORS.get(status, "#6c757d")
            popup = folium.Popup(IFrame(html=make_popup_html(row), width=330, height=230), max_width=340)
            tooltip_text = f"{row['country']} | {row['status_review'].upper()} | Last: {row['last_reviewed'] or '-'} | Tema: {row['tema_dominan']}"
            folium.CircleMarker(
                location=[row["lat"], row["lon"]], radius=8, color=color, weight=2,
                fill=True, fill_color=color, fill_opacity=0.85,
                tooltip=tooltip_text, popup=popup
            ).add_to(fg)
        fg.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    legend_html = """
    <div style="position: fixed; bottom: 20px; left: 20px; z-index: 9999; background: white; border: 1px solid #ccc; border-radius: 8px; padding: 10px 12px; font-size: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.15);">
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
        st.code("country, iso2, region, status_review, last_reviewed, tema_dominan, catatan_singkat, lat, lon, ftf_hub_url, brief_internal_url", language="text")

    try:
        df = load_data(uploaded)
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        st.stop()

    with st.sidebar:
        st.markdown("---")
        regions = sorted(df["region"].dropna().unique().tolist(), key=lambda x: REGION_ORDER.index(x) if x in REGION_ORDER else 999)
        selected_regions = st.multiselect("Filter wilayah", regions, default=regions)
        statuses = ["belum", "draft", "final"]
        selected_statuses = st.multiselect("Filter status review", statuses, default=statuses)
        theme_keywords = sorted({t.strip() for items in df["tema_dominan"].fillna("").astype(str) for t in items.split(";") if t.strip()})
        selected_theme = st.selectbox("Filter tema dominan (opsional)", ["(semua)"] + theme_keywords)
        search_text = st.text_input("Cari negara / catatan")

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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total negara (filter)", len(filtered))
    c2.metric("Belum", int((filtered["status_review"] == "belum").sum()) if len(filtered) else 0)
    c3.metric("Draft", int((filtered["status_review"] == "draft").sum()) if len(filtered) else 0)
    c4.metric("Final", int((filtered["status_review"] == "final").sum()) if len(filtered) else 0)

    if filtered.empty:
        st.warning("Tidak ada data yang cocok dengan filter.")
        st.stop()

    left, right = st.columns([2.0, 1.0], gap="large")
    with left:
        m = build_map(filtered, tile_style)
        if HAS_ST_FOLIUM:
            event = st_folium(m, width=None, height=620, returned_objects=["last_object_clicked_tooltip"])
            if event and event.get("last_object_clicked_tooltip"):
                st.info(f"Tooltip terakhir diklik: {event['last_object_clicked_tooltip']}")
        else:
            st.warning("`streamlit-folium` belum terpasang. Peta tetap tampil (render HTML). Tambahkan dependency `streamlit-folium` untuk interaksi lebih baik.")
            st.components.v1.html(m._repr_html_(), height=640, scrolling=False)

    with right:
        st.subheader("📋 Tabel Ringkas")
        show_cols = ["country", "region", "status_review", "last_reviewed", "tema_dominan", "catatan_singkat"]
        st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True, height=420)
        st.subheader("📥 Template & Export")
        st.download_button("Download data hasil filter (CSV)", data=filtered.to_csv(index=False).encode("utf-8"), file_name="ftf_country_status_filtered.csv", mime="text/csv")
        with st.expander("Petunjuk penggunaan singkat", expanded=True):
            st.markdown("""
            1. **Mulai dari data contoh** atau unggah CSV matriks internal.  
            2. Atur **filter wilayah / status / tema** di sidebar.  
            3. **Klik marker** pada peta untuk melihat ringkasan negara dan tautan FTF Hub / brief internal.  
            4. Gunakan tabel ringkas untuk cross-check cepat sebelum presentasi internal.
            """)

    st.markdown("---")
    st.markdown("### Rekomendasi pengembangan lanjutan (opsional)")
    st.markdown("- Tambahkan halaman detail negara.\n- Integrasikan scoring coverage/quality review.\n- Tambahkan riwayat pembaruan (log reviewer, tanggal revisi, perubahan status).")

if __name__ == "__main__":
    main()
