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
# 3. SIDEBAR (Instellingen & Uitgebreide Template Upload)
# =========================================================
st.sidebar.title(L['settings'])
st.session_state.lang = st.sidebar.selectbox("Language / Sprache / Taal", ["NL", "EN", "DE"])

# De oude vertrouwde toggles
mix_boxes = st.sidebar.toggle(L['mix'], value=False)
opt_stack = st.sidebar.toggle(L['stack'], value=True)
opt_orient = st.sidebar.toggle(L['orient'], value=True)

st.sidebar.divider()

# Verbeterde Template Download (met de 4 benodigde tabbladen)
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    pd.DataFrame(columns=["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"]).to_excel(writer, sheet_name='Item Data', index=False)
    pd.DataFrame(columns=["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"]).to_excel(writer, sheet_name='Box Data', index=False)
    pd.DataFrame(columns=["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"]).to_excel(writer, sheet_name='Pallet Data', index=False)
    pd.DataFrame(columns=["OrderNr", "ItemNr", "Aantal"]).to_excel(writer, sheet_name='Order Data', index=False)

st.sidebar.download_button(
    label=L['download'],
    data=buffer.getvalue(),
    file_name="pleksel_template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Uitgebreide Template Upload
uploaded_file = st.sidebar.file_uploader(L['upload'], type=['xlsx'])

if uploaded_file:
    try:
        # Open het Excel bestand
        xls = pd.ExcelFile(uploaded_file)
        
        # Lees de specifieke tabbladen in en zet ze in de session_state
        # .fillna(0) zorgt dat lege cellen geen errors veroorzaken
        st.session_state.df_items = pd.read_excel(xls, 'Item Data').fillna(0)
        st.session_state.df_boxes = pd.read_excel(xls, 'Box Data').fillna(0)
        st.session_state.df_pallets = pd.read_excel(xls, 'Pallet Data').fillna(0)
        st.session_state.df_orders = pd.read_excel(xls, 'Order Data').fillna(0)
        
        st.sidebar.success("Bestand succesvol geladen! Data is verdeeld over de tabs.")
    except Exception as e:
        st.sidebar.error(f"Fout bij laden. Controleer of alle tabbladen (Item Data, Box Data, etc.) bestaan.")
# =========================================================
# 4. REKEN ENGINE (VERPAKKINGS-HIERARCHIE)
# =========================================================
def calculate_metrics():
    # 1. Haal data op uit de editor/state
    # We proberen de data uit de session_state te halen als die er is, anders uit de editor keys
    items = st.session_state.get('item_editor', pd.DataFrame())
    orders = st.session_state.get('order_editor', pd.DataFrame())
    boxes = st.session_state.get('box_editor', pd.DataFrame())
    pallets_cfg = st.session_state.get('pallet_editor', pd.DataFrame())

    if orders.empty or items.empty:
        return 0, 0, 0, 0, 0, []

    # 2. Merge Order met Item data
    # Zorg dat we kolommen hebben: ItemNr, L, B, H, Kg, Aantal
    df = pd.merge(orders, items, on="ItemNr", how="left").fillna(0)
    
    total_weight = 0
    total_volume = 0
    calculated_pallets = []
    
    # Simpele aanname voor berekening (Box-fit & Pallet-fit)
    # In een echte scenario zou je hier een Bin Packing algoritme gebruiken.
    # Hier berekenen we het op basis van volume-capaciteit.
    
    for _, row in df.iterrows():
        qty = int(row['Aantal'])
        item_vol = row['L'] * row['B'] * row['H']
        total_weight += qty * row['Kg']
        total_volume += (qty * item_vol) / 1000000

    # 3. Bereken aantal pallets (Voorbeeld-logica: 1.5m3 per pallet of max hoogte)
    # We gebruiken de eerste pallet uit de lijst als standaard
    if not pallets_cfg.empty:
        p_l = pallets_cfg.iloc[0]['L']
        p_b = pallets_cfg.iloc[0]['B']
        p_max_h = pallets_cfg.iloc[0]['MaxH']
        p_vol_cap = (p_l * p_b * p_max_h) * 0.85 # 85% efficiëntie
    else:
        p_l, p_b, p_max_h, p_vol_cap = 120, 80, 200, 1800000
    
    # Bereken benodigde pallets op basis van totaal volume vs pallet capaciteit
    total_item_vol_cm3 = total_volume * 1000000
    num_pallets = int(np.ceil(total_item_vol_cm3 / p_vol_cap)) if total_item_vol_cm3 > 0 else 0
    
    # 4. Genereer pallet posities voor 3D viewer
    current_x = 0
    for i in range(num_pallets):
        # We plaatsen pallets 2-dik (naast elkaar op de Y-as)
        y_pos = 0 if i % 2 == 0 else 85
        if i > 0 and i % 2 == 0:
            current_x += p_l + 5
            
        calculated_pallets.append({
            'id': f'Pallet_{i+1}',
            'weight': total_weight / num_pallets if num_pallets > 0 else 0,
            'dim': [p_l, p_b, p_max_h * 0.7], # We vullen ze voor 70% voor het zicht
            'pos': [current_x, y_pos, 0]
        })

    # 5. Finale statistieken
    lm = round((current_x + p_l) / 100, 2) if num_pallets > 0 else 0
    trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0
    
    return round(total_weight, 1), round(total_volume, 2), num_pallets, trucks, lm, calculated_pallets

# =========================================================
# 5. UI TABS (DAARNÁ AANROEPEN)
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
    # NU is de functie bekend en kan deze aangeroepen worden
    tw, tv, tp, tt, tlm, active_pallets = calculate_real_metrics()

    # Dashboard
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [(L['stats_weight'], f"{tw} kg"), (L['stats_vol'], f"{tv} m³"), (L['stats_pal'], tp), (L['stats_trucks'], tt), (L['stats_lm'], f"{tlm} m")]
    for i, (label, val) in enumerate(metrics):
        with [c1, c2, c3, c4, c5][i]:
            st.markdown(f"<div class='metric-card'><small>{label}</small><br><span class='metric-val'>{val}</span></div>", unsafe_allow_html=True)

    # 3D Viewer
    fig = go.Figure()
    fig.add_trace(go.Mesh3d(x=[0, 1360, 1360, 0, 0, 1360, 1360, 0], y=[0, 0, 245, 245, 0, 0, 245, 245], z=[0, 0, 0, 0, 1, 1, 1, 1], color='gray', opacity=0.4))
    
    for p in active_pallets:
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





