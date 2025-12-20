import streamlit as st
import pandas as pd
import math, io
from fpdf import FPDF

# =========================================================
# 1. PAGE CONFIG & THEMA
# =========================================================
st.set_page_config(page_title="PLEKSEL PRO", page_icon="🚛", layout="wide")

LANGS = {
    "NL": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Pallet/Truck berekening",
        "btn_calc": "Bereken Planning", "pals": "Pallets", "weight": "Totaal Gewicht (KG)", 
        "meters": "Laadmeters", "num_trucks": "Trucks Nodig", "warn_orders": "Voeg eerst orders toe!",
        "opt_stack": "Pallets stapelbaar?", "opt_mix_box": "Meerdere soorten dozen toestaan?",
        "opt_mixed_items": "Mixed items in dozen toestaan?", "opt_separate": "Orders apart berekenen?",
        "btn_pdf": "📄 Download PDF", "header_results": "📊 Berekeningsresultaten"
    },
    "EN": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Pallet/Truck calculation",
        "btn_calc": "Calculate Planning", "pals": "Pallets", "weight": "Total Weight (KG)", 
        "meters": "Loading Meters", "num_trucks": "Trucks Needed", "warn_orders": "Add orders first!",
        "opt_stack": "Pallets stackable?", "opt_mix_box": "Allow multiple box types?",
        "opt_mixed_items": "Allow mixed items in boxes?", "opt_separate": "Calculate orders separately?",
        "btn_pdf": "📄 Download PDF", "header_results": "📊 Calculation Results"
    }
}

st.sidebar.title("Instellingen / Settings")
lang_choice = st.sidebar.selectbox("Language", ["NL", "EN"])
T = LANGS[lang_choice]

# =========================================================
# 2. DATA INITIALISATIE
# =========================================================
MASTER_COLS = {"ItemNr": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
BOXES_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "Gewicht": float}
PALLETS_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "MaxHoogte": float, "Gewicht": float, "PalletHoogte": float, "PalletStapelbaar": bool}

for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("orders_df", {"OrderNr": str, "ItemNr": str, "Aantal": int})]:
    if key not in st.session_state: st.session_state[key] = pd.DataFrame(columns=cols.keys())

# =========================================================
# 3. CORE LOGICA (GEWICHT & VERPAKKING)
# =========================================================
def bereken_verpakking(df_items, boxes_df, allow_mix_box, allow_mixed_items):
    if boxes_df.empty: return [{"Box": "Geen", "Aantal": 0, "Gewicht": 0}]
    
    sorted_boxes = boxes_df.copy()
    sorted_boxes['vol'] = sorted_boxes['Lengte'] * sorted_boxes['Breedte'] * sorted_boxes['Hoogte']
    sorted_boxes = sorted_boxes.sort_values('vol', ascending=False)
    
    verpakkings_resultaat = []
    
    # Als we geen mixed items willen, groeperen we per item
    groups = [df_items] if allow_mixed_items else [df_items[df_items['ItemNr'] == i] for i in df_items['ItemNr'].unique()]
    
    for group in groups:
        totaal_vol = (group['Lengte'] * group['Breedte'] * group['Hoogte'] * group['Aantal']).sum() * 1.15
        
        if not allow_mix_box:
            # Gebruik alleen de best passende enkele doossoort
            best_box = sorted_boxes[sorted_boxes['vol'] >= (totaal_vol / group['Aantal'].sum())].iloc[-1] if not sorted_boxes.empty else sorted_boxes.iloc[0]
            aantal_dozen = math.ceil(totaal_vol / best_box['vol'])
            verpakkings_resultaat.append({"Box": best_box['Naam'], "Aantal": aantal_dozen, "Gewicht": best_box['Gewicht'] * aantal_dozen})
        else:
            # Mix van dozen (vul eerst de grootste)
            overgebleven_vol = totaal_vol
            for _, box in sorted_boxes.iterrows():
                if overgebleven_vol <= 0: break
                aantal = int(overgebleven_vol // box['vol'])
                if aantal > 0:
                    verpakkings_resultaat.append({"Box": box['Naam'], "Aantal": aantal, "Gewicht": box['Gewicht'] * aantal})
                    overgebleven_vol -= (aantal * box['vol'])
            if overgebleven_vol > 0: # Restant in kleinste doos
                small_box = sorted_boxes.iloc[-1]
                verpakkings_resultaat.append({"Box": small_box['Naam'], "Aantal": 1, "Gewicht": small_box['Gewicht']})
                
    return verpakkings_resultaat

# =========================================================
# 4. UI
# =========================================================
st.markdown(f"<h1>PLEKSEL 🚛</h1>", unsafe_allow_html=True)
page = st.sidebar.radio("Menu", [T["nav_templates"], T["nav_orders"], T["nav_calc"]])

if page == T["nav_templates"]:
    st.header(T["nav_templates"])
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", key="m1")
    st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", key="b1")
    st.session_state.pallets_df = st.data_editor(st.session_state.pallets_df, num_rows="dynamic", key="p1")

elif page == T["nav_orders"]:
    st.header(T["nav_orders"])
    st.session_state.orders_df = st.data_editor(st.session_state.orders_df, num_rows="dynamic", key="o1")

elif page == T["nav_calc"]:
    st.header(T["nav_calc"])
    
    with st.expander("⚙️ Logistieke Parameters", expanded=True):
        col1, col2, col3 = st.columns(3)
        allow_mix_box = col1.toggle(T["opt_mix_box"], value=False)
        allow_mixed_items = col2.toggle(T["opt_mixed_items"], value=True)
        separate_orders = col3.toggle(T["opt_separate"], value=False)
        
        sel_p_name = st.selectbox("Kies Pallet Type", st.session_state.pallets_df['Naam'].unique())
        p_info = st.session_state.pallets_df[st.session_state.pallets_df['Naam'] == sel_p_name].iloc[0]

    if st.button(T["btn_calc"]):
        orders = st.session_state.orders_df.merge(st.session_state.master_data_df, on="ItemNr")
        
        # Groeperen op basis van 'apart berekenen'
        calc_groups = orders.groupby('OrderNr') if separate_orders else [("Gecombineerd", orders)]
        
        for name, group in calc_groups:
            st.subheader(f"Resultaat: {name}")
            
            # 1. Verpakking
            verpakking = bereken_verpakking(group, st.session_state.boxes_df, allow_mix_box, allow_mixed_items)
            extra_gewicht_verpakking = sum(v['Gewicht'] for v in verpakking)
            
            # 2. Palletisering (Schatting op basis van volume en stapelbaarheid)
            item_vol = (group['Lengte'] * group['Breedte'] * group['Hoogte'] * group['Aantal']).sum()
            pallet_vol_cap = p_info['Lengte'] * p_info['Breedte'] * (p_info['MaxHoogte'] - p_info['PalletHoogte'])
            
            aantal_pals = math.ceil(item_vol / pallet_vol_cap)
            
            # Check stapelbaarheid uit template
            is_stapelbaar = p_info['PalletStapelbaar']
            laadmeters_pals = aantal_pals if not is_stapelbaar else math.ceil(aantal_pals / 2)
            laadmeters = (laadmeters_pals * p_row['Lengte'] if 'p_row' in locals() else laadmeters_pals * p_info['Lengte']) / 240 # Simpele LM berekening
            
            # 3. Totaal Gewicht (ZEER BELANGRIJK)
            netto_gewicht_items = (group['Gewicht'] * group['Aantal']).sum()
            totaal_gewicht = netto_gewicht_items + extra_gewicht_verpakking + (aantal_pals * p_info['Gewicht'])
            
            # UI Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric(T["pals"], f"{aantal_pals} LP")
            m2.metric(T["weight"], f"{totaal_gewicht:.2f} kg")
            m3.metric(T["meters"], f"{max(0.4, laadmeters):.2f} m")
            
            # Doos detail
            st.write("**Geadviseerde Verpakking:**")
            st.table(pd.DataFrame(verpakking))
            
            # PDF Per Resultaat
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, f"Rapport: {name}", ln=True)
            pdf.set_font("Arial", '', 12)
            pdf.cell(200, 10, f"Totaal Gewicht: {totaal_gewicht:.2f} kg", ln=True)
            pdf.cell(200, 10, f"Pallets: {aantal_pals}", ln=True)
            st.download_button(f"📥 Download PDF {name}", pdf.output(dest='S').encode('latin-1'), f"Rapport_{name}.pdf")
            st.divider()
