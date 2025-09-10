import streamlit as st

st.title("Ciao — la mia app Streamlit")
name = st.text_input("Come ti chiami?")
if st.button("Saluta"):
    st.success(f"Ciao {name} 👋")
