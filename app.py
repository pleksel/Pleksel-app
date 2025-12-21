import streamlit as st
import pandas as pd
import math, io, os
from fpdf import FPDF

# =========================================================
# 1. GEAVANCEERDE UI CONFIG & STYLING (THE GAME LOOK)
# =========================================================
st.set_page_config(page_title="PLEKSEL PRO", page_icon="🚀", layout="wide")

def local_css():
    st.markdown("""
    <style>
        /* Importeer een modern font */
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Inter:wght@300;400;600&display=swap');

        /* Algemene achtergrond met gradient */
        .stApp {
            background: radial-gradient(circle at top right, #1e293b, #0f172a);
            color: #f8fafc;
            font-family: 'Inter', sans-serif;
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: rgba(15, 23, 42, 0.8) !important;
            border-right: 1px solid #334155;
        }

        /* Glassmorphism containers (De "Game" look) */
        div[data-testid="stMetric"], .stContainer, .table-container {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 15px !important;
            padding: 20px !important;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 24px 0 rgba(0, 0, 0, 0.3);
        }

        /* Headers met neon gloed */
        h1, h2, h3 {
            font-family: 'Orbitron', sans-serif !important;
            color: #38bdf8 !important;
            text-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
            letter-spacing: 2px;
        }

        /* Knoppen die oplichten */
        div.stButton > button {
            background: linear-gradient(90deg, #0ea5e9 0%, #2563eb 100%);
            color: white !important;
            border: none !important;
            font-weight: bold !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s ease;
            height: 3em;
        }
        
        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 20px rgba(14, 165, 233, 0.6);
        }

        /* Tabel headers styling */
        .table-header {
            font-family: 'Orbitron', sans-serif;
            color: #94a3b8;
            font-size: 0.8rem;
            margin-bottom: 5px;
            text-transform: uppercase;
        }
        
        /* Progress bar neon */
        .stProgress > div > div > div > div {
            background-image: linear-gradient(to right, #38bdf8 , #818cf8);
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# =========================================================
# 2. DATA & LOGICA
# =========================================================
# (Dataframes blijven hetzelfde als in jouw origineel)
LANGS = {
    "NL": {
        "title": "PLEKSEL DASHBOARD", "nav_templates": "📁 CONFIGURATIE", 
        "nav_orders": "📑 ORDERS", "nav_calc": "🚛 SIMULATIE",
        "header_master": "📦 ARTIKELEN MASTER DATA", "header_boxes": "🎁 DOZEN TYPE",
        "header_pallets": "🟫 PALLET TYPE", "header_trucks": "🚛 VLOOT BEHEER"
    },
    "EN": { "title": "PLEKSEL COMMAND CENTER", "nav_templates": "📁 CONFIG", "nav_orders": "📑 ORDERS", "nav_calc": "🚛 SIMULATION", "header_master": "📦 MASTER DATA", "header_boxes": "🎁 BOX TYPES", "header_pallets": "🟫 PALLET TYPES", "header_trucks": "🚛 FLEET MGMT" }
}

st.sidebar.markdown("# 🕹️ CONTROL PANEL")
lang_choice = st.sidebar.selectbox("SYSTEM LANGUAGE", ["NL", "EN"])
T = LANGS[lang_choice]

# Init Session States (Zelfde als jouw code)
for key in ["master_data_df", "boxes_df", "pallets_df", "orders_df", "custom_trucks_df"]:
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame()

# =========================================================
# 3. UI SECTIES
# =========================================================
st.title(f"🚀 {T['title']}")

page = st.sidebar.radio("NAVIGATION", [T["nav_templates"], T["nav_orders"], T["nav_calc"]])

if page == T["nav_templates"]:
    # Bovenste rij met statistieken (Game-vibe)
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("GELADEN ITEMS", len(st.session_state.master_data_df))
    with m2: st.metric("ACTIEVE DOZEN", len(st.session_state.boxes_df))
    with m3: st.metric("VLOOT TYPE", len(st.session_state.custom_trucks_df))

    st.divider()

    # Hoofd Sectie: Master Data in een brede 'terminal'
    with st.container():
        st.markdown(f"<div class='table-header'>{T['header_master']}</div>", unsafe_allow_html=True)
        st.session_state.master_data_df = st.data_editor(
            st.session_state.master_data_df, 
            num_rows="dynamic", 
            use_container_width=True,
            key="master_editor"
        )

    st.write("") # Spacer

    # Grid voor Dozen en Pallets
    col_left, col_right = st.columns(2)
    with col_left:
        with st.container():
            st.markdown(f"<div class='table-header'>{T['header_boxes']}</div>", unsafe_allow_html=True)
            st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", use_container_width=True)

    with col_right:
        with st.container():
            st.markdown(f"<div class='table-header'>{T['header_pallets']}</div>", unsafe_allow_html=True)
            st.session_state.pallets_df = st.data_editor(st.session_state.pallets_df, num_rows="dynamic", use_container_width=True)

    # Truck sectie onderaan
    with st.container():
        st.markdown(f"<div class='table-header'>{T['header_trucks']}</div>", unsafe_allow_html=True)
        st.session_state.custom_trucks_df = st.data_editor(st.session_state.custom_trucks_df, num_rows="dynamic", use_container_width=True)

elif page == T["nav_calc"]:
    st.subheader("🛠️ SIMULATIE ENGINE")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        with st.container():
            st.markdown("**PARAMETERS**")
            st.toggle("AUTO-STACKING")
            st.toggle("MULTI-ORDER PACKING")
            st.slider("MAX BELASTING %", 0, 100, 95)
            if st.button("RUN ENGINE"):
                with st.spinner("Calculating optimal routes..."):
                    # Hier komt je logica
                    st.success("Calculated!")
    
    with c2:
        # Hier zou je een 3D viewer of grafiek kunnen zetten
        st.info("De visuele weergave van de vrachtwagen wordt hier geladen...")
        st.progress(75, text="Capaciteit bereikt")

# Footer
st.sidebar.divider()
st.sidebar.caption("PLEKSEL PRO v2.0 | Engine: ShaderPilot Style")
