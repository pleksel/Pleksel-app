import streamlit as st
import pandas as pd
import math, io, os, shutil
from fpdf import FPDF

# =========================================================
# 1. CONFIG & THEMA
# =========================================================
st.set_page_config(page_title="PLEKSEL PRO", page_icon="🚛", layout="wide")

# Map voor templates
TEMPLATE_DIR = "pleksel_templates"
if not os.path.exists(TEMPLATE_DIR):
    os.makedirs(TEMPLATE_DIR)

LANGS = {
    "NL": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Pallet/Truck berekening",
        "btn_calc": "Bereken Planning", "pals": "Pallets", "weight": "Totaal Gewicht (KG)", 
        "meters": "Laadmeters", "num_trucks": "Trucks Nodig", "warn_orders": "Voeg eerst orders toe!",
        "opt_stack": "Pallets stapelbaar?", "opt_mix_box": "Meerdere soorten dozen toestaan?",
        "opt_mixed_items": "Mixed items in dozen toestaan?", "opt_separate": "Orders apart berekenen?",
        "btn_pdf": "📄 Download PDF", "header_results": "📊 Resultaten", "save_btn": "💾 Opslaan", "load_btn": "📂 Laden"
    },
    "EN": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Pallet/Truck calculation",
        "btn_calc": "Calculate Planning", "pals": "Pallets", "weight": "Total Weight (KG)", 
        "meters": "Loading Meters", "num_trucks": "Trucks Needed", "warn_orders": "Add orders first!",
        "opt_stack": "Pallets stackable?", "opt_mix_box": "Allow multiple box types?",
        "opt_mixed_items": "Allow mixed items in boxes?", "opt_separate": "Calculate orders separately?",
        "btn_pdf": "📄 Download PDF", "header_results": "📊 Results", "save_btn": "💾 Save", "load_btn": "📂 Load"
    }
}

st.sidebar.title("Instellingen")
lang_choice = st.sidebar.selectbox("Taal / Language", ["NL", "EN"])
T = LANGS[lang_choice]

# =========================================================
# 2. DATA FUNCTIES
# =========================================================
MASTER_COLS = {"ItemNr": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
BOXES_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
PALLETS_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "MaxHoogte": float, "Gewicht": float, "PalletHoogte": float, "PalletStapelbaar": bool}
ORDERS_COLS = {"OrderNr": str, "ItemNr": str, "Aantal": int}

def enforce_dtypes(df, dtypes):
    if df is None or df.empty: return pd.DataFrame(columns=dtypes.keys())
    for col, dtype in dtypes.items():
        if col in df.columns:
            if dtype in (float, int): df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df[list(dtypes.keys())]

for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("orders_df", ORDERS_COLS)]:
    if key not in st.session_state: st.session_state[key] = pd.DataFrame(columns=cols.keys())

# =========================================================
# 3. TEMPLATE BEHEER
# =========================================================
def save_template(name):
    path = os.path.join(TEMPLATE_DIR, name)
    if not os.path.exists(path): os.makedirs(path)
    with pd.ExcelWriter(os.path.join(path, "config.xlsx")) as writer:
        st.session_state.master_data_df.to_excel(writer, sheet_name="Master", index=False)
        st.session_state.boxes_df.to_excel(writer, sheet_name="Boxes", index=False)
        st.session_state.pallets_df.to_excel(writer, sheet_name="Pallets", index=False)
    st.success(f"Template '{name}' opgeslagen!")

def load_template(name):
    path = os.path.join(TEMPLATE_DIR, name, "config.xlsx")
    if os.path.exists(path):
        xls = pd.ExcelFile(path)
        st.session_state.master_data_df = enforce_dtypes(pd.read_excel(xls, "Master"), MASTER_COLS)
        st.session_state.boxes_df = enforce_dtypes(pd.read_excel(xls, "Boxes"), BOXES_COLS)
        st.session_state.pallets_df = enforce_dtypes(pd.read_excel(xls, "Pallets"), PALLETS_COLS)
        st.rerun()

# =========================================================
# 4. REKEN LOGICA
# =========================================================
def bereken_verpakking(df_items, boxes_df, allow_mix_box, allow_mixed_items):
    if boxes_df.empty: return []
    sorted_boxes = boxes_df.copy()
    sorted_boxes['vol'] = sorted_boxes['Lengte'] * sorted_boxes['Breedte'] * sorted_boxes['Hoogte']
    sorted_boxes = sorted_boxes.sort_values('vol', ascending=False)
    
    verpakking_lijst = []
    
    # Stap 1: Bepaal groepen (Mixed of Apart)
    if allow_mixed_items:
        groups = [df_items]
    else:
        groups = [df_items[df_items['ItemNr'] == i] for i in df_items['ItemNr'].unique()]

    for group in groups:
        totaal_vol_items = (group['Lengte'] * group['Breedte'] * group['Hoogte'] * group['Aantal']).sum() * 1.15
        
        if not allow_mix_box:
            # Zoek de kleinste doos waar het volume in past
            possible = sorted_boxes[sorted_boxes['vol'] >= (totaal_vol_items / group['Aantal'].sum())]
            best_box = possible.iloc[-1] if not possible.empty else sorted_boxes.iloc[0]
            aantal = math.ceil(totaal_vol_items / best_box['vol'])
            verpakking_lijst.append({"Box": best_box['Naam'], "Aantal": aantal, "Gewicht": best_box['Gewicht'] * aantal})
        else:
            # Mix van dozen: Vul eerst de grootste dozen
            overgebleven_vol = totaal_vol_items
            for _, box in sorted_boxes.iterrows():
                aantal = int(overgebleven_vol // box['vol'])
                if aantal > 0:
                    verpakking_lijst.append({"Box": box['Naam'], "Aantal": aantal, "Gewicht": box['Gewicht'] * aantal})
                    overgebleven_vol -= (aantal * box['vol'])
            if overgebleven_vol > 0:
                last_box = sorted_boxes.iloc[-1]
                verpakking_lijst.append({"Box": last_box['Naam'], "Aantal": 1, "Gewicht": last_box['Gewicht']})
                
    return verpakking_lijst

# =========================================================
# 5. UI LAYOUT
# =========================================================
st.markdown("<h1>PLEKSEL PRO 🚛</h1>", unsafe_allow_html=True)
page = st.sidebar.radio("Navigatie", [T["nav_templates"], T["nav_orders"], T["nav_calc"]])

if page == T["nav_templates"]:
    st.header(T["nav_templates"])
    
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            all_t = [f for f in os.listdir(TEMPLATE_DIR) if os.path.isdir(os.path.join(TEMPLATE_DIR, f))]
            sel = st.selectbox("Selecteer Template", [""] + all_t)
            if sel and st.button(T["load_btn"]): load_template(sel)
        with c2:
            new_t = st.text_input("Nieuwe Template Naam")
            if st.button(T["save_btn"]): save_template(new_t)
        with c3:
            if sel and st.button("🗑️ Wis"): 
                shutil.rmtree(os.path.join(TEMPLATE_DIR, sel))
                st.rerun()

    st.subheader(T["master_data"])
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", key="m_edit")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader(T["boxes"])
        st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", key="b_edit")
    with col_b:
        st.subheader("🟫 Pallets (CM)")
        st.session_state.pallets_df = st.data_editor(st.session_state.pallets_df, num_rows="dynamic", key="p_edit")

elif page == T["nav_orders"]:
    st.header(T["nav_orders"])
    st.session_state.orders_df = st.data_editor(st.session_state.orders_df, num_rows="dynamic", key="o_edit")

elif page == T["nav_calc"]:
    st.header(T["nav_calc"])
    if st.session_state.orders_df.empty: st.warning(T["warn_orders"]); st.stop()

    with st.expander("⚙️ Logistieke Instellingen", expanded=True):
        c1, c2 = st.columns(2)
        allow_mix_box = c1.toggle(T["opt_mix_box"], value=False)
        allow_mixed_items = c2.toggle(T["opt_mixed_items"], value=True)
        separate_orders = c1.toggle(T["opt_separate"], value=False)
        
        sel_p = st.selectbox("Kies Pallet", st.session_state.pallets_df['Naam'].unique())
        p_row = st.session_state.pallets_df[st.session_state.pallets_df['Naam'] == sel_p].iloc[0]

    if st.button(T["btn_calc"]):
        full_df = st.session_state.orders_df.merge(st.session_state.master_data_df, on="ItemNr")
        groups = full_df.groupby('OrderNr') if separate_orders else [("Totaal", full_df)]

        for name, group in groups:
            st.subheader(f"📦 Order: {name}")
            
            # 1. Verpakking & Gewicht
            verpakking = bereken_verpakking(group, st.session_state.boxes_df, allow_mix_box, allow_mixed_items)
            verp_gewicht = sum(v['Gewicht'] for v in verpakking)
            item_gewicht = (group['Gewicht'] * group['Aantal']).sum()
            
            # 2. Pallets
            tot_vol = (group['Lengte'] * group['Breedte'] * group['Hoogte'] * group['Aantal']).sum()
            pal_cap = p_row['Lengte'] * p_row['Breedte'] * (p_row['MaxHoogte'] - p_row['PalletHoogte'])
            aantal_pals = math.ceil(tot_vol / (pal_cap * 0.85)) # 85% vullingsgraad
            
            totaal_gewicht = item_gewicht + verp_gewicht + (aantal_pals * p_row['Gewicht'])
            
            # 3. Laadmeters
            if p_row['PalletStapelbaar']:
                laad_pals = math.ceil(aantal_pals / 2) # Per 2 pallets op elkaar
            else:
                laad_pals = aantal_pals
            
            # We gaan uit van 2 pallets breed in een truck (80cm of 100cm/120cm)
            lm = (laad_pals / 2) * (p_row['Lengte'] / 100)

            res = st.columns(3)
            res[0].metric(T["pals"], f"{aantal_pals} LP")
            res[1].metric(T["weight"], f"{totaal_gewicht:.1f} KG")
            res[2].metric(T["meters"], f"{lm:.2f} m")
            
            st.write("**Verpakkingsdetails:**")
            st.dataframe(pd.DataFrame(verpakking), hide_index=True)
            
            # PDF Genereren
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16); pdf.cell(200, 10, f"Rapport: {name}", ln=True)
            pdf.set_font("Arial", '', 12); pdf.cell(200, 10, f"Gewicht: {totaal_gewicht:.1f} KG | Pallets: {aantal_pals}", ln=True)
            st.download_button(f"📄 Download PDF {name}", pdf.output(dest='S').encode('latin-1'), f"Rapport_{name}.pdf")
            st.divider()
