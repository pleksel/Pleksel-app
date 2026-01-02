import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import io
import streamlit as st
# ... andere imports ...

st.session_state.clear() # TIJDELIJK TOEVOEGEN
# =========================================================
# 1. UI & THEME
# =========================================================
st.set_page_config(page_title="PLEKSEL TRAILER ENGINE", layout="wide")

def apply_ui_theme():
    st.markdown("""
    <style>
        .stApp { background-color: #020408; color: #e2e8f0; }
        section[data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #38bdf8; }
        div.stButton > button { background-color: #38bdf8 !important; color: #000 !important; font-weight: bold; border-radius: 4px; }
        .metric-card { background: #111827; border: 1px solid #38bdf8; padding: 15px; border-radius: 8px; text-align: center; }
        .metric-val { color: #38bdf8; font-size: 24px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

apply_ui_theme()

# =========================================================
# 2. SESSION STATE INITIALISATIE
# =========================================================
if 'lang' not in st.session_state:
    st.session_state.lang = 'NL'

for df_key, cols in [
    ('df_items', ["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"]),
    ('df_boxes', ["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"]),
    ('df_pallets', ["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"]),
    ('df_orders', ["OrderNr", "ItemNr", "Aantal"])
]:
    if df_key not in st.session_state:
        st.session_state[df_key] = pd.DataFrame(columns=cols)

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
# 3. SIDEBAR
# =========================================================
st.sidebar.title(L['settings'])

st.session_state.lang = st.sidebar.selectbox(
    "Language / Sprache / Taal", ["NL", "EN", "DE"], key="lang_select"
)

st.session_state.calc_mode = st.sidebar.select_slider(
    "Berekeningsmethode",
    options=["Automatisch (Volume)", "Handmatig (Volle units)"],
    value=st.session_state.get("calc_mode", "Handmatig (Volle units)"),
    help="Automatisch berekent hoeveel er op een pallet past. Handmatig ziet elke order-regel als een aparte unit."
)

st.session_state.mix_boxes = st.sidebar.toggle(
    L['mix'], value=st.session_state.get("mix_boxes", False)
)
st.session_state.opt_stack = st.sidebar.toggle(
    L['stack'], value=st.session_state.get("opt_stack", True)
)
st.session_state.opt_orient = st.sidebar.toggle(
    L['orient'], value=st.session_state.get("opt_orient", True)
)
st.sidebar.divider()

# Download template
buffer_dl = io.BytesIO()
with pd.ExcelWriter(buffer_dl, engine='xlsxwriter') as writer:
    st.session_state.df_items.to_excel(writer, sheet_name='Item Data', index=False)
    st.session_state.df_boxes.to_excel(writer, sheet_name='Box Data', index=False)
    st.session_state.df_pallets.to_excel(writer, sheet_name='Pallet Data', index=False)
    st.session_state.df_orders.to_excel(writer, sheet_name='Order Data', index=False)

st.sidebar.download_button(L['download'], buffer_dl.getvalue(), "pleksel_template.xlsx")

# Upload template
uploaded_file = st.sidebar.file_uploader(L['upload'], type=['xlsx'])
if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        st.session_state.df_items = pd.read_excel(xls, 'Item Data').fillna(0)
        st.session_state.df_boxes = pd.read_excel(xls, 'Box Data').fillna(0)
        st.session_state.df_pallets = pd.read_excel(xls, 'Pallet Data').fillna(0)
        st.session_state.df_orders = pd.read_excel(xls, 'Order Data').fillna(0)
        st.sidebar.success("Geladen!")
    except Exception as e:
        st.sidebar.error(f"Fout in bestand: {e}")

# =========================================================
# 4. REKEN ENGINE MET 3D STACKING
# =========================================================
def calculate_metrics():
    orders = st.session_state.df_orders
    items = st.session_state.df_items
    opt_orient = st.session_state.opt_orient

    if orders.empty or items.empty:
        return 0, 0, 0, 0, 0, []

    df = pd.merge(
        orders.astype({"ItemNr": str}),
        items.astype({"ItemNr": str}),
        on="ItemNr", how="inner"
    )

    if df.empty:
        return 0, 0, 0, 0, 0, []

    units = []
    for _, row in df.iterrows():
        for i in range(int(row['Aantal'])):
            l, b, h = float(row['L_cm']), float(row['B_cm']), float(row['H_cm'])
            if opt_orient and l > b:
                l, b = b, l
            units.append({
                'id': f"{row['ItemNr']}_{i}",
                'dim': [l, b, h],
                'weight': float(row['Kg']),
                'stackable': str(row.get('Stapelbaar', 'Ja')).lower() in ['ja','1','yes','true']
            })

    # 3D stacking logic: pos x, y, z
    positioned_units = []
    curr_x, curr_y, curr_z = 0, 0, 0
    row_depth, row_height = 0, 0
    MAX_WIDTH = st.session_state.get("trailer_width", 245)
    TRAILER_LEN = st.session_state.get("trailer_length", 1360)
    SPACING = 2

    for u in units:
        l, b, h = u['dim']
        if curr_y + b > MAX_WIDTH:
            curr_x += row_depth + SPACING
            curr_y = 0
            row_depth = 0
            row_height = 0
        positioned_units.append({
            'id': u['id'],
            'dim': [l, b, h],
            'weight': u['weight'],
            'stackable': u['stackable'],
            'pos': [curr_x, curr_y],
            'pz': curr_z
        })
        curr_y += b
        row_depth = max(row_depth, l)
        row_height = max(row_height, h)

    total_w = sum(p['weight'] for p in positioned_units)
    total_v = sum((p['dim'][0]*p['dim'][1]*p['dim'][2])/1_000_000 for p in positioned_units)
    used_length = min(curr_x + row_depth, TRAILER_LEN)
    lm = round(used_length / 100, 2)
    trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0

    return round(total_w,1), round(total_v,2), len(units), trucks, lm, positioned_units

# =========================================================
# 5. UI TABS
# =========================================================
tab_data, tab_calc = st.tabs([L['data_tab'], L['calc_tab']])

# --- TAB DATA ---
with tab_data:
    t1, t2, t3, t4, t5 = st.tabs(["Items","Boxes","Pallets","Orders","Trailers"])
    with t1:
        st.session_state.df_items = st.data_editor(
            st.session_state.df_items, use_container_width=True, num_rows="dynamic"
        )
    with t2:
        st.session_state.df_boxes = st.data_editor(
            st.session_state.df_boxes, use_container_width=True, num_rows="dynamic"
        )
    with t3:
        st.session_state.df_pallets = st.data_editor(
            st.session_state.df_pallets, use_container_width=True, num_rows="dynamic"
        )
    with t4:
        st.session_state.df_orders = st.data_editor(
            st.session_state.df_orders, use_container_width=True, num_rows="dynamic"
        )
    with t5:
        st.subheader("Trailer / Container type")
        trailer_type = st.selectbox(
            "Kies trailer", ["Standaard trailer (13.6m)", "40ft container", "20ft container", "Custom"]
        )
        if trailer_type == "Standaard trailer (13.6m)":
            st.session_state.trailer_length = 1360
            st.session_state.trailer_width = 245
            st.session_state.trailer_height = 270
        elif trailer_type == "40ft container":
            st.session_state.trailer_length = 1203
            st.session_state.trailer_width = 235
            st.session_state.trailer_height = 239
        elif trailer_type == "20ft container":
            st.session_state.trailer_length = 590
            st.session_state.trailer_width = 235
            st.session_state.trailer_height = 239
        else:  # Custom
            st.session_state.trailer_length = st.number_input("Lengte (cm)", 500, 2000, 1360)
            st.session_state.trailer_width = st.number_input("Breedte (cm)", 200, 300, 245)
            st.session_state.trailer_height = st.number_input("Hoogte (cm)", 200, 350, 270)

