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
# 3. SIDEBAR & UPLOAD LOGICA (VERBETERD)
# =========================================================
st.sidebar.title(L['settings'])
st.session_state.lang = st.sidebar.selectbox("Language", ["NL"])

st.sidebar.divider()

# Template genereren
buffer_dl = io.BytesIO()
with pd.ExcelWriter(buffer_dl, engine='xlsxwriter') as writer:
    pd.DataFrame(columns=["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"]).to_excel(writer, sheet_name='Item Data', index=False)
    pd.DataFrame(columns=["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"]).to_excel(writer, sheet_name='Box Data', index=False)
    pd.DataFrame(columns=["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"]).to_excel(writer, sheet_name='Pallet Data', index=False)
    pd.DataFrame(columns=["OrderNr", "ItemNr", "Aantal"]).to_excel(writer, sheet_name='Order Data', index=False)

st.sidebar.download_button(L['download'], buffer_dl.getvalue(), "template.xlsx")

# Upload en Verwerk
uploaded_file = st.sidebar.file_uploader(L['upload'], type=['xlsx'])
if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        # We overschrijven de session_state direct
        st.session_state.df_items = pd.read_excel(xls, 'Item Data').fillna(0)
        st.session_state.df_boxes = pd.read_excel(xls, 'Box Data').fillna(0)
        st.session_state.df_pallets = pd.read_excel(xls, 'Pallet Data').fillna(0)
        st.session_state.df_orders = pd.read_excel(xls, 'Order Data').fillna(0)
        st.sidebar.success("Data geladen! Ga naar PLANNING.")
    except Exception as e:
        st.sidebar.error(f"Check tabblad namen: {e}")
# =========================================================
# 4. REKEN ENGINE (GEKOPPELD AAN DATA & VIEWER)
# =========================================================
def calculate_real_metrics():
    # Controleer of er data is, anders return leegte
    if st.session_state.df_orders.empty or st.session_state.df_items.empty:
        return 0, 0, 0, 0, 0, []
    
    # Koppel Order aan Item Data op basis van ItemNr
    merged = pd.merge(st.session_state.df_orders, st.session_state.df_items, on="ItemNr", how="left")
    
    pallets_to_draw = []
    current_x = 0
    
    # Maak voor elk item in de order een 3D-blokje aan
    for idx, row in merged.iterrows():
        # Controleer of de benodigde kolommen bestaan
        try:
            aantal = int(row['Aantal'])
            l = float(row['L_cm'])
            b = float(row['B_cm'])
            h = float(row['H_cm'])
            kg = float(row['Kg'])
        except:
            continue

        for i in range(aantal):
            pallets_to_draw.append({
                'id': f"{row['ItemNr']}_{idx}_{i}",
                'dim': [l, b, h],
                'pos': [current_x, 0, 0], # Simpele plaatsing achter elkaar
                'weight': kg
            })
            current_x += l + 2  # 2cm tussenruimte
    
    total_w = sum(p['weight'] for p in pallets_to_draw)
    total_v = sum((p['dim'][0]*p['dim'][1]*p['dim'][2])/1000000 for p in pallets_to_draw)
    num_pal = len(pallets_to_draw)
    lm = round(current_x / 100, 2)
    trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0
    
    return total_w, round(total_v, 2), num_pal, trucks, lm, pallets_to_draw


# =========================================================
# 5. UI TABS
# =========================================================
tab_data, tab_calc = st.tabs([L['data_tab'], L['calc_tab']])

with tab_data:
    t1, t2, t3, t4 = st.tabs(["Items", "Boxes", "Pallets", "Orders"])
    with t1: st.session_state.df_items = st.data_editor(st.session_state.df_items, use_container_width=True, num_rows="dynamic", key="ed_items")
    with t2: st.session_state.df_boxes = st.data_editor(st.session_state.df_boxes, use_container_width=True, num_rows="dynamic", key="ed_boxes")
    with t3: st.session_state.df_pallets = st.data_editor(st.session_state.df_pallets, use_container_width=True, num_rows="dynamic", key="ed_pallets")
    with t4: st.session_state.df_orders = st.data_editor(st.session_state.df_orders, use_container_width=True, num_rows="dynamic", key="ed_orders")

with tab_calc:
    # Haal de data op uit de reken engine
    tw, tv, tp, tt, tlm, active_pallets = calculate_real_metrics()

    # Statistieken Dashboard
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (L['stats_weight'], f"{tw} kg"),
        (L['stats_vol'], f"{tv} m³"),
        (L['stats_pal'], tp),
        (L['stats_trucks'], tt),
        (L['stats_lm'], f"{tlm} m")
    ]
    for i, (label, val) in enumerate(metrics):
        with [c1, c2, c3, c4, c5][i]:
            st.markdown(f"<div class='metric-card'><small>{label}</small><br><span class='metric-val'>{val}</span></div>", unsafe_allow_html=True)

    st.divider()

    # 3D Viewer
    fig = go.Figure()
    
    # Teken Trailer Vloer (Grijs vlak)
    fig.add_trace(go.Mesh3d(x=[0, 1360, 1360, 0, 0, 1360, 1360, 0], y=[0, 0, 245, 245, 0, 0, 245, 245], z=[0, 0, 0, 0, 1, 1, 1, 1], color='gray', opacity=0.4))
    
    # Teken elk item uit de Excel-order
    for p in active_pallets:
        px, py, pz = p['pos']
        pl, pb, ph = p['dim']
        fig.add_trace(go.Mesh3d(
            x=[px, px+pl, px+pl, px, px, px+pl, px+pl, px],
            y=[py, py, py+pb, py+pb, py, py, py+pb, py+pb],
            z=[pz, pz, pz, pz, pz+ph, pz+ph, pz+ph, pz+ph],
            # Mesh indices voor een dichte box
            i=[7,0,0,0,4,4,6,6,4,0,3,2], j=[3,4,1,2,5,6,5,2,0,1,6,3], k=[0,7,2,3,6,7,1,1,5,5,7,6],
            color='#38bdf8', opacity=0.7, name=p['id']
        ))

    fig.update_layout(
        scene=dict(aspectmode='data', xaxis_title='Lengte (cm)', yaxis_title='Breedte (cm)', zaxis_title='Hoogte (cm)'),
        paper_bgcolor="black", 
        margin=dict(l=0,r=0,b=0,t=0)
    )
    st.plotly_chart(fig, use_container_width=True)


