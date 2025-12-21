import streamlit as st
import pandas as pd
import io, os

# =========================================================
# 1. THE GAME ENGINE UI (CONTRAST & SIMULATOR LOOK)
# =========================================================
st.set_page_config(page_title="TRUCK SIMULATOR PRO", page_icon="🚛", layout="wide")

def apply_simulator_theme():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');

        /* Dashboard Achtergrond */
        .stApp {
            background-color: #0a0e14;
            background-image: 
                linear-gradient(rgba(0, 255, 255, 0.05) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 255, 255, 0.05) 1px, transparent 1px);
            background-size: 30px 30px;
            color: #ffffff;
            font-family: 'Rajdhani', sans-serif;
        }

        /* Tekst beter zichtbaar maken */
        p, span, label, .stMarkdown {
            color: #ffffff !important;
            font-weight: 500;
            font-size: 1.1rem;
        }

        /* Glazen Containers met felle randen */
        div[data-testid="stMetric"], .stContainer, .stDataEditor {
            background: rgba(16, 22, 32, 0.9) !important;
            border: 2px solid #38bdf8 !important;
            border-radius: 10px !important;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.2);
        }

        /* Simulator Knoppen (Neon Oranje/Geel) */
        div.stButton > button {
            background: #f59e0b !important;
            color: #000000 !important;
            border: none !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            box-shadow: 0 0 10px #f59e0b;
        }

        /* Truck Icon Header */
        .truck-header {
            text-align: center;
            padding: 20px;
            background: linear-gradient(90deg, transparent, #38bdf8, transparent);
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

apply_simulator_theme()

# =========================================================
# 2. LOGICA & DATA INITIALISATIE
# =========================================================
if 'master_data_df' not in st.session_state:
    st.session_state.master_data_df = pd.DataFrame(columns=["ItemNr", "Lengte", "Breedte", "Hoogte", "Gewicht"])
if 'boxes_df' not in st.session_state:
    st.session_state.boxes_df = pd.DataFrame(columns=["Naam", "Lengte", "Breedte", "Hoogte"])
if 'pallets_df' not in st.session_state:
    st.session_state.pallets_df = pd.DataFrame(columns=["Type", "L", "B", "MaxH"])

# =========================================================
# 3. GAME INTERFACE (DE TRUCK)
# =========================================================

# Geen logo, maar een "game-achtige truck" visual
st.markdown("<div class='truck-header'><h1>🚛 TRUCK CALCULATION ENGINE v2.1</h1></div>", unsafe_allow_html=True)

# Sidebar voor instellingen
st.sidebar.header("🕹️ DASHBOARD CONTROLS")
mode = st.sidebar.selectbox("SELECT MODULE", ["DATA INPUT", "ORDER PLANNING", "FLEET MGMT"])

# =========================================================
# 4. FUNCTIES & SCHERMEN
# =========================================================

if mode == "DATA INPUT":
    st.subheader("📁 SYSTEM TEMPLATES & UPLOADS")
    
    col_up, col_down = st.columns(2)
    with col_up:
        # Hier is de upload functie terug
        uploaded_file = st.file_uploader("UPLOAD EXCEL MANIFEST", type=["xlsx"])
        if uploaded_file:
            st.success("MANIFEST GELADEN")
            # Logica voor verwerking zou hier komen
            
    with col_down:
        st.info("DOWNLOAD SYSTEEM TEMPLATE")
        st.button("GENERATE .XLSX TEMPLATE")

    st.divider()

    # De data editors (met beter zichtbare tekst)
    st.markdown("### 📦 ARTIKEL MASTER DATA")
    st.session_state.master_data_df = st.data_editor(
        st.session_state.master_data_df, 
        num_rows="dynamic", 
        use_container_width=True,
        key="editor_master"
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🎁 DOOS CONFIGURATIE")
        st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", use_container_width=True)
    with c2:
        st.markdown("### 🟫 PALLET TYPES")
        st.session_state.pallets_df = st.data_editor(st.session_state.pallets_df, num_rows="dynamic", use_container_width=True)

elif mode == "ORDER PLANNING":
    st.subheader("🚛 CARGO OPTIMIZATION")
    
    # Game-achtige HUD voor statistieken
    h1, h2, h3 = st.columns(3)
    h1.metric("AVAILABLE SPACE", "94%", delta="2.4m")
    h2.metric("TOTAL WEIGHT", "14.500 KG", delta="-500 KG")
    h3.metric("EFFICIENCY SCORE", "98/100")

    st.button("🚀 START BEREKENING (RUN SIMULATION)")
    
    # Placeholder voor de truck visualisatie
    st.image("https://img.icons8.com/clouds/500/semi-truck.png", width=300) # Een gestileerde truck icon
    st.write("Wacht op data invoer voor visualisatie...")

# Footer informatie
st.sidebar.markdown("---")
st.sidebar.markdown("**STATUS:** 🟢 SYSTEM ONLINE")
st.sidebar.markdown("**USER:** OPERATOR_01")
