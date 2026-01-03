import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import io
import streamlit as st

# =========================================================
# 1. INITIALISATIE & UI
# =========================================================
st.set_page_config(page_title="PLEKSEL TRAILER ENGINE", layout="wide")

# Theme
st.markdown("""
<style>
    .stApp { background-color: #020408; color: #e2e8f0; }
    section[data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #38bdf8; }
    div.stButton > button { background-color: #38bdf8 !important; color: #000 !important; font-weight: bold; border-radius: 4px; }
    .metric-card { background: #111827; border: 1px solid #38bdf8; padding: 15px; border-radius: 8px; text-align: center; }
    .metric-val { color: #38bdf8; font-size: 24px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Session State Initialisatie
if 'df_items' not in st.session_state:
    st.session_state.df_items = pd.DataFrame(columns=["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"])
if 'df_orders' not in st.session_state:
    st.session_state.df_orders = pd.DataFrame(columns=["OrderNr", "ItemNr", "Aantal"])
if 'trailer_width' not in st.session_state: st.session_state.trailer_width = 245
if 'trailer_length' not in st.session_state: st.session_state.trailer_length = 1360
if 'trailer_height' not in st.session_state: st.session_state.trailer_height = 270

# =========================================================
# 2. REKEN ENGINE (VEILIG TEGEN UNBOUNDLOCALERROR)
# =========================================================
def calculate_metrics():
    # STAP 1: Initialiseer ALLES direct aan het begin
    total_w = 0.0
    total_v = 0.0
    res_p = 0
    trucks = 0
    lm = 0.0
    positioned_units = []

    # STAP 2: Controleer of er data is
    orders = st.session_state.get('df_orders', pd.DataFrame())
    items = st.session_state.get('df_items', pd.DataFrame())

    if orders.empty or items.empty:
        return total_w, total_v, res_p, trucks, lm, positioned_units

    try:
        # Data opschonen (Strings van ItemNr maken voor de merge)
        ord_c = orders.copy().astype({'ItemNr': str, 'Aantal': float})
        itm_c = items.copy().astype({'ItemNr': str, 'L_cm': float, 'B_cm': float, 'H_cm': float, 'Kg': float})

        df = pd.merge(ord_c, itm_c, on="ItemNr", how="inner")
        
        if df.empty:
            return total_w, total_v, res_p, trucks, lm, positioned_units

        # Basis logica voor laden
        curr_x, curr_y, row_depth = 0.0, 0.0, 0.0
        max_w = float(st.session_state.trailer_width)
        gap = 2.0

        for _, row in df.iterrows():
            for i in range(int(row['Aantal'])):
                l, b, h = row['L_cm'], row['B_cm'], row['H_cm']
                
                # Simpele rotatie check
                if l > b and (curr_y + l <= max_w):
                    l_eff, b_eff = b, l
                else:
                    l_eff, b_eff = l, b

                if curr_y + b_eff > max_w:
                    curr_x += row_depth + gap
                    curr_y, row_depth = 0.0, 0.0
                
                positioned_units.append({
                    'id': f"{row['ItemNr']}_{i}",
                    'dim': [l_eff, b_eff, h],
                    'pos': [curr_x, curr_y],
                    'pz': 0,
                    'weight': row['Kg']
                })
                
                curr_y += b_eff + gap
                row_depth = max(row_depth, l_eff)

        # Bereken totalen
        if positioned_units:
            total_w = sum(u['weight'] for u in positioned_units)
            total_v = sum((u['dim'][0]*u['dim'][1]*u['dim'][2])/1000000 for u in positioned_units)
            res_p = len(positioned_units)
            used_l = curr_x + row_depth
            lm = round(used_l / 100, 2)
            trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0

    except Exception as e:
        st.error(f"Fout in berekening: {e}")

    # STAP 3: Return ALTIJD de variabelen, ook als het misging
    return round(total_w, 1), round(total_v, 2), res_p, trucks, lm, positioned_units

# =========================================================
# 3. UI LAYOUT
# =========================================================
st.sidebar.title("Instellingen")

# Template Download/Upload
st.sidebar.subheader("Data Import")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    st.session_state.df_items.to_excel(writer, sheet_name='Item Data', index=False)
    st.session_state.df_orders.to_excel(writer, sheet_name='Order Data', index=False)
st.sidebar.download_button("Download Template", buffer.getvalue(), "template.xlsx")

uploaded = st.sidebar.file_uploader("Upload Template", type=['xlsx'])
if uploaded:
    try:
        xls = pd.ExcelFile(uploaded, engine='openpyxl')
        st.session_state.df_items = pd.read_excel(xls, 'Item Data').dropna(how='all').fillna(0)
        st.session_state.df_orders = pd.read_excel(xls, 'Order Data').dropna(how='all').fillna(0)
        st.sidebar.success("Geladen!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Bestand fout: {e}")

# Tabs
t_input, t_plan = st.tabs(["01: DATA INVOER", "02: PLANNING"])

with t_input:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Items")
        st.session_state.df_items = st.data_editor(st.session_state.df_items, num_rows="dynamic", key="ed_items")
    with c2:
        st.subheader("Orders")
        st.session_state.df_orders = st.data_editor(st.session_state.df_orders, num_rows="dynamic", key="ed_orders")

with t_plan:
    # Hier gaat het vaak mis als calculate_metrics() niet robuust is
    res_w, res_v, res_p, res_t, res_lm, active_units = calculate_metrics()

    # Dashboard
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Gewicht", f"{res_w} kg")
    m2.metric("Volume", f"{res_v} m3")
    m3.metric("Units", res_p)
    m4.metric("Trucks", res_t)
    m5.metric("Laadmeters", f"{res_lm} m")

    if active_units:
        # 3D Plot
        fig = go.Figure()
        for u in active_units:
            x, y, z = u['pos'][0], u['pos'][1], u['pz']
            l, b, h = u['dim']
            fig.add_trace(go.Mesh3d(
                x=[x, x, x+l, x+l, x, x, x+l, x+l],
                y=[y, y+b, y+b, y, y, y+b, y+b, y],
                z=[z, z, z, z, z+h, z+h, z+h, z+h],
                i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
                color="#38bdf8", opacity=0.7
            ))
        fig.update_layout(scene=dict(aspectmode='data'), margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

        # PDF Knop (Simpel & Veilig)
        if st.button("Genereer PDF"):
            try:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(190, 10, "LAADPLAN RAPPORT", ln=True, align='C')
                pdf.set_font("Arial", '', 10)
                pdf.cell(190, 10, f"Gewicht: {res_w}kg | Meters: {res_lm}m", ln=True)
                
                # Voorkom crash bij te veel rijen
                for u in active_units[:40]:
                    pdf.cell(190, 7, f"Item {u['id']}: Pos X={int(u['pos'][0])} Y={int(u['pos'][1])}", ln=True)
                
                pdf_out = pdf.output(dest='S')
                pdf_bytes = pdf_out.encode('latin-1') if isinstance(pdf_out, str) else pdf_out
                st.download_button("Download PDF", pdf_bytes, "laadplan.pdf", "application/pdf")
            except Exception as e:
                st.error(f"PDF Fout: {e}")
