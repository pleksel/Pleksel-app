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
        div[data-testid="stDataEditor"] { background-color: #0f172a !important; border: 1px solid #38bdf8 !important; }
        .table-header { color: #38bdf8; font-weight: bold; border-bottom: 2px solid #38bdf8; padding: 5px 0; margin-top: 20px; margin-bottom: 10px; }
        div.stButton > button { background-color: #38bdf8 !important; color: #000 !important; font-weight: bold; width: 100%; border-radius: 4px; }
        .stTabs [data-baseweb="tab-list"] { background-color: #020408; }
        .stTabs [aria-selected="true"] { background-color: #38bdf8 !important; color: #000 !important; }
    </style>
    """, unsafe_allow_html=True)

apply_ui_theme()

# =========================================================
# 2. TAAL & INITIALISATIE
# =========================================================
if 'lang' not in st.session_state: st.session_state.lang = 'NL'

T = {
    'NL': {
        'title': "PLEKSEL TRAILER ENGINE",
        'settings': "Trailer Instellingen",
        'mix': "Mix Boxes (Verschillende items per doos)",
        'data_tab': "01: DATA INVOER",
        'calc_tab': "02: TRAILER PLANNING",
        'master': "Master Data (Items & Stapelbaarheid)",
        'order': "Order Lijst",
        'boxes': "Dozen Configuraties",
        'pallets': "Pallet Types",
        'truck': "Container / Truck Afmetingen",
        'download': "Download Template",
        'upload': "Upload Template (Excel/CSV)",
        'gen_pdf': "Genereer PDF per Order"
    },
    'EN': {
        'title': "PLEKSEL TRAILER ENGINE",
        'settings': "Trailer Settings",
        'mix': "Mix Boxes (Different items per box)",
        'data_tab': "01: DATA ENTRY",
        'calc_tab': "02: TRAILER PLANNING",
        'master': "Master Data (Items & Stackability)",
        'order': "Order List",
        'boxes': "Box Configurations",
        'pallets': "Pallet Types",
        'truck': "Container / Truck Dimensions",
        'download': "Download Template",
        'upload': "Upload Template (Excel/CSV)",
        'gen_pdf': "Generate PDF per Order"
    }
}
L = T[st.session_state.lang]

# Data Kolommen
MASTER_COLS = ["ItemNr", "Lengte_cm", "Breedte_cm", "Hoogte_cm", "Gewicht_kg", "VerplichteDoos", "MagStapelen"]
BOXES_COLS = ["Naam", "Lengte_cm", "Breedte_cm", "Hoogte_cm", "LeegGewicht_kg"]
PALLETS_COLS = ["Naam", "Lengte_cm", "Breedte_cm", "EigenGewicht_kg", "MaxHoogte_cm"]
TRUCK_COLS = ["Naam", "Lengte_cm", "Breedte_cm", "Hoogte_cm", "MaxLading_kg"]
ORDER_COLS = ["OrderNr", "ItemNr", "Aantal"]

for key, cols in [("m_df", MASTER_COLS), ("b_df", BOXES_COLS), ("p_df", PALLETS_COLS), ("t_df", TRUCK_COLS), ("o_df", ORDER_COLS)]:
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(columns=cols)

# =========================================================
# 3. SIDEBAR (Instellingen & Taal)
# =========================================================
st.sidebar.title(L['settings'])
st.session_state.lang = st.sidebar.selectbox("Language / Taal", ["NL", "EN"])
mix_boxes = st.sidebar.toggle(L['mix'], value=False) # Standaard UIT zoals gevraagd

# Template Functies
def get_template():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame(columns=MASTER_COLS).to_excel(writer, sheet_name='MasterData', index=False)
        pd.DataFrame(columns=ORDER_COLS).to_excel(writer, sheet_name='Orders', index=False)
    return output.getvalue()

st.sidebar.download_button(L['download'], get_template(), "pleksel_template.xlsx")
uploaded_file = st.sidebar.file_uploader(L['upload'], type=['xlsx', 'csv'])

# =========================================================
# 4. LOGICA & VISUALISATIE
# =========================================================
def draw_trailer_3d(l, b, h, pallets=[]):
    fig = go.Figure()
    # Vloer
    fig.add_trace(go.Mesh3d(x=[0, l, l, 0, 0, l, l, 0], y=[0, 0, b, b, 0, 0, b, b], z=[0, 0, 0, 0, 1, 1, 1, 1], color='gray', opacity=0.5))
    
    # Logisch laden (Pallets achter elkaar plaatsen)
    current_x = 0
    pallet_colors = ['#00f2ff', '#7000ff', '#ff0070', '#38bdf8']
    
    for i, p in enumerate(pallets):
        px, py, pz = p['pos']
        pl, pb, ph = p['dim']
        
        fig.add_trace(go.Mesh3d(
            x=[px, px+pl, px+pl, px, px, px+pl, px+pl, px],
            y=[py, py, py+pb, py+pb, py, py, py+pb, py+pb],
            z=[pz, pz, pz, pz, pz+ph, pz+ph, pz+ph, pz+ph],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=pallet_colors[i % len(pallet_colors)],
            opacity=0.8,
            name=f"Order {p['order']}"
        ))

    fig.update_layout(scene=dict(aspectmode='data'), paper_bgcolor="black", margin=dict(l=0,r=0,b=0,t=0))
    return fig

# =========================================================
# 5. PDF GENERATOR
# =========================================================
def generate_order_pdf(order_nr, pallet_list):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"Loading Manifest - Order: {order_nr}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(40, 10, "Pallet ID", 1)
    pdf.cell(60, 10, "Afmetingen (LxBxH)", 1)
    pdf.cell(40, 10, "Gewicht", 1)
    pdf.cell(40, 10, "Stapelbaar", 1)
    pdf.ln()
    
    pdf.set_font("Arial", '', 12)
    for p in pallet_list:
        if p['order'] == order_nr:
            pdf.cell(40, 10, p['id'], 1)
            pdf.cell(60, 10, f"{p['dim'][0]}x{p['dim'][1]}x{p['dim'][2]}", 1)
            pdf.cell(40, 10, f"{p['weight']} kg", 1)
            pdf.cell(40, 10, p['stack'], 1)
            pdf.ln()
            
    return pdf.output(dest='S').encode('latin-1')

# =========================================================
# 6. MAIN APP INTERFACE
# =========================================================
tab_data, tab_calc = st.tabs([L['data_tab'], L['calc_tab']])

with tab_data:
    st.markdown(f"<div class='table-header'>{L['master']}</div>", unsafe_allow_html=True)
    st.session_state.m_df = st.data_editor(st.session_state.m_df, num_rows="dynamic", use_container_width=True)
    
    col_o, col_b = st.columns(2)
    with col_o:
        st.markdown(f"<div class='table-header'>{L['order']}</div>", unsafe_allow_html=True)
        st.session_state.o_df = st.data_editor(st.session_state.o_df, num_rows="dynamic", use_container_width=True)
    with col_b:
        st.markdown(f"<div class='table-header'>{L['boxes']}</div>", unsafe_allow_html=True)
        st.session_state.b_df = st.data_editor(st.session_state.b_df, num_rows="dynamic", use_container_width=True)

    # UI Fix: Truck en Pallet velden onder elkaar
    st.markdown(f"<div class='table-header'>{L['pallets']}</div>", unsafe_allow_html=True)
    st.session_state.p_df = st.data_editor(st.session_state.p_df, num_rows="dynamic", use_container_width=True)
    
    st.markdown(f"<div class='table-header'>{L['truck']}</div>", unsafe_allow_html=True)
    st.session_state.t_df = st.data_editor(st.session_state.t_df, num_rows="dynamic", use_container_width=True)

with tab_calc:
    # MOCK DATA VOOR LOGICA
    mock_pallets = [
        {'id': 'PAL-01', 'order': '1001', 'pos': [0, 0, 0], 'dim': [120, 80, 150], 'weight': 350, 'stack': 'Nee'},
        {'id': 'PAL-02', 'order': '1001', 'pos': [125, 0, 0], 'dim': [120, 80, 150], 'weight': 400, 'stack': 'Nee'},
        {'id': 'PAL-03', 'order': '1002', 'pos': [0, 85, 0], 'dim': [120, 80, 110], 'weight': 150, 'stack': 'Ja'}
    ]

    col_3d, col_info = st.columns([3, 1])
    
    with col_3d:
        st.subheader("ShaderPilot 3D Trailer Viewer")
        fig = draw_trailer_3d(1360, 245, 270, mock_pallets)
        st.plotly_chart(fig, use_container_width=True)
    
    with col_info:
        st.markdown("<div style='background:#111827; padding:15px; border-left:4px solid #38bdf8;'>", unsafe_allow_html=True)
        st.write(f"### {L['gen_pdf']}")
        
        # Haal unieke orders op
        available_orders = ["1001", "1002"] # In productie: st.session_state.o_df['OrderNr'].unique()
        selected_order = st.selectbox("Select Order", available_orders)
        
        if st.button(f"Genereer PDF {selected_order}"):
            pdf_bytes = generate_order_pdf(selected_order, mock_pallets)
            st.download_button(label="Download PDF", data=pdf_bytes, file_name=f"Order_{selected_order}.pdf", mime="application/pdf")
        
        st.divider()
        st.write("**Total Weight:** 900 kg")
        st.write("**Load Meters:** 2.5 m")
        st.markdown("</div>", unsafe_allow_html=True)
