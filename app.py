import streamlit as st

dashboard = st.Page("pages/dashboard.py", title="Dashboard", icon="📊")
ask = st.Page("pages/ask.py", title="Ask Me Anything", icon="💬")
developer = st.Page("pages/developer.py", title="Developer", icon="🛠️")

pages = [dashboard, ask, developer]
nav = st.navigation(pages)

nav.run()
