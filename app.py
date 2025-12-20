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

LANGS = {
    "NL": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Pallet/Truck berekening",
        "header_storage": "🗄️ Online Bestandsbeheer", "info_storage": "Download hier je volledige configuratie om deze later weer in te laden.",
        "btn_download": "💾 Download Huidige Template", "btn_upload": "📂 Inladen", "master_data": "📦 Master Data",
        "boxes": "🎁 Dozen (CM)", "pallets": "🟫 Pallets (CM)", "trucks": "🚛 Custom Trucks", "order_mgmt": "📝 Orderbeheer",
        "transport": "Transport", "pallet": "Pallet", "box": "Doos", "auto_box": "Automatisch Optimaliseren (Alleen uit lijst)",
        "btn_calc": "Bereken & Genereer Rapport", "summary": "Samenvatting", "pals": "Pallets", "weight": "Gewicht",
        "meters": "Laadmeters", "num_trucks": "Trucks Nodig", "btn_pdf": "📄 Download PDF Rapport", "warn_orders": "Voeg eerst orders toe!",
        "no_box": "GEEN PASSENDE DOOS GEVONDEN IN LIJST"
    },
    "EN": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Pallet/Truck calculation",
        "header_storage": "🗄️ Online Storage Management", "info_storage": "Download your full configuration here to reload it later.",
        "btn_download": "💾 Download Current Template", "btn_upload": "📂 Load", "master_data": "📦 Master Data",
        "boxes": "🎁 Boxes (CM)", "pallets": "🟫 Pallets (CM)", "trucks": "🚛 Custom Trucks", "order_mgmt": "📝 Order Management",
        "transport": "Transport", "pallet": "Pallet", "box": "Box", "auto_box": "Automatic Optimization (Only from list)",
        "btn_calc": "Calculate & Generate Report", "summary": "Summary", "pals": "Pallets", "weight": "Weight",
        "meters": "Loading Meters", "num_trucks": "Trucks Needed", "btn_pdf": "📄 Download PDF Report", "warn_orders": "Add orders first!",
        "no_box": "NO SUITABLE BOX FOUND IN LIST"
    },
    "DE": {
        "nav_templates": "📁 Vorlagen", "nav_orders": "📑 Bestellungen", "nav_calc": "🚛 Paletten/LKW Berechnung",
        "header_storage": "🗄️ Online-Dateiverwaltung", "info_storage": "Laden Sie hier Ihre vollständige Konfiguration herunter, um sie später wieder zu laden.",
        "btn_download": "💾 Aktuelle Vorlage herunterladen", "btn_upload": "📂 Laden", "master_data": "📦 Stammdaten",
        "boxes": "🎁 Kartons (CM)", "pallets": "🟫 Paletten (CM)", "trucks": "🚛 Eigene LKW", "order_mgmt": "📝 Auftragsverwaltung",
        "transport": "Transport", "pallet": "Palette", "box": "Karton", "auto_box": "Automatisch optimieren (Nur aus Liste)",
        "btn_calc": "Berechnen & Bericht erstellen", "summary": "Zusammenfassung", "pals": "Paletten", "weight": "Gewicht",
        "meters": "Lademeter", "num_trucks": "LKWs benötigt", "btn_pdf": "📄 PDF-Bericht herunterladen", "warn_orders": "Zuerst Bestellungen hinzufügen!",
        "no_box": "KEIN PASSENDER KARTON IN DER LISTE GEFUNDEN"
    },
    "PL": {
        "nav_templates": "📁 Szablony", "nav_orders": "📑 Zamówienia", "nav_calc": "🚛 Kalkulacja palet/ciężarówek",
        "header_storage": "🗄️ Zarządzanie plikami online", "info_storage": "Pobierz pełną konfigurację tutaj, aby załadować ją później.",
        "btn_download": "💾 Pobierz bieżący szablon", "btn_upload": "📂 Załaduj", "master_data": "📦 Dane podstawowe",
        "boxes": "🎁 Pudełka (CM)", "pallets": "🟫 Palety (CM)", "trucks": "🚛 Niestandardowe ciężarówki", "order_mgmt": "📝 Zarządzanie zamówieniami",
        "transport": "Transport", "pallet": "Paleta", "box": "Pudełko", "auto_box": "Automatyczna optymalizacja (tylko z listy)",
        "btn_calc": "Oblicz i wygeneruj raport", "summary": "Podsumowanie", "pals": "Palety", "weight": "Waga",
        "meters": "Metry ładunkowe", "num_trucks": "Potrzebne ciężarówki", "btn_pdf": "📄 Pobierz raport PDF", "warn_orders": "Najpierw dodaj zamówienia!",
        "no_box": "NIE ZNALEZIONO PASUJĄCEGO PUDEŁKA NA LIŚCIE"
    }
}

st.sidebar.title("Language / Taal")
lang_choice = st.sidebar.selectbox("Select Language", ["NL", "EN", "DE", "PL"])
T = LANGS[lang_choice]

# =========================================================
# 2. INITIALISATIE
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

for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("orders_df", ORDERS_COLS), ("custom_trucks_df", TRUCK_CUSTOM_COLS)]:
    if key not in st.session_state: st.session_state[key] = enforce_dtypes(None, cols)

# =========================================================
# 3. REKENLOGICA (STRIKT)
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

def bepaal_optimale_doos_strikt(groep_items, dozen_df):
    if dozen_df.empty: return T["no_box"], 0.0
    vol_nodig = (groep_items['Lengte'] * groep_items['Breedte'] * groep_items['Hoogte'] * groep_items['Aantal']).sum() * 1.15
    dozen = dozen_df.copy()
    dozen['vol'] = dozen['Lengte'] * dozen['Breedte'] * dozen['Hoogte']
    dozen = dozen.sort_values('vol')
    
    for _, d in dozen.iterrows():
        if d['vol'] >= vol_nodig:
            # Check of het grootste item fysiek in de doos past
            if groep_items['Lengte'].max() <= d['Lengte'] and groep_items['Breedte'].max() <= d['Breedte'] and groep_items['Hoogte'].max() <= d['Hoogte']:
                return d['Naam'], d['Gewicht']
    return T["no_box"], 0.0

def calc_planning(df_full, p_row, t_dims, box_weights):
    T_L = t_dims['Lengte'] * 100 if t_dims['Lengte'] < 100 else t_dims['Lengte']
    T_W = t_dims['Breedte'] * 100 if t_dims['Breedte'] < 100 else t_dims['Breedte']
    T_MAX_KG = t_dims['MaxGewicht']
    
    total_pals, total_kg = 0, 0
    for nr, group in df_full.groupby('OrderNr'):
        bw = box_weights.get(nr, 0)
        for _, r in group.iterrows():
            fit = max(1, (int(p_row['Lengte'] // r['Lengte']) * int(p_row['Breedte'] // r['Breedte'])))
            lagen = max(1, int((p_row['MaxHoogte'] - p_row['PalletHoogte']) // r['Hoogte']))
            total_pals += math.ceil(r['Aantal'] / (fit * lagen))
            total_kg += (r['Aantal'] * (r['Gewicht'] + bw))
    
    total_kg += (total_pals * p_row['Gewicht'])
    rijen = math.ceil(total_pals / max(1, int(T_W // p_row['Breedte'])))
    lm = (rijen * p_row['Lengte']) / 100
    trucks = max(math.ceil(lm / (T_L/100)), math.ceil(total_kg / T_MAX_KG))
    return total_pals, total_kg, lm, max(1, trucks)

# =========================================================
# 4. UI
# =========================================================
st.markdown(f"<h1>PLEKSEL 🚛</h1>", unsafe_allow_html=True)
page = st.sidebar.radio("Menu", [T["nav_templates"], T["nav_orders"], T["nav_calc"]])

if page == T["nav_templates"]:
    st.header(T["header_storage"])
    with st.container(border=True):
        st.info(T["info_storage"])
        c1, c2 = st.columns(2)
        c1.download_button(T["btn_download"], export_config(), "pleksel_config.xlsx", use_container_width=True)
        up = c2.file_uploader("Upload Excel", type="xlsx")
        if up and st.button(T["btn_upload"]): 
            xls = pd.ExcelFile(up)
            st.session_state.master_data_df = enforce_dtypes(pd.read_excel(xls, "Master"), MASTER_COLS)
            st.session_state.boxes_df = enforce_dtypes(pd.read_excel(xls, "Boxes"), BOXES_COLS)
            st.session_state.pallets_df = enforce_dtypes(pd.read_excel(xls, "Pallets"), PALLETS_COLS)
            st.session_state.orders_df = enforce_dtypes(pd.read_excel(xls, "Orders"), ORDERS_COLS)
            if "Trucks" in xls.sheet_names: st.session_state.custom_trucks_df = enforce_dtypes(pd.read_excel(xls, "Trucks"), TRUCK_CUSTOM_COLS)
            st.rerun()

    st.subheader(T["master_data"])
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", use_container_width=True)
    st.subheader(T["boxes"])
    st.session_state.boxes_df = st.data_editor(st.session_state.boxes_df, num_rows="dynamic", use_container_width=True)
    st.subheader(T["pallets"])
    st.session_state.pallets_df = st.data_editor(st.session_state.pallets_df, num_rows="dynamic", use_container_width=True)
    st.subheader(T["trucks"])
    st.session_state.custom_trucks_df = st.data_editor(st.session_state.custom_trucks_df, num_rows="dynamic", use_container_width=True)

elif page == T["nav_orders"]:
    st.header(T["order_mgmt"])
    st.session_state.orders_df = st.data_editor(st.session_state.orders_df, num_rows="dynamic", use_container_width=True)

elif page == T["nav_calc"]:
    st.header(T["nav_calc"])
    if st.session_state.orders_df.empty: st.warning(T["warn_orders"]); st.stop()
    if st.session_state.pallets_df.empty: st.error("No Pallets defined in Templates!"); st.stop()
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        t_opts = list(TRANSPORT_DIMENSIONS.keys()) + st.session_state.custom_trucks_df['Naam'].tolist()
        sel_t = c1.selectbox(T["transport"], t_opts)
        sel_p = c2.selectbox(T["pallet"], st.session_state.pallets_df['Naam'].tolist())
        box_opt = c3.selectbox(T["box"], [T["auto_box"]] + st.session_state.boxes_df['Naam'].tolist())

    if st.button(T["btn_calc"]):
        df_f = st.session_state.orders_df.merge(st.session_state.master_data_df, on="ItemNr")
        box_weights, advies = {}, []
        
        for nr, grp in df_f.groupby('OrderNr'):
            if box_opt == T["auto_box"]:
                n, w = bepaal_optimale_doos_strikt(grp, st.session_state.boxes_df)
            else: 
                row = st.session_state.boxes_df[st.session_state.boxes_df['Naam']==box_opt]
                n, w = (row['Naam'].values[0], row['Gewicht'].values[0]) if not row.empty else (T["no_box"], 0.0)
            
            box_weights[nr] = w
            advies.append({"Order": nr, "Box": n, "Box Weight": w})
        
        st.dataframe(pd.DataFrame(advies), hide_index=True)
        
        # Check of er een truck en pallet is geselecteerd
        t_dims = TRANSPORT_DIMENSIONS[sel_t] if sel_t in TRANSPORT_DIMENSIONS else st.session_state.custom_trucks_df[st.session_state.custom_trucks_df['Naam']==sel_t].iloc[0].to_dict()
        p_row = st.session_state.pallets_df[st.session_state.pallets_df['Naam']==sel_p].iloc[0]
        
        pals, kg, lm, num_t = calc_planning(df_f, p_row, t_dims, box_weights)
        
        res = st.columns(4)
        res[0].metric(T["pals"], f"{pals} LP")
        res[1].metric(T["weight"], f"{kg:.0f} KG")
        res[2].metric(T["meters"], f"{lm:.2f} m")
        res[3].metric(T["num_trucks"], f"{num_t}")
