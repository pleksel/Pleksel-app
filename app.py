import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import io
import streamlit as st

# =========================================================
# 1. INITIALISATIE & THEME
# =========================================================
st.set_page_config(page_title="PLEKSEL TRAILER ENGINE", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #020408; color: #e2e8f0; }
    section[data-testid="stSidebar"] { background-color: #000000 !important; border-right: 1px solid #38bdf8; }
    div.stButton > button { background-color: #38bdf8 !important; color: #000 !important; font-weight: bold; border-radius: 4px; }
    .metric-card { background: #111827; border: 1px solid #38bdf8; padding: 15px; border-radius: 8px; text-align: center; }
    .metric-val { color: #38bdf8; font-size: 24px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Zorg dat de basis dataframes altijd in het geheugen staan
if 'df_items' not in st.session_state:
    st.session_state.df_items = pd.DataFrame(columns=["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"])
if 'df_orders' not in st.session_state:
    st.session_state.df_orders = pd.DataFrame(columns=["OrderNr", "ItemNr", "Aantal"])

# =========================================================
# 2. REKEN ENGINE (VOLLEDIG VEILIG)
# =========================================================
def calculate_metrics():
    # Forceer alle variabelen naar een beginstand om UnboundLocalError te voorkomen
    total_w, total_v, res_p, trucks, lm = 0.0, 0.0, 0, 0, 0.0
    positioned_units = []

    try:
        orders = st.session_state.get('df_orders', pd.DataFrame())
        items = st.session_state.get('df_items', pd.DataFrame())

        if orders.empty or items.empty:
            return total_w, total_v, res_p, trucks, lm, positioned_units

        # Data types gelijktrekken voor de merge
        ord_c = orders.copy().dropna(subset=['ItemNr', 'Aantal'])
        itm_c = items.copy().dropna(subset=['ItemNr', 'L_cm', 'B_cm'])
        ord_c['ItemNr'] = ord_c['ItemNr'].astype(str)
        itm_c['ItemNr'] = itm_c['ItemNr'].astype(str)

        df = pd.merge(ord_c, itm_c, on="ItemNr", how="inner")
        
        if df.empty:
            return total_w, total_v, res_p, trucks, lm, positioned_units

        # Simpele rekenlogica
        curr_x, curr_y, row_depth = 0.0, 0.0, 0.0
        max_w = 245.0 # Standaard breedte
        
        for _, row in df.iterrows():
            try:
                aantal = int(float(row['Aantal']))
                for i in range(aantal):
                    l, b, h = float(row['L_cm']), float(row['B_cm']), float(row['H_cm'])
                    
                    if curr_y + b > max_w:
                        curr_x += row_depth + 2
                        curr_y, row_depth = 0.0, 0.0
                    
                    positioned_units.append({
                        'id': f"{row['ItemNr']}_{i}",
                        'dim': [l, b, h],
                        'pos': [curr_x, curr_y],
                        'weight': float(row['Kg'])
                    })
                    curr_y += b + 2
                    row_depth = max(row_depth, l)
            except:
                continue

        if positioned_units:
            total_w = sum(u['weight'] for u in positioned_units)
            total_v = sum((u['dim'][0]*u['dim'][1]*u['dim'][2])/1000000 for u in positioned_units)
            res_p = len(positioned_units)
            lm = round((curr_x + row_depth) / 100, 2)
            trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0

    except Exception as e:
        st.error(f"Berekeningsfout: {e}")

    return round(total_w, 1), round(total_v, 2), res_p, trucks, lm, positioned_units

# =========================================================
# 3. UI LAYOUT
# =========================================================
st.sidebar.title("Instellingen")

# Template Upload
uploaded = st.sidebar.file_uploader("Upload Excel", type=['xlsx'])
if uploaded:
    try:
        xls = pd.ExcelFile(uploaded, engine='openpyxl')
        st.session_state.df_items = pd.read_excel(xls, 'Item Data').dropna(how='all').fillna(0)
        st.session_state.df_orders = pd.read_excel(xls, 'Order Data').dropna(how='all').fillna(0)
        st.sidebar.success("Geladen!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Fout: {e}")

tab1, tab2 = st.tabs(["Data", "Planning"])

with tab1:
    st.subheader("Items")
    st.session_state.df_items = st.data_editor(st.session_state.df_items, num_rows="dynamic", key="itm_ed")
    st.subheader("Orders")
    st.session_state.df_orders = st.data_editor(st.session_state.df_orders, num_rows="dynamic", key="ord_ed")

with tab2:
    # Hier worden de resultaten opgehaald
    res_w, res_v, res_p, res_t, res_lm, active_units = calculate_metrics()

    c = st.columns(5)
    c[0].metric("Gewicht", f"{res_w} kg")
    c[1].metric("Volume", f"{res_v} m3")
    c[2].metric("Units", res_p)
    c[3].metric("Trucks", res_t)
    c[4].metric("Meters", f"{res_lm} m")

    if active_units:
        fig = go.Figure()
        for u in active_units:
            x, y = u['pos'][0], u['pos'][1]
            l, b, h = u['dim']
            fig.add_trace(go.Mesh3d(
                x=[x, x, x+l, x+l, x, x, x+l, x+l],
                y=[y, y+b, y+b, y, y, y+b, y+b, y],
                z=[0, 0, 0, 0, h, h, h, h],
                i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
                color="#38bdf8"
            ))
        st.plotly_chart(fig, use_container_width=True)
