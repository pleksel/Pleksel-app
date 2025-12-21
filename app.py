import streamlit as st
import pandas as pd
import io

# =========================================================
# 1. THEME & CSS FIX (VOOR CONTRAST & LEESBAARHEID)
# =========================================================
st.set_page_config(page_title="Logistiek Planning Systeem", layout="wide")

def apply_ui_fix():
    st.markdown("""
    <style>
        /* Basis Achtergrond */
        .stApp { background-color: #0b0f14; color: #ffffff; }

        /* --- SIDEBAR FIX (LINKS) --- */
        /* Zorg dat de sidebar donker is en de tekst FELBLAUW/WIT */
        section[data-testid="stSidebar"] {
            background-color: #05070a !important;
            border-right: 1px solid #1e293b;
        }
        section[data-testid="stSidebar"] .stMarkdown, 
        section[data-testid="stSidebar"] label, 
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] p {
            color: #38bdf8 !important; /* Felblauw voor de titels */
            font-weight: bold !important;
            opacity: 1 !important;
        }
        /* Radio buttons en checkboxes tekst kleur */
        div[data-testid="stWidgetLabel"] p { color: #ffffff !important; }

        /* --- TABELLEN / DATA EDITOR --- */
        div[data-testid="stDataEditor"] {
            background-color: #161d27 !important;
            border: 1px solid #334155 !important;
        }
        /* Forceer donkere achtergrond in de cellen (geen wit meer) */
        div[data-testid="stDataEditor"] canvas {
            filter: invert(0.9) hue-rotate(180deg) brightness(0.8);
        }

        /* --- FILE UPLOADER --- */
        div[data-testid="stFileUploadDropzone"] {
            background-color: #161d27 !important;
            border: 2px dashed #38bdf8 !important;
            color: #ffffff !important;
        }

        /* --- DOWNLOAD KNOP (FIX WIT OP WIT) --- */
        div.stDownloadButton > button {
            background-color: #1e293b !important;
            color: #ffffff !important;
            border: 1px solid #38bdf8 !important;
            width: 100%;
        }

        /* --- TABS --- */
        .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
        .stTabs [data-baseweb="tab"] {
            background-color: #1e293b;
            color: #ffffff;
            padding: 10px 20px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #38bdf8 !important;
            color: #000000 !important;
        }

        /* Algemene Titels */
        .table-title { color: #38bdf8; font-weight: 700; font-size: 1.1rem; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

apply_ui_fix()

# =========================================================
# 2. CONFIGURATIE & MEERTALIGHEID (ALLE OPTIES TERUG)
# =========================================================
LANGS = {
    "NL": {
        "nav_in": "DATA INVOER", "nav_res": "RESULTATEN",
        "btn_calc": "Start Berekening", "opt_stack": "Pallets stapelbaar?",
        "opt_sep": "Orders apart berekenen?", "header_master": "Artikelen Master Data",
        "header_boxes": "Dozen Configuraties", "header_pallets": "Pallet Types",
        "header_trucks": "Vloot Beheer (Trucks/Containers)"
    },
    "EN": {
        "nav_in": "DATA INPUT", "nav_res": "RESULTS",
        "btn_calc": "Start Calculation", "opt_stack": "Stackable pallets?",
        "opt_sep": "Separate orders?", "header_master": "Items Master Data",
        "header_boxes": "Box Configurations", "header_pallets": "Pallet Types",
        "header_trucks": "Fleet Management"
    },
    "DE": { "nav_in": "DATENEINGABE", "nav_res": "ERGEBNISSE", "btn_calc": "Berechnung starten", "opt_stack": "Paletten stapelbar?", "opt_sep": "Aufträge separat?", "header_master": "Artikelstammdaten", "header_boxes": "Kartonkonfigurationen", "header_pallets": "Palettentypen", "header_trucks": "Fuhrpark" },
    "PL": { "nav_in": "DANE WEJŚCIOWE", "nav_res": "WYNIKI", "btn_calc": "Rozpocznij obliczenia", "opt_stack": "Palety piętrowalne?", "opt_sep": "Zamówienia osobno?", "header_master": "Dane podstawowe", "header_boxes": "Konfiguracja kartonów", "header_pallets": "Typy palet", "header_trucks": "Zarządzanie flotą" }
}

# Sidebar Instellingen (Nu goed leesbaar)
st.sidebar.title("SYSTEEM INSTELLINGEN")
lang_choice = st.sidebar.selectbox("Taal / Language", ["NL", "EN", "DE", "PL"])
T = LANGS[lang_choice]

st.sidebar.divider()
st.sidebar.subheader("BEREKENING OPTIES")
allow_stacking = st.sidebar.checkbox(T["opt_stack"], value=True)
calc_separate = st.sidebar.checkbox(T["opt_sep"], value=False)
safety_margin = st.sidebar.slider("Veiligheidsmarge (%)", 0, 10, 5)

# Kolomdefinities
MASTER_COLS = {"ItemNr": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
BOXES_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
PALLETS_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "MaxHoogte": float, "PalletHoogte": float, "PalletStapelbaar": bool}
TRUCK_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "MaxGewicht": float}

# Init Session State
for key, cols in [("master_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("trucks_df", TRUCK_COLS)]:
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(columns=cols.keys())

# =========================================================
# 3. INTERFACE (TABS)
# =========================================================
st.title("Logistiek Planning Systeem")

tab_data, tab_results = st.tabs([f" {T['nav_in']} ", f" {T['nav_res']} "])

with tab_data:
    # Bovenste rij: Knoppen & Upload
    c1, c2 = st.columns([1, 2])
    with c1:
        st.download_button("Download Lege Template", io.BytesIO(b"Data").getvalue(), "template.xlsx")
    with c2:
        st.file_uploader("EXCEL IMPORT (.XLSX)", type="xlsx")

    # Hoofdtabel: Artikelen
    st.markdown(f"<div class='table-title'>{T['header_master']}</div>", unsafe_allow_html=True)
    st.session_state.master_df = st.data_editor(st.session_state.master_df, num_rows="dynamic", key="m_ed", use_container_width=True)

    # Grid voor Dozen, Pallets en Vloot
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(f"<div class='table-title'>{T['header_boxes']}</div>", unsafe_allow_html=True)
        st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", key="b_ed", use_container_width=True)
        
        st.markdown(f"<div class='table-title'>{T['header_pallets']}</div>", unsafe_allow_html=True)
        st.session_state.pallets_df = st.data_editor(st.session_state.pallets_df, num_rows="dynamic", key="p_ed", use_container_width=True)

    with col_r:
        st.markdown(f"<div class='table-title'>{T['header_trucks']}</div>", unsafe_allow_html=True)
        st.session_state.trucks_df = st.data_editor(st.session_state.trucks_df, num_rows="dynamic", key="t_ed", use_container_width=True)
        
        st.write("")
        if st.button(T["btn_calc"]):
            st.toast("Berekening gestart...", icon="🚛")

with tab_results:
    st.subheader("Transport Analyse")
    st.info("De planning verschijnt hier na de berekening.")
