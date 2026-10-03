import streamlit as st


def check_login(username: str, password: str) -> str | None:
    users = st.secrets["users"]
    if username not in users:
        return None
    if password != users[username]["password"]:
        return None
    return users[username]["role"]


if __name__ == "__main__":
    print(check_login("analyst", "analyst"))
    print(check_login("developer", "abc"))
    print(check_login("admin", "wrong"))
