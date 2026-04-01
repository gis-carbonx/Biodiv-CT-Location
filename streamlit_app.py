import streamlit as st
import folium
import requests
from streamlit_folium import st_folium

st.title("Simple Map")

m = folium.Map(
    location=[0.7942129043922784, 110.23949401166948],
    zoom_start=10,
    tiles="CartoDB positron"
)

# Load grid GeoJSON from Google Drive
url = "https://drive.google.com/uc?id=1r19dsxoqU-fY0XvPu1gonn7k1kNA3lyo"
data = requests.get(url).json()

# Style grid
def style_function(feature):
    return {
        "fillColor": "transparent",
        "color": "black",  
        "weight": 1,
        "fillOpacity": 0  
    }

folium.GeoJson(
    data,
    name="Grid",
    style_function=style_function,
    tooltip=folium.GeoJsonTooltip(
        fields=["Index"],
        aliases=["Grid ID:"], 
        sticky=True
    )
).add_to(m)

st_folium(m, width=700, height=500)
