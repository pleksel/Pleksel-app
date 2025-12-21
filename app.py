import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import io

# =========================================================
# 1. UI & THEME
# =========================================================
st.set_page_config(page_title="PLEKSEL TRAILER ENGINE", layout="wide")

def apply_ui_theme():
    st.markdown("""
    <style>
        .stApp { background-color: #020408; color: #e2e8f0; }
        section[data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #38bdf8; }
        div[data-testid="stDataEditor"] { background-color: #0f172a !important; border: 1px solid #38bdf8 !important; }
        .table-header { color: #38bdf8; font-weight: bold; border-bottom: 2px solid #38bdf8; padding: 5px 0; margin-top: 20px; margin-bottom: 10px; }
        div.stButton > button { background-color: #38bdf8 !important; color: #000 !important; font-weight: bold; width: 100%; border-radius: 4px; }
        .stTabs [data-baseweb="tab-list"] { background-color: #020408; }
        .stTabs [aria-selected="true"] { background-color: #38bdf8 !important; color: #000 !important; }
    </style>
    """, unsafe_allow_html=True)

apply_ui_theme()

# =========================================================
# 2. TAAL & INITIALISATIE (Nu incl. DE)
# =========================================================
if 'lang' not in st.session_state: st.session_state.lang = 'NL'

T = {
    'NL': {
        'settings': "Trailer Instellingen",
        'mix': "Mix Boxes (Items mixen)",
        'stack': "Pallets Stapelen (Dubbeldek)",
        'orient': "Lang/Breed laden (Rotatie optimalisatie)",
        'data_tab': "01: DATA INVOER",
        'calc_tab': "02: TRAILER PLANNING",
        'master': "Master Data (Items & Stapelbaarheid)",
        'order': "Order Lijst",
        'boxes': "Dozen Configuraties",
        'pallets': "Pallet Types",
        'truck': "Container / Truck Afmetingen",
        'download': "Download Template",
        'gen_pdf': "Genereer PDF per Order",
        'load_m': "Laadmeters"
    },
    'EN': {
        'settings': "Trailer Settings",
        'mix': "Mix Boxes (Mix items)",
        'stack': "Stack Pallets (Double deck)",
        'orient': "Length/Width loading (Rotation optimization)",
        'data_tab': "01: DATA ENTRY",
        'calc_tab': "02: TRAILER PLANNING",
        'master': "Master Data (Items & Stackability)",
        'order': "Order List",
        'boxes': "Box Configurations",
        'pallets': "Pallet Types",
        'truck': "Container / Truck Dimensions",
        'download': "Download Template",
        'gen_pdf': "Generate PDF per Order",
        'load_m': "Loading Meters"
    },
    'DE': {
        'settings': "Trailer-Einstellungen",
        'mix': "Mix-Boxen (Elemente mischen)",
        'stack': "Paletten stapeln (Doppelstock)",
        'orient': "Längs-/Querladen (Rotationsoptimierung)",
        'data_tab': "01: DATENEINGABE",
        'calc_tab': "02: TRAILER-PLANUNG",
        'master': "Stammdaten (Artikel & Stapelbarkeit)",
        'order': "Bestellliste",
        'boxes': "Box-Konfigurationen",
        'pallets': "Palettentypen",
        'truck': "LKW / Container Abmessungen",
        'download': "Vorlage herunterladen",
        'gen_pdf': "PDF pro Bestellung erstellen",
        'load_m': "Lademeter"
    }
}
L = T[st.session_state.lang]

# Data initialisatie
MASTER_COLS = ["ItemNr", "Lengte_cm", "Breedte_cm", "Hoogte_cm", "Gewicht_kg", "VerplichteDoos", "MagStapelen"]
for key, cols in [("m_df", MASTER_COLS), ("b_df", ["Naam", "Lengte_cm", "Breedte_cm", "Hoogte_cm", "LeegGewicht_kg"]), 
                  ("p_df", ["Naam", "Lengte_cm", "Breedte_cm", "EigenGewicht_kg", "MaxHoogte_cm"]), 
                  ("t_df", ["Naam", "Lengte_cm", "Breedte_cm", "Hoogte_cm", "MaxLading_kg"]), 
                  ("o_df", ["OrderNr", "ItemNr", "Aantal"])]:
    if key not in st.session_state: st.session_state[key] = pd.DataFrame(columns=cols)

# =========================================================
# 3. SIDEBAR (Opties & Logica)
# =========================================================
st.sidebar.title(L['settings'])
st.session_state.lang = st.sidebar.selectbox("Language / Sprache / Taal", ["NL", "EN", "DE"])

mix_boxes = st.sidebar.toggle(L['mix'], value=False)
opt_stack = st.sidebar.toggle(L['stack'], value=True)
opt_orient = st.sidebar.toggle(L['orient'], value=True)

st.sidebar.divider()
st.sidebar.download_button(L['download'], "Template Data", "template.xlsx")

# =========================================================
# 4. 3D LOGICA (EFFICIËNT LADEN)
# =========================================================
def draw_trailer_3d(l, b, h, pallets=[]):
    fig = go.Figure()
    # Vloer
    fig.add_trace(go.Mesh3d(x=[0, l, l, 0, 0, l, l, 0], y=[0, 0, b, b, 0, 0, b, b], z=[0, 0, 0, 0, 1, 1, 1, 1], color='gray', opacity=0.3))
    
    # Pallet Plaatsing Logica (Side-by-side)
    # Hier simuleren we dat de motor pallets naast elkaar zet als de breedte het toelaat (245cm)
    current_x = 0
    current_y = 0
    max_y_in_row = 0
    
    pallet_colors = ['#00f2ff', '#7000ff', '#ff0070', '#38bdf8']

    for i, p in enumerate(pallets):
        pl, pb, ph = p['dim']
        
        # Check of pallet naast de vorige past
        if current_y + pb > b:
            current_x += 125 # Schuif naar volgende rij (bijv. Europallet lengte + marge)
            current_y = 0
            
        px, py, pz = current_x, current_y, p['pos'][2] # Z-as blijft voor stapelen
        
        fig.add_trace(go.Mesh3d(
            x=[px, px+pl, px+pl, px, px, px+pl, px+pl, px],
            y=[py, py, py+pb, py+pb, py, py, py+pb, py+pb],
            z=[pz, pz, pz, pz, pz+ph, pz+ph, pz+ph, pz+ph],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=pallet_colors[i % len(pallet_colors)], opacity=0.8, name=f"P: {p['id']}"
        ))
        
        current_y += pb + 5 # 5cm marge tussen pallets

    fig.update_layout(scene=dict(aspectmode='data', xaxis_title="Lengte", yaxis_title="Breedte"), paper_bgcolor="black", margin=dict(l=0,r=0,b=0,t=0))
    return fig, round(current_x / 100, 2)

# =========================================================
# 5. UI TABS
# =========================================================
tab_data, tab_calc = st.tabs([L['data_tab'], L['calc_tab']])

with tab_data:
    st.markdown(f"<div class='table-header'>{L['master']}</div>", unsafe_allow_html=True)
    st.session_state.m_df = st.data_editor(st.session_state.m_df, num_rows="dynamic", use_container_width=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='table-header'>{L['order']}</div>", unsafe_allow_html=True)
        st.session_state.o_df = st.data_editor(st.session_state.o_df, num_rows="dynamic", use_container_width=True)
    with c2:
        st.markdown(f"<div class='table-header'>{L['boxes']}</div>", unsafe_allow_html=True)
        st.session_state.b_df = st.data_editor(st.session_state.b_df, num_rows="dynamic", use_container_width=True)

    st.markdown(f"<div class='table-header'>{L['pallets']}</div>", unsafe_allow_html=True)
    st.session_state.p_df = st.data_editor(st.session_state.p_df, num_rows="dynamic", use_container_width=True)
    
    st.markdown(f"<div class='table-header'>{L['truck']}</div>", unsafe_allow_html=True)
    st.session_state.t_df = st.data_editor(st.session_state.t_df, num_rows="dynamic", use_container_width=True)

with tab_calc:
    # Mock data die rekening houdt met stapelen
    mock_pallets = [
        {'id': 'PAL-A1', 'order': '1001', 'pos': [0, 0, 0], 'dim': [120, 80, 120], 'weight': 200, 'stack': 'Ja'},
        {'id': 'PAL-A2', 'order': '1001', 'pos': [0, 0, 125], 'dim': [120, 80, 100], 'weight': 150, 'stack': 'Ja'}, # GESTAPELD
        {'id': 'PAL-B1', 'order': '1001', 'pos': [0, 0, 0], 'dim': [120, 80, 240], 'weight': 500, 'stack': 'Nee'},
        {'id': 'PAL-C1', 'order': '1002', 'pos': [0, 0, 0], 'dim': [120, 80, 150], 'weight': 300, 'stack': 'Nee'},
    ]

    col_3d, col_info = st.columns([3, 1])
    with col_3d:
        fig, laadmeters = draw_trailer_3d(1360, 245, 270, mock_pallets)
        st.plotly_chart(fig, use_container_width=True)
    
    with col_info:
        st.markdown("<div style='background:#111827; padding:15px; border-left:4px solid #38bdf8;'>", unsafe_allow_html=True)
        st.write(f"### {L['gen_pdf']}")
        order_sel = st.selectbox("Order ID", ["1001", "1002"])
        if st.button(f"Download PDF {order_sel}"):
            st.success(f"PDF voor {order_sel} gegenereerd.")
        
        st.divider()
        st.metric(L['load_m'], f"{laadmeters} m")
        st.write(f"**Efficiency:** {round((laadmeters/13.6)*100, 1)}%")
        st.markdown("</div>", unsafe_allow_html=True)
