import streamlit as st
import pandas as pd
import io

# =========================================================
# 1. THE SIMULATOR ENGINE - UI & CONTRAST
# =========================================================
st.set_page_config(page_title="TRUCK LOAD ENGINE", layout="wide")

def apply_industrial_theme():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Rajdhani:wght@600&display=swap');

        /* Achtergrond */
        .stApp {
            background-color: #0f1216;
            color: #e2e8f0;
            font-family: 'JetBrains Mono', monospace;
        }

        /* SIDEBAR: Donker met fel contrast */
        section[data-testid="stSidebar"] {
            background-color: #05070a !important;
            border-right: 1px solid #1e293b;
        }
        
        /* Sidebar tekst: Fel Blauw/Cyaan voor leesbaarheid */
        section[data-testid="stSidebar"] .stMarkdown, 
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] span {
            color: #38bdf8 !important; 
            font-family: 'Rajdhani', sans-serif;
            font-size: 1rem !important;
        }

        /* Tab styling: Maak ze groot en opvallend */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: #0f1216;
        }

        .stTabs [data-baseweb="tab"] {
            height: 50px;
            background-color: #1e293b;
            border-radius: 5px 5px 0px 0px;
            color: #ffffff;
            padding: 10px 30px;
        }

        .stTabs [aria-selected="true"] {
            background-color: #38bdf8 !important;
            color: #000000 !important;
            font-weight: bold;
        }

        /* Container blokken */
        .input-block {
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid #334155;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        /* Knoppen */
        div.stButton > button {
            background: #38bdf8 !important;
            color: #0f1216 !important;
            border: none !important;
            font-weight: bold;
            text-transform: uppercase;
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

apply_industrial_theme()

# =========================================================
# 2. SESSION STATE (DATA OPSLAG)
# =========================================================
for key in ['master_data_df', 'boxes_df', 'pallets_df', 'trucks_df', 'results_df']:
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame()

# =========================================================
# 3. SIDEBAR CONTROLS
# =========================================================
with st.sidebar:
    st.markdown("### SYSTEM CONTROLS")
    st.divider()
    calc_mode = st.radio("OPTIMIZATION STRATEGY", ["Max Volume", "Max Weight", "Balanced"])
    st.divider()
    st.checkbox("Allow Stackable Items", value=True)
    st.checkbox("Group by Order ID", value=False)
    st.slider("Safety Margin (%)", 0, 10, 5)

# =========================================================
# 4. MAIN INTERFACE (TABS)
# =========================================================
st.title("TRUCK LOAD CALCULATOR")

tab_input, tab_output = st.tabs(["[ 01: MISSION DATA ]", "[ 02: CALCULATION RESULTS ]"])

# --- TAB 1: DATA INVOER ---
with tab_input:
    st.markdown("### DATA ACQUISITION")
    
    # Upload Rij
    with st.container():
        st.markdown("<div class='input-block'>", unsafe_allow_html=True)
        up_col, down_col = st.columns([2, 1])
        with up_col:
            st.file_uploader("IMPORT EXCEL MANIFEST", type=["xlsx"])
        with down_col:
            st.write("ACTIONS")
            st.button("CLEAR ALL DATA")
        st.markdown("</div>", unsafe_allow_html=True)

    # Tables Grid
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.write("ITEM MASTER DATA")
        st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", use_container_width=True, key="ed_m")
        
        st.write("PALLET CONFIGURATION")
        st.session_state.pallets_df = st.data_editor(st.session_state.pallets_df, num_rows="dynamic", use_container_width=True, key="ed_p")

    with col_r:
        st.write("BOX DIMENSIONS")
        st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", use_container_width=True, key="ed_b")
        
        st.write("TRUCK / CONTAINER FLEET")
        st.session_state.trucks_df = st.data_editor(st.session_state.trucks_df, num_rows="dynamic", use_container_width=True, key="ed_t")

    st.divider()
    if st.button("RUN CALCULATION ENGINE"):
        st.toast("Processing data...", icon="⏳")

# --- TAB 2: UITKOMSTEN ---
with tab_output:
    st.markdown("### ANALYTICS & LOADING PLAN")
    
    # HUD Stats
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TRUCKS NEEDED", "0")
    m2.metric("TOTAL LOADING METERS", "0.0m")
    m3.metric("UTILIZATION", "0%")
    m4.metric("TOTAL WEIGHT", "0 kg")

    st.markdown("<div class='input-block'>", unsafe_allow_html=True)
    st.write("LOADING SEQUENCE & INSTRUCTIONS")
    if st.session_state.results_df.empty:
        st.warning("NO RESULTS YET. RUN THE ENGINE ON THE DATA TAB.")
    else:
        st.dataframe(st.session_state.results_df, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.button("DOWNLOAD LOADING PLAN (PDF)")
