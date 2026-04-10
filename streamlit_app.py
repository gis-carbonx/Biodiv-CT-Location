import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
from shapely.geometry import Point, shape
import json
import plotly.express as px

st.set_page_config(page_title="Draft - Monitoring camtrap", layout="wide")

st.title("Draft - Monitoring camtrap")
st.markdown("testsad asoda jadsiadsan sdasdksdandp asdsjni asdsjadnpsad asdksn asd asdkmpovdsv mk[ psannaspffnunjsadksamdsandsadnm asdpianfhaaslas].")

# Cached loaders
@st.cache_data
def load_geojson(url):
    return requests.get(url).json()

@st.cache_data(ttl=60)
def load_sheet(sheet_id):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    return pd.read_csv(url)

@st.cache_data
def compute_grid_camera(geojson2_str, point_camera_tuples):
    geojson2 = json.loads(geojson2_str)
    points_shapely = [(Point(lon, lat), cam) for lat, lon, cam in point_camera_tuples]
    result = {}
    for i, feature in enumerate(geojson2["features"]):
        polygon = shape(feature["geometry"])
        cameras = set(cam for pt, cam in points_shapely if polygon.contains(pt))
        result[i] = len(cameras)
    return result

# geojson data, 1 (area cmi), 2 (grid), 3 (forest cover)
geojson1 = load_geojson("https://drive.google.com/uc?export=download&id=19pbjbedC3iF48QgLbatDA-XeNF4flIgc")
geojson2 = load_geojson("https://drive.google.com/uc?export=download&id=148vZDiPQxhCOnxZ-8eqlxvcy0H0__oub")
geojson3 = load_geojson("https://drive.google.com/uc?export=download&id=19eNxhUKyGC3_3ZbvjQ_luiwFLa-L7aGU")

df = load_sheet("1aSlHTdSJOm4CIDbe9VV7eOfRfxfUgyBWZl0EKMDXzXA")
df = df.rename(columns={
    df.columns[0]:  "No",
    df.columns[4]:  "Lokasi",
    df.columns[5]:  "Latitude",
    df.columns[6]:  "Longitude",
    df.columns[7]:  "ID_Camera",
    df.columns[8]:  "Tanggal",
    df.columns[9]:  "Jam",
    df.columns[11]:  "Kelas",
    df.columns[12]:  "Spesies",
    df.columns[13]: "Nama_Lokal",
    df.columns[14]: "Status_IUCN",
    df.columns[15]: "Jml_Tangkapan",
    df.columns[18]:  "Nama_File",
})
df = df.dropna(subset=["Latitude", "Longitude"])
df["Jml_Tangkapan"] = pd.to_numeric(df["Jml_Tangkapan"], errors="coerce").fillna(0)

COORD_PRECISION = 6
df["Lat_r"] = df["Latitude"].round(COORD_PRECISION)
df["Lon_r"] = df["Longitude"].round(COORD_PRECISION)

total_tangkapan = int(df["Jml_Tangkapan"].sum())
total_spesies   = df[df["Jml_Tangkapan"] > 0]["Spesies"].nunique()
total_camera    = df["ID_Camera"].nunique()
total_lokasi    = df.groupby(["Lat_r", "Lon_r"]).ngroups

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Tangkapan", total_tangkapan)
col2.metric("Jumlah Spesies", total_spesies)
col3.metric("Jumlah Kamera", total_camera)
col4.metric("Jumlah Lokasi", total_lokasi)

point_camera_tuples = tuple(
    (row["Latitude"], row["Longitude"], row["ID_Camera"])
    for _, row in df.iterrows()
)
grid_camera_count = compute_grid_camera(json.dumps(geojson2), point_camera_tuples)

all_counts = sorted(set(v for v in grid_camera_count.values() if v > 0))
max_count  = max(all_counts) if all_counts else 1

if len(all_counts) <= 4:
    classes = all_counts
else:
    step = max_count / 4
    classes = sorted(set([int(step), int(step*2), int(step*3), max_count]))
if not classes:
    classes = [1]

color_palette = ["#FFFF00", "#FFA500", "#FF4500", "#CC0000"]
colors    = color_palette[:len(classes)]
opacities = [0.25, 0.40, 0.55, 0.70][:len(classes)]

def get_class_index(count):
    if count == 0: return -1
    for idx, threshold in enumerate(classes):
        if count <= threshold: return idx
    return len(classes) - 1

def get_color(count):
    idx = get_class_index(count)
    return colors[idx] if idx >= 0 else None

def get_fill_opacity(count):
    idx = get_class_index(count)
    return opacities[idx] if idx >= 0 else 0

def make_legend_labels(classes):
    labels = []
    for i, threshold in enumerate(classes):
        low_val = 1 if i == 0 else classes[i-1] + 1
        labels.append(f"{low_val} kamera" if low_val == threshold else f"{low_val}–{threshold} kamera")
    return labels

legend_labels = make_legend_labels(classes)

m = folium.Map(location=[0.7870908235692126, 110.27529459792473], zoom_start=12, tiles="CartoDB dark_matter")

folium.GeoJson(
    geojson1, name="Area CMI",
    style_function=lambda f: {
        "fillColor": "transparent", "color": "#9B59B6", "weight": 2, "fillOpacity": 0,
    }
).add_to(m)

grid_group = folium.FeatureGroup(name="Grid Intensitas Kamera", show=True)
for i, feature in enumerate(geojson2["features"]):
    count = grid_camera_count.get(i, 0)
    color = get_color(count)
    fo    = get_fill_opacity(count)
    folium.GeoJson(
        feature,
        style_function=lambda f, c=color, fo=fo: {
            "fillColor": c if c else "transparent",
            "fillOpacity": fo,
            "color": c if c else "#808080",
            "weight": 1.5 if c else 1,
        },
        tooltip=f"Jumlah Kamera: {count}" if count > 0 else "Tidak ada kamera"
    ).add_to(grid_group)
grid_group.add_to(m)

forest_group = folium.FeatureGroup(name="Forest Area", show=False)
folium.GeoJson(
    geojson3,
    style_function=lambda f: {
        "fillColor": "#228B22", "fillOpacity": 0.25,
        "color": "#228B22", "weight": 1,
    }
).add_to(forest_group)
forest_group.add_to(m)

legend_items_html = ""
for i, label in enumerate(legend_labels):
    legend_items_html += f"""
    <div style="display:flex; align-items:center; margin-bottom:7px;">
        <div style="width:20px; height:20px; background:{colors[i]};
                    opacity:{opacities[i]+0.3}; border-radius:3px;
                    margin-right:10px; flex-shrink:0;"></div>
        <span>{label}</span>
    </div>"""

legend_items_html += """
    <div style="display:flex; align-items:center; margin-bottom:7px;">
        <div style="width:20px; height:20px; background:transparent;
                    border:1px solid #808080; border-radius:3px;
                    margin-right:10px; flex-shrink:0;"></div>
        <span>Tidak ada kamera</span>
    </div>
    <hr style="border-color:#374151; margin:8px 0;">
    <div style="display:flex; align-items:center; margin-bottom:7px;">
        <div style="width:20px; height:20px; background:#228B22; opacity:0.55;
                    border-radius:3px; margin-right:10px; flex-shrink:0;"></div>
        <span>Forest Area</span>
    </div>
    <div style="display:flex; align-items:center; margin-bottom:7px;">
        <div style="width:20px; height:20px; background:transparent;
                    border:2px solid #9B59B6; border-radius:3px;
                    margin-right:10px; flex-shrink:0;"></div>
        <span>Area CMI</span>
    </div>
    <div style="display:flex; align-items:center;">
        <div style="width:20px; height:20px; background:#00BFFF;
                    border-radius:50%; margin-right:10px; flex-shrink:0;"></div>
        <span>Lokasi Kamera</span>
    </div>
"""

legend_html = f"""
<div style="position:fixed; bottom:30px; right:10px; z-index:9999;
    background:rgba(15,20,30,0.92); border:1px solid #374151;
    border-radius:10px; padding:14px 18px; font-family:Arial;
    font-size:13px; color:#f9fafb; min-width:200px;
    box-shadow:0 4px 12px rgba(0,0,0,0.5);">
    <b style="font-size:14px; color:#fff;">📷 Intensitas Camera Trap</b>
    <hr style="border-color:#374151; margin:8px 0;">
    {legend_items_html}
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

point_group = folium.FeatureGroup(name="Satwa Liar", show=True)

for (lat_r, lon_r), coord_group in df.groupby(["Lat_r", "Lon_r"]):
    lat = coord_group["Latitude"].iloc[0]
    lon = coord_group["Longitude"].iloc[0]

    jumlah          = int(coord_group["Jml_Tangkapan"].sum())
    nama_lokasi_list = sorted(coord_group["Lokasi"].dropna().unique().tolist())
    nama_lokasi_str  = " / ".join(nama_lokasi_list)
    camera_list      = sorted(coord_group["ID_Camera"].dropna().unique().tolist())
    jumlah_kamera    = len(camera_list)
    camera_ids_str   = ", ".join(str(c) for c in camera_list)

    spesies_list = coord_group[coord_group["Jml_Tangkapan"] > 0].groupby("Spesies").agg(
        Nama_Lokal=("Nama_Lokal", "first"),
        Jml=("Jml_Tangkapan", "sum")
    ).reset_index()

    spesies_rows = "".join([
        f"<tr>"
        f"<td style='padding:5px 8px; font-style:italic; white-space:nowrap;'>{r['Spesies']}</td>"
        f"<td style='padding:5px 8px; white-space:nowrap;'>{r['Nama_Lokal']}</td>"
        f"<td style='padding:5px 8px; text-align:center;'>{int(r['Jml'])}</td>"
        f"</tr>"
        for _, r in spesies_list.iterrows()
    ])

    uid = f"{str(lat_r).replace('.','_').replace('-','m')}_{str(lon_r).replace('.','_').replace('-','m')}"

    popup_html = f"""
        <div style="font-family:Arial; font-size:13px; width:500px; max-width:500px;">
            <b style="font-size:15px;">{nama_lokasi_str}</b>
            <hr style="margin:5px 0">
            <b>Total Tangkapan:</b> {jumlah}<br>
            <b>Jumlah Kamera:</b> {jumlah_kamera}<br>
            <b>ID Kamera:</b> {camera_ids_str}<br><br>
            <b>Daftar Spesies:</b>
            <a href="#" onclick="
                var el = document.getElementById('tbl_{uid}');
                var lnk = document.getElementById('lnk_{uid}');
                if(el.style.display==='none'){{
                    el.style.display='block'; lnk.textContent='Show less ▲';
                }} else {{
                    el.style.display='none'; lnk.textContent='Show more ▼';
                }}
                return false;
            " id="lnk_{uid}"
            style="margin-left:8px; font-size:12px; color:#1a73e8; text-decoration:none;">
                Show more ▼
            </a>
            <div id="tbl_{uid}" style="display:none; margin-top:8px; max-height:200px;
                 overflow-y:auto; border:1px solid #ddd; border-radius:4px;">
                <table style="width:100%; border-collapse:collapse;">
                    <thead>
                        <tr style="background:#eee; position:sticky; top:0;">
                            <th style="text-align:left; padding:5px 8px;">Spesies</th>
                            <th style="text-align:left; padding:5px 8px;">Nama Lokal</th>
                            <th style="text-align:center; padding:5px 8px;">Jml</th>
                        </tr>
                    </thead>
                    <tbody>{spesies_rows}</tbody>
                </table>
            </div>
        </div>
    """

    folium.CircleMarker(
        location=[lat, lon], radius=8,
        color="#00BFFF", fill=True, fill_color="#00BFFF",
        fill_opacity=0.8, weight=1.5,
        popup=folium.Popup(popup_html, max_width=520),
        tooltip=f"{lat_r}, {lon_r}"
    ).add_to(point_group)

point_group.add_to(m)
folium.LayerControl().add_to(m)

map_data = st_folium(m, width="100%", height=580)

#TREEMAP
st.divider()
st.subheader("🌿 Treemap Tangkapan Spesies per Kamera")

clicked_info = map_data.get("last_object_clicked_popup") if map_data else None

all_cameras = sorted(df["ID_Camera"].dropna().unique().tolist())
selected_cameras = st.multiselect(
    "Filter berdasarkan ID Kamera (kosongkan = semua kamera)",
    options=all_cameras,
    default=[],
    placeholder="Pilih satu atau lebih kamera..."
)

df_filtered = df[df["Jml_Tangkapan"] > 0].copy()
if selected_cameras:
    df_filtered = df_filtered[df_filtered["ID_Camera"].isin(selected_cameras)]

df_tree = (
    df_filtered
    .groupby(["Kelas", "Spesies", "Nama_Lokal", "Status_IUCN"], dropna=False)
    .agg(Total=("Jml_Tangkapan", "sum"))
    .reset_index()
)
df_tree["Status_IUCN"] = df_tree["Status_IUCN"].fillna("Tidak diketahui")
df_tree["Label"] = df_tree["Spesies"] + "<br><i>" + df_tree["Nama_Lokal"].fillna("") + "</i>"

if df_tree.empty:
    st.info("Tidak ada data tangkapan untuk filter yang dipilih.")
else:
    fig = px.treemap(
        df_tree,
        path=[px.Constant("Semua"), "Kelas", "Spesies"],
        values="Total",
        color="Kelas",
        hover_data={
            "Nama_Lokal": True,
            "Status_IUCN": True,
            "Total": True,
            "Kelas": False,
            "Spesies": False,
        },
        color_discrete_sequence=px.colors.qualitative.Safe,
        title="Distribusi Tangkapan per Spesies" + (
            f" — Kamera: {', '.join(str(c) for c in selected_cameras)}"
            if selected_cameras else " — Semua Kamera"
        ),
    )
    fig.update_traces(
        texttemplate="<b>%{label}</b><br>%{value} tangkapan",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Nama Lokal: %{customdata[0]}<br>"
            "Status IUCN: %{customdata[1]}<br>"
            "Total Tangkapan: %{value}<extra></extra>"
        ),
        root_color="rgba(0,0,0,0)",
    )
    fig.update_layout(
        height=520,
        margin=dict(t=50, l=10, r=10, b=10),
        font_family="Arial",
    )
    st.plotly_chart(fig, use_container_width=True)
