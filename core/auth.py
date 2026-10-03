"""Login check for AskBI's two roles: "end_user" and "developer".

Users live in .streamlit/secrets.toml (git-ignored), for example:

    [users.analyst]
    password = "..."
    role = "end_user"

Note: plain-text passwords are OK for a v0 demo only. Real apps store
HASHED passwords in a database (planned for a later version).

Quick test (from the askbi folder, with the venv active):
    python core/auth.py
"""

import streamlit as st


def check_login(username: str, password: str) -> str | None:
    """Return the user's role if the credentials are valid, else None."""
    users = st.secrets["users"]  # the [users.*] sections of secrets.toml

    # Guard clauses: handle each failure first and leave early.
    if username not in users:  # unknown user
        return None
    if password != users[username]["password"]:  # wrong password
        return None
    return users[username]["role"]  # only valid logins reach this line


# Quick manual tests: run only with `python core/auth.py`, never when
# app.py imports this file.
if __name__ == "__main__":
    print(check_login("analyst", "analyst"))  # right password → end_user
    print(check_login("developer", "abc"))  # unknown user   → None
    print(check_login("admin", "wrong"))  # wrong password → None
