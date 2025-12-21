import pandas as pd

import numpy as np

import plotly.graph_objects as go

from fpdf import FPDF

import io

import streamlit as st  # Deze ontbrak



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

# 2. TAAL & INITIALISATIE (FIX VOOR ATTRIBUTE ERROR)

# =========================================================

if 'lang' not in st.session_state: 

    st.session_state.lang = 'NL'



# Zorg dat de dataframes altijd bestaan voordat de rest van de app start

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

        'stats_pal': "Aantal Pallets", 'stats_trucks': "Aantal Trucks", 'stats_lm': "Laadmeters"

    }

}

L = T[st.session_state.lang]







# =========================================================
# 3. SIDEBAR (Instellingen & Template Upload)  ✅ FIXED
# =========================================================

st.sidebar.title(L['settings'])
st.session_state.lang = st.sidebar.selectbox(
    "Language / Sprache / Taal", ["NL", "EN", "DE"], key="lang_select"
)

# ---- Berekeningsmethode (SLIDER) ----
st.session_state.calc_mode = st.sidebar.select_slider(
    "Berekeningsmethode",
    options=["Automatisch (Volume)", "Handmatig (Volle units)"],
    value=st.session_state.get("calc_mode", "Handmatig (Volle units)"),
    help="Automatisch berekent hoeveel er op een pallet past. Handmatig ziet elke order-regel als een aparte unit."
)

# ---- Toggles (MOETEN in session_state!) ----
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

# ---- Template Download ----
buffer_dl = io.BytesIO()
with pd.ExcelWriter(buffer_dl, engine='xlsxwriter') as writer:
    pd.DataFrame(columns=["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"]).to_excel(
        writer, sheet_name='Item Data', index=False
    )
    pd.DataFrame(columns=["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"]).to_excel(
        writer, sheet_name='Box Data', index=False
    )
    pd.DataFrame(columns=["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"]).to_excel(
        writer, sheet_name='Pallet Data', index=False
    )
    pd.DataFrame(columns=["OrderNr", "ItemNr", "Aantal"]).to_excel(
        writer, sheet_name='Order Data', index=False
    )

st.sidebar.download_button(L['download'], buffer_dl.getvalue(), "pleksel_template.xlsx")

# ---- Upload ----
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

# 4. REKEN ENGINE (GEFIKSTE KOLOMNAMEN)

# =========================================================

def calculate_metrics():

    # --- Orders (gefilterd of alles) ---
    orders = st.session_state.get(
        "df_orders_calc",
        st.session_state.get("df_orders", pd.DataFrame())
    )
    items = st.session_state.get("df_items", pd.DataFrame())

    opt_orient = st.session_state.get("opt_orient", True)

    if orders.empty or items.empty:
        return 0, 0, 0, 0, 0, []

    orders = orders.copy()
    items = items.copy()

    orders["ItemNr"] = orders["ItemNr"].astype(str)
    items["ItemNr"] = items["ItemNr"].astype(str)

    df = pd.merge(orders, items, on="ItemNr", how="inner")
    if df.empty:
        return 0, 0, 0, 0, 0, []

    # --------------------------------------------------
    # Units genereren
    # --------------------------------------------------
    units_to_load = []

    for _, row in df.iterrows():
        for i in range(int(row["Aantal"])):
            units_to_load.append({
                "id": f"{row['OrderNr']}_{row['ItemNr']}_{i}",
                "dim": [float(row["L_cm"]), float(row["B_cm"]), float(row["H_cm"])],
                "weight": float(row["Kg"]),
                "stackable": str(row.get("Stapelbaar", "Ja")).lower() in ["ja", "1", "yes", "true"]
            })

    # --------------------------------------------------
    # Simpele stabiele plaatsing (rij-voor-rij)
    # --------------------------------------------------
    positioned_units = []

    curr_x = 0
    curr_y = 0
    row_depth = 0

    MAX_WIDTH = st.session_state.get("trailer_width", 245)
    SPACING = 2

    for u in units_to_load:
        l, b, h = u["dim"]

        if opt_orient and l > b:
            l, b = b, l

        if curr_y + b > MAX_WIDTH:
            curr_x += row_depth + SPACING
            curr_y = 0
            row_depth = 0

        positioned_units.append({
            **u,
            "pos": (curr_x, curr_y),
            "pz": 0
        })

        curr_y += b + SPACING
        row_depth = max(row_depth, l)

    # --------------------------------------------------
    # Statistieken
    # --------------------------------------------------
    total_w = sum(p["weight"] for p in positioned_units)
    total_v = sum(
        (p["dim"][0] * p["dim"][1] * p["dim"][2]) / 1_000_000
        for p in positioned_units
    )

    used_length = curr_x + row_depth
    lm = round(used_length / 100, 2)
    trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0

    return (
        round(total_w, 1),
        round(total_v, 2),
        len(positioned_units),
        trucks,
        lm,
        positioned_units
    )

    

    

    # === Trailer instellingen ophalen (STAP 2) ===
    TRAILER_L = st.session_state.get("trailer_length", 1360)

    used_length = min(curr_x + row_depth, TRAILER_L)
    lm = round(used_length / 100, 2)

    trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0

    return round(total_w, 1), round(total_v, 2), len(units_to_load), trucks, lm, positioned_units






# =========================================================
# 5. UI TABS & 3D CALCULATION ENGINE (COMPLETE SECTOR 5)
# =========================================================

tab_data, tab_calc = st.tabs([L['data_tab'], L['calc_tab']])

with tab_data:
    t1, t2, t3, t4, t5 = st.tabs([
    "Items",
    "Boxes",
    "Pallets",
    "Orders",
    "Trailers"
])

    with t1:
        st.session_state.df_items = st.data_editor(st.session_state.df_items, use_container_width=True, num_rows="dynamic", key="ed_items")
    with t2:
        st.session_state.df_boxes = st.data_editor(st.session_state.df_boxes, use_container_width=True, num_rows="dynamic", key="ed_boxes")
    with t3:
        st.session_state.df_pallets = st.data_editor(st.session_state.df_pallets, use_container_width=True, num_rows="dynamic", key="ed_pallets")
    with t4:
        st.session_state.df_orders = st.data_editor(st.session_state.df_orders, use_container_width=True, num_rows="dynamic", key="ed_orders")
with t5:
    st.subheader("Trailer / Container type")

    trailer_type = st.selectbox(
        "Kies trailer",
        ["Standaard trailer (13.6m)", "40ft container", "20ft container", "Custom"]
    )

    if trailer_type == "Standaard trailer (13.6m)":
        st.session_state.trailer_length = 1360
        st.session_state.trailer_width  = 245
        st.session_state.trailer_height = 270

    elif trailer_type == "40ft container":
        st.session_state.trailer_length = 1203
        st.session_state.trailer_width  = 235
        st.session_state.trailer_height = 239

    elif trailer_type == "20ft container":
        st.session_state.trailer_length = 590
        st.session_state.trailer_width  = 235
        st.session_state.trailer_height = 239

    else:  # Custom
        st.session_state.trailer_length = st.number_input("Lengte (cm)", 500, 2000, 1360)
        st.session_state.trailer_width  = st.number_input("Breedte (cm)", 200, 300, 245)
        st.session_state.trailer_height = st.number_input("Hoogte (cm)", 200, 350, 270)


with tab_calc:
    # Voer berekening uit (houdt rekening met toggles uit de sidebar)
    res_w, res_v, res_p, res_t, res_lm, active_units = calculate_metrics()
with tab_calc:

    st.subheader("Order selectie")

    orders_df = st.session_state.df_orders

    order_mode = st.radio(
        "Bereken op basis van:",
        ["Alle orders", "Eén order", "Meerdere orders"],
        horizontal=True
    )

    selected_orders = None

    if order_mode == "Eén order":
        selected_orders = st.selectbox(
            "Selecteer order",
            orders_df["OrderNr"].unique()
        )

    elif order_mode == "Meerdere orders":
        selected_orders = st.multiselect(
            "Selecteer orders",
            orders_df["OrderNr"].unique()
        )
    # --- Orders filteren ---
    if order_mode == "Alle orders":
        st.session_state.df_orders_calc = orders_df.copy()

    elif order_mode == "Eén order":
        st.session_state.df_orders_calc = orders_df[
            orders_df["OrderNr"] == selected_orders
        ]

    elif order_mode == "Meerdere orders":
        st.session_state.df_orders_calc = orders_df[
            orders_df["OrderNr"].isin(selected_orders)
        ]

    # Dashboard Metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (L['stats_weight'], f"{res_w} kg"), 
        (L['stats_vol'], f"{res_v} m³"), 
        (L['stats_pal'], res_p), 
        (L['stats_trucks'], res_t), 
        (L['stats_lm'], f"{res_lm} m")
    ]
    for i, (label, val) in enumerate(metrics):
        with [c1, c2, c3, c4, c5][i]:
            st.markdown(f"<div class='metric-card'><small>{label}</small><br><span class='metric-val'>{val}</span></div>", unsafe_allow_html=True)

    st.divider()

    # --- 3D INTERACTIEVE TRAILER ---
    st.subheader("3D Trailer Layout & Legenda")

    if not active_units:
        st.info("Geen data om te visualiseren. Voer orders in bij Tab 01.")
    else:
        # Layout met kolom voor legenda
        col_viz, col_leg = st.columns([4, 1])

        fig = go.Figure()
        colors = ['#0ea5e9', '#f59e0b', '#ef4444', '#10b981', '#8b5cf6', '#ec4899', '#f43f5e', '#06b6d4']
        item_color_map = {}

        for p in active_units:
            l, b, h = p['dim']
            x, y, z_base = p['pos'][0], p['pos'][1], p['pz']
            
            # Kleur bepalen op basis van ItemNr (prefix van ID)
            item_type = str(p['id']).split('_')[0]
            if item_type not in item_color_map:
                item_color_map[item_type] = colors[len(item_color_map) % len(colors)]
            
            base_color = item_color_map[item_type]

            # 3D Mesh constructie (Shader look)
            fig.add_trace(go.Mesh3d(
                x=[x, x, x+l, x+l, x, x, x+l, x+l],
                y=[y, y+b, y+b, y, y, y+b, y+b, y],
                z=[z_base, z_base, z_base, z_base, z_base+h, z_base+h, z_base+h, z_base+h],
                i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
                j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
                k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
                color=base_color,
                opacity=0.9,
                flatshading=True,
                name=f"Type: {item_type}",
                hoverinfo="text",
                customdata=[[item_type, l, b, h, p['weight'], "Ja" if p.get('stackable', True) else "Nee"]],
                hovertemplate=(
                    "<b>Item: %{customdata[0]}</b><br>" +
                    "Afmetingen: %{customdata[1]}x%{customdata[2]}x%{customdata[3]} cm<br>" +
                    "Gewicht: %{customdata[4]} kg<br>" +
                    "Stapelbaar: %{customdata[5]}<br>" +
                    "<extra></extra>"
                )
            ))

        # Trailer visualisatie instellingen
              # Trailer visualisatie instellingen
        trailer_len = st.session_state.get("trailer_length", 1360)
        trailer_w   = st.session_state.get("trailer_width", 245)
        trailer_h   = st.session_state.get("trailer_height", 270)

        fig.update_layout(
            scene=dict(
                xaxis=dict(
                    title="Lengte (cm)",
                    range=[0, trailer_len],
                    backgroundcolor="#0f172a"
                ),
                yaxis=dict(
                    title="Breedte (cm)",
                    range=[0, trailer_w],
                    backgroundcolor="#0f172a"
                ),
                zaxis=dict(
                    title="Hoogte (cm)",
                    range=[0, trailer_h],
                    backgroundcolor="#0f172a"
                ),
                aspectmode="manual",
                aspectratio=dict(
                    x=trailer_len / trailer_w,
                    y=1,
                    z=trailer_h / trailer_w
                )
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, b=0, t=0),
            showlegend=False
        )




        fig.update_layout(
            scene=dict(
                xaxis=dict(title='Lengte (cm)', range=[0, trailer_len], backgroundcolor="#0f172a"),
                yaxis=dict(title='Breedte (cm)', range=[0, 245], backgroundcolor="#0f172a"),
                zaxis=dict(title='Hoogte (cm)', range=[0, 270], backgroundcolor="#0f172a"),
                aspectmode='manual',
    aspectratio=dict(
    x=trailer_len / trailer_w,
    y=1,
    z=trailer_h / trailer_w


            ),
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, b=0, t=0),
            showlegend=False
        )

        with col_viz:
            st.plotly_chart(fig, use_container_width=True)

        with col_leg:
            st.markdown("### Legenda")
            for itype, icolor in item_color_map.items():
                st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 5px;">
                        <div style="width: 20px; height: 20px; background-color: {icolor}; border-radius: 4px; margin-right: 10px;"></div>
                        <span>Item: {itype}</span>
                    </div>
                """, unsafe_allow_html=True)
            
            st.info(f"**Status:**\n- Mix: {'AAN' if mix_boxes else 'UIT'}\n- Stapel: {'AAN' if opt_stack else 'UIT'}\n- Orient: {'AAN' if opt_orient else 'UIT'}")

        # --- PDF EXPORT ---
        st.divider()
        if st.button("Genereer PDF Rapport"):
            try:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(190, 10, "PLEKSEL TRAILER LAADPLAN", ln=True, align='C')
                pdf.ln(10)
                
                # Stats in PDF
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(190, 10, f"Totaal Gewicht: {res_w} kg | Laadmeters: {res_lm} m", ln=True)
                pdf.ln(5)

                # Tabel met laadlijst
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(60, 8, "Item ID", border=1)
                pdf.cell(40, 8, "Afmetingen", border=1)
                pdf.cell(40, 8, "Positie (X,Y)", border=1)
                pdf.cell(40, 8, "Hoogte (Z)", border=1, ln=True)

                pdf.set_font("Arial", '', 9)
                for p in active_units:
                    pdf.cell(60, 7, str(p['id']), border=1)
                    pdf.cell(40, 7, f"{p['dim'][0]}x{p['dim'][1]}", border=1)
                    pdf.cell(40, 7, f"{round(p['pos'][0])},{round(p['pos'][1])}", border=1)
                    pdf.cell(40, 7, f"{round(p['pz'])}", border=1, ln=True)

                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.download_button("Download PDF", data=pdf_bytes, file_name="laadplan.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"Fout bij PDF genereren: {e}")


























