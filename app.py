import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import io
import streamlit as st

# =========================================================
# 1. UI & THEME
# =========================================================
st.set_page_config(page_title="PLEKSEL TRAILER ENGINE 3D", layout="wide")

def apply_ui_theme():
    st.markdown("""
    <style>
        .stApp { background-color: #020408; color: #e2e8f0; }
        section[data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #38bdf8; }
        .metric-card { background: #111827; border: 1px solid #38bdf8; padding: 15px; border-radius: 8px; text-align: center; }
        .metric-val { color: #38bdf8; font-size: 24px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

apply_ui_theme()

# Initialisatie sessie states
for key in ['df_items', 'df_boxes', 'df_pallets', 'df_orders']:
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame()

# =========================================================
# 2. PDF GENERATOR FUNCTIE
# =========================================================
def generate_pdf(order_df, items_df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Order Packlist - Pleksel Trailer Engine", ln=True, align='C')
    pdf.ln(10)
    
    merged = pd.merge(order_df, items_df, on="ItemNr", how="left")
    
    for order_nr in merged['OrderNr'].unique():
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Order: {order_nr}", ln=True)
        pdf.set_font("Arial", '', 10)
        subset = merged[merged['OrderNr'] == order_nr]
        for _, row in subset.iterrows():
            txt = f"- Item: {row['ItemNr']} | Aantal: {row['Aantal']} | Dim: {row['L_cm']}x{row['B_cm']}x{row['H_cm']} cm"
            pdf.cell(0, 8, txt, ln=True)
        pdf.ln(5)
        
    return pdf.output(dest='S').encode('latin-1')

# =========================================================
# 3. SIDEBAR & FILTERS
# =========================================================
st.sidebar.title("📦 Trailer Engine")

# File Upload
uploaded_file = st.sidebar.file_uploader("Upload Template", type=['xlsx'])
if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    st.session_state.df_items = pd.read_excel(xls, 'Item Data').fillna(0)
    st.session_state.df_orders = pd.read_excel(xls, 'Order Data').fillna(0)

# Order Selectie
available_orders = []
if not st.session_state.df_orders.empty:
    available_orders = st.session_state.df_orders['OrderNr'].unique().tolist()

selected_orders = st.sidebar.multiselect("Selecteer Orders", options=available_orders, default=available_orders)

# PDF Download Knop
if st.sidebar.button("Genereer PDF Rapport") and not st.session_state.df_orders.empty:
    pdf_bytes = generate_pdf(st.session_state.df_orders[st.session_state.df_orders['OrderNr'].isin(selected_orders)], st.session_state.df_items)
    st.sidebar.download_button("Download PDF", data=pdf_bytes, file_name="order_details.pdf", mime="application/pdf")

# =========================================================
# 4. REKEN ENGINE & 3D PLOT
# =========================================================
def draw_truck_3d(positioned_units):
    fig = go.Figure()

    # Trailer omtrek (standaard trailer 13.6m x 2.45m x 2.6m)
    fig.add_trace(go.Mesh3d(
        x=[0, 1360, 1360, 0, 0, 1360, 1360, 0],
        y=[0, 0, 245, 245, 0, 0, 245, 245],
        z=[0, 0, 0, 0, 260, 260, 260, 260],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        opacity=0.05, color='gray', name='Trailer'
    ))

    for unit in positioned_units:
        l, b, h = unit['dim']
        px, py, pz = unit['pos'][0], unit['pos'][1], unit['pz']
        
        # Maak een 3D box voor elke pallet
        fig.add_trace(go.Mesh3d(
            x=[px, px+l, px+l, px, px, px+l, px+l, px],
            y=[py, py, py+b, py+b, py, py, py+b, py+b],
            z=[pz, pz, pz, pz, pz+h, pz+h, pz+h, pz+h],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            opacity=0.8,
            color='#38bdf8',
            hoverinfo="text",
            text=f"ID: {unit['id']}<br>Gewicht: {unit['weight']}kg<br>H: {h}cm"
        ))

    fig.update_layout(
        scene=dict(xaxis_title='Lengte (cm)', yaxis_title='Breedte (cm)', zaxis_title='Hoogte (cm)'),
        margin=dict(l=0, r=0, b=0, t=0),
        height=600
    )
    return fig

# Berekening Logica (vereenvoudigd voor demo)
def get_loading_plan(selected_orders):
    if st.session_state.df_orders.empty or st.session_state.df_items.empty:
        return []
    
    df = pd.merge(st.session_state.df_orders, st.session_state.df_items, on="ItemNr")
    df = df[df['OrderNr'].isin(selected_orders)]
    
    plan = []
    curr_x = 0
    for idx, row in df.iterrows():
        for i in range(int(row['Aantal'])):
            # Simpele plaatsing: 2 pallets naast elkaar
            side = 0 if i % 2 == 0 else 125
            plan.append({
                'id': f"O:{row['OrderNr']}-{row['ItemNr']}",
                'dim': [row['L_cm'], row['B_cm'], row['H_cm']],
                'pos': [curr_x, side, 0],
                'pz': 0,
                'weight': row['Kg']
            })
            if side == 125: curr_x += row['L_cm'] + 5
    return plan

# =========================================================
# 5. MAIN UI
# =========================================================
tab_viz, tab_data = st.tabs(["3D TRAILER VIEW", "DATA OVERZICHT"])

with tab_viz:
    loading_plan = get_loading_plan(selected_orders)
    
    if loading_plan:
        st.plotly_chart(draw_truck_3d(loading_plan), use_container_width=True)
        
        st.subheader("📋 Pallet Details (Interactief overzicht)")
        st.table(pd.DataFrame(loading_plan).drop(columns=['pos', 'pz']))
    else:
        st.info("Upload data en selecteer orders om de trailer te vullen.")

with tab_data:
    st.subheader("Data Input")
    st.write("Items:", st.session_state.df_items)
    st.write("Geselecteerde Orders:", st.session_state.df_orders[st.session_state.df_orders['OrderNr'].isin(selected_orders)])
