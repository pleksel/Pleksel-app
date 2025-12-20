import streamlit as st
import pandas as pd
import math, io, os, shutil
from fpdf import FPDF

# =========================================================
# 1. CONFIG & THEMA
# =========================================================
st.set_page_config(page_title="PLEKSEL PRO", page_icon="🚛", layout="wide")

TEMPLATE_DIR = "pleksel_templates"
os.makedirs(TEMPLATE_DIR, exist_ok=True)

LANGS = {
    "NL": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Pallet/Truck berekening",
        "btn_calc": "Bereken Planning", "pals": "Pallets", "weight": "Totaal Gewicht (KG)", 
        "meters": "Laadmeters", "warn_orders": "Voeg eerst orders toe!",
        "opt_stack": "Pallets stapelbaar?", "opt_mix_box": "Meerdere soorten dozen?",
        "opt_mixed_items": "Mixed items in doos?", "opt_separate": "Orders apart?",
        "save_btn": "💾 Opslaan in systeem", "load_btn": "📂 Laden uit systeem", "upload_header": "📤 Excel Bestand Uploaden"
    },
    "EN": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Pallet/Truck calculation",
        "btn_calc": "Calculate Planning", "pals": "Pallets", "weight": "Total Weight (KG)", 
        "meters": "Loading Meters", "warn_orders": "Add orders first!",
        "opt_stack": "Stackable?", "opt_mix_box": "Multiple box types?",
        "opt_mixed_items": "Mixed items in box?", "opt_separate": "Separate orders?",
        "save_btn": "💾 Save to system", "load_btn": "📂 Load from system", "upload_header": "📤 Upload Excel File"
    }
}

st.sidebar.title("Instellingen")
lang_choice = st.sidebar.selectbox("Taal / Language", ["NL", "EN"])
T = LANGS[lang_choice]

# Kolomdefinities
MASTER_COLS = {"ItemNr": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
BOXES_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
PALLETS_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "MaxHoogte": float, "Gewicht": float, "PalletHoogte": float, "PalletStapelbaar": bool}
ORDERS_COLS = {"OrderNr": str, "ItemNr": str, "Aantal": int}

for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("orders_df", ORDERS_COLS)]:
    if key not in st.session_state: st.session_state[key] = pd.DataFrame(columns=cols.keys())

# =========================================================
# 2. LOGICA: VERPAKKING & PDF
# =========================================================

def bereken_verpakking(df_items, boxes_df, allow_mix_box, allow_mixed_items):
    if boxes_df.empty: return []
    boxes = boxes_df.copy()
    boxes['vol'] = boxes['Lengte'] * boxes['Breedte'] * boxes['Hoogte']
    boxes = boxes.sort_values('vol', ascending=False)
    
    result = []
    item_groups = [df_items] if allow_mixed_items else [df_items[df_items['ItemNr'] == i] for i in df_items['ItemNr'].unique()]

    for group in item_groups:
        totaal_vol = (group['Lengte'] * group['Breedte'] * group['Hoogte'] * group['Aantal']).sum() * 1.15
        if not allow_mix_box:
            possible = boxes[boxes['vol'] >= (totaal_vol / group['Aantal'].sum())]
            best_box = possible.iloc[-1] if not possible.empty else boxes.iloc[0]
            aantal = math.ceil(totaal_vol / best_box['vol'])
            result.append({"Box": best_box['Naam'], "Aantal": aantal, "Gewicht": best_box['Gewicht'] * aantal})
        else:
            rem_vol = totaal_vol
            for _, b in boxes.iterrows():
                cnt = int(rem_vol // b['vol'])
                if cnt > 0:
                    result.append({"Box": b['Naam'], "Aantal": cnt, "Gewicht": b['Gewicht'] * cnt})
                    rem_vol -= (cnt * b['vol'])
            if rem_vol > 0:
                result.append({"Box": boxes.iloc[-1]['Naam'], "Aantal": 1, "Gewicht": boxes.iloc[-1]['Gewicht']})
    return result

# =========================================================
# 3. UI - TEMPLATES & UPLOAD
# =========================================================
page = st.sidebar.radio("Navigatie", [T["nav_templates"], T["nav_orders"], T["nav_calc"]])

if page == T["nav_templates"]:
    st.header(T["nav_templates"])
    
    # SECTIE 1: BESTAND UPLOADEN (Direct van computer)
    with st.expander(T["upload_header"], expanded=True):
        uploaded_file = st.file_uploader("Kies een Excel bestand (.xlsx)", type="xlsx")
        if uploaded_file:
            xls = pd.ExcelFile(uploaded_file)
            if "Master" in xls.sheet_names: st.session_state.master_data_df = pd.read_excel(xls, "Master")
            if "Boxes" in xls.sheet_names: st.session_state.boxes_df = pd.read_excel(xls, "Boxes")
            if "Pallets" in xls.sheet_names: st.session_state.pallets_df = pd.read_excel(xls, "Pallets")
            st.success("Bestand succesvol geüpload!")

    # SECTIE 2: INTERN OPSLAAN / LADEN
    with st.container(border=True):
        st.subheader("Systeemopslag")
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            all_t = [f for f in os.listdir(TEMPLATE_DIR) if os.path.isdir(os.path.join(TEMPLATE_DIR, f))]
            sel = st.selectbox("Kies uit lijst", [""] + all_t)
            if sel and st.button(T["load_btn"]):
                xls = pd.ExcelFile(os.path.join(TEMPLATE_DIR, sel, "config.xlsx"))
                st.session_state.master_data_df = pd.read_excel(xls, "Master")
                st.session_state.boxes_df = pd.read_excel(xls, "Boxes")
                st.session_state.pallets_df = pd.read_excel(xls, "Pallets")
                st.rerun()
        with c2:
            new_t = st.text_input("Nieuwe naam")
            if st.button(T["save_btn"]) and new_t:
                p = os.path.join(TEMPLATE_DIR, new_t)
                os.makedirs(p, exist_ok=True)
                with pd.ExcelWriter(os.path.join(p, "config.xlsx")) as w:
                    st.session_state.master_data_df.to_excel(w, sheet_name="Master", index=False)
                    st.session_state.boxes_df.to_excel(w, sheet_name="Boxes", index=False)
                    st.session_state.pallets_df.to_excel(w, sheet_name="Pallets", index=False)
                st.success("Opgeslagen!")
        with c3:
            if sel and st.button("🗑️ Wis"): shutil.rmtree(os.path.join(TEMPLATE_DIR, sel)); st.rerun()

    st.divider()
    st.subheader("Handmatige aanpassing")
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", use_container_width=True, key="ed_m")
    col_x, col_y = st.columns(2)
    st.session_state.boxes_df = col_x.data_editor(st.session_state.boxes_df, num_rows="dynamic", use_container_width=True, key="ed_b")
    st.session_state.pallets_df = col_y.data_editor(st.session_state.pallets_df, num_rows="dynamic", use_container_width=True, key="ed_p")

# =========================================================
# 4. UI - ORDERS & BEREKENING
# =========================================================
elif page == T["nav_orders"]:
    st.header(T["nav_orders"])
    up_orders = st.file_uploader("Upload Order Excel", type="xlsx")
    if up_orders:
        st.session_state.orders_df = pd.read_excel(up_orders)
    st.session_state.orders_df = st.data_editor(st.session_state.orders_df, num_rows="dynamic", use_container_width=True)

elif page == T["nav_calc"]:
    st.header(T["nav_calc"])
    if st.session_state.orders_df.empty: st.stop()

    with st.expander("Logistieke Opties", expanded=True):
        c1, c2 = st.columns(2)
        m_box = c1.toggle(T["opt_mix_box"], False)
        m_item = c2.toggle(T["opt_mixed_items"], True)
        sep = c1.toggle(T["opt_separate"], False)
        sel_p = st.selectbox("Pallet type", st.session_state.pallets_df['Naam'].unique() if not st.session_state.pallets_df.empty else ["Geen"])
    
    if st.button(T["btn_calc"]):
        p_info = st.session_state.pallets_df[st.session_state.pallets_df['Naam'] == sel_p].iloc[0]
        full = st.session_state.orders_df.merge(st.session_state.master_data_df, on="ItemNr")
        groups = full.groupby('OrderNr') if sep else [("Zending Totaal", full)]

        for name, group in groups:
            verp = bereken_verpakking(group, st.session_state.boxes_df, m_box, m_item)
            v_kg = sum(v['Gewicht'] for v in verp)
            i_kg = (group['Gewicht'] * group['Aantal']).sum()
            
            vol = (group['Lengte'] * group['Breedte'] * group['Hoogte'] * group['Aantal']).sum()
            cap = p_info['Lengte'] * p_info['Breedte'] * (p_info['MaxHoogte'] - p_info['PalletHoogte'])
            pals = math.ceil(vol / (cap * 0.85)) # 85% vullingsgraad
            
            t_kg = i_kg + v_kg + (pals * p_info['Gewicht'])
            
            # Laadmeters berekening met stapelbaarheid
            lm_pals = math.ceil(pals / 2) if p_info['PalletStapelbaar'] else pals
            lm = (lm_pals / 2) * (p_info['Lengte'] / 100)

            st.subheader(f"📦 Resultaat: {name}")
            m = st.columns(3)
            m[0].metric(T["pals"], f"{pals} LP")
            m[1].metric(T["weight"], f"{t_kg:.1f} KG")
            m[2].metric(T["meters"], f"{lm:.2f} m")
            
            # Verpakkingsdetails tonen
            st.table(pd.DataFrame(verp))
            st.divider()
