import streamlit as st
import pandas as pd
import io

# =========================================================
# 1. THE SIMULATOR ENGINE - UI & CONTRAST FIX
# =========================================================
st.set_page_config(page_title="TRUCK SIMULATOR PRO", page_icon="🚛", layout="wide")

def apply_pro_simulator_theme():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;600&display=swap');

        /* Achtergrond van de hele app */
        .stApp {
            background-color: #05070a;
            color: #ffffff;
            font-family: 'Rajdhani', sans-serif;
        }

        /* SIDEBAR FIX: Donkere achtergrond met Neon Groene tekst */
        section[data-testid="stSidebar"] {
            background-color: #0c1117 !important;
            border-right: 2px solid #00ff41;
        }
        
        section[data-testid="stSidebar"] .stMarkdown, 
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] span {
            color: #00ff41 !important; /* Klassieke Terminal Groen */
            font-family: 'Orbitron', sans-serif;
            font-size: 0.9rem;
            font-weight: bold;
        }

        /* Tekst in het middenvlak (beter zichtbaar) */
        h1, h2, h3 {
            font-family: 'Orbitron', sans-serif !important;
            color: #38bdf8 !important;
            text-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
        }

        /* Doorbreken van de Excel-look: Kaarten in plaats van alleen rijen */
        .data-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid #38bdf8;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: inset 0 0 15px rgba(56, 189, 248, 0.1);
        }

        /* Knoppen: "Industrial" look */
        div.stButton > button {
            background: #ffaa00 !important;
            color: #000000 !important;
            border: 2px solid #cc8800 !important;
            font-family: 'Orbitron', sans-serif;
            font-weight: bold;
            letter-spacing: 2px;
            width: 100%;
        }

        /* Styling voor de tabellen om ze minder 'Excel' te maken */
        .stDataEditor {
            background-color: #0c1117 !important;
            border: 1px solid #334155 !important;
        }
    </style>
    """, unsafe_allow_html=True)

apply_pro_simulator_theme()

# =========================================================
# 2. DATA INITIALISATIE
# =========================================================
for key in ['master_data_df', 'boxes_df', 'pallets_df', 'trucks_df']:
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame()

# =========================================================
# 3. ZIJBALK (CONTROL PANEL) - NU GOED LEESBAAR
# =========================================================
with st.sidebar:
    st.markdown("## 📟 COMMAND CENTER")
    st.divider()
    menu = st.radio("SELECT MISSION", ["🚀 CARGO DASHBOARD", "📁 DATABASE", "🚛 FLEET MGMT"])
    
    st.divider()
    st.markdown("### 🛠️ ENGINE SETTINGS")
    st.toggle("Stapelbaar", value=True)
    st.toggle("Gezamenlijke Orders", value=False)
    st.slider("Max Load %", 0, 100, 95)
    
    st.sidebar.markdown("---")
    st.sidebar.caption("SYSTEM STATUS: ONLINE")

# =========================================================
# 4. HOOFDSCHERMEN
# =========================================================

if menu == "🚀 CARGO DASHBOARD":
    st.title("🚛 TRUCK SIMULATOR ENGINE")
    
    # HUD Display (Snel overzicht)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("AVAILABLE PAYLOAD", "24,000 kg", "Ready")
    with col2:
        st.metric("CARGO VOLUME", "86 m³", "Optimaal")
    with col3:
        st.metric("TRUCK EFFICIENCY", "92%", "High")

    st.markdown("---")

    # Actie sectie
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("<div class='data-card'><h3>📦 ACTIVE CARGO LIST</h3>", unsafe_allow_html=True)
        # Upload functie prominent aanwezig
        up = st.file_uploader("Sleep Excel manifest hierheen", type=["xlsx"])
        st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", use_container_width=True, key="main_ed")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='data-card'><h3>🎮 ACTIONS</h3>", unsafe_allow_html=True)
        if st.button("RUN SIMULATION"):
            st.balloons()
        st.button("EXPORT LOADING PLAN (PDF)")
        st.button("GENERATE EMPTY TEMPLATE")
        st.markdown("</div>", unsafe_allow_html=True)

elif menu == "📁 DATABASE":
    st.title("🗄️ MASTER DATA STORAGE")
    
    tab1, tab2 = st.tabs(["🎁 BOX TYPES", "🟫 PALLET SPECS"])
    with tab1:
        st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", use_container_width=True)
    with tab2:
        st.session_state.pallets_df = st.data_editor(st.session_state.pallets_df, num_rows="dynamic", use_container_width=True)

elif menu == "🚛 FLEET MGMT":
    st.title("🚛 VLOOT CONFIGURATIE")
    st.info("Beheer hier de afmetingen van je vrachtwagens en containers.")
    st.session_state.trucks_df = st.data_editor(st.session_state.trucks_df, num_rows="dynamic", use_container_width=True)
