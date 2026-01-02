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
        div.stButton > button { background-color: #38bdf8 !important; color: #000 !important; font-weight: bold; }
        .metric-card { background: #111827; border: 1px solid #38bdf8; padding: 15px; border-radius: 8px; text-align: center; }
        .metric-val { color: #38bdf8; font-size: 24px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

apply_ui_theme()

# =========================================================
# 2. SESSION STATE
# =========================================================
if 'lang' not in st.session_state:
    st.session_state.lang = 'NL'

for key, cols in {
    'df_items': ["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"],
    'df_boxes': ["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"],
    'df_pallets': ["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"],
    'df_orders': ["OrderNr", "ItemNr", "Aantal"]
}.items():
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(columns=cols)

# =========================================================
# 3. SIDEBAR
# =========================================================
st.sidebar.title("Trailer Instellingen")

st.session_state.mix_boxes = st.sidebar.toggle("Mix Boxes", False)
st.session_state.opt_stack = st.sidebar.toggle("Stapelen", True)
st.session_state.opt_orient = st.sidebar.toggle("Draaien", True)

# =========================================================
# 4. REKEN ENGINE
# =========================================================
def calculate_metrics():
    orders = st.session_state.df_orders
    items = st.session_state.df_items

    if orders.empty or items.empty:
        return 0, 0, 0, 0, 0, []

    df = pd.merge(
        orders.astype({'ItemNr': str}),
        items.astype({'ItemNr': str}),
        on="ItemNr"
    )

    units = []
    for _, r in df.iterrows():
        for i in range(int(r["Aantal"])):
            units.append({
                "id": f"{r['ItemNr']}_{i}",
                "dim": [float(r["L_cm"]), float(r["B_cm"]), float(r["H_cm"])],
                "weight": float(r["Kg"]),
                "stackable": str(r["Stapelbaar"]).lower() in ["ja", "yes", "1", "true"]
            })

    placed = []
    x = y = z = 0
    row_depth = 0
    WIDTH = st.session_state.trailer_width

    for u in units:
        l, b, h = u["dim"]
        if st.session_state.opt_orient and l > b:
            l, b = b, l

        if y + b > WIDTH:
            x += row_depth + 2
            y = 0
            row_depth = 0

        u["pos"] = (x, y)
        u["pz"] = 0
        placed.append(u)

        y += b + 2
        row_depth = max(row_depth, l)

    total_w = sum(p["weight"] for p in placed)
    total_v = sum((p["dim"][0]*p["dim"][1]*p["dim"][2])/1e6 for p in placed)
    lm = round((x + row_depth) / 100, 2)
    trucks = int(np.ceil(lm / 13.6)) if lm else 0

    return round(total_w,1), round(total_v,2), len(placed), trucks, lm, placed

# =========================================================
# 5. UI TABS
# =========================================================
tab_data, tab_calc = st.tabs(["01: DATA", "02: PLANNING"])

with tab_data:
    t1, t2, t3, t4, t5 = st.tabs(["Items","Boxes","Pallets","Orders","Trailer"])

    with t1:
        st.session_state.df_items = st.data_editor(st.session_state.df_items, num_rows="dynamic")
    with t2:
        st.session_state.df_boxes = st.data_editor(st.session_state.df_boxes, num_rows="dynamic")
    with t3:
        st.session_state.df_pallets = st.data_editor(st.session_state.df_pallets, num_rows="dynamic")
    with t4:
        st.session_state.df_orders = st.data_editor(st.session_state.df_orders, num_rows="dynamic")
    with t5:
        trailer = st.selectbox("Trailer", ["Standaard", "40ft", "20ft", "Custom"])
        if trailer == "Standaard":
            st.session_state.trailer_length = 1360
            st.session_state.trailer_width = 245
            st.session_state.trailer_height = 270
        elif trailer == "40ft":
            st.session_state.trailer_length = 1203
            st.session_state.trailer_width = 235
            st.session_state.trailer_height = 239
        elif trailer == "20ft":
            st.session_state.trailer_length = 590
            st.session_state.trailer_width = 235
            st.session_state.trailer_height = 239
        else:
            st.session_state.trailer_length = st.number_input("Lengte", 500, 2000, 1360)
            st.session_state.trailer_width = st.number_input("Breedte", 200, 300, 245)
            st.session_state.trailer_height = st.number_input("Hoogte", 200, 350, 270)

with tab_calc:
    w, v, p, t, lm, units = calculate_metrics()

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, lbl, val in zip(
        [c1,c2,c3,c4,c5],
        ["Gewicht","Volume","Units","Trucks","Laadmeters"],
        [f"{w} kg", f"{v} m³", p, t, f"{lm} m"]
    ):
        with col:
            st.markdown(f"<div class='metric-card'><small>{lbl}</small><div class='metric-val'>{val}</div></div>", unsafe_allow_html=True)

    if units:
        fig = go.Figure()
        for u in units:
            l,b,h = u["dim"]
            x,y = u["pos"]
            z = u["pz"]
            fig.add_trace(go.Mesh3d(
                x=[x,x,x+l,x+l,x,x,x+l,x+l],
                y=[y,y+b,y+b,y,y,y+b,y+b,y],
                z=[z,z,z,z,z+h,z+h,z+h,z+h],
                opacity=0.9
            ))

        fig.update_layout(scene=dict(
            xaxis=dict(range=[0, st.session_state.trailer_length]),
            yaxis=dict(range=[0, st.session_state.trailer_width]),
            zaxis=dict(range=[0, st.session_state.trailer_height])
        ))
        st.plotly_chart(fig, use_container_width=True)
