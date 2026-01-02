import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fpdf import FPDF
import io
import streamlit as st

# =========================================================
# 1. CONFIGURATIE & UI THEMA
# =========================================================
def setup_page():
    st.set_page_config(page_title="PLEKSEL TRAILER ENGINE", layout="wide")
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

# =========================================================
# 2. SESSION STATE INITIALISATIE
# =========================================================
def init_session_state():
    if 'lang' not in st.session_state: st.session_state.lang = 'NL'
    
    # Dataframes
    defaults = {
        'df_items': pd.DataFrame(columns=["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"]),
        'df_boxes': pd.DataFrame(columns=["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"]),
        'df_pallets': pd.DataFrame(columns=["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"]),
        'df_orders': pd.DataFrame(columns=["OrderNr", "ItemNr", "Aantal"]),
        'df_orders_calc': pd.DataFrame()
    }
    
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

# =========================================================
# 3. HELPER FUNCTIES (Berekeningen & Data)
# =========================================================
def get_translations():
    return {
        'NL': {
            'settings': "Trailer Instellingen", 'mix': "Mix Boxes", 'stack': "Pallets Stapelen", 
            'orient': "Lang/Breed laden", 'data_tab': "01: DATA INVOER", 'calc_tab': "02: PLANNING",
            'item_data': "Item Data", 'box_data': "Box Data", 'pallet_data': "Pallet Data",
            'order_data': "Order Data", 'truck': "Truck/Container", 'download': "Download Template", 
            'upload': "Upload Template", 'stats_weight': "Totaal Gewicht", 'stats_vol': "Totaal Volume", 
            'stats_pal': "Aantal Pallets", 'stats_trucks': "Aantal Trucks", 'stats_lm': "Laadmeters"
        }
    }

def calculate_metrics():
    orders = st.session_state.get("df_orders_calc", st.session_state.df_orders)
    items = st.session_state.df_items
    
    if orders.empty or items.empty:
        return 0, 0, 0, 0, 0, []

    # Join data
    df = pd.merge(orders.copy(), items.copy(), on="ItemNr", how="inner")
    if df.empty: return 0, 0, 0, 0, 0, []

    # Instellingen
    MAX_WIDTH = st.session_state.get("trailer_width", 245)
    opt_orient = st.session_state.get("opt_orient", True)
    
    units_to_load = []
    for _, row in df.iterrows():
        for i in range(int(row['Aantal'])):
            units_to_load.append({
                'order': row['OrderNr'],
                'id': f"{row['ItemNr']}_{i}",
                'dim': [float(row['L_cm']), float(row['B_cm']), float(row['H_cm'])],
                'weight': float(row['Kg']),
                'stackable': str(row.get('Stapelbaar', 'Ja')).lower() in ['ja', '1', 'yes', 'true']
            })

    # Simpele 2D naar 3D nesting logica
    positioned_units = []
    curr_x, curr_y, row_depth, SPACING = 0, 0, 0, 2

    for u in units_to_load:
        l, b, h = u["dim"]
        if opt_orient and l > b: l, b = b, l

        if curr_y + b > MAX_WIDTH:
            curr_x += row_depth + SPACING
            curr_y, row_depth = 0, 0

        positioned_units.append({**u, "pos": (curr_x, curr_y), "pz": 0, "dim": [l, b, h]})
        curr_y += b + SPACING
        row_depth = max(row_depth, l)

    # Statistieken
    total_w = sum(p["weight"] for p in positioned_units)
    total_v = sum((p["dim"][0] * p["dim"][1] * p["dim"][2]) / 1_000_000 for p in positioned_units)
    lm = round((curr_x + row_depth) / 100, 2)
    trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0

    return round(total_w, 1), round(total_v, 2), len(positioned_units), trucks, lm, positioned_units

# =========================================================
# 4. SIDEBAR SECTIE
# =========================================================
def render_sidebar(L):
    st.sidebar.title(L['settings'])
    st.session_state.lang = st.sidebar.selectbox("Language", ["NL", "EN", "DE"], index=0)

    st.session_state.calc_mode = st.sidebar.select_slider(
        "Berekeningsmethode",
        options=["Automatisch (Volume)", "Handmatig (Volle units)"],
        value="Handmatig (Volle units)"
    )

    st.session_state.mix_boxes = st.sidebar.toggle(L['mix'], value=False)
    st.session_state.opt_stack = st.sidebar.toggle(L['stack'], value=True)
    st.session_state.opt_orient = st.sidebar.toggle(L['orient'], value=True)

    st.sidebar.divider()
    
    # Template & Upload
    render_file_controls(L)

def render_file_controls(L):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        for sheet, df_name in [('Item Data', 'df_items'), ('Box Data', 'df_boxes'), 
                               ('Pallet Data', 'df_pallets'), ('Order Data', 'df_orders')]:
            st.session_state[df_name].to_excel(writer, sheet_name=sheet, index=False)
    
    st.sidebar.download_button(L['download'], buffer.getvalue(), "pleksel_template.xlsx")
    
    uploaded_file = st.sidebar.file_uploader(L['upload'], type=['xlsx'])
    if uploaded_file:
        try:
            xls = pd.ExcelFile(uploaded_file)
            st.session_state.df_items = pd.read_excel(xls, 'Item Data').fillna(0)
            st.session_state.df_boxes = pd.read_excel(xls, 'Box Data').fillna(0)
            st.session_state.df_pallets = pd.read_excel(xls, 'Pallet Data').fillna(0)
            st.session_state.df_orders = pd.read_excel(xls, 'Order Data').fillna(0)
            st.sidebar.success("Data geladen!")
        except Exception as e:
            st.sidebar.error(f"Fout: {e}")

# =========================================================
# 5. MAIN UI TABS
# =========================================================
def render_data_tab():
    t1, t2, t3, t4, t5 = st.tabs(["Items", "Boxes", "Pallets", "Orders", "Trailers"])
    with t1: st.session_state.df_items = st.data_editor(st.session_state.df_items, use_container_width=True, num_rows="dynamic", key="ed_items")
    with t2: st.session_state.df_boxes = st.data_editor(st.session_state.df_boxes, use_container_width=True, num_rows="dynamic", key="ed_boxes")
    with t3: st.session_state.df_pallets = st.data_editor(st.session_state.df_pallets, use_container_width=True, num_rows="dynamic", key="ed_pallets")
    with t4: st.session_state.df_orders = st.data_editor(st.session_state.df_orders, use_container_width=True, num_rows="dynamic", key="ed_orders")
    
    with t5:
        trailer_type = st.selectbox("Kies trailer", ["Standaard trailer (13.6m)", "40ft container", "20ft container", "Custom"])
        dims = {"Standaard trailer (13.6m)": (1360, 245, 270), "40ft container": (1203, 235, 239), "20ft container": (590, 235, 239)}
        
        if trailer_type in dims:
            st.session_state.trailer_length, st.session_state.trailer_width, st.session_state.trailer_height = dims[trailer_type]
        else:
            st.session_state.trailer_length = st.number_input("Lengte (cm)", 500, 2000, 1360)
            st.session_state.trailer_width = st.number_input("Breedte (cm)", 200, 300, 245)
            st.session_state.trailer_height = st.number_input("Hoogte (cm)", 200, 350, 270)

def render_visualization(active_units, res_lm, res_w):
    col_viz, col_leg = st.columns([4, 1])
    
    fig = go.Figure()
    colors = ['#0ea5e9', '#f59e0b', '#ef4444', '#10b981', '#8b5cf6', '#ec4899']
    item_color_map = {}

    for p in active_units:
        l, b, h = p['dim']
        x, y, z = p['pos'][0], p['pos'][1], p['pz']
        itype = str(p['id']).split('_')[0]
        
        if itype not in item_color_map:
            item_color_map[itype] = colors[len(item_color_map) % len(colors)]
        
        fig.add_trace(go.Mesh3d(
            x=[x, x, x+l, x+l, x, x, x+l, x+l],
            y=[y, y+b, y+b, y, y, y+b, y+b, y],
            z=[z, z, z, z, z+h, z+h, z+h, z+h],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=item_color_map[itype], opacity=0.9, flatshading=True, name=itype,
            hoverinfo="text", hovertemplate=f"<b>Item: {itype}</b><br>Afm: {l}x{b}x{h}<extra></extra>"
        ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[0, st.session_state.trailer_length], backgroundcolor="#0f172a"),
            yaxis=dict(range=[0, st.session_state.trailer_width], backgroundcolor="#0f172a"),
            zaxis=dict(range=[0, st.session_state.trailer_height], backgroundcolor="#0f172a"),
            aspectmode="manual", aspectratio=dict(x=st.session_state.trailer_length/245, y=1, z=st.session_state.trailer_height/245)
        ),
        margin=dict(l=0, r=0, b=0, t=0), paper_bgcolor="rgba(0,0,0,0)"
    )

    with col_viz: st.plotly_chart(fig, use_container_width=True)
    with col_leg:
        st.markdown("### Legenda")
        for itype, icolor in item_color_map.items():
            st.markdown(f'<div style="display:flex; align-items:center;"><div style="width:15px; height:15px; background:{icolor}; margin-right:10px; border-radius:3px;"></div>{itype}</div>', unsafe_allow_html=True)

# =========================================================
# 6. PDF GENERATOR
# =========================================================
def generate_pdf(units, weight, lm):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "PLEKSEL TRAILER LAADPLAN", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(190, 10, f"Gewicht: {weight} kg | Laadmeters: {lm} m", ln=True)
    
    # Table headers
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(50, 8, "Item ID", 1); pdf.cell(40, 8, "Afm (cm)", 1); pdf.cell(50, 8, "Pos (X,Y)", 1); pdf.cell(30, 8, "Z", 1, ln=True)
    
    pdf.set_font("Arial", '', 9)
    for p in units:
        pdf.cell(50, 7, str(p['id']), 1)
        pdf.cell(40, 7, f"{p['dim'][0]}x{p['dim'][1]}", 1)
        pdf.cell(50, 7, f"{int(p['pos'][0])}, {int(p['pos'][1])}", 1)
        pdf.cell(30, 7, f"{int(p['pz'])}", 1, ln=True)
    
    return pdf.output(dest='S')

# =========================================================
# HOOFDPROGRAMMA
# =========================================================
def main():
    setup_page()
    init_session_state()
    L = get_translations()[st.session_state.lang]
    render_sidebar(L)

    tab_data, tab_calc = st.tabs([L['data_tab'], L['calc_tab']])

    with tab_data:
        render_data_tab()

    with tab_calc:
        # Order filter
        if not st.session_state.df_orders.empty:
            mode = st.radio("Selectie:", ["Alle", "Eén", "Meerdere"], horizontal=True)
            if mode == "Eén":
                sel = st.selectbox("Order", st.session_state.df_orders["OrderNr"].unique())
                st.session_state.df_orders_calc = st.session_state.df_orders[st.session_state.df_orders["OrderNr"] == sel]
            elif mode == "Meerdere":
                sel = st.multiselect("Orders", st.session_state.df_orders["OrderNr"].unique())
                st.session_state.df_orders_calc = st.session_state.df_orders[st.session_state.df_orders["OrderNr"].isin(sel)]
            else:
                st.session_state.df_orders_calc = st.session_state.df_orders.copy()

        # Berekening & Vis
        res_w, res_v, res_p, res_t, res_lm, active_units = calculate_metrics()
        
        if active_units:
            render_visualization(active_units, res_lm, res_w)
            if st.button("Genereer PDF Rapport"):
                pdf_bytes = generate_pdf(active_units, res_w, res_lm)
                st.download_button("Download PDF", pdf_bytes, "laadplan.pdf", "application/pdf")
        else:
            st.info("Voer data in om de planning te starten.")

if __name__ == "__main__":
    main()


























