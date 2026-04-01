import streamlit as st
import folium
import requests
import pandas as pd
from streamlit_folium import st_folium
from shapely.geometry import Point, shape

st.set_page_config(layout="wide")

st.title("Camera Trap Distribution")

st.sidebar.header("Controls")
st.sidebar.write("This is placeholder UI")

m = folium.Map(
    location=[0.7768975139061223, 110.26771899364478],
    zoom_start=11,
    tiles="CartoDB positron"
)

sheet_url = "https://docs.google.com/spreadsheets/d/1o3EIYudtvLR_mMxknK9nIE4k3ulv02sP7aCT2trDX_g/export?format=csv"

df = pd.read_csv(sheet_url)
df.columns = df.columns.str.strip()

points = [Point(row["Longitude"], row["Latitude"]) for _, row in df.iterrows()]

# GRID LAYER (WITH ANALYSIS)

grid_id = "1r19dsxoqU-fY0XvPu1gonn7k1kNA3lyo"
grid_url = f"https://drive.google.com/uc?export=download&id={grid_id}"

grid_res = requests.get(grid_url)
grid_data = grid_res.json()

def style_grid(feature):
    polygon = shape(feature["geometry"])
    
    has_point = any(polygon.contains(pt) for pt in points)

    return {
        "color": "black",
        "weight": 1,
        "fillColor": "red" if has_point else "transparent",
        "fillOpacity": 0.5 if has_point else 0
    }

folium.GeoJson(
    grid_data,
    name="Grid",
    style_function=style_grid
).add_to(m)

# LAYER 2 (CMI)
layer2_id = "19pbjbedC3iF48QgLbatDA-XeNF4flIgc"
layer2_url = f"https://drive.google.com/uc?export=download&id={layer2_id}"

layer2_res = requests.get(layer2_url)
layer2_data = layer2_res.json()

folium.GeoJson(
    layer2_data,
    name="Konsesi",
    style_function=lambda feature: {
        "color": "purple",
        "weight": 3,
        "fillOpacity": 0
    }
).add_to(m)


grouped = df.groupby(["Latitude", "Longitude"])

for (lat, lon), group in grouped:
    
    total_records = len(group)
    unique_species = group["Spesies"].nunique()
    
    species_count = group["Spesies"].value_counts().to_dict()
    
    popup_html = f"""
    <b>Camera Trap</b><br>
    Total Records: {total_records}<br>
    Unique Species: {unique_species}<br><br>
    <b>Species Count:</b><br>
    """
    
    for sp, count in species_count.items():
        popup_html += f"{sp}: {count}<br>"
    
    folium.CircleMarker(
        location=[lat, lon],
        radius=5,
        color="blue",
        fill=True,
        fillOpacity=0.8,
        popup=folium.Popup(popup_html, max_width=250)
    ).add_to(m)

folium.LayerControl().add_to(m)

st_folium(m, width="100%", height=600)
