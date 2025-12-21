import streamlit as st
import pandas as pd
import math, io, os
from fpdf import FPDF

# =========================================================
# 1. THEME & FORCEER DONKERE INVOERVELDEN (GEEN WIT)
# =========================================================
st.set_page_config(page_title="Logistiek Planning Systeem", layout="wide")

def apply_pro_industrial_theme():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
        
        /* Basis Achtergrond */
        .stApp { background-color: #0b0f14; color: #ffffff; font-family: 'Inter', sans-serif; }
        
        /* SIDEBAR */
        section[data-testid="stSidebar"] { background-color: #05070a !important; border-right: 1px solid #1e293b; }
        section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label {
            color: #38bdf8 !important; font-weight: 600;
        }

        /* --- FORCEER DONKERE INVOERVELDEN (DE OPLOSSING) --- */
        
        /* 1. Algemene tabel achtergrond */
        div[data-testid="stDataEditor"] {
            background-color: #161d27 !important;
            border: 1px solid #334155 !important;
        }

        /* 2. Forceer de 'canvas' en alle interne containers van de editor naar donker */
        div[data-testid="stDataEditor"] > div {
            background-color: #161d27 !important;
        }

        /* 3. Specifieke styling voor de handmatige invoer-cellen (Glide Data Grid) */
        /* Dit zorgt dat de cellen NIET wit uitslaan als ze passief zijn */
        [data-testid="stDataEditor"] canvas {
            filter: invert(0.9) hue-rotate(180deg) brightness(0.8); /* Techniek om canvas kleuren om te draaien naar donker */
        }

        /* 4. Andere Streamlit invoervelden (mochten die gebruikt worden) */
        input, select, textarea {
            background-color: #161d27 !important;
            color: #ffffff !important;
            border: 1px solid #334155 !important;
        }

        /* Download knop fix */
        div.stDownloadButton > button {
            background-color: #1e293b !important;
            color: #ffffff !important;
            border: 1px solid #38bdf8 !important;
            font-weight: 600;
            width: 100%;
        }
        div.stDownloadButton > button:hover {
            background-color: #38bdf8 !important;
            color: #000000 !important;
        }

        /* TABS Styling */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: transparent; }
        .stTabs [data-baseweb="tab"] {
            height: 45px; background-color: #1e293b; border-radius: 4px 4px 0px 0px; color: #ffffff; 
            border: none; padding: 0px 25px;
        }
        .stTabs [aria-selected="true"] { 
            background-color: #38bdf8 !important; color: #000000 !important; font-weight: bold; 
        }

        /* Titels */
        .table-title { color: #38bdf8; font-weight: 700; font-size: 1.1rem; margin-top: 25px; margin-bottom: 10px; }
        
        /* Actie knop */
        div.stButton > button {
            background: #38bdf8 !important; color: #000000 !important; border: none !important;
            font-weight: 700; height: 3.5em;
        }
    </style>
    """, unsafe_allow_html=True)

apply_pro_industrial_theme()

# =========================================================
# 2. CONFIGURATIE & MEERTALIGHEID
# =========================================================
LANGS = {
    "NL": {
        "tab_input": "01: DATA INVOER", "tab_output": "02: RESULTATEN",
        "btn_calc": "Start Berekening", "header_master": "Artikelen Master Data", 
        "header_boxes": "Dozen Configuraties", "header_pallets": "Pallet Types", 
        "header_trucks": "Vloot Beheer (Trucks/Containers)"
    },
    "EN": {
        "tab_input": "01: DATA INPUT", "tab_output": "02: RESULTS",
        "btn_calc": "Start Calculation", "header_master": "Items Master Data", 
        "header_boxes": "Box Configurations", "header_pallets": "Pallet Types", 
        "header_trucks": "Fleet Management"
    }
}

lang_choice = st.sidebar.selectbox("Taal / Language", ["NL", "EN"])
T = LANGS[lang_choice]

# Kolomdefinities
MASTER_COLS = {"ItemNr": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
BOXES_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
TRUCK_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "MaxGewicht": float}

# Init Session State
for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("custom_trucks_df", TRUCK_COLS)]:
    if key not in st.session_state: 
        st.session_state[key] = pd.DataFrame(columns=cols.keys())

# =========================================================
# 3. DASHBOARD LAYOUT
# =========================================================
st.title("Logistiek Planning Systeem")

tab_data, tab_results = st.tabs([f" {T['tab_input']} ", f" {T['tab_output']} "])

with tab_data:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.download_button("Download Lege Template", io.BytesIO(b"Data").getvalue(), "template.xlsx")
    with c2:
        up = st.file_uploader("EXCEL IMPORT (.XLSX)", type="xlsx")

    st.markdown(f"<div class='table-title'>{T['header_master']}</div>", unsafe_allow_html=True)
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", key="m_ed", use_container_width=True)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(f"<div class='table-title'>{T['header_boxes']}</div>", unsafe_allow_html=True)
        st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", key="b_ed", use_container_width=True)
    
    with col_r:
        st.markdown(f"<div class='table-title'>{T['header_trucks']}</div>", unsafe_allow_html=True)
        st.session_state.custom_trucks_df = st.data_editor(st.session_state.custom_trucks_df, num_rows="dynamic", key="t_ed", use_container_width=True)
        
        st.write("")
        if st.button(T["btn_calc"]):
            st.toast("Berekening gestart...", icon="🚛")

with tab_results:
    st.subheader("Transport Analyse Resultaten")
    st.info("De planning verschijnt hier na de berekening.")
