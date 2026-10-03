import streamlit as st

from core.auth import check_login

if "role" not in st.session_state:
    st.title("AskBI login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Log in"):
        role = check_login(username, password)
        if role is None:
            st.error("Wrong username or password")
        else:
            st.session_state["role"] = role
            st.rerun()
    st.stop()


dashboard = st.Page("pages/dashboard.py", title="Dashboard", icon="📊")
ask = st.Page("pages/ask.py", title="Ask Me Anything", icon="💬")
developer = st.Page("pages/developer.py", title="Developer", icon="🛠️")

pages = [dashboard, ask, developer]
nav = st.navigation(pages)

nav.run()
