import streamlit as st
import pandas as pd
import io

# =========================================================
# 1. THEME & STYLING (ELIMINATIE VAN WITTE VLAKKEN)
# =========================================================
st.set_page_config(page_title="Logistiek Planning Systeem", layout="wide")

def apply_final_pro_theme():
    st.markdown("""
    <style>
        /* Basis achtergrond van de hele app */
        .stApp { 
            background-color: #0b0f14; 
            color: #ffffff; 
        }

        /* --- 1. DATA EDITOR (DE TABELLEN) --- */
        /* De container van de tabel */
        div[data-testid="stDataEditor"] {
            background-color: #161d27 !important;
            border: 1px solid #38bdf8 !important;
            border-radius: 4px;
        }

        /* Forceer de achtergrond van de grid-laag die op de foto wit was */
        div[data-testid="stDataEditor"] > div:first-child {
            background-color: #161d27 !important;
        }

        /* De 'canvas' filter: hiermee draaien we de kleuren van de tabelinhoud om 
           zodat deze altijd donker is, ook zonder muis-over. */
        div[data-testid="stDataEditor"] canvas {
            filter: invert(0.9) hue-rotate(180deg) brightness(0.7) contrast(1.2);
        }

        /* --- 2. FILE UPLOADER (UPLOAD VAK) --- */
        /* Het vak zelf */
        div[data-testid="stFileUploadDropzone"] {
            background-color: #161d27 !important;
            border: 2px dashed #38bdf8 !important;
            color: #ffffff !important;
        }
        
        /* De knop 'Browse files' in de uploader */
        div[data-testid="stFileUploadDropzone"] button {
            background-color: #1e293b !important;
            color: #38bdf8 !important;
            border: 1px solid #38bdf8 !important;
        }

        /* --- 3. KNOPPEN (DOWNLOAD & BEREKEN) --- */
        /* De witte downloadknop uit de foto herstellen */
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

        /* De blauwe actieknop */
        div.stButton > button {
            background-color: #38bdf8 !important;
            color: #000000 !important;
            font-weight: 700;
            border: none !important;
            height: 3.5em;
        }

        /* --- 4. TABS & TITELS --- */
        .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
        .stTabs [data-baseweb="tab"] {
            background-color: #1e293b;
            color: #ffffff;
            border-radius: 4px 4px 0px 0px;
            margin-right: 5px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #38bdf8 !important;
            color: #000000 !important;
        }

        .table-title {
            color: #38bdf8;
            font-weight: 700;
            font-size: 1.15rem;
            margin-top: 30px;
            margin-bottom: 10px;
            text-transform: none;
        }

        /* Sidebar tekstkleur */
        section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label {
            color: #38bdf8 !important;
        }
    </style>
    """, unsafe_allow_html=True)

apply_final_pro_theme()

# =========================================================
# 2. LOGISTIEKE CONFIGURATIE & DATA
# =========================================================
LANGS = {
    "NL": {
        "tab_in": "01: DATA INVOER", 
        "tab_out": "02: RESULTATEN",
        "btn_calc": "Start Berekening", 
        "header_master": "Artikelen Master Data", 
        "header_boxes": "Dozen Configuraties", 
        "header_trucks": "Vloot Beheer (Trucks/Containers)"
    }
}
T = LANGS["NL"]

# Kolomdefinities voor de tabellen
MASTER_COLS = {"ItemNr": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
BOXES_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
TRUCK_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "MaxGewicht": float}

# Initialize Session State voor data behoud
for key, cols in [("master_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("trucks_df", TRUCK_COLS)]:
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(columns=cols.keys())

# =========================================================
# 3. DASHBOARD INTERFACE
# =========================================================
st.title("Logistiek Planning Systeem")

tab_data, tab_results = st.tabs([f" {T['tab_in']} ", f" {T['tab_out']} "])

with tab_data:
    # Bovenste sectie: Bestanden
    col_btn, col_up = st.columns([1, 2])
    with col_btn:
        st.download_button("Download Lege Template", io.BytesIO(b"Data").getvalue(), "template.xlsx")
    with col_up:
        # Dit vak is nu donker door de CSS
        st.file_uploader("EXCEL IMPORT (.XLSX)", type="xlsx")

    # Hoofdtabel: Artikelen
    st.markdown(f"<div class='table-title'>{T['header_master']}</div>", unsafe_allow_html=True)
    st.session_state.master_df = st.data_editor(
        st.session_state.master_df, 
        num_rows="dynamic", 
        key="editor_master", 
        use_container_width=True
    )

    # Onderste rij: Configuratie
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(f"<div class='table-title'>{T['header_boxes']}</div>", unsafe_allow_html=True)
        st.session_state.boxes_df = st.data_editor(
            st.session_state.boxes_df, 
            num_rows="dynamic", 
            key="editor_boxes", 
            use_container_width=True
        )
    
    with col_r:
        st.markdown(f"<div class='table-title'>{T['header_trucks']}</div>", unsafe_allow_html=True)
        st.session_state.trucks_df = st.data_editor(
            st.session_state.trucks_df, 
            num_rows="dynamic",
