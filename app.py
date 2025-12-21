import streamlit as st
import pandas as pd
import math, io, os
from fpdf import FPDF

# =========================================================
# 1. THEME & ENGINE UI (Industrial Contrast)
# =========================================================
st.set_page_config(page_title="PLEKSEL PRO - ENGINE", layout="wide")

def apply_simulator_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Rajdhani:wght@600&display=swap');
        
        .stApp { background-color: #05070a; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; }
        
        /* SIDEBAR: Donker met fel Cyaan tekst */
        section[data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #38bdf8; }
        section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label {
            color: #38bdf8 !important; font-family: 'Rajdhani', sans-serif; font-size: 1.1rem !important;
        }

        /* TABS Styling */
        .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #05070a; }
        .stTabs [data-baseweb="tab"] {
            height: 50px; background-color: #1e293b; border-radius: 5px 5px 0px 0px; color: #ffffff; padding: 10px 30px;
        }
        .stTabs [aria-selected="true"] { background-color: #38bdf8 !important; color: #000000 !important; font-weight: bold; }

        /* Headers & Containers */
        h1, h2, h3 { font-family: 'Rajdhani', sans-serif; color: #38bdf8; text-transform: uppercase; letter-spacing: 2px; }
        .table-header { font-weight: bold; color: #38bdf8; margin-top: 15px; border-bottom: 1px solid #38bdf8; padding-bottom: 5px; }
        
        /* Buttons */
        div.stButton > button {
            background: #ffaa00 !important; color: #000000 !important; border: none !important;
            font-weight: bold; text-transform: uppercase; width: 100%; height: 3em;
        }
    </style>
    """, unsafe_allow_html=True)

apply_simulator_css()

# =========================================================
# 2. CONFIGURATIE & MEERTALIGHEID (JOUW DATA)
# =========================================================
LANGS = {
    "NL": {
        "tab_input": "01: MISSION DATA", "tab_output": "02: RESULTS",
        "btn_calc": "Bereken Planning", "pals": "Pallets", "weight": "Totaal Gewicht (KG)", 
        "meters": "Laadmeters", "trucks": "Trucks Nodig", "opt_stack": "Pallets stapelbaar?",
        "download_template": "Download Lege Template", "header_master": "📦 Artikelen Master Data", 
        "header_boxes": "🎁 Dozen Configuratie", "header_pallets": "🟫 Pallet Types", "header_trucks": "🚛 Custom Trucks"
    },
    "EN": {
        "tab_input": "01: MISSION DATA", "tab_output": "02: RESULTS",
        "btn_calc": "Calculate Planning", "pals": "Pallets", "weight": "Total Weight (KG)", 
        "meters": "Loading Meters", "trucks": "Trucks Needed", "opt_stack": "Pallets stackable?",
        "download_template": "Download Empty Template", "header_master": "📦 Items Master Data", 
        "header_boxes": "🎁 Boxes Configuration", "header_pallets": "🟫 Pallet Types", "header_trucks": "🚛 Custom Trucks"
    }
}

# Sidebar settings & Taal selectie
st.sidebar.title("SYSTEM SETTINGS")
lang_choice = st.sidebar.selectbox("Select Language", ["NL", "EN"])
T = LANGS[lang_choice]

# Kolomdefinities (Jouw originele specs)
MASTER_COLS = {"ItemNr": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
BOXES_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
PALLETS_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "MaxHoogte": float, "Gewicht": float, "PalletHoogte": float, "PalletStapelbaar": bool}
TRUCK_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "MaxGewicht": float}

# Init Session State (Jouw originele specs)
for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("orders_df", {"OrderNr": str, "ItemNr": str, "Aantal": int}), ("custom_trucks_df", TRUCK_COLS)]:
    if key not in st.session_state: 
        st.session_state[key] = pd.DataFrame(columns=cols.keys())

# =========================================================
# 3. INTERFACE (TABBLADEN)
# =========================================================
st.title("🚛 PLEKSEL PRO ENGINE")

tab_data, tab_results = st.tabs([f" [ {T['tab_input']} ] ", f" [ {T['tab_output']} ] "])

# --- TAB 1: DATA INVOER ---
with tab_data:
    st.subheader("COMMAND & DATA INPUT")
    
    # Download/Upload Sectie
    c1, c2 = st.columns([1, 2])
    with c1:
        st.download_button(T["download_template"], io.BytesIO().getvalue(), "template.xlsx")
    with c2:
        up = st.file_uploader("UPLOAD EXCEL MANIFEST", type="xlsx")

    # Hoofd Tabel
    st.markdown(f"<div class='table-header'>{T['header_master']}</div>", unsafe_allow_html=True)
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", key="m_ed", use_container_width=True)

    # Sub Tabellen
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown(f"<div class='table-header'>{T['header_boxes']}</div>", unsafe_allow_html=True)
        st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", key="b_ed", use_container_width=True)
    
    with col_right:
        st.markdown(f"<div class='table-header'>{T['header_pallets']}</div>", unsafe_allow_html=True)
        st.session_state.pallets_df = st.data_editor(st.session_state.pallets_df, num_rows="dynamic", key="p_ed", use_container_width=True)

    st.markdown(f"<div class='table-header'>{T['header_trucks']}</div>", unsafe_allow_html=True)
    st.session_state.custom_trucks_df = st.data_editor(st.session_state.custom_trucks_df, num_rows="dynamic", key="t_ed", use_container_width=True)

    st.divider()
    if st.button(T["btn_calc"]):
        st.success("SIMULATION STARTED...")

# --- TAB 2: UITKOMSTEN ---
with tab_results:
    st.subheader("MISSION ANALYTICS")
    
    # HUD Display voor statistieken
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(T["pals"], "0")
    m2.metric(T["weight"], "0 KG")
    m3.metric(T["meters"], "0.0 m")
    m4.metric(T["trucks"], "0")

    st.markdown("<div class='table-header'>LOADING PLAN SEQUENCE</div>", unsafe_allow_html=True)
    # Placeholder voor resultaten tabel
    st.info("No data processed. Please run calculation in the Mission Data tab.")
    
    st.sidebar.divider()
    st.sidebar.write("ENGINE STATUS: 🟢 ACTIVE")
