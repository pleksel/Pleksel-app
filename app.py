import streamlit as st
import pandas as pd
import math, io, os
from fpdf import FPDF

# =========================================================
# 1. PAGE CONFIG & THEMA
# =========================================================
st.set_page_config(page_title="PLEKSEL", page_icon="🚛", layout="wide")

LANGS = {
    "NL": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Pallet/Truck berekening",
        "header_storage": "🗄️ Online Bestandsbeheer", "btn_download": "💾 Download Template", "btn_upload": "📂 Inladen",
        "master_data": "📦 Master Data", "boxes": "🎁 Dozen (CM)", "pallets": "🟫 Pallets (CM)", "trucks": "🚛 Custom Trucks",
        "transport": "Transport", "pallet": "Pallet", "box": "Doos Type", "auto_box": "Slimme Doos Selectie (Splitsen)",
        "btn_calc": "Bereken Planning & PDF", "pals": "Pallets", "weight": "Totaal Gewicht", "meters": "Laadmeters",
        "num_trucks": "Trucks Nodig", "warn_orders": "Voeg eerst orders toe!", "order_mgmt": "📝 Orderbeheer"
    },
    "EN": {
        "nav_templates": "📁 Templates", "nav_orders": "📑 Orders", "nav_calc": "🚛 Pallet/Truck calculation",
        "header_storage": "🗄️ Storage Management", "btn_download": "💾 Download Template", "btn_upload": "📂 Load",
        "master_data": "📦 Master Data", "boxes": "🎁 Boxes (CM)", "pallets": "🟫 Pallets (CM)", "trucks": "🚛 Custom Trucks",
        "transport": "Transport", "pallet": "Pallet", "box": "Box Type", "auto_box": "Smart Box Selection (Split)",
        "btn_calc": "Calculate & PDF", "pals": "Pallets", "weight": "Total Weight", "meters": "Loading Meters",
        "num_trucks": "Trucks Needed", "warn_orders": "Add orders first!", "order_mgmt": "📝 Order Management"
    },
    "DE": { "nav_templates": "📁 Vorlagen", "nav_orders": "📑 Bestellungen", "nav_calc": "🚛 Paletten/LKW Berechnung", "header_storage": "🗄️ Dateiverwaltung", "btn_download": "💾 Download", "btn_upload": "📂 Laden", "master_data": "📦 Stammdaten", "boxes": "🎁 Kartons", "pallets": "🟫 Paletten", "trucks": "🚛 LKWs", "transport": "Transport", "pallet": "Palette", "box": "Karton", "auto_box": "Smarte Kartonwahl", "btn_calc": "Berechnen", "pals": "Paletten", "weight": "Gewicht", "meters": "Lademeter", "num_trucks": "LKWs", "warn_orders": "Bestellungen fehlen!", "order_mgmt": "📝 Verwaltung" },
    "PL": { "nav_templates": "📁 Szablony", "nav_orders": "📑 Zamówienia", "nav_calc": "🚛 Kalkulacja", "header_storage": "🗄️ Zarządzanie", "btn_download": "💾 Pobierz", "btn_upload": "📂 Załaduj", "master_data": "📦 Dane", "boxes": "🎁 Pudełka", "pallets": "🟫 Palety", "trucks": "🚛 Ciężarówki", "transport": "Transport", "pallet": "Paleta", "box": "Pudełko", "auto_box": "Inteligentny dobór", "btn_calc": "Oblicz", "pals": "Palety", "weight": "Waga", "meters": "Metry", "num_trucks": "Ciężarówki", "warn_orders": "Dodaj zamówienia!", "order_mgmt": "📝 Zarządzanie" }
}

st.sidebar.title("Language / Taal")
lang_choice = st.sidebar.selectbox("Select Language", ["NL", "EN", "DE", "PL"])
T = LANGS[lang_choice]

# =========================================================
# 2. INITIALISATIE & DTYPES
# =========================================================
MASTER_COLS = {"ItemNr": str,"Omschrijving": str,"Lengte": float,"Breedte": float,"Hoogte": float,"Gewicht": float,"Stapelbaar": bool}
BOXES_COLS = {"Naam": str,"Lengte": float,"Breedte": float,"Hoogte": float,"Gewicht": float}
PALLETS_COLS = {"Naam": str,"Lengte": float,"Breedte": float,"MaxHoogte": float,"Gewicht": float, "PalletHoogte": float, "PalletStapelbaar": bool}
ORDERS_COLS = {"OrderNr": str,"ItemNr": str,"Aantal": int}
TRUCK_CUSTOM_COLS = {"Naam": str, "Lengte": float, "Breedte": float, "Hoogte": float, "MaxGewicht": float}

def enforce_dtypes(df, dtypes):
    if df is None or (isinstance(df, pd.DataFrame) and df.empty): return pd.DataFrame(columns=dtypes.keys())
    df_copy = df.copy()
    for col, dtype in dtypes.items():
        if col not in df_copy.columns: df_copy[col] = 0.0 if dtype in (float, int) else ("" if dtype == str else True)
        if dtype in (float, int): df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').fillna(0)
    return df_copy[list(dtypes.keys())]

for key, cols in [("master_data_df", MASTER_COLS), ("boxes_df", BOXES_COLS), ("pallets_df", PALLETS_COLS), ("orders_df", ORDERS_COLS), ("custom_trucks_df", TRUCK_CUSTOM_COLS)]:
    if key not in st.session_state: st.session_state[key] = enforce_dtypes(None, cols)

# =========================================================
# 3. SLIMME REKENFUNCTIES (SPLITSEN)
# =========================================================
def bepaal_dozen_voor_order(groep_items, dozen_df):
    """Berekent hoeveel dozen er nodig zijn, splitst indien nodig."""
    if dozen_df.empty: return "Standaard", 0.0, 1
    
    # Sorteer dozen op volume
    dozen = dozen_df.copy()
    dozen['vol'] = dozen['Lengte'] * dozen['Breedte'] * dozen['Hoogte']
    dozen = dozen.sort_values('vol', ascending=False)
    
    total_vol_items = (groep_items['Lengte'] * groep_items['Breedte'] * groep_items['Hoogte'] * groep_items['Aantal']).sum() * 1.15
    grootste_doos = dozen.iloc[0]
    
    num_dozen = math.ceil(total_vol_items / grootste_doos['vol'])
    return grootste_doos['Naam'], grootste_doos['Gewicht'], num_dozen

def create_pdf(summary, advies_df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "PLEKSEL Transport Report", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    for k, v in summary.items(): pdf.cell(200, 10, f"{k}: {v}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Order Details:", ln=True)
    pdf.set_font("Arial", '', 10)
    for _, r in advies_df.iterrows():
        pdf.cell(200, 8, f"Order {r['Order']}: {r['Aantal Dozen']}x {r['Box']} ({r['Gewicht p/st']}kg)", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# =========================================================
# 4. UI PAGINA'S
# =========================================================
st.markdown(f"<h1>PLEKSEL 🚛</h1>", unsafe_allow_html=True)
page = st.sidebar.radio("Menu", [T["nav_templates"], T["nav_orders"], T["nav_calc"]])

if page == T["nav_templates"]:
    st.header(T["header_storage"])
    c1, c2 = st.columns(2)
    
    # Export / Import logic
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for k in ["master_data_df", "boxes_df", "pallets_df", "orders_df", "custom_trucks_df"]:
            st.session_state[k].to_excel(writer, sheet_name=k[:10], index=False)
    c1.download_button(T["btn_download"], output.getvalue(), "config.xlsx", use_container_width=True)
    
    up = c2.file_uploader(T["btn_upload"], type="xlsx")
    if up and st.button("Bevestig Upload"):
        xls = pd.ExcelFile(up)
        # Snel inladen op basis van sheet index om fouten te voorkomen
        st.session_state.master_data_df = enforce_dtypes(pd.read_excel(xls, xls.sheet_names[0]), MASTER_COLS)
        st.session_state.boxes_df = enforce_dtypes(pd.read_excel(xls, xls.sheet_names[1]), BOXES_COLS)
        st.session_state.pallets_df = enforce_dtypes(pd.read_excel(xls, xls.sheet_names[2]), PALLETS_COLS)
        st.rerun()

    st.subheader(T["master_data"])
    st.session_state.master_data_df = st.data_editor(st.session_state.master_data_df, num_rows="dynamic", use_container_width=True)
    col1, col2 = st.columns(2)
    st.session_state.boxes_df = col1.data_editor(st.session_state.boxes_df, num_rows="dynamic", use_container_width=True)
    st.session_state.pallets_df = col2.data_editor(st.session_state.pallets_df, num_rows="dynamic", use_container_width=True)

elif page == T["nav_orders"]:
    st.header(T["order_mgmt"])
    st.session_state.orders_df = st.data_editor(st.session_state.orders_df, num_rows="dynamic", use_container_width=True)

elif page == T["nav_calc"]:
    st.header(T["nav_calc"])
    if st.session_state.orders_df.empty: st.warning(T["warn_orders"]); st.stop()
    
    c1, c2, c3 = st.columns(3)
    t_opts = ["Standaard Trailer (13.6m)"] + st.session_state.custom_trucks_df['Naam'].tolist()
    sel_t = c1.selectbox(T["transport"], t_opts)
    sel_p = c2.selectbox(T["pallet"], st.session_state.pallets_df['Naam'].tolist() if not st.session_state.pallets_df.empty else ["Geen"])
    box_opt = c3.selectbox(T["box"], [T["auto_box"]] + st.session_state.boxes_df['Naam'].tolist())

    if st.button(T["btn_calc"]):
        df_f = st.session_state.orders_df.merge(st.session_state.master_data_df, on="ItemNr")
        box_data, advies = {}, []
        
        for nr, grp in df_f.groupby('OrderNr'):
            n, w, count = bepaal_dozen_voor_order(grp, st.session_state.boxes_df)
            box_data[nr] = {"gewicht_extra": w * count, "aantal_dozen": count}
            advies.append({"Order": nr, "Box": n, "Gewicht p/st": w, "Aantal Dozen": count})
        
        advies_df = pd.DataFrame(advies)
        st.table(advies_df)
        
        # Truck/Pallet logica
        p_row = st.session_state.pallets_df[st.session_state.pallets_df['Naam'] == sel_p].iloc[0]
        t_dims = {"Lengte": 13.6, "Breedte": 2.4, "MaxGewicht": 24000} # Default
        
        total_pals = 0
        total_kg = 0
        for nr, grp in df_f.groupby('OrderNr'):
            # Simpele schatting: Hoeveel van deze items passen op de geselecteerde pallet
            # We gebruiken hier een vullingsgraad van 85% voor de pallethoogte
            item = grp.iloc[0]
            fit_layer = (p_row['Lengte'] // item['Lengte']) * (p_row['Breedte'] // item['Breedte'])
            max_lagen = (p_row['MaxHoogte'] - p_row['PalletHoogte']) // item['Hoogte']
            per_pal = max(1, fit_layer * max_lagen)
            pals_needed = math.ceil(item['Aantal'] / per_pal)
            
            total_pals += pals_needed
            total_kg += (grp['Gewicht'] * grp['Aantal']).sum() + box_data[nr]['gewicht_extra'] + (pals_needed * p_row['Gewicht'])

        lm = (total_pals / 2) * (p_row['Lengte'] / 100) # Uitgaande van 2 pallets naast elkaar
        num_trucks = max(1, math.ceil(lm / 13.6) or math.ceil(total_kg / 24000))

        res = st.columns(4)
        res[0].metric(T["pals"], f"{total_pals} LP")
        res[1].metric(T["weight"], f"{int(total_kg)} KG")
        res[2].metric(T["meters"], f"{lm:.2f} m")
        res[3].metric(T["num_trucks"], num_trucks)
        
        summary = {"Transport": sel_t, "Pallet": sel_p, "Totaal Pallets": total_pals, "Totaal Gewicht": f"{int(total_kg)} KG"}
        pdf_file = create_pdf(summary, advies_df)
        st.download_button("📄 Download PDF Rapport", pdf_file, "Pleksel_Rapport.pdf", "application/pdf")
