import streamlit as st
import pandas as pd
import math, io, os, shutil
from fpdf import FPDF

# =========================================================
# 1. PAGE CONFIG & THEMA
# =========================================================
st.set_page_config(page_title="PLEKSEL PRO", page_icon="🚛", layout="wide")

st.markdown("""
<style>
    h1 { text-align: center; color: #007AA3; }
    div.stButton > button { width: 100%; border-radius: 0.5rem; border: 1px solid #007AA3; background-color: #e0f2f7; color: #007AA3; }
    div[data-testid="stMetric"], .stContainer { border-radius: 8px; background-color: #f0f8ff; border: 1px solid #cce5ff; padding: 15px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. CONFIGURATIE & MEERTALIGHEID
# =========================================================
TEMPLATE_DIR = "pleksel_templates"
os.makedirs(TEMPLATE_DIR, exist_ok=True)

TRANSPORT_PRESETS = {
    "Standaard Truck Trailer": {"Lengte": 1360, "Breedte": 245, "Hoogte": 270, "MaxGewicht": 24000},
    "20ft Container": {"Lengte": 590, "Breedte": 235, "Hoogte": 239, "MaxGewicht": 28000},
    "40ft Container": {"Lengte": 1203, "Breedte": 235, "Hoogte": 239, "MaxGewicht": 26000},
}

LANGS = {
    "NL": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Planning",
        "btn_calc": "Bereken Planning", "pals": "Pallets", "weight": "Totaal Gewicht (KG)", 
        "meters": "Laadmeters", "trucks": "Trucks Nodig", "opt_stack": "Pallets stapelbaar?",
        "opt_mix_box": "Meerdere soorten dozen?", "opt_mixed_items": "Mixed items in doos?",
        "opt_separate": "Orders apart berekenen?", "download_template": "Download Lege Template",
        "truck_select": "Truck/Container Type", "box_strat": "Doos Strategie"
    },
    "EN": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Planning",
        "btn_calc": "Calculate Planning", "pals": "Pallets", "weight": "Total Weight (KG)", 
        "meters": "Loading Meters", "trucks": "Trucks Needed", "opt_stack": "Pallets stackable?",
        "opt_mix_box": "Multiple box types?", "opt_mixed_items": "Mixed items in box?",
        "opt_separate": "Calculate orders separately?", "download_template": "Download Empty Template",
        "truck_select": "Truck/Container Type", "box_strat": "Box Strategy"
    },
    "DE": {
        "nav_templates": "📁 Vorlagen", "nav_orders": "📑 Aufträge", "nav_calc": "🚛 Planung",
        "btn_calc": "Planung berechnen", "pals": "Paletten", "weight": "Gesamtgewicht (KG)", 
        "meters": "Lademeter", "trucks": "LKW benötigt", "opt_stack": "Paletten stapelbar?",
        "opt_mix_box": "Mehrere Kartontypen?", "opt_mixed_items": "Gemischte Artikel im Karton?",
        "opt_separate": "Aufträge separat berechnen?", "download_template": "Leere Vorlage herunterladen",
        "truck_select": "LKW/Container Typ", "box_strat": "Karton-Strategie"
    },
    "PL": {
        "nav_templates": "📁 Szablony", "nav_orders": "📑 Zamówienia", "nav_calc": "🚛 Planowanie",
        "btn_calc": "Oblicz planowanie", "pals": "Palety", "weight": "Waga całkowita (KG)", 
        "meters": "Metry ładunkowe", "trucks": "Potrzebne ciężarówki", "opt_stack": "Palety piętrowalne?",
        "opt_mix_box": "Wiele rodzajów kartonów?", "opt_mixed_items": "Mieszane produkty w kartonie?",
        "opt_separate": "Oblicz zamówienia oddzielnie?", "download_template": "Pobierz pusty szablon",
        "truck_select": "Typ ciężarówki/kontenera", "box_strat": "Strategia kartonów"
    }
}

st.sidebar.title("PLEKSEL Settings")
lang_choice = st.sidebar.selectbox("Language / Język / Sprache", ["NL", "EN", "DE", "PL"])
T = LANGS[lang_choice]

# Kolomdefinities
MASTER_COLS = {"ItemNr": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
BOXES_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
PALLETS_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "MaxHoogte": float, "Gewicht": float, "PalletHoogte": float, "PalletStapelbaar": bool}
ORDERS_COLS = {"OrderNr": str, "ItemNr": str, "Aantal": int}
TRUCK_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "MaxGewicht": float}

for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("orders_df", ORDERS_COLS), ("custom_trucks_df", TRUCK_COLS)]:
    if key not in st.session_state: st.session_state[key] = pd.DataFrame(columns=cols.keys())

# =========================================================
# 3. HELPER FUNCTIES
# =========================================================
def bepaal_optimale_doos(group, boxes_df):
    if boxes_df.empty: return "Standard", 0.0
    vol_nodig = (group['Lengte'] * group['Breedte'] * group['Hoogte'] * group['Aantal']).sum() * 1.15
    temp_boxes = boxes_df.copy()
    temp_boxes['vol'] = temp_boxes['Lengte'] * temp_boxes['Breedte'] * temp_boxes['Hoogte']
    temp_boxes = temp_boxes.sort_values('vol')
    for _, d in temp_boxes.iterrows():
        if d['vol'] >= (vol_nodig / group['Aantal'].sum()):
            return d['Naam'], d['Gewicht']
    return "Custom Box", 0.5

def create_empty_template():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame(columns=MASTER_COLS.keys()).to_excel(writer, sheet_name='Master', index=False)
        pd.DataFrame(columns=BOXES_COLS.keys()).to_excel(writer, sheet_name='Boxes', index=False)
        pd.DataFrame(columns=PALLETS_COLS.keys()).to_excel(writer, sheet_name='Pallets', index=False)
        pd.DataFrame(columns=ORDERS_COLS.keys()).to_excel(writer, sheet_name='Orders', index=False)
    return output.getvalue()

# =========================================================
# 4. UI SECTIES
# =========================================================
st.markdown(f"<h1>PLEKSEL {lang_choice} 🚛</h1>", unsafe_allow_html=True)
page = st.sidebar.radio("Menu", [T["nav_templates"], T["nav_orders"], T["nav_calc"]])

if page == T["nav_templates"]:
    st.header(T["nav_templates"])
    c1, c2 = st.columns(2)
    c1.download_button(T["download_template"], create_empty_template(), "pleksel_template.xlsx")
    up = c2.file_uploader("Upload Excel Template", type="xlsx")
    if up:
        xls = pd.ExcelFile(up)
        for sheet, key in [("Master", "master_data_df"), ("Boxes", "boxes_df"), ("Pallets", "pallets_df")]:
            if sheet in xls.sheet_names: st.session_state[key] = pd.read_excel(xls, sheet)
        st.success("Template geladen!")

    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", key="m_ed", use_container_width=True)
    col_a, col_b = st.columns(2)
    st.session_state.boxes_df = col_a.data_editor(st.session_state.boxes_df, num_rows="dynamic", key="b_ed", use_container_width=True)
    st.session_state.pallets_df = col_b.data_editor(st.session_state.pallets_df, num_rows="dynamic", key="p_ed", use_container_width=True)
    st.subheader("Custom Trucks")
    st.session_state.custom_trucks_df = st.data_editor(st.session_state.custom_trucks_df, num_rows="dynamic", key="t_ed", use_container_width=True)

elif page == T["nav_orders"]:
    st.header(T["nav_orders"])
    up_o = st.file_uploader("Upload Orders Excel", type="xlsx")
    if up_o: st.session_state.orders_df = pd.read_excel(up_o)
    st.session_state.orders_df = st.data_editor(st.session_state.orders_df, num_rows="dynamic", use_container_width=True)

elif page == T["nav_calc"]:
    st.header(T["nav_calc"])
    if st.session_state.orders_df.empty: st.warning("No data."); st.stop()

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        truck_list = list(TRANSPORT_PRESETS.keys()) + st.session_state.custom_trucks_df['Naam'].tolist()
        sel_t = col1.selectbox(T["truck_select"], truck_list)
        sel_p = col2.selectbox(T["pals"], st.session_state.pallets_df['Naam'].tolist())
        box_strat = col3.selectbox(T["box_strat"], ["Automatisch", "Vaste Doos"])
        
        c_opt1, c_opt2, c_opt3 = st.columns(3)
        m_item = c_opt1.toggle(T["opt_mixed_items"], True)
        sep_ord = c_opt2.toggle(T["opt_separate"], False)

    if st.button(T["btn_calc"]):
        t_info = TRANSPORT_PRESETS[sel_t] if sel_t in TRANSPORT_PRESETS else st.session_state.custom_trucks_df[st.session_state.custom_trucks_df['Naam'] == sel_t].iloc[0].to_dict()
        p_info = st.session_state.pallets_df[st.session_state.pallets_df['Naam'] == sel_p].iloc[0]
        full_df = st.session_state.orders_df.merge(st.session_state.master_data_df, on="ItemNr")
        
        calc_groups = full_df.groupby('OrderNr') if sep_ord else [("Total", full_df)]

        for name, group in calc_groups:
            # Doos berekening
            box_name, box_weight = bepaal_optimale_doos(group, st.session_state.boxes_df) if box_strat == "Automatisch" else (st.session_state.boxes_df.iloc[0]['Naam'], st.session_state.boxes_df.iloc[0]['Gewicht'])
            
            # Pallet berekening
            tot_vol = (group['Lengte'] * group['Breedte'] * group['Hoogte'] * group['Aantal']).sum() * 1.15
            p_cap = p_info['Lengte'] * p_info['Breedte'] * (p_info['MaxHoogte'] - p_info['PalletHoogte'])
            pals = math.ceil(tot_vol / p_cap)
            
            # GEWICHT CORRECTIE (Items + Dozen + Pallets)
            t_kg = (group['Gewicht'] * group['Aantal']).sum() + (pals * p_info['Gewicht']) + (group['Aantal'] * box_weight)
            
            # LAADMETERS & TRUCKS (Rekening houdend met Stapelbaarheid uit pallet tabel)
            lm_pals = math.ceil(pals / 2) if p_info['PalletStapelbaar'] else pals
            lm = (lm_pals / 2) * (p_info['Lengte'] / 100)
            trucks = math.ceil(lm / (t_info['Lengte']/100))

            st.subheader(f"📦 Order: {name}")
            res = st.columns(4)
            res[0].metric(T["pals"], f"{pals} LP")
            res[1].metric(T["weight"], f"{t_kg:.0f} KG")
            res[2].metric(T["meters"], f"{lm:.2f} m")
            res[3].metric(T["trucks"], f"{trucks}")
            
            # PDF Download link
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16); pdf.cell(200, 10, f"Rapport: {name}", ln=True)
            pdf.set_font("Arial", '', 12); pdf.cell(200, 10, f"Truck: {sel_t} | {T['pals']}: {pals}", ln=True)
            st.download_button(f"📄 PDF {name}", pdf.output(dest='S').encode('latin-1'), f"{name}.pdf")
            st.divider()
