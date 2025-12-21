import streamlit as st
import pandas as pd
import math, io, os
from fpdf import FPDF

# =========================================================
# 1. THEME & GEAVANCEERDE CSS (CONTRAST OPTIMALISATIE)
# =========================================================
st.set_page_config(page_title="PLEKSEL LOGISTICS PRO", layout="wide")

def apply_pro_industrial_theme():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
        
        /* Basis Achtergrond */
        .stApp { background-color: #0b0f14; color: #ffffff; font-family: 'Inter', sans-serif; }
        
        /* SIDEBAR: Donkergrijs/Zwart met Blauwe accenten */
        section[data-testid="stSidebar"] { background-color: #05070a !important; border-right: 1px solid #1e293b; }
        section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label {
            color: #38bdf8 !important; font-weight: 600;
        }

        /* DATA EDITOR / INVOERVELDEN (FIX VOOR WITTE VAKKEN) */
        /* Dit overschrijft de witte achtergrond van de tabellen uit de foto */
        div[data-testid="stDataEditor"] {
            background-color: #111827 !important;
            border: 1px solid #334155 !important;
            border-radius: 4px;
        }
        
        /* De cellen zelf krijgen een diepe kleur */
        div[data-testid="stDataEditor"] [role="gridcell"], 
        div[data-testid="stDataEditor"] [role="columnheader"] {
            background-color: #161d27 !important;
            color: #e2e8f0 !important;
            border: 0.5px solid #1e293b !important;
        }

        /* TABS Styling gebaseerd op de foto */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: transparent; }
        .stTabs [data-baseweb="tab"] {
            height: 45px; background-color: #1e293b; border-radius: 4px 4px 0px 0px; color: #ffffff; 
            border: none; padding: 0px 25px;
        }
        .stTabs [aria-selected="true"] { 
            background-color: #38bdf8 !important; color: #000000 !important; font-weight: bold; 
        }

        /* Headers: Zakelijk en strak */
        h1, h2, h3 { color: #38bdf8; font-weight: 700; text-transform: none; letter-spacing: -0.5px; }
        .table-title { color: #38bdf8; font-weight: 700; font-size: 1.2rem; margin-top: 25px; margin-bottom: 10px; }
        
        /* Knoppen: Opvallend maar zakelijk */
        div.stButton > button {
            background: #38bdf8 !important; color: #000000 !important; border: none !important;
            font-weight: 700; width: 100%; height: 3em; transition: 0.3s;
        }
        div.stButton > button:hover { background: #7dd3fc !important; box-shadow: 0 0 15px rgba(56, 189, 248, 0.4); }
        
        /* File Uploader styling */
        div[data-testid="stFileUploadDropzone"] {
            background-color: #161d27 !important; border: 1px dashed #38bdf8 !important;
        }
    </style>
    """, unsafe_allow_html=True)

apply_pro_industrial_theme()

# =========================================================
# 2. LOGISTIEKE CONFIGURATIE (GEEN GAME BENAMINGEN)
# =========================================================
LANGS = {
    "NL": {
        "tab_input": "01: DATA INVOER", 
        "tab_output": "02: RESULTATEN",
        "btn_calc": "Start Berekening",
        "header_master": "Artikelen Master Data", 
        "header_boxes": "Dozen Configuraties", 
        "header_pallets": "Pallet Types", 
        "header_trucks": "Vloot Beheer (Trucks/Containers)"
    },
    "EN": {
        "tab_input": "01: DATA INPUT", 
        "tab_output": "02: RESULTS",
        "btn_calc": "Start Calculation",
        "header_master": "Items Master Data", 
        "header_boxes": "Box Configurations", 
        "header_pallets": "Pallet Types", 
        "header_trucks": "Fleet Management"
    }
}

st.sidebar.title("Instellingen")
lang_choice = st.sidebar.selectbox("Taal / Language", ["NL", "EN"])
T = LANGS[lang_choice]

# Kolomdefinities
MASTER_COLS = {"ItemNr": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
BOXES_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
PALLETS_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "MaxHoogte": float, "Gewicht": float, "PalletHoogte": float, "PalletStapelbaar": bool}
TRUCK_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "MaxGewicht": float}

# Init Session State
for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("custom_trucks_df", TRUCK_COLS)]:
    if key not in st.session_state: 
        st.session_state[key] = pd.DataFrame(columns=cols.keys())

# =========================================================
# 3. DASHBOARD LAYOUT
# =========================================================
st.title("Logistiek Planning Systeem")

tab_data, tab_results = st.tabs([f" {T['tab_input']} ", f" {T['tab_output']} "])

with tab_data:
    # Bovenste rij: Template & Import
    c1, c2 = st.columns([1, 2])
    with c1:
        st.download_button("Download Lege Template", io.BytesIO().getvalue(), "template.xlsx")
    with c2:
        up = st.file_uploader("EXCEL IMPORT (.XLSX)", type="xlsx")

    # Hoofdtabel: Artikelen
    st.markdown(f"<div class='table-title'>{T['header_master']}</div>", unsafe_allow_html=True)
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", key="m_ed", use_container_width=True)

    # Grid voor Dozen, Pallets en Vloot
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(f"<div class='table-title'>{T['header_boxes']}</div>", unsafe_allow_html=True)
        st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", key="b_ed", use_container_width=True)
        
        st.markdown(f"<div class='table-title'>{T['header_pallets']}</div>", unsafe_allow_html=True)
        st.session_state.pallets_df = st.data_editor(st.session_state.pallets_df, num_rows="dynamic", key="p_ed", use_container_width=True)

    with col_r:
        st.markdown(f"<div class='table-title'>{T['header_trucks']}</div>", unsafe_allow_html=True)
        st.session_state.custom_trucks_df = st.data_editor(st.session_state.custom_trucks_df, num_rows="dynamic", key="t_ed", use_container_width=True)
        
        st.write("")
        if st.button(T["btn_calc"]):
            st.toast("Berekening gestart...", icon="🚛")

with tab_results:
    st.subheader("Transport Analyse")
    st.info("Voer data in en klik op 'Start Berekening' om de resultaten te bekijken.")

st.sidebar.divider()
st.sidebar.caption("Versie 3.0.1 | Data-driven Logistics")
