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
        div.stButton > button { background-color: #38bdf8 !important; color: #000 !important; font-weight: bold; border-radius: 4px; }
        .metric-card { background: #111827; border: 1px solid #38bdf8; padding: 15px; border-radius: 8px; text-align: center; }
        .metric-val { color: #38bdf8; font-size: 24px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

apply_ui_theme()

# =========================================================
# 2. INITIALISATIE
# =========================================================
# Initialiseer alle session state variabelen
for key, val in {
    'lang': 'NL', 'mix_boxes': False, 'opt_stack': True, 'opt_orient': True,
    'calc_mode': "Handmatig (Volle units)", 'trailer_length': 1360,
    'trailer_width': 245, 'trailer_height': 270,
    'df_items': pd.DataFrame(columns=["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"]),
    'df_boxes': pd.DataFrame(columns=["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"]),
    'df_pallets': pd.DataFrame(columns=["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"]),
    'df_orders': pd.DataFrame(columns=["OrderNr", "ItemNr", "Aantal"])
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

T = {
    'NL': {
        'settings': "Trailer Instellingen", 'mix': "Mix Boxes", 'stack': "Pallets Stapelen", 
        'orient': "Lang/Breed laden", 'data_tab': "01: DATA INVOER", 'calc_tab': "02: PLANNING",
        'item_data': "Item Data", 'box_data': "Box Data", 'pallet_data': "Pallet Data",
        'order_data': "Order Data", 'download': "Download Template", 
        'upload': "Upload Template", 'stats_weight': "Gewicht", 'stats_vol': "Volume", 
        'stats_pal': "Units", 'stats_trucks': "Trucks", 'stats_lm': "Meters"
    }
}
L = T.get(st.session_state.lang, T['NL'])

# =========================================================
# 3. SIDEBAR
# =========================================================
st.sidebar.title(L['settings'])
st.sidebar.selectbox("Taal", ["NL", "EN", "DE"], key="lang")
st.sidebar.select_slider("Methode", options=["Automatisch (Volume)", "Handmatig (Volle units)"], key="calc_mode")
st.sidebar.toggle(L['mix'], key="mix_boxes")
st.sidebar.toggle(L['stack'], key="opt_stack")
st.sidebar.toggle(L['orient'], key="opt_orient")

# Template Download
buffer_dl = io.BytesIO()
with pd.ExcelWriter(buffer_dl, engine='xlsxwriter') as writer:
    st.session_state.df_items.to_excel(writer, sheet_name='Item Data', index=False)
    st.session_state.df_orders.to_excel(writer, sheet_name='Order Data', index=False)
st.sidebar.download_button(L['download'], buffer_dl.getvalue(), "template.xlsx")

# Excel Upload FIX (engine toegevoegd)
uploaded_file = st.sidebar.file_uploader(L['upload'], type=['xlsx'])
if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file, engine='openpyxl')
        st.session_state.df_items = pd.read_excel(xls, 'Item Data').fillna(0)
        st.session_state.df_orders = pd.read_excel(xls, 'Order Data').fillna(0)
        st.sidebar.success("Geladen!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Bestand fout: {e}")

# =========================================================
# 4. REKEN ENGINE (VEILIG TEGEN CRASHES)
# =========================================================
def calculate_metrics():
    total_w, total_v, trucks, lm = 0.0, 0.0, 0, 0.0
    positioned_units = []
    
    orders = st.session_state.df_orders
    items = st.session_state.df_items
    
    if orders.empty or items.empty:
        return 0.0, 0.0, 0, 0, 0.0, []

    try:
        # Data types fix
        ord_c = orders.copy().astype({'ItemNr': str, 'Aantal': float})
        itm_c = items.copy().astype({'ItemNr': str, 'L_cm': float, 'B_cm': float, 'Kg': float})
        df = pd.merge(ord_c, itm_c, on="ItemNr", how="inner")

        max_w = float(st.session_state.trailer_width)
        curr_x, curr_y, row_depth = 0.0, 0.0, 0.0

        for _, row in df.iterrows():
            for i in range(int(row['Aantal'])):
                l, b, h = row['L_cm'], row['B_cm'], float(row['H_cm'])
                # Rotatie check
                l_eff, b_eff = (b, l) if (st.session_state.opt_orient and l > b and curr_y + l <= max_w) else (l, b)

                if curr_y + b_eff > max_w:
                    curr_x += row_depth + 2
                    curr_y, row_depth = 0.0, 0.0
                
                positioned_units.append({
                    'id': f"{row['ItemNr']}_{i}",
                    'dim': [l_eff, b_eff, h],
                    'pos': [curr_x, curr_y],
                    'pz': 0,
                    'weight': row['Kg']
                })
                curr_y += b_eff + 2
                row_depth = max(row_depth, l_eff)

        if positioned_units:
            total_w = sum(u['weight'] for u in positioned_units)
            total_v = sum((u['dim'][0]*u['dim'][1]*u['dim'][2])/1000000 for u in positioned_units)
            lm = round((curr_x + row_depth) / 100, 2)
            trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0

    except Exception as e:
        st.error(f"Engine Fout: {e}")

    return round(total_w, 1), round(total_v, 2), len(positioned_units), trucks, lm, positioned_units

# =========================================================
# 5. UI TABS & VISUALISATIE
# =========================================================
tab_data, tab_calc = st.tabs([L['data_tab'], L['calc_tab']])

with tab_data:
    st.subheader("Data Invoer")
    st.session_state.df_items = st.data_editor(st.session_state.df_items, num_rows="dynamic", key="editor_items")
    st.session_state.df_orders = st.data_editor(st.session_state.df_orders, num_rows="dynamic", key="editor_orders")

with tab_calc:
    res_w, res_v, res_p, res_t, res_lm, active_units = calculate_metrics()

    cols = st.columns(5)
    labels = [L['stats_weight'], L['stats_vol'], L['stats_pal'], L['stats_trucks'], L['stats_lm']]
    vals = [f"{res_w}kg", f"{res_v}m3", res_p, res_t, f"{res_lm}m"]
    for i, col in enumerate(cols):
        col.metric(labels[i], vals[i])

    if active_units:
        fig = go.Figure()
        for p in active_units:
            x, y, z = p['pos'][0], p['pos'][1], p['pz']
            l, b, h = p['dim']
            fig.add_trace(go.Mesh3d(
                x=[x, x, x+l, x+l, x, x, x+l, x+l],
                y=[y, y+b, y+b, y, y, y+b, y+b, y],
                z=[z, z, z, z, z+h, z+h, z+h, z+h],
                i=[7,0,0,0,4,4,6,6,4,0,3,2], j=[3,4,1,2,5,6,5,2,0,1,6,3], k=[0,7,2,3,6,7,1,1,5,5,7,6],
                color="#38bdf8", opacity=0.8
            ))
        fig.update_layout(scene=dict(aspectmode='data'), margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

        # PDF FIX (Safe encoding)
        if st.button("Genereer PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(190, 10, "PLEKSEL LAADPLAN", ln=True, align='C')
            pdf.set_font("Arial", '', 10)
            pdf.cell(190, 10, f"Gewicht: {res_w}kg | Meters: {res_lm}m", ln=True)
            
            # Voorkom crash bij teveel data in PDF
            for p in active_units[:50]: 
                pdf.cell(190, 7, f"Item {p['id']}: Pos {p['pos']}", ln=True)
            
            pdf_output = pdf.output(dest='S')
            # Check of output bytes of string is (verschilt per fpdf versie)
            pdf_bytes = pdf_output if isinstance(pdf_output, bytes) else pdf_output.encode('latin-1')
            st.download_button("Download PDF", pdf_bytes, "laadplan.pdf", "application/pdf")
