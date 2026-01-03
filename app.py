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
# 2. INITIALISATIE (SESSION STATE)
# =========================================================
if 'lang' not in st.session_state: st.session_state.lang = 'NL'
if 'mix_boxes' not in st.session_state: st.session_state.mix_boxes = False
if 'opt_stack' not in st.session_state: st.session_state.opt_stack = True
if 'opt_orient' not in st.session_state: st.session_state.opt_orient = True

# Trailer afmetingen
for key, val in {"trailer_length": 1360, "trailer_width": 245, "trailer_height": 270}.items():
    if key not in st.session_state: st.session_state[key] = val

# Dataframes
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
        'stats_pal': "Aantal Units", 'stats_trucks': "Aantal Trucks", 'stats_lm': "Laadmeters"
    }
}
L = T[st.session_state.lang]

# =========================================================
# 3. SIDEBAR & EXCEL ENGINE
# =========================================================
st.sidebar.title(L['settings'])
st.sidebar.selectbox("Language", ["NL", "EN", "DE"], key="lang")
st.sidebar.toggle(L['mix'], key="mix_boxes")
st.sidebar.toggle(L['stack'], key="opt_stack")
st.sidebar.toggle(L['orient'], key="opt_orient")

st.sidebar.divider()

# Template Download
buffer_dl = io.BytesIO()
with pd.ExcelWriter(buffer_dl, engine='xlsxwriter') as writer:
    st.session_state.df_items.to_excel(writer, sheet_name='Item Data', index=False)
    st.session_state.df_boxes.to_excel(writer, sheet_name='Box Data', index=False)
    st.session_state.df_pallets.to_excel(writer, sheet_name='Pallet Data', index=False)
    st.session_state.df_orders.to_excel(writer, sheet_name='Order Data', index=False)

st.sidebar.download_button(L['download'], buffer_dl.getvalue(), "pleksel_template.xlsx")

# Upload (GEFIKST)
uploaded_file = st.sidebar.file_uploader(L['upload'], type=['xlsx'])
if uploaded_file:
    try:
        # Gebruik openpyxl engine
        xls = pd.ExcelFile(uploaded_file, engine='openpyxl')
        st.session_state.df_items = pd.read_excel(xls, 'Item Data').dropna(how='all').fillna(0)
        st.session_state.df_boxes = pd.read_excel(xls, 'Box Data').dropna(how='all').fillna(0)
        st.session_state.df_pallets = pd.read_excel(xls, 'Pallet Data').dropna(how='all').fillna(0)
        st.session_state.df_orders = pd.read_excel(xls, 'Order Data').dropna(how='all').fillna(0)
        st.sidebar.success("✅ Geladen!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Fout: {e}")

# =========================================================
# 4. REKEN ENGINE
# =========================================================
def calculate_metrics():
    total_w, total_v, lm, trucks = 0.0, 0.0, 0.0, 0
    positioned_units = []
    
    orders = st.session_state.df_orders
    items = st.session_state.df_items
    
    if orders.empty or items.empty:
        return 0, 0, 0, 0, 0, []

    try:
        df = pd.merge(orders.astype(str), items.astype(str), on="ItemNr", how="inner")
        if df.empty: return 0, 0, 0, 0, 0, []

        max_w = st.session_state.trailer_width
        curr_x, curr_y, row_h = 0, 0, 0
        spacing = 2

        for _, row in df.iterrows():
            aantal = int(float(row['Aantal']))
            l, b, h = float(row['L_cm']), float(row['B_cm']), float(row['H_cm'])
            
            for i in range(aantal):
                l_eff, b_eff = (b, l) if (st.session_state.opt_orient and l > b) else (l, b)
                
                if curr_y + b_eff > max_w:
                    curr_x += row_h + spacing
                    curr_y, row_h = 0, 0
                
                positioned_units.append({
                    'id': f"{row['ItemNr']}_{i}",
                    'dim': [l_eff, b_eff, h],
                    'pos': [curr_x, curr_y],
                    'pz': 0,
                    'weight': float(row['Kg'])
                })
                curr_y += b_eff + spacing
                row_h = max(row_h, l_eff)

        total_w = sum(u['weight'] for u in positioned_units)
        total_v = sum((u['dim'][0]*u['dim'][1]*u['dim'][2])/1000000 for u in positioned_units)
        lm = round((curr_x + row_h) / 100, 2)
        trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0
        
    except Exception as e:
        st.error(f"Berekening error: {e}")
        
    return round(total_w, 1), round(total_v, 2), len(positioned_units), trucks, lm, positioned_units

# =========================================================
# 5. UI TABS & VISUALISATIE
# =========================================================
tab_data, tab_calc = st.tabs([L['data_tab'], L['calc_tab']])

with tab_data:
    t1, t2, t3, t4, t5 = st.tabs(["Items", "Boxes", "Pallets", "Orders", "Trailer"])
    with t1: st.session_state.df_items = st.data_editor(st.session_state.df_items, num_rows="dynamic", key="ed1")
    with t4: st.session_state.df_orders = st.data_editor(st.session_state.df_orders, num_rows="dynamic", key="ed4")
    with t5:
        st.session_state.trailer_length = st.number_input("Lengte", value=st.session_state.trailer_length)
        st.session_state.trailer_width = st.number_input("Breedte", value=st.session_state.trailer_width)
        st.session_state.trailer_height = st.number_input("Hoogte", value=st.session_state.trailer_height)

with tab_calc:
    res_w, res_v, res_p, res_t, res_lm, active_units = calculate_metrics()
    
    cols = st.columns(5)
    metrics = [(L['stats_weight'], f"{res_w}kg"), (L['stats_vol'], f"{res_v}m3"), (L['stats_pal'], res_p), (L['stats_trucks'], res_t), (L['stats_lm'], f"{res_lm}m")]
    for i, (lab, val) in enumerate(metrics):
        cols[i].markdown(f"<div class='metric-card'><small>{lab}</small><br><span class='metric-val'>{val}</span></div>", unsafe_allow_html=True)

    if active_units:
        fig = go.Figure()
        for p in active_units:
            l, b, h = p['dim']
            x, y, z = p['pos'][0], p['pos'][1], p['pz']
            fig.add_trace(go.Mesh3d(
                x=[x, x, x+l, x+l, x, x, x+l, x+l],
                y=[y, y+b, y+b, y, y, y+b, y+b, y],
                z=[z, z, z, z, z+h, z+h, z+h, z+h],
                i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
                color="#38bdf8", opacity=0.8, flatshading=True
            ))
        
        fig.update_layout(scene=dict(
            xaxis=dict(range=[0, st.session_state.trailer_length]),
            yaxis=dict(range=[0, st.session_state.trailer_width]),
            zaxis=dict(range=[0, st.session_state.trailer_height]),
            aspectratio=dict(x=st.session_state.trailer_length/st.session_state.trailer_width, y=1, z=st.session_state.trailer_height/st.session_state.trailer_width)
        ), margin=dict(l=0,r=0,b=0,t=0), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        # --- PDF EXPORT (GEFIKST) ---
        if st.button("📥 Download PDF"):
            try:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(190, 10, "PLEKSEL LAADPLAN", ln=True, align='C')
                pdf.ln(10)
                pdf.set_font("Arial", '', 12)
                pdf.cell(190, 10, f"Gewicht: {res_w}kg | Volume: {res_v}m3 | Laadmeter: {res_lm}m", ln=True)
                pdf.ln(5)
                
                # Tabel Header
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(60, 8, "Item ID", 1)
                pdf.cell(40, 8, "Afmeting", 1)
                pdf.cell(45, 8, "Positie X,Y", 1)
                pdf.cell(45, 8, "Z", 1, ln=True)

                pdf.set_font("Arial", '', 9)
                for u in active_units[:50]: # Limiet voor PDF snelheid
                    pdf.cell(60, 7, str(u['id']), 1)
                    pdf.cell(40, 7, f"{int(u['dim'][0])}x{int(u['dim'][1])}", 1)
                    pdf.cell(45, 7, f"{int(u['pos'][0])},{int(u['pos'][1])}", 1)
                    pdf.cell(45, 7, str(int(u['pz'])), 1, ln=True)
                
                pdf_output = pdf.output(dest='S')
                # Handle fpdf strings vs bytes
                pdf_bytes = pdf_output.encode('latin-1') if isinstance(pdf_output, str) else pdf_output
                st.download_button("Klik hier om PDF op te slaan", data=pdf_bytes, file_name="laadplan.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"PDF Fout: {e}")
