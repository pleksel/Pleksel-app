import streamlit as st
import pandas as pd
import math, io, os
from fpdf import FPDF

# =========================================================
# 1. THEME & GEAVANCEERDE CSS (KLEURRIJKE INVOERVELDEN)
# =========================================================
st.set_page_config(page_title="PLEKSEL PRO - ENGINE", layout="wide")

def apply_simulator_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Rajdhani:wght@600&display=swap');
        
        /* Basis Achtergrond */
        .stApp { background-color: #05070a; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; }
        
        /* SIDEBAR: Donker met fel Cyaan tekst */
        section[data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #38bdf8; }
        section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label {
            color: #38bdf8 !important; font-family: 'Rajdhani', sans-serif; font-size: 1.1rem !important;
        }

        /* DATA EDITOR / INVOERVELDEN STYLING */
        /* Dit zorgt ervoor dat de cellen in de tabel een industriële kleur krijgen in plaats van wit */
        div[data-testid="stDataEditor"] {
            background-color: #111827 !important;
            border: 1px solid #38bdf8 !important;
            border-radius: 5px;
        }
        
        /* De tekst binnen de editor cellen */
        div[data-testid="stDataEditor"] [role="gridcell"] {
            background-color: #1e293b !important;
            color: #38bdf8 !important;
            border: 0.5px solid #334155 !important;
        }

        /* TABS Styling */
        .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #05070a; }
        .stTabs [data-baseweb="tab"] {
            height: 50px; background-color: #1e293b; border-radius: 5px 5px 0px 0px; color: #ffffff; padding: 10px 30px;
        }
        .stTabs [aria-selected="true"] { background-color: #38bdf8 !important; color: #000000 !important; font-weight: bold; }

        /* Headers & Containers */
        h1, h2, h3 { font-family: 'Rajdhani', sans-serif; color: #38bdf8; text-transform: uppercase; letter-spacing: 2px; }
        .table-header { font-weight: bold; color: #38bdf8; margin-top: 15px; border-bottom: 2px solid #38bdf8; padding-bottom: 5px; font-size: 1.2rem; }
        
        /* Buttons (Opvallend Oranje) */
        div.stButton > button {
            background: #ffaa00 !important; color: #000000 !important; border: 2px solid #cc8800 !important;
            font-weight: bold; text-transform: uppercase; width: 100%; height: 3.5em;
            box-shadow: 0 0 10px rgba(255, 170, 0, 0.4);
        }
        
        /* File Uploader Contrast */
        div[data-testid="stFileUploadDropzone"] {
            background-color: #1e293b !important;
            border: 2px dashed #38bdf8 !important;
        }
    </style>
    """, unsafe_allow_html=True)

apply_simulator_css()

# =========================================================
# 2. CONFIGURATIE & MEERTALIGHEID (ALLE FUNCTIES BEHOUDEN)
# =========================================================
LANGS = {
    "NL": {
        "tab_input": "01: MISSION DATA", "tab_output": "02: RESULTS",
        "btn_calc": "Bereken Planning", "pals": "Pallets", "weight": "Totaal Gewicht (KG)", 
        "meters": "Laadmeters", "trucks": "Trucks Nodig", "opt_stack": "Pallets stapelbaar?",
        "download_template": "Download Lege Template", "header_master": "Artikelen Master Data", 
        "header_boxes": "Dozen Configuratie", "header_pallets": "Pallet Types", "header_trucks": "Custom Trucks / Containers"
    },
    "EN": {
        "tab_input": "01: MISSION DATA", "tab_output": "02: RESULTS",
        "btn_calc": "Calculate Planning", "pals": "Pallets", "weight": "Total Weight (KG)", 
        "meters": "Loading Meters", "trucks": "Trucks Needed", "opt_stack": "Pallets stackable?",
        "download_template": "Download Empty Template", "header_master": "Items Master Data", 
        "header_boxes": "Boxes Configuration", "header_pallets": "Pallet Types", "header_trucks": "Custom Trucks / Containers"
    },
    "DE": { "tab_input": "01: MISSION DATA", "tab_output": "02: RESULTS", "btn_calc": "Planung berechnen", "pals": "Paletten", "weight": "Gesamtgewicht (KG)", "meters": "Lademeter", "trucks": "LKW benötigt", "opt_stack": "Paletten stapelbaar?", "download_template": "Leere Vorlage herunterladen", "header_master": "Stammdaten Artikel", "header_boxes": "Karton Konfiguration", "header_pallets": "Palettentypen", "header_trucks": "Eigene LKW / Container" },
    "PL": { "tab_input": "01: MISSION DATA", "tab_output": "02: RESULTS", "btn_calc": "Oblicz planowanie", "pals": "Palety", "weight": "Waga całkowita (KG)", "meters": "Metry ładunkowe", "trucks": "Potrzebne ciężarówki", "opt_stack": "Palety piętrowalne?", "download_template": "Pobierz pusty szablon", "header_master": "Dane podstawowe produktów", "header_boxes": "Konfiguracja kartonów", "header_pallets": "Typy palet", "header_trucks": "Własne ciężarówki / kontenery" }
}

st.sidebar.title("SYSTEM SETTINGS")
lang_choice = st.sidebar.selectbox("Language / Język / Sprache", ["NL", "EN", "DE", "PL"])
T = LANGS[lang_choice]

# Kolomdefinities
MASTER_COLS = {"ItemNr": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
BOXES_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
PALLETS_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "MaxHoogte": float, "Gewicht": float, "PalletHoogte": float, "PalletStapelbaar": bool}
TRUCK_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "MaxGewicht": float}

# Init Session State
for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("orders_df", {"OrderNr": str, "ItemNr": str, "Aantal": int}), ("custom_trucks_df", TRUCK_COLS)]:
    if key not in st.session_state: 
        st.session_state[key] = pd.DataFrame(columns=cols.keys())

# =========================================================
# 3. INTERFACE (TABS)
# =========================================================
st.title("🚛 TRUCK LOAD COMMAND CENTER")

tab_data, tab_results = st.tabs([f" {T['tab_input']} ", f" {T['tab_output']} "])

with tab_data:
    # Bovenste actie-rij
    c1, c2 = st.columns([1, 2])
    with c1:
        st.download_button(T["download_template"], io.BytesIO().getvalue(), "template.xlsx")
    with c2:
        up = st.file_uploader("EXCEL IMPORT", type="xlsx")

    # Hoofdtabel: Artikelen (Ingekleurde cellen via CSS bovenin)
    st.markdown(f"<div class='table-header'>{T['header_master']}</div>", unsafe_allow_html=True)
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", key="m_ed", use_container_width=True)

    # Grid voor Dozen, Pallets en Trucks
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(f"<div class='table-header'>{T['header_boxes']}</div>", unsafe_allow_html=True)
        st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", key="b_ed", use_container_width=True)
        
        st.markdown(f"<div class='table-header'>{T['header_pallets']}</div>", unsafe_allow_html=True)
        st.session_state.pallets_df = st.data_editor(st.session_state.pallets_df, num_rows="dynamic", key="p_ed", use_container_width=True)

    with col_r:
        st.markdown(f"<div class='table-header'>{T['header_trucks']}</div>", unsafe_allow_html=True)
        st.session_state.custom_trucks_df = st.data_editor(st.session_state.custom_trucks_df, num_rows="dynamic", key="t_ed", use_container_width=True)
        
        # Extra ruimte voor acties
        st.write("")
        st.write("")
        if st.button(T["btn_calc"]):
            st.toast("Calculating Engine Started...", icon="⏳")

with tab_results:
    st.subheader("ANALYTICS OUTPUT")
    
    # HUD-stijl statistieken
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    res_col1.metric(T["pals"], "0")
    res_col2.metric(T["weight"], "0 KG")
    res_col3.metric(T["meters"], "0.0 m")
    res_col4.metric(T["trucks"], "0")

    st.divider()
    st.info("No calculations performed yet. Fill in the mission data and press 'Bereken Planning'.")

# Footer in sidebar
st.sidebar.divider()
st.sidebar.markdown("SYSTEM: **ACTIVE**")
st.sidebar.markdown("VERSION: **2.5.0-PRO**")
