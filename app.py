"""AskBI entry point: login gate + page navigation.

How to run (from the askbi folder, with the venv active):
    source .venv/bin/activate
    streamlit run app.py
Stop the app with Ctrl + C in the terminal.

How it works: Streamlit re-runs this WHOLE file from the top on every click.
st.session_state is the only thing that survives between re-runs, so the
logged-in user's role is stored there.
"""

# Import order (Ruff): standard library → third-party → our own code.
import streamlit as st  # third-party

from core.auth import check_login  # our own code

# ---------------------------------------------------------------------------
# 1. Login gate (a guard clause for the whole app)
#    If nobody is logged in: show the login form, then STOP, so the pages
#    below are never drawn for anonymous users.
# ---------------------------------------------------------------------------
if "role" not in st.session_state:
    st.title("AskBI login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")  # hides the typed characters

    # st.button(...) is True only on the re-run right after the click.
    if st.button("Log in"):
        role = check_login(username, password)  # "end_user" / "developer" / None
        if role is None:
            st.error("Wrong username or password")
        else:
            st.session_state["role"] = role  # remember the role across re-runs
            st.rerun()  # re-run now: "role" is set, so this block is skipped

    st.stop()  # not logged in → don't run anything below this line


# ---------------------------------------------------------------------------
# 2. Pages (only reached when logged in)
#    st.Page(file, title, icon) describes one screen; paths are relative to
#    this file's folder (the askbi root).
# ---------------------------------------------------------------------------
dashboard = st.Page("pages/dashboard.py", title="Dashboard", icon="📊")
ask = st.Page("pages/ask.py", title="Ask Me Anything", icon="💬")
developer = st.Page("pages/developer.py", title="Developer", icon="🛠️")

# Role-based pages: everyone gets Dashboard + Ask; only developers also
# get the Developer page (end users never see it in the sidebar).
pages = [dashboard, ask]
if st.session_state["role"] == "developer":
    pages.append(developer)  # () calls the method; add the page object itself

# Sidebar: show who's logged in, plus a Log out button.
st.sidebar.caption(f"Logged in as: {st.session_state['role']}")

if st.sidebar.button("Log out"):
    st.session_state.clear()  # forget the role (and anything else stored)
    st.rerun()  # re-run → "role" is missing → the login gate shows again

# Build the sidebar menu and show the selected page.
nav = st.navigation(pages)
nav.run()
