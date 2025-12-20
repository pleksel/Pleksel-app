import streamlit as st
import pandas as pd
import math, io, os
from fpdf import FPDF
import plotly.graph_objects as go

# =========================================================
# 1. PAGE CONFIG & THEMA
# =========================================================
st.set_page_config(page_title="PLEKSEL – Truck Packing", page_icon="🚛", layout="wide")

st.markdown("""
<style>
    .stApp > header { display: none; }
    h1 { text-align: center; color: #007AA3; }
    div[data-testid="stMetric"], .stContainer { border-radius: 8px; background-color: #f0f8ff; border: 1px solid #cce5ff; padding: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. INITIALISATIE & DATATYPES
# =========================================================
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
    return df_copy[list(dtypes.keys())]

for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("orders_df", ORDERS_COLS), ("custom_trucks_df", TRUCK_CUSTOM_COLS)]:
    if key not in st.session_state: st.session_state[key] = enforce_dtypes(None, cols)

# =========================================================
# 3. ONLINE STORAGE (EXCEL CONFIG) FUNCTIES
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
        st.session_state.master_data_df = pd.read_excel(xls, "Master")
        st.session_state.boxes_df = pd.read_excel(xls, "Boxes")
        st.session_state.pallets_df = pd.read_excel(xls, "Pallets")
        st.session_state.orders_df = pd.read_excel(xls, "Orders")
        if "Trucks" in xls.sheet_names:
            st.session_state.custom_trucks_df = pd.read_excel(xls, "Trucks")
        st.rerun()

# =========================================================
# 4. REKENLOGICA
# =========================================================
def bepaal_optimale_doos(items, dozen):
    if dozen.empty: return "Standaard", 0.0
    vol = (items['Lengte'] * items['Breedte'] * items['Hoogte'] * items['Aantal']).sum() * 1.15
    for _, d in dozen.sort_values(by='Lengte').iterrows():
        if (d['Lengte'] * d['Breedte'] * d['Hoogte']) >= vol:
            return d['Naam'], d['Gewicht']
    return "Maatwerk", 0.0

def calc_planning(df, pal, truck, box_weights):
    T_L = truck['Lengte'] * 100 if truck['Lengte'] < 100 else truck['Lengte']
    T_W = truck['Breedte'] * 100 if truck['Breedte'] < 100 else truck['Breedte']
    
    total_pals = 0
    total_kg = 0
    for nr, group in df.groupby('OrderNr'):
        bw = box_weights.get(nr, 0)
        for _, r in group.iterrows():
            fit = max(1, (int(pal['Lengte'] // r['Lengte']) * int(pal['Breedte'] // r['Breedte'])))
            lagen = max(1, int((pal['MaxHoogte'] - pal['PalletHoogte']) // r['Hoogte']))
            total_pals += math.ceil(r['Aantal'] / (fit * lagen))
            total_kg += (r['Aantal'] * (r['Gewicht'] + bw))
    
    total_kg += (total_pals * pal['Gewicht'])
    rijen = math.ceil(total_pals / max(1, int(T_W // pal['Breedte'])))
    lm = (rijen * pal['Lengte']) / 100
    trucks = max(math.ceil(lm / (T_L/100)), math.ceil(total_kg / truck['MaxGewicht']))
    return total_pals, total_kg, lm, max(1, trucks)

# =========================================================
# 5. UI & NAVIGATIE
# =========================================================
st.markdown("<h1>PLEKSEL 🚛</h1>", unsafe_allow_html=True)

# NAVIGATIE DEFINIËREN
page = st.sidebar.radio("Navigatie", ["📁 Templates", "📑 Orders", "🚛 Planning"])

if page == "📁 Templates":
    st.header("🗄️ Online Bestandsbeheer")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("💾 Download Huidige Template", export_config(), "mijn_template.xlsx", use_container_width=True)
    with c2:
        up = st.file_uploader("Upload een Template", type="xlsx")
        if up and st.button("📂 Inladen"): import_config(up)

    st.subheader("📦 Master Data")
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", use_container_width=True)
    
    st.subheader("🎁 Dozen & 🟫 Pallets")
    ca, cb = st.columns(2)
    st.session_state.boxes_df = ca.data_editor(st.session_state.boxes_df, num_rows="dynamic", use_container_width=True)
    st.session_state.pallets_df = cb.data_editor(st.session_state.pallets_df, num_rows="dynamic", use_container_width=True)
    
    st.subheader("🚛 Custom Trucks (Lengte/Breedte/Hoogte in CM, Gewicht in KG)")
    st.session_state.custom_trucks_df = st.data_editor(st.session_state.custom_trucks_df, num_rows="dynamic", use_container_width=True)

elif page == "📑 Orders":
    st.header("📝 Orders")
    st.session_state.orders_df = st.data_editor(st.session_state.orders_df, num_rows="dynamic", use_container_width=True)

elif page == "🚛 Planning":
    st.header("🚀 Planning")
    if st.session_state.orders_df.empty: 
        st.warning("Geen orders! Voeg eerst orders toe bij het tabblad Orders.")
        st.stop()
    
    t_opt = ["Standaard Truck Trailer"] + st.session_state.custom_trucks_df['Naam'].tolist()
    sel_t = st.selectbox("Transport", t_opt)
    
    if st.session_state.pallets_df.empty:
        st.error("Voeg eerst een pallet type toe bij Templates.")
        st.stop()
        
    sel_p = st.selectbox("Pallet", st.session_state.pallets_df['Naam'].tolist())
    
    if st.button("Bereken Planning"):
        df_f = st.session_state.orders_df.merge(st.session_state.master_data_df, on="ItemNr")
        box_w = {nr: bepaal_optimale_doos(g, st.session_state.boxes_df)[1] for nr, g in df_f.groupby('OrderNr')}
        
        if "Standaard" in sel_t:
            t_dims = {"Lengte": 13.6, "Breedte": 2.45, "MaxGewicht": 24000}
        else:
            t_dims = st.session_state.custom_trucks_df[st.session_state.custom_trucks_df['Naam']==sel_t].iloc[0].to_dict()
            
        p_row = st.session_state.pallets_df[st.session_state.pallets_df['Naam']==sel_p].iloc[0]
        
        pals, kg, lm, num_t = calc_planning(df_f, p_row, t_dims, box_w)
        
        res1, res2, res3, res4 = st.columns(4)
        res1.metric("Pallets", f"{pals} LP")
        res2.metric("Gewicht", f"{kg:.0f} KG")
        res3.metric("Laadmeters", f"{lm:.2f} m")
        res4.metric("Trucks Nodig", f"{num_t}")
