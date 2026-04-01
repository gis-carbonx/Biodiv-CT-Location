import streamlit as st
import folium
import geopandas as gpd
from streamlit_folium import st_folium

st.title("Simple Map")

m = folium.Map(
    location=[0.7942129043922784, 110.23949401166948],
    zoom_start=10,
    tiles="CartoDB positron"
)

gdf = gpd.read_file("./Data/Grid.json")

folium.GeoJson(gdf, name="Grid").add_to(m)

st_folium(m, width=700, height=500)
