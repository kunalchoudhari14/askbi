"""AskBI core logic (auth now; SQL, RAG and chart building later).

Kept separate from the Streamlit pages so a FastAPI/React version can reuse it.
This file makes core/ a Python package, so `from core.auth import ...` works.
"""
