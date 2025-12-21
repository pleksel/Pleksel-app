import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import io

# =========================================================
# 1. THEME & ADVANCED CSS (Zwart/Blauw/Donker)
# =========================================================
st.set_page_config(page_title="PLEKSEL LOGISTICS ENGINE", layout="wide")

def apply_custom_css():
    st.markdown("""
    <style>
        .stApp { background-color: #05070a; color: #e2e8f0; }
        section[data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #38bdf8; }
        div[data-testid="stDataEditor"] { background-color: #111827 !important; border: 1px solid #38bdf8 !important; }
        div[data-testid="stDataEditor"] canvas { filter: invert(0.9) hue-rotate(180deg) brightness(0.8); }
        .table-header { color: #38bdf8; font-weight: bold; border-bottom: 2px solid #38bdf8; padding: 5px 0; margin-top: 20px; }
        div.stButton > button { background-color: #38bdf8 !important; color: #000!important; font-weight: bold; width: 100%; border-radius: 0; }
        .stTabs [data-baseweb="tab-list"] { background-color: #05070a; }
        .stTabs [aria-selected="true"] { background-color: #38bdf8 !important; color: #000 !important; }
    </style>
    """, unsafe_allow_html=True)

apply_custom_css()

# =========================================================
# 2. DATA INITIALISATIE & TEMPLATE
# =========================================================
# Kolommen aangepast voor restricties en handmatige invoer
MASTER_COLS = ["ItemNr", "Lengte_cm", "Breedte_cm", "Hoogte_cm", "Gewicht_kg", "VerplichteDoos"]
BOXES_COLS = ["Naam", "Lengte_cm", "Breedte_cm", "Hoogte_cm", "LeegGewicht_kg"]
PALLETS_COLS = ["Naam", "Lengte_cm", "Breedte_cm", "EigenGewicht_kg", "MaxHoogte_cm"]
TRUCK_COLS = ["Naam", "Lengte_cm", "Breedte_cm", "Hoogte_cm", "MaxLading_kg"]
ORDER_COLS = ["OrderNr", "ItemNr", "Aantal"]

for key, cols in [("m_df", MASTER_COLS), ("b_df", BOXES_COLS), ("p_df", PALLETS_COLS), ("t_df", TRUCK_COLS), ("o_df", ORDER_COLS)]:
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(columns=cols)

def create_full_template():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.m_df.to_excel(writer, sheet_name='Artikelen', index=False)
        st.session_state.b_df.to_excel(writer, sheet_name='Dozen', index=False)
        st.session_state.p_df.to_excel(writer, sheet_name='Pallets', index=False)
        st.session_state.t_df.to_excel(writer, sheet_name='Trucks_Containers', index=False)
        st.session_state.o_df.to_excel(writer, sheet_name='Orders', index=False)
    return output.getvalue()

# =========================================================
# 3. PDF GENERATIE FUNCTIE
# =========================================================
class OrderPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, f'LADING SPECIFICATIE - ORDER: {self.order_id}', 0, 1, 'C')
        self.ln(5)

def generate_order_pdf(order_id, pallet_data, summary):
    pdf = OrderPDF()
    pdf.order_id = order_id
    pdf.add_page()
    
    for i, p in enumerate(pallet_data):
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f"Pallet {i+1}: {p['type']} ({p['dim']})", 1, 1, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 8, f"Inhoud: {p['items']}", 0, 1)
        pdf.cell(0, 8, f"Totaal Gewicht (incl. pallet): {p['weight']} kg", 0, 1)
        pdf.ln(5)
    
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "OVERZICHT", 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, f"Totaal Pallets: {summary['total_pallets']}", 0, 1)
    pdf.cell(0, 8, f"Laadmeters: {summary['loading_meters']} m", 0, 1)
    return pdf.output(dest='S').encode('latin-1')

# =========================================================
# 4. DASHBOARD & INTERFACE
# =========================================================
st.title("🚛 PLEKSEL LOGISTICS ENGINE (ORTEC-PRO)")

tab_data, tab_calc, tab_vis = st.tabs(["01: DATA INVOER", "02: BEREKENING", "03: 3D SIMULATIE"])

with tab_data:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.download_button("Download Volledige Template", create_full_template(), "pleksel_template.xlsx")
    with c2:
        uploaded_file = st.file_uploader("Importeer Excel data", type="xlsx")
        if uploaded_file:
            try:
                st.session_state.m_df = pd.read_excel(uploaded_file, sheet_name='Artikelen')
                st.session_state.o_df = pd.read_excel(uploaded_file, sheet_name='Orders')
                st.success("Data succesvol geladen!")
            except: st.error("Fout in Excel format.")

    st.markdown("<div class='table-header'>Orders & Artikelen</div>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a: st.session_state.o_df = st.data_editor(st.session_state.o_df, num_rows="dynamic", key="order_ed", use_container_width=True)
    with col_b: st.session_state.m_df = st.data_editor(st.session_state.m_df, num_rows="dynamic", key="art_ed", use_container_width=True)

    st.markdown("<div class='table-header'>Configuratie (Dozen, Pallets, Trucks)</div>", unsafe_allow_html=True)
    c_box, c_pal, c_tr = st.columns(3)
    with c_box: st.session_state.b_df = st.data_editor(st.session_state.b_df, num_rows="dynamic", key="box_ed")
    with c_pal: st.session_state.p_df = st.data_editor(st.session_state.p_df, num_rows="dynamic", key="pal_ed")
    with c_tr: st.session_state.t_df = st.data_editor(st.session_state.t_df, num_rows="dynamic", key="tr_ed")

with tab_calc:
    st.subheader("Selecteer Orders voor Planning")
    all_orders = st.session_state.o_df['OrderNr'].unique() if not st.session_state.o_df.empty else []
    selected_orders = st.multiselect("Selecteer orders die samen geladen moeten worden:", all_orders)
    
    st.sidebar.subheader("Order Instellingen")
    stackable = st.sidebar.toggle("Pallets Stapelbaar (voor deze run)", value=True)
    
    if st.button("START BEREKENING & GENERATE PDFS"):
        # SIMULATIE LOGICA (Vereenvoudigd voor demo)
        st.success(f"Planning voltooid voor {len(selected_orders)} orders.")
        
        # Voorbeeld resultaat HUD
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Volume", "42.5 m³")
        h2.metric("Laadmeters", "1.2 m")
        h3.metric("Totaal Gewicht", "1450 kg")
        h4.metric("Aantal Trucks", "1")

        # PDF Download per Order
        for oid in selected_orders:
            mock_summary = {"total_pallets": 2, "loading_meters": 0.8}
            mock_pallet = [{"type": "Euro120", "dim": "120x80", "items": "12x Item A", "weight": 450}]
            pdf_data = generate_order_pdf(oid, mock_pallet, mock_summary)
            st.download_button(f"Download PDF Order {oid}", pdf_data, f"Order_{oid}.pdf")

with tab_vis:
    st.subheader("3D Truck Loading View (ShaderPilot Mode)")
    # Ortec-stijl visualisatie
    fig = go.Figure()
    # Mock Pallet 1
    fig.add_trace(go.Mesh3d(x=[0,1.2,1.2,0,0,1.2,1.2,0], y=[0,0,0.8,0.8,0,0,0.8,0.8], z=[0,0,0,0,1.5,1.5,1.5,1.5],
                             i=[7,0,0,0,4,4,6,6,4,0,3,2], j=[3,4,1,2,5,6,5,2,0,1,6,3], k=[0,7,2,3,6,7,1,1,5,5,7,6],
                             color='cyan', opacity=0.5, name="Pallet A01 (Order 1001)"))
    
    fig.update_layout(scene=dict(xaxis_title='Lengte', yaxis_title='Breedte', zaxis_title='Hoogte'),
                      width=900, height=600, margin=dict(r=0, l=0, b=0, t=0))
    st.plotly_chart(fig, use_container_width=True)
    st.info("Klik op de pallet in de 3D view voor details. De lijn in de resultatenlijst zal oplichten.")

st.sidebar.markdown("---")
st.sidebar.write("Systeem status: **STANDBY**")
