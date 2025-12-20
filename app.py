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

# Kolomdefinities voor de templates
MASTER_COLS = ["ItemNr", "Lengte", "Breedte", "Hoogte", "Gewicht"]
BOXES_COLS = ["Naam", "Lengte", "Breedte", "Hoogte", "Gewicht"]
PALLETS_COLS = ["Naam", "Lengte", "Breedte", "MaxHoogte", "Gewicht", "PalletHoogte", "PalletStapelbaar"]
ORDERS_COLS = ["OrderNr", "ItemNr", "Aantal"]

# Functie om een leeg Excel-bestand te maken
def create_empty_template():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame(columns=MASTER_COLS).to_excel(writer, sheet_name='Master', index=False)
        pd.DataFrame(columns=BOXES_COLS).to_excel(writer, sheet_name='Boxes', index=False)
        pd.DataFrame(columns=PALLETS_COLS).to_excel(writer, sheet_name='Pallets', index=False)
    return output.getvalue()

# Initialisatie session state
for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("orders_df", ORDERS_COLS)]:
    if key not in st.session_state:
        st.session_state[key] = pd.DataFrame(columns=cols if isinstance(cols, list) else cols.keys())

# ... (Rekenlogica en PDF-functies blijven gelijk aan vorige versie) ...

# =========================================================
# 2. UI - TEMPLATES & DOWNLOAD
# =========================================================
page = st.sidebar.radio("Navigatie", ["📁 Templates", "📑 Orders", "🚛 Pallet/Truck berekening"])

if page == "📁 Templates":
    st.header("📁 Template Beheer")
    
    # NIEUW: Download sectie voor de lege template
    with st.container(border=True):
        st.subheader("📥 Download Lege Basis Template")
        st.info("Gebruik dit bestand om je eigen data in te vullen en upload het daarna hieronder.")
        st.download_button(
            label="Download Lege Excel Template",
            data=create_empty_template(),
            file_name="pleksel_basis_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # SECTIE: BESTAND UPLOADEN
    with st.expander("📤 Excel Bestand Uploaden", expanded=True):
        uploaded_file = st.file_uploader("Kies je ingevulde Excel bestand", type="xlsx")
        if uploaded_file:
            xls = pd.ExcelFile(uploaded_file)
            if "Master" in xls.sheet_names: st.session_state.master_data_df = pd.read_excel(xls, "Master")
            if "Boxes" in xls.sheet_names: st.session_state.boxes_df = pd.read_excel(xls, "Boxes")
            if "Pallets" in xls.sheet_names: st.session_state.pallets_df = pd.read_excel(xls, "Pallets")
            st.success("Data succesvol ingeladen!")

    # SECTIE: INTERN OPSLAAN / LADEN (System opslag)
    st.subheader("💾 Systeemopslag")
    c1, c2 = st.columns(2)
    with c1:
        all_t = [f for f in os.listdir(TEMPLATE_DIR) if os.path.isdir(os.path.join(TEMPLATE_DIR, f))]
        sel = st.selectbox("Kies uit systeem", [""] + all_t)
        if sel and st.button("📂 Laden"):
            xls = pd.ExcelFile(os.path.join(TEMPLATE_DIR, sel, "config.xlsx"))
            st.session_state.master_data_df = pd.read_excel(xls, "Master")
            st.session_state.boxes_df = pd.read_excel(xls, "Boxes")
            st.session_state.pallets_df = pd.read_excel(xls, "Pallets")
            st.rerun()
    with c2:
        new_t = st.text_input("Opslaan als nieuwe template")
        if st.button("💾 Opslaan") and new_t:
            p = os.path.join(TEMPLATE_DIR, new_t)
            os.makedirs(p, exist_ok=True)
            with pd.ExcelWriter(os.path.join(p, "config.xlsx")) as w:
                st.session_state.master_data_df.to_excel(w, sheet_name="Master", index=False)
                st.session_state.boxes_df.to_excel(w, sheet_name="Boxes", index=False)
                st.session_state.pallets_df.to_excel(w, sheet_name="Pallets", index=False)
            st.success(f"'{new_t}' is opgeslagen in het systeem!")

    st.divider()
    st.subheader("Handmatige aanpassing")
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", use_container_width=True, key="ed_m")
    col_x, col_y = st.columns(2)
    st.session_state.boxes_df = col_x.data_editor(st.session_state.boxes_df, num_rows="dynamic", use_container_width=True, key="ed_b")
    st.session_state.pallets_df = col_y.data_editor(st.session_state.pallets_df, num_rows="dynamic", use_container_width=True, key="ed_p")

# ... (Rest van de code voor Orders en Berekening) ...
