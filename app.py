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

# 3. SIDEBAR (Instellingen & Template Upload)

# =========================================================

st.sidebar.title(L['settings'])

st.session_state.lang = st.sidebar.selectbox("Language / Sprache / Taal", ["NL", "EN", "DE"])



# Nieuwe Slider voor berekeningsmethode

calc_mode = st.sidebar.select_slider(

    "Berekeningsmethode",

    options=["Automatisch (Volume)", "Handmatig (Volle units)"],

    value="Handmatig (Volle units)",

    help="Automatisch berekent hoeveel er op een pallet past. Handmatig ziet elke order-regel als een aparte unit."

)



mix_boxes = st.sidebar.toggle(L['mix'], value=False)

opt_stack = st.sidebar.toggle(L['stack'], value=True)

opt_orient = st.sidebar.toggle(L['orient'], value=True)



st.sidebar.divider()



# Template Download (4 tabbladen)

buffer_dl = io.BytesIO()

with pd.ExcelWriter(buffer_dl, engine='xlsxwriter') as writer:

    pd.DataFrame(columns=["ItemNr", "L_cm", "B_cm", "H_cm", "Kg", "Stapelbaar"]).to_excel(writer, sheet_name='Item Data', index=False)

    pd.DataFrame(columns=["BoxNaam", "L_cm", "B_cm", "H_cm", "LeegKg"]).to_excel(writer, sheet_name='Box Data', index=False)

    pd.DataFrame(columns=["PalletType", "L_cm", "B_cm", "EigenKg", "MaxH_cm"]).to_excel(writer, sheet_name='Pallet Data', index=False)

    pd.DataFrame(columns=["OrderNr", "ItemNr", "Aantal"]).to_excel(writer, sheet_name='Order Data', index=False)



st.sidebar.download_button(L['download'], buffer_dl.getvalue(), "pleksel_template.xlsx")



uploaded_file = st.sidebar.file_uploader(L['upload'], type=['xlsx'])

if uploaded_file:

    try:

        xls = pd.ExcelFile(uploaded_file)

        st.session_state.df_items = pd.read_excel(xls, 'Item Data').fillna(0)

        st.session_state.df_boxes = pd.read_excel(xls, 'Box Data').fillna(0)

        st.session_state.df_pallets = pd.read_excel(xls, 'Pallet Data').fillna(0)

        st.session_state.df_orders = pd.read_excel(xls, 'Order Data').fillna(0)

        st.sidebar.success("Geladen!")

    except:

        st.sidebar.error("Fout in bestand.")

# =========================================================

# 4. REKEN ENGINE (GEFIKSTE KOLOMNAMEN)

# =========================================================

def calculate_metrics():

    orders = st.session_state.get('df_orders', pd.DataFrame())

    items = st.session_state.get('df_items', pd.DataFrame())

    

    # Haal instellingen uit session_state

    opt_stack = st.session_state.get('opt_stack', True)

    opt_orient = st.session_state.get('opt_orient', True)



    if orders.empty or items.empty:

        return 0, 0, 0, 0, 0, []

    

    # Normaliseer kolomnamen

    items_cp = items.copy().rename(columns={'L': 'L_cm', 'B': 'B_cm', 'H': 'H_cm', 'Stapelbaar': 'Stack'})

    orders_cp = orders.copy()

    orders_cp['ItemNr'] = orders_cp['ItemNr'].astype(str)

    items_cp['ItemNr'] = items_cp['ItemNr'].astype(str)

    

    df = pd.merge(orders_cp, items_cp, on="ItemNr", how="inner").fillna(0)

    if df.empty: return 0, 0, 0, 0, 0, []



    units_to_load = []

    for _, row in df.iterrows():

        for i in range(int(row['Aantal'])):

            units_to_load.append({

                'id': f"{row['ItemNr']}_{i}",

                'dim': [float(row['L_cm']), float(row['B_cm']), float(row['H_cm'])],

                'weight': float(row['Kg']),

                'stackable': str(row.get('Stack', 'Ja')).lower() in ['ja', '1', 'yes', 'true']

            })



    positioned_units = []

    curr_x = 0

    i = 0

    max_h = 250 



    while i < len(units_to_load):

        u = units_to_load[i]

        l, b, h = u['dim']

        

        # Oriëntatie logica

        if opt_orient and l > b:

            l, b = b, l 



        # Stapel logica: Zoek of dit item op een bestaande positie past

        stacked = False

        if opt_stack and u['stackable']:

            for p in positioned_units:

                # Check of er ruimte bovenop een unit op de huidige x-as is

                if p['pos'][0] == curr_x and p['pz'] == 0 and (p['dim'][2] + h <= max_h):

                    positioned_units.append({

                        'id': u['id'], 'dim': [l, b, h], 'pos': [curr_x, p['pos'][1], 0], 

                        'pz': p['dim'][2], 'weight': u['weight']

                    })

                    stacked = True

                    break

        

        if not stacked:

            # Als we niet kunnen stapelen, check of we 2-breed kunnen laden

            if opt_orient and b <= 120 and (i + 1) < len(units_to_load):

                positioned_units.append({'id': u['id'], 'dim': [l, b, h], 'pos': [curr_x, 0, 0], 'pz': 0, 'weight': u['weight']})

                i += 1

                u2 = units_to_load[i]

                positioned_units.append({'id': u2['id'], 'dim': [u2['dim'][1], u2['dim'][0], u2['dim'][2]], 'pos': [curr_x, 122, 0], 'pz': 0, 'weight': u2['weight']})

                curr_x += 82

            else:

                positioned_units.append({'id': u['id'], 'dim': [l, b, h], 'pos': [curr_x, 0, 0], 'pz': 0, 'weight': u['weight']})

                curr_x += l + 2

        i += 1



    total_w = sum(p['weight'] for p in positioned_units)

    total_v = sum((p['dim'][0]*p['dim'][1]*p['dim'][2])/1000000 for p in positioned_units)

    lm = round(curr_x / 100, 2)

    trucks = int(np.ceil(lm / 13.6)) if lm > 0 else 0

    

    return round(total_w, 1), round(total_v, 2), len(units_to_load), trucks, lm, positioned_units



# =========================================================

# 5. UI TABS (Gecorrigeerd)

# =========================================================



# Zorg dat de namen in de lijst exact overeenkomen met de variabelen die je aanroept

tab_data, tab_calc = st.tabs([L['data_tab'], L['calc_tab']])



with tab_data:

    t1, t2, t3, t4 = st.tabs(["Items", "Boxes", "Pallets", "Orders"])

    with t1:

        st.session_state.df_items = st.data_editor(st.session_state.df_items, use_container_width=True, num_rows="dynamic", key="ed_items")

    with t2:

        st.session_state.df_boxes = st.data_editor(st.session_state.df_boxes, use_container_width=True, num_rows="dynamic", key="ed_boxes")

    with t3:

        st.session_state.df_pallets = st.data_editor(st.session_state.df_pallets, use_container_width=True, num_rows="dynamic", key="ed_pallets")

    with t4:

        st.session_state.df_orders = st.data_editor(st.session_state.df_orders, use_container_width=True, num_rows="dynamic", key="ed_orders")



with tab_calc:

    # Hier begint de berekening pas nadat de tabs zijn aangemaakt

    res_w, res_v, res_p, res_t, res_lm, active_units = calculate_metrics()



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



    # Plotly Chart logica volgt hieronder...

# =========================================================
        # 6. EXPORT FUNCTIE (PDF MET VISUALISATIE)
        # =========================================================
        st.divider()
        if st.button("Genereer PDF Rapport"):
            pdf = FPDF()
            pdf.add_page()
            
            # Header
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, "PLEKSEL TRAILER LAADPLAN", ln=True, align='C')
            pdf.set_font("Arial", '', 10)
            pdf.cell(190, 10, f"Datum: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
            pdf.ln(10)

            # Statistieken tabel
            pdf.set_fill_color(56, 189, 248) # Pleksel Blauw
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(190, 10, " Transport Statistieken", ln=True, fill=True)
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 10)
            stats_data = [
                ["Totaal Gewicht", f"{res_w} kg"],
                ["Totaal Volume", f"{res_v} m3"],
                ["Aantal Units", f"{res_p}"],
                ["Laadmeters", f"{res_lm} m"]
            ]
            
            for item in stats_data:
                pdf.cell(95, 8, item[0], border=1)
                pdf.cell(95, 8, item[1], border=1, ln=True)
            
            pdf.ln(10)

            # Laadlijst Tabel
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(190, 10, " Gedetailleerde Laadlijst", ln=True, fill=True)
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 9)
            
            # Tabel Headers
            cols = ["ID", "L (cm)", "B (cm)", "H (cm)", "X-pos", "Z-hoogte"]
            widths = [50, 28, 28, 28, 28, 28]
            
            for i, col in enumerate(cols):
                pdf.cell(widths[i], 8, col, border=1, fill=False)
            pdf.ln()

            # Tabel Data
            for p in active_units:
                pdf.cell(widths[0], 7, str(p['id']), border=1)
                pdf.cell(widths[1], 7, str(p['dim'][0]), border=1)
                pdf.cell(widths[2], 7, str(p['dim'][1]), border=1)
                pdf.cell(widths[3], 7, str(p['dim'][2]), border=1)
                pdf.cell(widths[4], 7, str(round(p['pos'][0])), border=1)
                pdf.cell(widths[5], 7, str(round(p['pz'])), border=1, ln=True)

            # Output PDF naar geheugen
            pdf_output = pdf.output(dest='S').encode('latin-1')
            st.download_button(
                label="Download Laadplan PDF",
                data=pdf_output,
                file_name="pleksel_laadplan.pdf",
                mime="application/pdf"
            )
