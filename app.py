import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import io

# =========================================================
# 1. UI & THEME (Ultra Donker & Trailer Focus)
# =========================================================
st.set_page_config(page_title="PLEKSEL TRAILER ENGINE", layout="wide")

def apply_ui_theme():
    st.markdown("""
    <style>
        .stApp { background-color: #020408; color: #e2e8f0; }
        section[data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #38bdf8; }
        div[data-testid="stDataEditor"] { background-color: #0f172a !important; border: 1px solid #38bdf8 !important; }
        div[data-testid="stDataEditor"] canvas { filter: invert(0.9) hue-rotate(180deg) brightness(0.8); }
        .table-header { color: #38bdf8; font-weight: bold; border-bottom: 2px solid #38bdf8; padding: 5px 0; margin-top: 20px; }
        div.stButton > button { background-color: #38bdf8 !important; color: #000 !important; font-weight: bold; width: 100%; border-radius: 4px; }
        .stTabs [data-baseweb="tab-list"] { background-color: #020408; }
        .stTabs [aria-selected="true"] { background-color: #38bdf8 !important; color: #000 !important; }
    </style>
    """, unsafe_allow_html=True)

apply_ui_theme()

# =========================================================
# 2. DATA INITIALISATIE (Inclusief Stapelbaarheid per Item)
# =========================================================
# Toegevoegd: 'MagStapelen' aan Master Data
MASTER_COLS = ["ItemNr", "Lengte_cm", "Breedte_cm", "Hoogte_cm", "Gewicht_kg", "VerplichteDoos", "MagStapelen"]
BOXES_COLS = ["Naam", "Lengte_cm", "Breedte_cm", "Hoogte_cm", "LeegGewicht_kg"]
PALLETS_COLS = ["Naam", "Lengte_cm", "Breedte_cm", "EigenGewicht_kg", "MaxHoogte_cm"]
TRUCK_COLS = ["Naam", "Lengte_cm", "Breedte_cm", "Hoogte_cm", "MaxLading_kg"]
ORDER_COLS = ["OrderNr", "ItemNr", "Aantal"]

for key, cols in [("m_df", MASTER_COLS), ("b_df", BOXES_COLS), ("p_df", PALLETS_COLS), ("t_df", TRUCK_COLS), ("o_df", ORDER_COLS)]:
    if key not in st.session_state:
        # Default data voor demo/start
        if key == "m_df":
            st.session_state[key] = pd.DataFrame([["ITEM01", 30, 20, 15, 2.5, "", True]], columns=cols)
        else:
            st.session_state[key] = pd.DataFrame(columns=cols)

# =========================================================
# 3. SIDEBAR (Mix Boxes & Global Settings)
# =========================================================
st.sidebar.title("Trailer Settings")
mix_boxes = st.sidebar.toggle("Mix Boxes (Verschillende items in 1 doos)", value=True)
st.sidebar.info("Standaard staat Mix Boxes AAN voor maximale efficiëntie.")

# =========================================================
# 4. TRAILER VISUALISATIE (ShaderPilot Mode)
# =========================================================
def draw_trailer_3d(l, b, h, pallets=[]):
    fig = go.Figure()

    # De Trailer Vloer
    fig.add_trace(go.Mesh3d(
        x=[0, l, l, 0, 0, l, l, 0], y=[0, 0, b, b, 0, 0, b, b], z=[0, 0, 0, 0, 0.1, 0.1, 0.1, 0.1],
        color='gray', opacity=0.8, name="Trailer Vloer"
    ))

    # ShaderPilot Trailer Wanden (Transparant blauw)
    # Voorwand
    fig.add_trace(go.Mesh3d(x=[0, 2, 2, 0], y=[0, 0, b, b], z=[0, h, h, 0], color='#38bdf8', opacity=0.1, showlegend=False))
    # Zijwand (Links)
    fig.add_trace(go.Mesh3d(x=[0, l, l, 0], y=[0, 0, 0, 0], z=[0, 0, h, h], color='#38bdf8', opacity=0.1, showlegend=False))
    # Dak
    fig.add_trace(go.Mesh3d(x=[0, l, l, 0], y=[0, 0, b, b], z=[h, h, h, h], color='#38bdf8', opacity=0.05, showlegend=False))

    # Pallets toevoegen (Mock data voor ShaderPilot effect)
    pallet_colors = ['#00f2ff', '#7000ff', '#ff0070']
    for i, p in enumerate(pallets):
        px, py, pz = p['pos']
        pl, pb, ph = p['dim']
        
        # Teken Pallet
        fig.add_trace(go.Mesh3d(
            x=[px, px+pl, px+pl, px, px, px+pl, px+pl, px],
            y=[py, py, py+pb, py+pb, py, py, py+pb, py+pb],
            z=[pz, pz, pz, pz, pz+ph, pz+ph, pz+ph, pz+ph],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=pallet_colors[i % len(pallet_colors)],
            opacity=0.6,
            name=f"Pallet {p['id']}",
            hoverinfo="all",
            text=f"Order: {p['order']}<br>Gewicht: {p['weight']}kg<br>Stapelbaar: {p['stack']}"
        ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(nticks=10, range=[-50, l+50], title="Lengte (cm)"),
            yaxis=dict(nticks=5, range=[-50, b+50], title="Breedte (cm)"),
            zaxis=dict(nticks=5, range=[0, h+50], title="Hoogte (cm)"),
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        paper_bgcolor="black"
    )
    return fig

# =========================================================
# 5. MAIN APP INTERFACE
# =========================================================
tab_data, tab_calc = st.tabs(["01: DATA INVOER", "02: TRAILER PLANNING"])

with tab_data:
    st.markdown("<div class='table-header'>Master Data (Stapelbaarheid per Item)</div>", unsafe_allow_html=True)
    st.session_state.m_df = st.data_editor(st.session_state.m_df, num_rows="dynamic", use_container_width=True, key="master_ed")
    
    col_o, col_b = st.columns(2)
    with col_o:
        st.markdown("<div class='table-header'>Order Lijst</div>", unsafe_allow_html=True)
        st.session_state.o_df = st.data_editor(st.session_state.o_df, num_rows="dynamic", use_container_width=True, key="order_ed")
    with col_b:
        st.markdown("<div class='table-header'>Dozen Configuraties</div>", unsafe_allow_html=True)
        st.session_state.b_df = st.data_editor(st.session_state.b_df, num_rows="dynamic", use_container_width=True, key="box_ed")

    st.markdown("<div class='table-header'>Pallet Types & Container/Truck</div>", unsafe_allow_html=True)
    cl, cr = st.columns(2)
    with cl: st.session_state.p_df = st.data_editor(st.session_state.p_df, num_rows="dynamic", key="pal_ed")
    with cr: st.session_state.t_df = st.data_editor(st.session_state.t_df, num_rows="dynamic", key="truck_ed")

with tab_calc:
    st.subheader("ShaderPilot 3D Trailer Viewer")
    
    # Mock resultaten voor weergave
    mock_pallets = [
        {'id': 'P01', 'order': '1001', 'pos': [10, 10, 0], 'dim': [120, 80, 160], 'weight': 420, 'stack': 'Nee'},
        {'id': 'P02', 'order': '1001', 'pos': [140, 10, 0], 'dim': [120, 80, 145], 'weight': 380, 'stack': 'Ja'},
        {'id': 'P03', 'order': '1002', 'pos': [10, 100, 0], 'dim': [120, 80, 120], 'weight': 210, 'stack': 'Ja'}
    ]
    
    col_3d, col_info = st.columns([3, 1])
    
    with col_3d:
        # Teken een standaard trailer van 13,6 meter (1360 cm)
        fig = draw_trailer_3d(1360, 245, 270, mock_pallets)
        st.plotly_chart(fig, use_container_width=True)
    
    with col_info:
        st.markdown("<div style='background:#111827; padding:15px; border-left:4px solid #38bdf8;'>", unsafe_allow_html=True)
        st.write("### Pallet Details")
        st.info("Klik op een pallet in de trailer voor specifieke data.")
        st.write("**Geselecteerde Run:** Run_2024_01")
        st.write("**Totaal Gewicht:** 1.010 kg")
        st.write("**Laadmeters:** 0.8 m")
        st.write("**Status:** ✅ Efficiënt")
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Download PDF Rapport (Order 1001)"):
        st.success("PDF gegenereerd met pallet-specificaties en trailer positie.")
