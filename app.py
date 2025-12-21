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

        .table-header { color: #38bdf8; font-weight: bold; border-bottom: 2px solid #38bdf8; padding: 5px 0; margin-top: 20px; margin-bottom: 10px; }

        div.stButton > button { background-color: #38bdf8 !important; color: #000 !important; font-weight: bold; border-radius: 4px; }

        .metric-card { background: #111827; border: 1px solid #38bdf8; padding: 15px; border-radius: 8px; text-align: center; }

        .metric-val { color: #38bdf8; font-size: 24px; font-weight: bold; }

    </style>

    """, unsafe_allow_html=True)



apply_ui_theme()



# =========================================================
# 2. TAAL & INITIALISATIE (FIX VOOR ATTRIBUTE ERROR)
# =========================================================
if 'lang' not in st.session_state: 
    st.session_state.lang = 'NL'

# Zorg dat de dataframes altijd bestaan voordat de rest van de app start
if 'df_items' not in st.session_state:
    st.session_state.df_items = pd.DataFrame(columns=["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"])

if 'df_boxes' not in st.session_state:
    st.session_state.df_boxes = pd.DataFrame(columns=["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"])

if 'df_pallets' not in st.session_state:
    st.session_state.df_pallets = pd.DataFrame(columns=["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"])

if 'df_orders' not in st.session_state:
    st.session_state.df_orders = pd.DataFrame(columns=["OrderNr", "ItemNr", "Aantal"])

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
L = T[st.session_state.lang]



# =========================================================
# 3. SIDEBAR (Instellingen & Template Upload)
# =========================================================
st.sidebar.title(L['settings'])
st.session_state.lang = st.sidebar.selectbox("Language / Sprache / Taal", ["NL", "EN", "DE"])

# Nieuwe Slider voor berekeningsmethode
calc_mode = st.sidebar.select_slider(
    "Berekeningsmethode",
    options=["Automatisch (Volume)", "Handmatig (Volle units)"],
    value="Handmatig (Volle units)",
    help="Automatisch berekent hoeveel er op een pallet past. Handmatig ziet elke order-regel als een aparte unit."
)

mix_boxes = st.sidebar.toggle(L['mix'], value=False)
opt_stack = st.sidebar.toggle(L['stack'], value=True)
opt_orient = st.sidebar.toggle(L['orient'], value=True)

st.sidebar.divider()

# Template Download (4 tabbladen)
buffer_dl = io.BytesIO()
with pd.ExcelWriter(buffer_dl, engine='xlsxwriter') as writer:
    pd.DataFrame(columns=["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"]).to_excel(writer, sheet_name='Item Data', index=False)
    pd.DataFrame(columns=["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"]).to_excel(writer, sheet_name='Box Data', index=False)
    pd.DataFrame(columns=["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"]).to_excel(writer, sheet_name='Pallet Data', index=False)
    pd.DataFrame(columns=["OrderNr", "ItemNr", "Aantal"]).to_excel(writer, sheet_name='Order Data', index=False)

st.sidebar.download_button(L['download'], buffer_dl.getvalue(), "pleksel_template.xlsx")

uploaded_file = st.sidebar.file_uploader(L['upload'], type=['xlsx'])
if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        st.session_state.df_items = pd.read_excel(xls, 'Item Data').fillna(0)
        st.session_state.df_boxes = pd.read_excel(xls, 'Box Data').fillna(0)
        st.session_state.df_pallets = pd.read_excel(xls, 'Pallet Data').fillna(0)
        st.session_state.df_orders = pd.read_excel(xls, 'Order Data').fillna(0)
        st.sidebar.success("Geladen!")
    except:
        st.sidebar.error("Fout in bestand.")
# =========================================================
# 4. REKEN ENGINE (DYNAMISCHE LOGICA)
# =========================================================
def calculate_metrics():
    # Veiligheidscheck voor data in session_state
    orders = st.session_state.get('df_orders', pd.DataFrame())
    items = st.session_state.get('df_items', pd.DataFrame())
    pallets_cfg = st.session_state.get('df_pallets', pd.DataFrame())

    if orders.empty or items.empty:
        return 0, 0, 0, 0, 0, []

    # Merge data en forceer types voor betrouwbare match
    orders_cp = orders.copy()
    items_cp = items.copy()
    orders_cp['ItemNr'] = orders_cp['ItemNr'].astype(str)
    items_cp['ItemNr'] = items_cp['ItemNr'].astype(str)
    
    df = pd.merge(orders_cp, items_cp, on="ItemNr", how="left").fillna(0)
    
    total_w = 0
    total_v = 0
    units_to_load = []
    
    # Haal pallet data op (indien aanwezig)
    p_l = float(pallets_cfg.iloc[0]['L_cm']) if not pallets_cfg.empty else 120.0
    p_b = float(pallets_cfg.iloc[0]['B_cm']) if not pallets_cfg.empty else 80.0
    p_h_max = float(pallets_cfg.iloc[0]['MaxH_cm']) if not pallets_cfg.empty else 200.0

    if "Handmatig" in calc_mode:
        # LOGICA: Elke order-regel * aantal is een losse unit
        for _, row in df.iterrows():
            qty = int(row['Aantal'])
            for i in range(qty):
                units_to_load.append({
                    'id': f"{row['ItemNr']}_{i}",
                    'dim': [float(row['L_cm']), float(row['B_cm']), float(row['H_cm'])],
                    'weight': float(row['Kg'])
                })
            total_w += qty * float(row['Kg'])
            total_v += (qty * (float(row['L_cm']) * float(row['B_cm']) * float(row['H_cm']))) / 1000000
    else:
        # LOGICA: Automatisch verpakken op basis van volume
        total_item_vol = 0
        for _, row in df.iterrows():
            qty = int(row['Aantal'])
            total_item_vol += qty * (float(row['L_cm']) * float(row['B_cm']) * float(row['H_cm']))
            total_w += qty * float(row['Kg'])
        
        total_v = total_item_vol / 1000000
        cap_per_pallet = (p_l * p_b * p_h_max) * 0.85
        num_p = int(np.ceil(total_item_vol / cap_per_pallet)) if total_item_vol > 0 else 0
        
        for i in range(num_p):
            units_to_load.append({
                'id': f"Pallet_{i}",
                'dim': [p_l, p_b, p_h_max * 0.8],
                'weight': total_w / num_p if num_p > 0 else 0
            })

    # Positioneren voor 3D Viewer (2-dik laden op Y-as)
    positioned_units = []
    curr_x = 0
    for idx, unit in enumerate(units_to_load):
        y_pos = 0 if idx % 2 == 0 else 85
        positioned_units.append({
            'id': unit['id'],
            'dim': unit['dim'],
            'pos': [curr_x, y_pos, 0],
            'weight': unit['weight']
        })
        if idx % 2 != 0: 
            curr_x += unit['dim'][0] + 5

    num_units = len(units_to_load)
    lm = round((curr_x + (p_l if num_units > 0 else 0)) / 100, 2)
    trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0
    
    return round(total_w, 1), round(total_v, 2), num_units, trucks, lm, positioned_units

# =========================================================
# 5. UI TABS
# =========================================================
tab_data, tab_calc = st.tabs([L['data_tab'], L['calc_tab']])

with tab_data:
    t1, t2, t3, t4 = st.tabs(["Items", "Boxes", "Pallets", "Orders"])
    with t1:
        st.session_state.df_items = st.data_editor(st.session_state.df_items, use_container_width=True, num_rows="dynamic", key="ed_items")
    with t2:
        st.session_state.df_boxes = st.data_editor(st.session_state.df_boxes, use_container_width=True, num_rows="dynamic", key="ed_boxes")
    with t3:
        st.session_state.df_pallets = st.data_editor(st.session_state.df_pallets, use_container_width=True, num_rows="dynamic", key="ed_pallets")
    with t4:
        st.session_state.df_orders = st.data_editor(st.session_state.df_orders, use_container_width=True, num_rows="dynamic", key="ed_orders")

with tab_calc:
    # Belangrijk: haal alle 6 de variabelen op
    tw, tv, tp, tt, tlm, active_units = calculate_metrics()

    # Statistieken
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [(L['stats_weight'], f"{tw} kg"), (L['stats_vol'], f"{tv} m³"), (L['stats_pal'], tp), (L['stats_trucks'], tt), (L['stats_lm'], f"{tlm} m")]
    for i, (label, val) in enumerate(metrics):
        with [c1, c2, c3, c4, c5][i]:
            st.markdown(f"<div class='metric-card'><small>{label}</small><br><span class='metric-val'>{val}</span></div>", unsafe_allow_html=True)

    st.divider()

    # 3D Viewer
    fig = go.Figure()
    # Trailer Vloer
    fig.add_trace(go.Mesh3d(x=[0, 1360, 1360, 0, 0, 1360, 1360, 0], y=[0, 0, 245, 245, 0, 0, 245, 245], z=[0, 0, 0, 0, 1, 1, 1, 1], color='gray', opacity=0.4))
    
    for p in active_units:
        px, py, pz = p['pos']
        pl, pb, ph = p['dim']
        fig.add_trace(go.Mesh3d(
            x=[px, px+pl, px+pl, px, px, px+pl, px+pl, px],
            y=[py, py, py+pb, py+pb, py, py, py+pb, py+pb],
            z=[pz, pz, pz, pz, pz+ph, pz+ph, pz+ph, pz+ph],
            i=[7,0,0,0,4,4,6,6,4,0,3,2], j=[3,4,1,2,5,6,5,2,0,1,6,3], k=[0,7,2,3,6,7,1,1,5,5,7,6],
            color='#38bdf8', opacity=0.7, name=p['id']
        ))

    fig.update_layout(scene=dict(aspectmode='data'), paper_bgcolor="black", margin=dict(l=0,r=0,b=0,t=0))
    st.plotly_chart(fig, use_container_width=True)


