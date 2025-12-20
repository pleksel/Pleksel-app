import streamlit as st
import pandas as pd
import math, io, os, shutil
from fpdf import FPDF

# =========================================================
# 1. PAGE CONFIG & THEMA
# =========================================================
st.set_page_config(page_title="PLEKSEL PRO", page_icon="🚛", layout="wide")

st.markdown("""
<style>
    h1 { text-align: center; color: #007AA3; }
    div.stButton > button { width: 100%; border-radius: 0.5rem; border: 1px solid #007AA3; background-color: #e0f2f7; color: #007AA3; }
    div[data-testid="stMetric"], .stContainer { border-radius: 8px; background-color: #f0f8ff; border: 1px solid #cce5ff; padding: 15px; }
    .table-header { font-weight: bold; color: #007AA3; margin-top: 20px; margin-bottom: 10px; border-bottom: 2px solid #007AA3; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. CONFIGURATIE & MEERTALIGHEID
# =========================================================
TEMPLATE_DIR = "pleksel_templates"
os.makedirs(TEMPLATE_DIR, exist_ok=True)

TRANSPORT_PRESETS = {
    "Standaard Truck Trailer": {"Lengte": 1360, "Breedte": 245, "Hoogte": 270, "MaxGewicht": 24000},
    "20ft Container": {"Lengte": 590, "Breedte": 235, "Hoogte": 239, "MaxGewicht": 28000},
    "40ft Container": {"Lengte": 1203, "Breedte": 235, "Hoogte": 239, "MaxGewicht": 26000},
}

LANGS = {
    "NL": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Planning",
        "btn_calc": "Bereken Planning", "pals": "Pallets", "weight": "Totaal Gewicht (KG)", 
        "meters": "Laadmeters", "trucks": "Trucks Nodig", "opt_stack": "Pallets stapelbaar?",
        "opt_mix_box": "Meerdere soorten dozen?", "opt_mixed_items": "Mixed items in doos?",
        "opt_separate": "Orders apart berekenen?", "download_template": "Download Lege Template",
        "header_master": "📦 Artikelen Master Data", "header_boxes": "🎁 Dozen Configuratie",
        "header_pallets": "🟫 Pallet Types", "header_trucks": "🚛 Custom Trucks / Containers"
    },
    "EN": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Planning",
        "btn_calc": "Calculate Planning", "pals": "Pallets", "weight": "Total Weight (KG)", 
        "meters": "Loading Meters", "trucks": "Trucks Needed", "opt_stack": "Pallets stackable?",
        "opt_mix_box": "Multiple box types?", "opt_mixed_items": "Mixed items in box?",
        "opt_separate": "Calculate orders separately?", "download_template": "Download Empty Template",
        "header_master": "📦 Items Master Data", "header_boxes": "🎁 Boxes Configuration",
        "header_pallets": "🟫 Pallet Types", "header_trucks": "🚛 Custom Trucks / Containers"
    },
    "DE": {
        "nav_templates": "📁 Vorlagen", "nav_orders": "📑 Aufträge", "nav_calc": "🚛 Planung",
        "btn_calc": "Planung berechnen", "pals": "Paletten", "weight": "Gesamtgewicht (KG)", 
        "meters": "Lademeter", "trucks": "LKW benötigt", "opt_stack": "Paletten stapelbar?",
        "opt_mix_box": "Mehrere Kartontypen?", "opt_mixed_items": "Gemischte Artikel?",
        "opt_separate": "Aufträge separat?", "download_template": "Leere Vorlage herunterladen",
        "header_master": "📦 Stammdaten Artikel", "header_boxes": "🎁 Karton Konfiguration",
        "header_pallets": "🟫 Palettentypen", "header_trucks": "🚛 Eigene LKW / Container"
    },
    "PL": {
        "nav_templates": "📁 Szablony", "nav_orders": "📑 Zamówienia", "nav_calc": "🚛 Planowanie",
        "btn_calc": "Oblicz planowanie", "pals": "Palety", "weight": "Waga całkowita (KG)", 
        "meters": "Metry ładunkowe", "trucks": "Potrzebne ciężarówki", "opt_stack": "Palety piętrowalne?",
        "opt_mix_box": "Wiele rodzajów kartonów?", "opt_mixed_items": "Mieszane produkty?",
        "opt_separate": "Zamówienia oddzielnie?", "download_template": "Pobierz pusty szablon",
        "header_master": "📦 Dane podstawowe produktów", "header_boxes": "🎁 Konfiguracja kartonów",
        "header_pallets": "🟫 Typy palet", "header_trucks": "🚛 Własne ciężarówki / kontenery"
    }
}

st.sidebar.title("PLEKSEL Settings")
lang_choice = st.sidebar.selectbox("Language / Język / Sprache", ["NL", "EN", "DE", "PL"])
T = LANGS[lang_choice]

# Kolomdefinities
MASTER_COLS = {"ItemNr": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
BOXES_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
PALLETS_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "MaxHoogte": float, "Gewicht": float, "PalletHoogte": float, "PalletStapelbaar": bool}
TRUCK_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "MaxGewicht": float}

# Init Session State
for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("orders_df", {"OrderNr": str, "ItemNr": str, "Aantal": int}), ("custom_trucks_df", TRUCK_COLS)]:
    if key not in st.session_state: st.session_state[key] = pd.DataFrame(columns=cols.keys())

# ... [Functies voor optimalisatie en template creatie blijven hetzelfde] ...

# =========================================================
# 3. UI SECTIES MET TABEL-KOPPEN
# =========================================================
page = st.sidebar.radio("Menu", [T["nav_templates"], T["nav_orders"], T["nav_calc"]])

if page == T["nav_templates"]:
    st.header(T["nav_templates"])
    
    # Download/Upload
    c1, c2 = st.columns(2)
    with c1: st.download_button(T["download_template"], io.BytesIO().getvalue(), "template.xlsx") # Versimpeld voor voorbeeld
    with c2: up = st.file_uploader("Excel Upload", type="xlsx")

    # TABELLEN MET DUIDELIJKE TITELS
    st.markdown(f"<div class='table-header'>{T['header_master']}</div>", unsafe_allow_html=True)
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", key="m_ed", use_container_width=True)

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown(f"<div class='table-header'>{T['header_boxes']}</div>", unsafe_allow_html=True)
        st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", key="b_ed", use_container_width=True)
    
    with col_right:
        st.markdown(f"<div class='table-header'>{T['header_pallets']}</div>", unsafe_allow_html=True)
        st.session_state.pallets_df = st.data_editor(st.session_state.pallets_df, num_rows="dynamic", key="p_ed", use_container_width=True)

    st.markdown(f"<div class='table-header'>{T['header_trucks']}</div>", unsafe_allow_html=True)
    st.session_state.custom_trucks_df = st.data_editor(st.session_state.custom_trucks_df, num_rows="dynamic", key="t_ed", use_container_width=True)

# ... [Rest van de pagina-logica voor Orders en Planning] ...
