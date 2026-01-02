import streamlit as st

tab_data, tab_calc = st.tabs(["Data", "Planning"])

with tab_data:
    st.write("Dit is de DATA tab")

with tab_calc:
    st.write("Dit is de PLANNING tab")
