import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import io
import streamlit as st

# =========================================================
# 1. UI CONFIGURATIE & THEMA
# =========================================================
def apply_custom_ui():
    st.set_page_config(page_title="PLEKSEL TRAILER ENGINE", layout="wide")
    st.markdown("""
    <style>
        .stApp { background-color: #020408; color: #e2e8f0; }
        section[data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #38bdf8; }
        div.stButton > button { background-color: #38bdf8 !important; color: #000 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# 2. SESSION STATE (DATA OPSLAG)
# =========================================================
def initialize_state():
    if 'lang' not in st.session_state: st.session_state.lang = 'NL'
    
    # Maak lege dataframes aan als ze niet bestaan
    default_dfs = {
        'df_items': ["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"],
        'df_boxes': ["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"],
        'df_pallets': ["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"],
        'df_orders': ["OrderNr", "ItemNr", "Aantal"]
    }
    for key, cols in default_dfs.items():
        if key not in st.session_state:
            st.session_state[key] = pd.DataFrame(columns=cols)
    
    # Trailer default maten
    if 'trailer_length' not in st.session_state: st.session_state.trailer_length = 1360
    if 'trailer_width' not in st.session_state: st.session_state.trailer_width = 245
    if 'trailer_height' not in st.session_state: st.session_state.trailer_height = 270

# =========================================================
# 3. REKEN ENGINE (LOGICA)
# =========================================================
def run_packing_calculation():
    orders = st.session_state.get("df_orders_calc", st.session_state.df_orders)
    items = st.session_state.df_items
    
    if orders.empty or items.empty:
        return None

    # Merge data
    df = pd.merge(orders, items, on="ItemNr", how="inner")
    
    units = []
    for _, row in df.iterrows():
        for i in range(int(row['Aantal'])):
            units.append({
                'id': str(row['ItemNr']),
                'dim': [float(row['L_cm']), float(row['B_cm']), float(row['H_cm'])],
                'weight': float(row['Kg'])
            })

    # Simpel Grid Algoritme
    pos_units = []
    cur_x, cur_y, row_l, spacing = 0, 0, 0, 2
    max_w = st.session_state.trailer_width

    for u in units:
        l, b, h = u['dim']
        if cur_y + b > max_w:
            cur_x += row_l + spacing
            cur_y = 0
            row_l = 0
        
        pos_units.append({**u, "pos": (cur_x, cur_y), "pz": 0})
        cur_y += b + spacing
        row_l = max(row_l, l)

    # Output statistieken
    stats = {
        'weight': sum(u['weight'] for u in units),
        'count': len(units),
        'lm': round((cur_x + row_l) / 100, 2),
        'units': pos_units
    }
    return stats

# =========================================================
# 4. UI COMPONENTEN (KLEINE SECTIES)
# =========================================================

def draw_3d_trailer(units):
    """Genereert de 3D visualisatie"""
    fig = go.Figure()
    colors = ['#38bdf8', '#fbbf24', '#f87171', '#34d399', '#a78bfa']
    
    for i, p in enumerate(units):
        l, b, h = p['dim']
        x, y, z = p['pos'][0], p['pos'][1], p['pz']
        color = colors[i % len(colors)]
        
        fig.add_trace(go.Mesh3d(
            x=[x, x, x+l, x+l, x, x, x+l, x+l],
            y=[y, y+b, y+b, y, y, y+b, y+b, y],
            z=[z, z, z, z, z+h, z+h, z+h, z+h],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], 
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], 
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=color, opacity=0.9, flatshading=True
        ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[0, st.session_state.trailer_length]),
            yaxis=dict(range=[0, st.session_state.trailer_width]),
            zaxis=dict(range=[0, st.session_state.trailer_height]),
            aspectmode="manual",
            aspectratio=dict(x=st.session_state.trailer_length/100, y=st.session_state.trailer_width/100, z=st.session_state.trailer_height/100)
        ),
        margin=dict(l=0, r=0, b=0, t=0)
    )
    st.plotly_chart(fig, use_container_width=True)

def render_data_editors():
    """Toont de tabellen voor invoer"""
    t1, t2, t3, t4 = st.tabs(["Items", "Boxes", "Pallets", "Orders"])
    with t1: st.session_state.df_items = st.data_editor(st.session_state.df_items, num_rows="dynamic", key="ed_items")
    with t2: st.session_state.df_boxes = st.data_editor(st.session_state.df_boxes, num_rows="dynamic", key="ed_boxes")
    with t3: st.session_state.df_pallets = st.data_editor(st.session_state.df_pallets, num_rows="dynamic", key="ed_pallets")
    with t4: st.session_state.df_orders = st.data_editor(st.session_state.df_orders, num_rows="dynamic", key="ed_orders")

# =========================================================
# 5. MAIN APP STRUCTUUR
# =========================================================
def main():
    apply_custom_ui()
    initialize_state()

    # --- SIDEBAR ---
    st.sidebar.title("Instellingen")
    st.session_state.lang = st.sidebar.selectbox("Taal", ["NL", "EN", "DE"])
    st.session_state.mix_boxes = st.sidebar.toggle("Mix Boxes", False)
    
    # --- TABS ---
    tab_data, tab_calc = st.tabs(["01: DATA INVOER", "02: PLANNING"])

    with tab_data:
        render_data_editors()
        st.divider()
        st.subheader("Trailer / Container Type")
        col1, col2, col3 = st.columns(3)
        st.session_state.trailer_length = col1.number_input("Lengte (cm)", value=st.session_state.trailer_length)
        st.session_state.trailer_width = col2.number_input("Breedte (cm)", value=st.session_state.trailer_width)
        st.session_state.trailer_height = col3.number_input("Hoogte (cm)", value=st.session_state.trailer_height)

    with tab_calc:
        results = run_packing_calculation()
        if results:
            c1, c2, c3 = st.columns(3)
            c1.metric("Totaal Gewicht", f"{results['weight']} kg")
            c2.metric("Items", results['count'])
            c3.metric("Laadmeters", f"{results['lm']} m")
            
            draw_3d_trailer(results['units'])
        else:
            st.info("Voer orders en items in bij de eerste tab.")

if __name__ == "__main__":
    main()









