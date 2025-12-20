import streamlit as st
import pandas as pd
import math, io, os
from fpdf import FPDF
import plotly.graph_objects as go
import numpy as np

# =========================================================
# 1. PAGE CONFIG & THEMA
# =========================================================
st.set_page_config(
    page_title="PLEKSEL – Truck / Container Packing",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp > header { display: none; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    h1 { text-align: center; color: #007AA3; margin-top: -30px; padding-bottom: 20px; }
    .block-container { padding-top: 0.5rem; padding-bottom: 0rem; padding-left: 1rem; padding-right: 1rem; }
    div.stButton > button { width: 100%; border-radius: 0.5rem; border: 1px solid #007AA3; background-color: #e0f2f7; color: #007AA3; transition: 0.3s; }
    div.stButton > button:hover { background-color: #cce5ff; }
    div[data-testid="stMetric"], .stContainer { border-radius: 8px; background-color: #f0f8ff; border: 1px solid #cce5ff; padding: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 0.75rem; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. CONFIGURATIE & INITIALISATIE
# =========================================================
TRANSPORT_DIMENSIONS = {
    "Standaard Truck Trailer": {"Lengte": 13.6, "Breedte": 2.45, "Hoogte": 2.7, "MaxGewicht": 24000},
    "20ft Container": {"Lengte": 5.898, "Breedte": 2.352, "Hoogte": 2.393, "MaxGewicht": 28000},
    "40ft Container": {"Lengte": 12.032, "Breedte": 2.352, "Hoogte": 2.393, "MaxGewicht": 26000},
}

MASTER_COLS = {"ItemNr": str,"Omschrijving": str,"Lengte": float,"Breedte": float,"Hoogte": float,"Gewicht": float,"Stapelbaar": bool}
BOXES_COLS = {"Naam": str,"Lengte": float,"Breedte": float,"Hoogte": float,"Gewicht": float}
PALLETS_COLS = {"Naam": str,"Lengte": float,"Breedte": float,"MaxHoogte": float,"Gewicht": float, "PalletHoogte": float, "PalletStapelbaar": bool}
ORDERS_COLS = {"OrderNr": str,"ItemNr": str,"Aantal": int}
TRUCK_CUSTOM_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "MaxGewicht": float}

def enforce_dtypes(df, dtypes):
    if df is None or (isinstance(df, pd.DataFrame) and df.empty): 
        return pd.DataFrame(columns=dtypes.keys())
    df_copy = df.copy()
    for col, dtype in dtypes.items():
        if col not in df_copy.columns:
            df_copy[col] = 0.0 if dtype in (float, int) else ("" if dtype == str else True)
        if dtype in (float, int):
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').fillna(0)
    return df_copy[list(dtypes.keys())]

# Initialize Session State
for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("orders_df", ORDERS_COLS), ("custom_trucks_df", TRUCK_CUSTOM_COLS)]:
    if key not in st.session_state: st.session_state[key] = enforce_dtypes(None, cols)

# =========================================================
# 3. HELPER FUNCTIES (PDF & Cloud Storage)
# =========================================================
def export_config():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.master_data_df.to_excel(writer, sheet_name="Master", index=False)
        st.session_state.boxes_df.to_excel(writer, sheet_name="Boxes", index=False)
        st.session_state.pallets_df.to_excel(writer, sheet_name="Pallets", index=False)
        st.session_state.orders_df.to_excel(writer, sheet_name="Orders", index=False)
        st.session_state.custom_trucks_df.to_excel(writer, sheet_name="Trucks", index=False)
    return output.getvalue()

def import_config(file):
    if file:
        xls = pd.ExcelFile(file)
        st.session_state.master_data_df = enforce_dtypes(pd.read_excel(xls, "Master"), MASTER_COLS)
        st.session_state.boxes_df = enforce_dtypes(pd.read_excel(xls, "Boxes"), BOXES_COLS)
        st.session_state.pallets_df = enforce_dtypes(pd.read_excel(xls, "Pallets"), PALLETS_COLS)
        st.session_state.orders_df = enforce_dtypes(pd.read_excel(xls, "Orders"), ORDERS_COLS)
        if "Trucks" in xls.sheet_names:
            st.session_state.custom_trucks_df = enforce_dtypes(pd.read_excel(xls, "Trucks"), TRUCK_CUSTOM_COLS)
        st.rerun()

def create_pdf(summary_data, advies_df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "PLEKSEL - Transport Planning", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Planning Samenvatting:", ln=True)
    pdf.set_font("Arial", '', 10)
    for k, v in summary_data.items():
        pdf.cell(200, 8, f"{k}: {v}", ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Gekozen Verpakkingen per Order:", ln=True)
    pdf.set_font("Arial", '', 9)
    for _, row in advies_df.iterrows():
        pdf.cell(200, 7, f"Order: {row['Order']} -> Doos: {row['Gekozen Doos']} ({row['Gewicht Doos']} kg)", ln=True)
    
    return pdf.output(dest='S').encode('latin-1')

def handle_upload(f, cols, key):
    if f:
        df = pd.read_csv(f) if f.name.endswith("csv") else pd.read_excel(f)
        st.session_state[key] = enforce_dtypes(df, cols)
        st.rerun()

# =========================================================
# 4. REKENLOGICA
# =========================================================
def bepaal_optimale_doos(groep_items, dozen_df):
    if dozen_df.empty: return "Standaard", 0.0
    vol_nodig = (groep_items['Lengte'] * groep_items['Breedte'] * groep_items['Hoogte'] * groep_items['Aantal']).sum() * 1.15
    dozen = dozen_df.copy()
    dozen['vol'] = dozen['Lengte'] * dozen['Breedte'] * dozen['Hoogte']
    dozen = dozen.sort_values('vol')
    for _, d in dozen.iterrows():
        if d['vol'] >= vol_nodig:
            return d['Naam'], d['Gewicht']
    return "XL Doos", 0.0

def calc_planning(df_full, p_row, t_dims, box_weights):
    T_L = t_dims['Lengte'] * 100 if t_dims['Lengte'] < 100 else t_dims['Lengte']
    T_W = t_dims['Breedte'] * 100 if t_dims['Breedte'] < 100 else t_dims['Breedte']
    T_MAX_KG = t_dims['MaxGewicht']
    
    total_pals = 0
    total_kg = 0
    for nr, group in df_full.groupby('OrderNr'):
        b_w = box_weights.get(nr, 0)
        for _, r in group.iterrows():
            fit = max(1, (int(p_row['Lengte'] // r['Lengte']) * int(p_row['Breedte'] // r['Breedte'])))
            lagen = max(1, int((p_row['MaxHoogte'] - p_row['PalletHoogte']) // r['Hoogte']))
            total_pals += math.ceil(r['Aantal'] / (fit * lagen))
            total_kg += (r['Aantal'] * (r['Gewicht'] + b_w))
            
    total_kg += (total_pals * p_row['Gewicht'])
    pals_naast_elkaar = max(1, int(T_W // p_row['Breedte']))
    rijen = math.ceil(total_pals / pals_naast_elkaar)
    laadmeters = (rijen * p_row['Lengte']) / 100
    trucks = max(math.ceil(laadmeters / (T_L/100)), math.ceil(total_kg / T_MAX_KG))
    return total_pals, total_kg, laadmeters, max(1, trucks)

# =========================================================
# 5. UI LAYOUT
# =========================================================
st.markdown("<h1>PLEKSEL 🚛</h1>", unsafe_allow_html=True)
page = st.sidebar.radio("Navigatie", ["📁 Templates", "📑 Orders", "🚛 Planning"])

if page == "📁 Templates":
    st.header("🗄️ Online Bestandsbeheer")
    with st.container(border=True):
        st.info("Download hier je volledige configuratie om deze later weer in te laden.")
        c1, c2 = st.columns(2)
        c1.download_button("💾 Download Huidige Template", export_config(), "mijn_pleksel_config.xlsx", use_container_width=True)
        up_conf = c2.file_uploader("Upload Template Excel", type="xlsx")
        if up_conf and st.button("📂 Inladen"): import_config(up_conf)

    st.subheader("📦 Master Data")
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", use_container_width=True, key="m_edit")
    handle_upload(st.file_uploader("Upload Master Data", key="u1"), MASTER_COLS, "master_data_df")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🎁 Dozen (CM)")
        st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", use_container_width=True, key="b_edit")
        handle_upload(st.file_uploader("Upload Dozen", key="u2"), BOXES_COLS, "boxes_df")
    with col_b:
        st.subheader("🟫 Pallets (CM)")
        st.session_state.pallets_df = st.data_editor(st.session_state.pallets_df, num_rows="dynamic", use_container_width=True, key="p_edit")
        handle_upload(st.file_uploader("Upload Pallets", key="u3"), PALLETS_COLS, "pallets_df")

    st.subheader("🚛 Custom Trucks")
    st.session_state.custom_trucks_df = st.data_editor(st.session_state.custom_trucks_df, num_rows="dynamic", use_container_width=True, key="t_edit")

elif page == "📑 Orders":
    st.header("📝 Orderbeheer")
    st.session_state.orders_df = st.data_editor(st.session_state.orders_df, num_rows="dynamic", use_container_width=True, key="o_edit")
    handle_upload(st.file_uploader("Upload Orders", key="u4"), ORDERS_COLS, "orders_df")

elif page == "🚛 Planning":
    st.header("🚀 Planning")
    if st.session_state.orders_df.empty: st.warning("Voeg eerst orders toe!"); st.stop()
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        truck_opts = list(TRANSPORT_DIMENSIONS.keys()) + st.session_state.custom_trucks_df['Naam'].tolist()
        sel_t = c1.selectbox("Transport", truck_opts)
        sel_p = c2.selectbox("Pallet", st.session_state.pallets_df['Naam'].tolist())
        box_opt = c3.selectbox("Doos", ["Automatisch Optimaliseren"] + st.session_state.boxes_df['Naam'].tolist())

    if st.button("Bereken & Genereer Rapport"):
        df_f = st.session_state.orders_df.merge(st.session_state.master_data_df, on="ItemNr")
        
        box_weights, advies = {}, []
        for nr, grp in df_f.groupby('OrderNr'):
            n, w = bepaal_optimale_doos(grp, st.session_state.boxes_df) if box_opt == "Automatisch Optimaliseren" else (box_opt, st.session_state.boxes_df[st.session_state.boxes_df['Naam']==box_opt]['Gewicht'].values[0])
            box_weights[nr], advies.append({"Order": nr, "Gekozen Doos": n, "Gewicht Doos": w})
        
        advies_df = pd.DataFrame(advies)
        st.dataframe(advies_df, hide_index=True)

        t_dims = TRANSPORT_DIMENSIONS[sel_t] if sel_t in TRANSPORT_DIMENSIONS else st.session_state.custom_trucks_df[st.session_state.custom_trucks_df['Naam']==sel_t].iloc[0].to_dict()
        p_row = st.session_state.pallets_df[st.session_state.pallets_df['Naam']==sel_p].iloc[0]

        pals, kg, lm, num_trucks = calc_planning(df_f, p_row, t_dims, box_weights)

        summary = {"Transport": sel_t, "Pallet Type": sel_p, "Totaal Pallets": f"{pals} LP", "Totaal Gewicht": f"{kg:.0f} KG", "Laadmeters": f"{lm:.2f} m", "Aantal Trucks": num_trucks}
        
        cols = st.columns(4)
        cols[0].metric("Pallets", summary["Totaal Pallets"])
        cols[1].metric("Gewicht", summary["Totaal Gewicht"])
        cols[2].metric("Laadmeters", summary["Laadmeters"])
        cols[3].metric("Trucks", summary["Aantal Trucks"])

        pdf_bytes = create_pdf(summary, advies_df)
        st.download_button("📄 Download PDF Rapport", pdf_bytes, "transport_planning.pdf", "application/pdf")
