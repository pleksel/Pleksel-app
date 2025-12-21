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

# 4. REKEN ENGINE (SIMULATIE)

# =========================================================

def calculate_metrics(pallets):

    total_w = sum(p['weight'] for p in pallets)

    total_v = sum((p['dim'][0]*p['dim'][1]*p['dim'][2])/1000000 for p in pallets)

    num_pal = len(pallets)

    # Bereken laadmeter op basis van unieke X-posities (max lengte van de trailer benutting)

    max_x = max([p['pos'][0] + p['dim'][0] for p in pallets]) if pallets else 0

    lm = round(max_x / 100, 2)

    trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0

    return total_w, round(total_v, 2), num_pal, trucks, lm



# =========================================================

# 5. UI TABS

# =========================================================

tab_data, tab_calc = st.tabs([L['data_tab'], L['calc_tab']])



with tab_data:

    st.markdown(f"<div class='table-header'>{L['master']}</div>", unsafe_allow_html=True)

    st.data_editor(pd.DataFrame(columns=["ItemNr", "L", "B", "H", "Kg", "Stapelbaar"]), num_rows="dynamic", use_container_width=True)

    

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(f"<div class='table-header'>{L['order']}</div>", unsafe_allow_html=True)

        st.data_editor(pd.DataFrame(columns=["OrderNr", "ItemNr", "Aantal"]), num_rows="dynamic", use_container_width=True)

    with col2:

        st.markdown(f"<div class='table-header'>{L['boxes']}</div>", unsafe_allow_html=True)

        st.data_editor(pd.DataFrame(columns=["Naam", "L", "B", "H", "LeegKg"]), num_rows="dynamic", use_container_width=True)



    st.markdown(f"<div class='table-header'>{L['pallets']}</div>", unsafe_allow_html=True)

    st.data_editor(pd.DataFrame(columns=["Naam", "L", "B", "EigenKg", "MaxH"]), num_rows="dynamic", use_container_width=True)

    

    st.markdown(f"<div class='table-header'>{L['truck']}</div>", unsafe_allow_html=True)

    st.data_editor(pd.DataFrame(columns=["Naam", "L", "B", "H", "MaxKg"]), num_rows="dynamic", use_container_width=True)



with tab_calc:

    # Mock data voor simulatie (X, Y, Z)

    # Let op: Y-as gaat tot 245cm voor 'naast elkaar' laden

    mock_pallets = [

        {'id': 'P1', 'weight': 400, 'dim': [120, 80, 110], 'pos': [0, 0, 0]},

        {'id': 'P2', 'weight': 400, 'dim': [120, 80, 110], 'pos': [0, 85, 0]},

        {'id': 'P3', 'weight': 400, 'dim': [120, 80, 110], 'pos': [0, 170, 0]},

        {'id': 'P4', 'weight': 200, 'dim': [120, 80, 100], 'pos': [0, 0, 115]}, # Gestapeld op P1

    ]

    

    tw, tv, tp, tt, tlm = calculate_metrics(mock_pallets)



    # Statistieken Dashboard boven de 3D beeld

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

    # Trailer Vloer (13.6m x 2.45m)

    fig.add_trace(go.Mesh3d(x=[0, 1360, 1360, 0, 0, 1360, 1360, 0], y=[0, 0, 245, 245, 0, 0, 245, 245], z=[0, 0, 0, 0, 1, 1, 1, 1], color='gray', opacity=0.4))

    

    for p in mock_pallets:

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
