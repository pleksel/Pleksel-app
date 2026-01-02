import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import io
import streamlit as st

# =========================================================
# 1. CONFIGURATIE & THEMA
# =========================================================
def setup_app():
    st.set_page_config(page_title="PLEKSEL TRAILER ENGINE", layout="wide")
    st.markdown("""
    <style>
        .stApp { background-color: #020408; color: #e2e8f0; }
        section[data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #38bdf8; }
        div.stButton > button { background-color: #38bdf8 !important; color: #000 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# 2. DATA INITIALISATIE (Session State)
# =========================================================
def init_data():
    if 'lang' not in st.session_state: st.session_state.lang = 'NL'
    
    # Maak lege dataframes als ze nog niet bestaan
    keys = {
        'df_items': ["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"],
        'df_boxes': ["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"],
        'df_pallets': ["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"],
        'df_orders': ["OrderNr", "ItemNr", "Aantal"]
    }
    for key, cols in keys.items():
        if key not in st.session_state:
            st.session_state[key] = pd.DataFrame(columns=cols)

# =========================================================
# 3. REKEN ENGINE
# =========================================================
def run_calculation():
    # Haal de geselecteerde orders op (of alles als er geen selectie is)
    orders = st.session_state.get("df_orders_calc", st.session_state.df_orders)
    items = st.session_state.df_items

    if orders.empty or items.empty:
        return 0, 0, 0, 0, 0, []

    # Combineer order data met item afmetingen
    df = pd.merge(orders, items, on="ItemNr", how="inner")
    
    units = []
    for _, row in df.iterrows():
        for i in range(int(row['Aantal'])):
            units.append({
                'id': f"{row['ItemNr']}_{i}",
                'dim': [float(row['L_cm']), float(row['B_cm']), float(row['H_cm'])],
                'weight': float(row['Kg'])
            })

    # Simpele vullogica (2D Grid)
    pos_units = []
    cur_x, cur_y, max_h_row, spacing = 0, 0, 0, 2
    max_w = st.session_state.get("trailer_width", 245)

    for u in units:
        l, b, h = u['dim']
        if cur_y + b > max_w:
            cur_x += max_h_row + spacing
            cur_y = 0
            max_h_row = 0
        
        pos_units.append({**u, "pos": (cur_x, cur_y), "pz": 0})
        cur_y += b + spacing
        max_h_row = max(max_h_row, l)

    # Statistieken
    total_w = sum(u['weight'] for u in units)
    lm = round((cur_x + max_h_row) / 100, 2)
    return total_w, len(units), lm, pos_units

# =========================================================
# 4. UI SECTIES (Functies voor overzicht)
# =========================================================

def render_sidebar():
    st.sidebar.title("Instellingen")
    st.session_state.lang = st.sidebar.selectbox("Taal", ["NL", "EN", "DE"])
    st.session_state.opt_orient = st.sidebar.toggle("Optimaliseer Oriëntatie", True)
    
    st.sidebar.divider()
    # Template download
    st.sidebar.subheader("Data Import/Export")
    # (Hier kun je de Excel download/upload code plaatsen zoals in de vorige versie)

def render_data_editor():
    """Tab 01: Data invoer"""
    t1, t2, t3, t4 = st.tabs(["Items", "Boxes", "Pallets", "Orders"])
    with t1:
        st.session_state.df_items = st.data_editor(st.session_state.df_items, num_rows="dynamic", key="edit_items")
    with t2:
        st.session_state.df_boxes = st.data_editor(st.session_state.df_boxes, num_rows="dynamic", key="edit_boxes")
    with t3:
        st.session_state.df_pallets = st.data_editor(st.session_state.df_pallets, num_rows="dynamic", key="edit_pallets")
    with t4:
        st.session_state.df_orders = st.data_editor(st.session_state.df_orders, num_rows="dynamic", key="edit_orders")

def render_planning_tab():
    """Tab 02: Planning & Visualisatie"""
    if st.session_state.df_orders.empty:
        st.warning("Voer eerst orders in bij Tab 01.")
        return

    # Berekening
    weight, count, lm, units = run_calculation()
    
    # Statistieken in kolommen
    c1, c2, c3 = st.columns(3)
    c1.metric("Gewicht", f"{weight} kg")
    c2.metric("Aantal Items", count)
    c3.metric("Laadmeters", f"{lm} m")

    # 3D Plotly visualisatie
    if units:
        fig = go.Figure()
        # Voeg hier de go.Mesh3d traces toe (zie vorige code)
        # ...
        st.plotly_chart(fig, use_container_width=True)

# =========================================================
# 5. HOOFD PROGRAMMA (Main Loop)
# =========================================================
def main():
    setup_app()
    init_data()
    render_sidebar()

    # De Tabs structuur (Hier zat je fout)
    tab_data, tab_calc = st.tabs(["01: DATA INVOER", "02: PLANNING"])

    with tab_data:
        render_data_editor()
        
        # Trailer instellingen onderaan de data tab
        st.divider()
        st.subheader("Trailer afmetingen")
        st.session_state.trailer_width = st.number_input("Breedte (cm)", value=245)
        st.session_state.trailer_length = st.number_input("Lengte (cm)", value=1360)

    with tab_calc:
        render_planning_tab()

if __name__ == "__main__":
    main()










