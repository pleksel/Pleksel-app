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

# 2. TAAL & INITIALISATIE

# =========================================================

if 'lang' not in st.session_state: st.session_state.lang = 'NL'



T = {

    'NL': {

        'settings': "Trailer Instellingen", 'mix': "Mix Boxes", 'stack': "Pallets Stapelen", 

        'orient': "Lang/Breed laden", 'data_tab': "01: DATA INVOER", 'calc_tab': "02: PLANNING",

        'master': "Master Data", 'order': "Order Lijst", 'boxes': "Dozen", 'pallets': "Pallet Types", 

        'truck': "Truck/Container", 'download': "Download Template", 'upload': "Upload Template",

        'stats_weight': "Totaal Gewicht", 'stats_vol': "Totaal Volume", 'stats_pal': "Aantal Pallets",

        'stats_trucks': "Aantal Trucks", 'stats_lm': "Laadmeters"

    },

    'EN': {

        'settings': "Trailer Settings", 'mix': "Mix Boxes", 'stack': "Stack Pallets", 

        'orient': "Long/Wide Loading", 'data_tab': "01: DATA ENTRY", 'calc_tab': "02: PLANNING",

        'master': "Master Data", 'order': "Order List", 'boxes': "Boxes", 'pallets': "Pallet Types", 

        'truck': "Truck/Container", 'download': "Download Template", 'upload': "Upload Template",

        'stats_weight': "Total Weight", 'stats_vol': "Total Volume", 'stats_pal': "Pallet Count",

        'stats_trucks': "Truck Count", 'stats_lm': "Loading Meters"

    },

    'DE': {

        'settings': "Trailer-Einstellungen", 'mix': "Mix-Boxen", 'stack': "Paletten stapeln", 

        'orient': "Längs-/Querladen", 'data_tab': "01: DATENEINGABE", 'calc_tab': "02: PLANUNG",

        'master': "Stammdaten", 'order': "Bestellliste", 'boxes': "Boxen", 'pallets': "Palettentypen", 

        'truck': "LKW/Container", 'download': "Vorlage laden", 'upload': "Vorlage hochladen",

        'stats_weight': "Gesamtgewicht", 'stats_vol': "Gesamtvolumen", 'stats_pal': "Anzahl Paletten",

        'stats_trucks': "Anzahl LKWs", 'stats_lm': "Lademeter"

    }

}

L = T[st.session_state.lang]



# =========================================================
# 3. SIDEBAR (Template met Item, Box, Pallet en Order Data)
# =========================================================
st.sidebar.title(L['settings'])
st.session_state.lang = st.sidebar.selectbox("Language / Sprache / Taal", ["NL", "EN", "DE"])

mix_boxes = st.sidebar.toggle(L['mix'], value=False)
opt_stack = st.sidebar.toggle(L['stack'], value=True)
opt_orient = st.sidebar.toggle(L['orient'], value=True)

st.sidebar.divider()

# Template genereren met 4 tabbladen
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    # Tab 1: De artikelen (Master Data)
    pd.DataFrame(columns=["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar_JaNee"]).to_excel(writer, sheet_name='Item Data', index=False)
    
    # Tab 2: De dozen (Master Data)
    pd.DataFrame(columns=["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"]).to_excel(writer, sheet_name='Box Data', index=False)
    
    # Tab 3: De pallets (Master Data)
    pd.DataFrame(columns=["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"]).to_excel(writer, sheet_name='Pallet Data', index=False)
    
    # Tab 4: De feitelijke bestelling (Order Data)
    pd.DataFrame(columns=["OrderNr", "ItemNr", "Aantal"]).to_excel(writer, sheet_name='Order Data', index=False)

# Download knop
st.sidebar.download_button(
    label=L['download'],
    data=buffer.getvalue(),
    file_name="pleksel_full_template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Template Upload
uploaded_file = st.sidebar.file_uploader(L['upload'], type=['xlsx', 'csv'])
if uploaded_file:
    st.sidebar.success("Bestand succesvol geladen!")

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
