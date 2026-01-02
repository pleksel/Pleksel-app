import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import io
import streamlit as st

# =========================================================
# 1. UI & THEME
# =========================================================
st.set_page_config(page_title="PLEKSEL TRAILER ENGINE", layout="wide")

def apply_ui_theme():
    st.markdown("""
    <style>
        .stApp { background-color: #020408; color: #e2e8f0; }
        section[data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #38bdf8; }
        .table-header { color: #38bdf8; font-weight: bold; border-bottom: 2px solid #38bdf8; padding: 5px 0; margin-top: 20px; margin-bottom: 10px; }
        div.stButton > button { background-color: #38bdf8 !important; color: #000 !important; font-weight: bold; border-radius: 4px; }
        .metric-card { background: #111827; border: 1px solid #38bdf8; padding: 15px; border-radius: 8px; text-align: center; }
        .metric-val { color: #38bdf8; font-size: 24px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

apply_ui_theme()

# =========================================================
# 2. INITIALISATIE
# =========================================================
if 'lang' not in st.session_state: st.session_state.lang = 'NL'
if 'df_items' not in st.session_state: st.session_state.df_items = pd.DataFrame(columns=["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"])
if 'df_boxes' not in st.session_state: st.session_state.df_boxes = pd.DataFrame(columns=["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"])
if 'df_pallets' not in st.session_state: st.session_state.df_pallets = pd.DataFrame(columns=["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"])
if 'df_orders' not in st.session_state: st.session_state.df_orders = pd.DataFrame(columns=["OrderNr", "ItemNr", "Aantal"])

# Default trailer waarden
if 'trailer_length' not in st.session_state: st.session_state.trailer_length = 1360
if 'trailer_width' not in st.session_state: st.session_state.trailer_width = 245
if 'trailer_height' not in st.session_state: st.session_state.trailer_height = 270

T = {
    'NL': {
        'settings': "Trailer Instellingen", 'mix': "Mix Boxes", 'stack': "Pallets Stapelen", 
        'orient': "Lang/Breed laden", 'data_tab': "01: DATA INVOER", 'calc_tab': "02: PLANNING",
        'item_data': "Item Data", 'box_data': "Box Data", 'pallet_data': "Pallet Data",
        'order_data': "Order Data", 'truck': "Truck/Container", 'download': "Download Template", 
        'upload': "Upload Template", 'stats_weight': "Totaal Gewicht", 'stats_vol': "Totaal Volume", 
        'stats_pal': "Aantal Pallets", 'stats_trucks': "Aantal Trucks", 'stats_lm': "Laadmeters"
    }
}
L = T.get(st.session_state.lang, T['NL'])

# =========================================================
# 3. SIDEBAR
# =========================================================
st.sidebar.title(L['settings'])
st.session_state.lang = st.sidebar.selectbox("Taal", ["NL", "EN", "DE"], index=0)

calc_mode = st.sidebar.select_slider(
    "Berekeningsmethode",
    options=["Automatisch (Volume)", "Handmatig (Volle units)"],
    value="Handmatig (Volle units)"
)

mix_boxes = st.sidebar.toggle(L['mix'], value=False)
opt_stack = st.sidebar.toggle(L['stack'], value=True)
opt_orient = st.sidebar.toggle(L['orient'], value=True)

# =========================================================
# 4. REKEN ENGINE
# =========================================================
def calculate_metrics():
    orders = st.session_state.df_orders
    items = st.session_state.df_items

    if orders.empty or items.empty:
        return 0, 0, 0, 0, 0, []

    df = pd.merge(orders.astype(str), items.astype(str), on="ItemNr", how="inner")
    
    units_to_load = []
    for _, row in df.iterrows():
        for i in range(int(float(row['Aantal']))):
            units_to_load.append({
                'id': f"{row['ItemNr']}_{i}",
                'dim': [float(row['L_cm']), float(row['B_cm']), float(row['H_cm'])],
                'weight': float(row['Kg']),
                'stackable': str(row.get('Stapelbaar', 'Ja')).lower() in ['ja', '1', 'yes', 'true']
            })

    positioned_units = []
    curr_x, curr_y, row_depth = 0, 0, 0
    MAX_WIDTH = st.session_state.trailer_width
    SPACING = 2

    for u in units_to_load:
        l, b, h = u['dim']
        if opt_orient and l > b: l, b = b, l

        if curr_y + b > MAX_WIDTH:
            curr_x += row_depth + SPACING
            curr_y = 0
            row_depth = 0

        u['pos'] = [curr_x, curr_y]
        u['pz'] = 0  # Simpele 2D grondvlak plaatsing voor nu
        positioned_units.append(u)
        
        curr_y += b + SPACING
        row_depth = max(row_depth, l)

    total_w = sum(p['weight'] for p in positioned_units)
    total_v = sum((p['dim'][0] * p['dim'][1] * p['dim'][2]) / 1_000_000 for p in positioned_units)
    used_length = curr_x + row_depth
    lm = round(used_length / 100, 2)
    trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0

    return round(total_w, 1), round(total_v, 2), len(units_to_load), trucks, lm, positioned_units

# =========================================================
# 5. UI TABS
# =========================================================
tab_data, tab_calc = st.tabs([L['data_tab'], L['calc_tab']])

with tab_data:
    t1, t2, t3, t4, t5 = st.tabs(["Items", "Boxes", "Pallets", "Orders", "Trailers"])
    with t1: st.session_state.df_items = st.data_editor(st.session_state.df_items, use_container_width=True, num_rows="dynamic")
    with t4: st.session_state.df_orders = st.data_editor(st.session_state.df_orders, use_container_width=True, num_rows="dynamic")
    with t5:
        trailer_type = st.selectbox("Kies trailer", ["Standaard trailer (13.6m)", "40ft container", "Custom"])
        if trailer_type == "Standaard trailer (13.6m)":
            st.session_state.trailer_length, st.session_state.trailer_width, st.session_state.trailer_height = 1360, 245, 270
        elif trailer_type == "40ft container":
            st.session_state.trailer_length, st.session_state.trailer_width, st.session_state.trailer_height = 1203, 235, 239

with tab_calc:
    res_w, res_v, res_p, res_t, res_lm, active_units = calculate_metrics()

    cols = st.columns(5)
    metrics = [(L['stats_weight'], f"{res_w} kg"), (L['stats_vol'], f"{res_v} m³"), (L['stats_pal'], res_p), (L['stats_trucks'], res_t), (L['stats_lm'], f"{res_lm} m")]
    for i, (label, val) in enumerate(metrics):
        cols[i].markdown(f"<div class='metric-card'><small>{label}</small><br><span class='metric-val'>{val}</span></div>", unsafe_allow_html=True)

    if active_units:
        fig = go.Figure()
        colors = ['#0ea5e9', '#f59e0b', '#ef4444', '#10b981']
        
        for p in active_units:
            l, b, h = p['dim']
            x, y, z = p['pos'][0], p['pos'][1], p['pz']
            item_type = str(p['id']).split('_')[0]
            
            fig.add_trace(go.Mesh3d(
                x=[x, x, x+l, x+l, x, x, x+l, x+l],
                y=[y, y+b, y+b, y, y, y+b, y+b, y],
                z=[z, z, z, z, z+h, z+h, z+h, z+h],
                i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
                j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
                k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
                color=colors[0], opacity=0.8, flatshading=True, name=item_type
            ))

        fig.update_layout(scene=dict(
            xaxis=dict(range=[0, st.session_state.trailer_length]),
            yaxis=dict(range=[0, st.session_state.trailer_width]),
            zaxis=dict(range=[0, st.session_state.trailer_height]),
            aspectmode='data'
        ), margin=dict(l=0, r=0, b=0, t=0))
        st.plotly_chart(fig, use_container_width=True)
        
        if st.button("Genereer PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, "LAADPLAN", ln=True, align='C')
            pdf.set_font("Arial", '', 10)
            for p in active_units:
                pdf.cell(190, 7, f"Item {p['id']}: Pos {p['pos']}", ln=True)
            st.download_button("Download PDF", pdf.output(dest='S'), "plan.pdf", "application/pdf")
    else:
        st.info("Voer eerst data in bij Tab 01.")
