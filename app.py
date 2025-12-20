import streamlit as st
import pandas as pd
import math, io, os, shutil
from fpdf import FPDF

# =========================================================
# 1. CONFIG & THEMA
# =========================================================
st.set_page_config(page_title="PLEKSEL PRO", page_icon="🚛", layout="wide")

# Veilig de template map aanmaken
TEMPLATE_DIR = "pleksel_templates"
os.makedirs(TEMPLATE_DIR, exist_ok=True)

LANGS = {
    "NL": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Pallet/Truck berekening",
        "btn_calc": "Bereken Planning", "pals": "Pallets", "weight": "Totaal Gewicht (KG)", 
        "meters": "Laadmeters", "num_trucks": "Trucks Nodig", "warn_orders": "Voeg eerst orders toe!",
        "opt_stack": "Stapelbaar?", "opt_mix_box": "Mix dozen?", "opt_mixed_items": "Mixed items in doos?", 
        "opt_separate": "Orders apart?", "save_btn": "💾 Opslaan", "load_btn": "📂 Laden"
    },
    "EN": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Pallet/Truck calculation",
        "btn_calc": "Calculate Planning", "pals": "Pallets", "weight": "Total Weight (KG)", 
        "meters": "Loading Meters", "num_trucks": "Trucks Needed", "warn_orders": "Add orders first!",
        "opt_stack": "Stackable?", "opt_mix_box": "Mix boxes?", "opt_mixed_items": "Mixed items in box?", 
        "opt_separate": "Separate orders?", "save_btn": "💾 Save", "load_btn": "📂 Load"
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

# Initialiseer session state
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
    # Groeperen op basis van mixed items optie
    item_groups = [df_items] if allow_mixed_items else [df_items[df_items['ItemNr'] == i] for i in df_items['ItemNr'].unique()]

    for group in item_groups:
        totaal_vol = (group['Lengte'] * group['Breedte'] * group['Hoogte'] * group['Aantal']).sum() * 1.15 # 15% lucht
        
        if not allow_mix_box:
            # Gebruik 1 soort doos (de kleinste waar alles in past of meerdere van de grootste)
            best_box = boxes[boxes['vol'] >= (totaal_vol / group['Aantal'].sum())].iloc[-1] if not boxes[boxes['vol'] >= (totaal_vol / group['Aantal'].sum())].empty else boxes.iloc[0]
            aantal = math.ceil(totaal_vol / best_box['vol'])
            result.append({"Box": best_box['Naam'], "Aantal": aantal, "Gewicht": best_box['Gewicht'] * aantal})
        else:
            # Mix van dozen
            rem_vol = totaal_vol
            for _, b in boxes.iterrows():
                cnt = int(rem_vol // b['vol'])
                if cnt > 0:
                    result.append({"Box": b['Naam'], "Aantal": cnt, "Gewicht": b['Gewicht'] * cnt})
                    rem_vol -= (cnt * b['vol'])
            if rem_vol > 0:
                result.append({"Box": boxes.iloc[-1]['Naam'], "Aantal": 1, "Gewicht": boxes.iloc[-1]['Gewicht']})
    return result

def genereer_pdf(name, gewicht, pals, lm, items_df, verp_lijst):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"Pallet/Truck Rapport: {name}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, f"Totaal Gewicht: {gewicht:.1f} KG", ln=True)
    pdf.cell(200, 10, f"Aantal Pallets: {pals} | Laadmeters: {lm:.2f} m", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(200, 10, "Artikelen op deze zending:", ln=True)
    pdf.set_font("Arial", '', 10)
    for _, r in items_df.iterrows():
        pdf.cell(200, 8, f"- {r['ItemNr']}: {r['Aantal']} stuks", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12); pdf.cell(200, 10, "Verpakkingsadvies (Dozen):", ln=True)
    pdf.set_font("Arial", '', 10)
    for v in verp_lijst:
        pdf.cell(200, 8, f"- {v['Aantal']}x {v['Box']} (Totaal {v['Gewicht']:.1f} kg)", ln=True)
    
    return pdf.output(dest='S').encode('latin-1')

# =========================================================
# 3. UI
# =========================================================
page = st.sidebar.radio("Navigatie", [T["nav_templates"], T["nav_orders"], T["nav_calc"]])

if page == T["nav_templates"]:
    st.header(T["nav_templates"])
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            all_t = [f for f in os.listdir(TEMPLATE_DIR) if os.path.isdir(os.path.join(TEMPLATE_DIR, f))]
            sel = st.selectbox("Template", [""] + all_t)
            if sel and st.button(T["load_btn"]):
                xls = pd.ExcelFile(os.path.join(TEMPLATE_DIR, sel, "config.xlsx"))
                st.session_state.master_data_df = pd.read_excel(xls, "Master")
                st.session_state.boxes_df = pd.read_excel(xls, "Boxes")
                st.session_state.pallets_df = pd.read_excel(xls, "Pallets")
                st.rerun()
        with c2:
            new_t = st.text_input("Naam")
            if st.button(T["save_btn"]) and new_t:
                p = os.path.join(TEMPLATE_DIR, new_t)
                os.makedirs(p, exist_ok=True)
                with pd.ExcelWriter(os.path.join(p, "config.xlsx")) as w:
                    st.session_state.master_data_df.to_excel(w, sheet_name="Master", index=False)
                    st.session_state.boxes_df.to_excel(w, sheet_name="Boxes", index=False)
                    st.session_state.pallets_df.to_excel(w, sheet_name="Pallets", index=False)
                st.success("Opgeslagen!")
        with c3:
            if sel and st.button("🗑️"): shutil.rmtree(os.path.join(TEMPLATE_DIR, sel)); st.rerun()

    st.subheader("Data Editor")
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", use_container_width=True)
    c_a, c_b = st.columns(2)
    st.session_state.boxes_df = c_a.data_editor(st.session_state.boxes_df, num_rows="dynamic", use_container_width=True, key="b")
    st.session_state.pallets_df = c_b.data_editor(st.session_state.pallets_df, num_rows="dynamic", use_container_width=True, key="p")

elif page == T["nav_orders"]:
    st.header(T["nav_orders"])
    st.session_state.orders_df = st.data_editor(st.session_state.orders_df, num_rows="dynamic", use_container_width=True)

elif page == T["nav_calc"]:
    st.header("🚛 Pallet/Truck berekening")
    if st.session_state.orders_df.empty: st.stop()

    with st.expander("Opties", expanded=True):
        col1, col2 = st.columns(2)
        m_box = col1.toggle(T["opt_mix_box"], False)
        m_item = col2.toggle(T["opt_mixed_items"], True)
        sep = col1.toggle(T["opt_separate"], False)
        sel_p = st.selectbox("Pallet", st.session_state.pallets_df['Naam'].unique())
    
    if st.button(T["btn_calc"]):
        p_info = st.session_state.pallets_df[st.session_state.pallets_df['Naam'] == sel_p].iloc[0]
        full = st.session_state.orders_df.merge(st.session_state.master_data_df, on="ItemNr")
        groups = full.groupby('OrderNr') if sep else [("Zending", full)]

        for name, group in groups:
            verp = bereken_verpakking(group, st.session_state.boxes_df, m_box, m_item)
            v_kg = sum(v['Gewicht'] for v in verp)
            i_kg = (group['Gewicht'] * group['Aantal']).sum()
            
            vol = (group['Lengte'] * group['Breedte'] * group['Hoogte'] * group['Aantal']).sum()
            cap = p_info['Lengte'] * p_info['Breedte'] * (p_info['MaxHoogte'] - p_info['PalletHoogte'])
            pals = math.ceil(vol / (cap * 0.85))
            
            t_kg = i_kg + v_kg + (pals * p_info['Gewicht'])
            lm_pals = math.ceil(pals / 2) if p_info['PalletStapelbaar'] else pals
            lm = (lm_pals / 2) * (p_info['Lengte'] / 100)

            st.subheader(f"📦 {name}")
            m = st.columns(3)
            m[0].metric(T["pals"], f"{pals} LP")
            m[1].metric(T["weight"], f"{t_kg:.1f} KG")
            m[2].metric(T["meters"], f"{lm:.2f} m")
            
            st.download_button(f"📄 PDF {name}", genereer_pdf(name, t_kg, pals, lm, group, verp), f"{name}.pdf")
            st.divider()
