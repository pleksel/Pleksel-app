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
# 4. REKEN ENGINE (GEFIKSTE KOLOMNAMEN)
# =========================================================
def calculate_metrics():
    orders = st.session_state.get('df_orders', pd.DataFrame())
    items = st.session_state.get('df_items', pd.DataFrame())
    
    if orders.empty or items.empty:
        return 0, 0, 0, 0, 0, []
    
    items = items.rename(columns={'L': 'L_cm', 'B': 'B_cm', 'H': 'H_cm'})
    orders_cp = orders.copy()
    items_cp = items.copy()
    orders_cp['ItemNr'] = orders_cp['ItemNr'].astype(str)
    items_cp['ItemNr'] = items_cp['ItemNr'].astype(str)
    
    df = pd.merge(orders_cp, items_cp, on="ItemNr", how="inner").fillna(0)
    if df.empty: return 0, 0, 0, 0, 0, []

    units_to_load = []
    for _, row in df.iterrows():
        qty = int(row['Aantal'])
        for i in range(qty):
            units_to_load.append({
                'id': f"{row['ItemNr']}_{i}",
                'dim': [float(row['L_cm']), float(row['B_cm']), float(row['H_cm'])],
                'weight': float(row['Kg']),
                'stackable': str(row.get('Stapelbaar', 'Ja')).lower() in ['ja', '1', 'yes', 'true']
            })

    positioned_units = []
    curr_x = 0
    i = 0
    trailer_width = 245
    max_h = 250 # Standaard trailer hoogte

    while i < len(units_to_load):
        u = units_to_load[i]
        l, b, h = u['dim']
        
        # Orientatie logica (Lang/Breed)
        if opt_orient and l > b and (curr_x + b <= 1360):
            l, b = b, l # Draai pallet
        
        # Stapel logica (alleen als opt_stack aan staat en item stapelbaar is)
        pz = 0
        target_idx = -1
        if opt_stack and u['stackable']:
            for idx, prev in enumerate(positioned_units):
                # Check of er iets onder kan (eenvoudige overlap check)
                if prev['pos'][0] == curr_x and prev['pos'][1] == 0: # Vereenvoudigd voor NL/EN logic
                    if prev['pz'] == 0 and (prev['dim'][2] + h) <= max_h:
                        pz = prev['dim'][2]
                        target_idx = idx
                        break

        # Breedte laden (Optie B uit origineel)
        if opt_orient and b <= 121 and (i + 1) < len(units_to_load):
            # Plaats 2 naast elkaar
            for j in range(2):
                if i < len(units_to_load):
                    positioned_units.append({
                        'id': units_to_load[i]['id'],
                        'dim': [80, 120, units_to_load[i]['dim'][2]],
                        'pos': [curr_x, j * 122, 0],
                        'pz': 0,
                        'weight': units_to_load[i]['weight']
                    })
                    i += 1
            curr_x += 81
        else:
            # Enkel laden
            positioned_units.append({
                'id': u['id'], 'dim': [l, b, h], 'pos': [curr_x, 0, 0], 
                'pz': pz, 'weight': u['weight']
            })
            if pz == 0: curr_x += l + 2
            i += 1

    total_w = sum(p['weight'] for p in positioned_units)
    total_v = sum((p['dim'][0]*p['dim'][1]*p['dim'][2])/1000000 for p in positioned_units)
    lm = round(curr_x / 100, 2)
    trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0
    
    return round(total_w, 1), round(total_v, 2), len(units_to_load), trucks, lm, positioned_units

# =========================================================
# 5. UI TABS
# =========================================================
with tab_calc:
    res_w, res_v, res_p, res_t, res_lm, active_units = calculate_metrics()

    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [(L['stats_weight'], f"{res_w} kg"), (L['stats_vol'], f"{res_v} m³"), (L['stats_pal'], res_p), (L['stats_trucks'], res_t), (L['stats_lm'], f"{res_lm} m")]
    for i, (label, val) in enumerate(metrics):
        with [c1, c2, c3, c4, c5][i]:
            st.markdown(f"<div class='metric-card'><small>{label}</small><br><span class='metric-val'>{val}</span></div>", unsafe_allow_html=True)

    st.divider()

    fig = go.Figure()
    # Trailer vloer
    fig.add_trace(go.Mesh3d(x=[0, 1360, 1360, 0, 0, 1360, 1360, 0], y=[0, 0, 245, 245, 0, 0, 245, 245], z=[0, 0, 0, 0, 1, 1, 1, 1], color='gray', opacity=0.2))
    
    for p in active_units:
        px, py, pz_base = p['pos'][0], p['pos'][1], p['pz']
        pl, pb, ph = p['dim']
        
        # Teken de box met z-offset (pz_base)
        fig.add_trace(go.Mesh3d(
            x=[px, px+pl, px+pl, px, px, px+pl, px+pl, px],
            y=[py, py, py+pb, py+pb, py, py, py+pb, py+pb],
            z=[pz_base, pz_base, pz_base, pz_base, pz_base+ph, pz_base+ph, pz_base+ph, pz_base+ph],
            i=[7,0,0,0,4,4,6,6,4,0,3,2], j=[3,4,1,2,5,6,5,2,0,1,6,3], k=[0,7,2,3,6,7,1,1,5,5,7,6],
            color='#38bdf8' if pz_base == 0 else '#fbbf24', # Geel voor gestapelde items
            opacity=0.9, name=p['id']
        ))

    fig.update_layout(
        scene=dict(
            aspectmode='data',
            xaxis=dict(title='Lengte (cm)', range=[0, 1360]),
            yaxis=dict(title='Breedte (cm)', range=[0, 245]),
            zaxis=dict(title='Hoogte (cm)', range=[0, 270])
        ),
        paper_bgcolor="black", 
        margin=dict(l=0,r=0,b=0,t=0)
    )
    st.plotly_chart(fig, use_container_width=True)
