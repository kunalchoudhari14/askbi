# AGENTS.md: rules for every agent working on AskBI

## Project
AskBI is an AI-powered BI app on the Olist Brazilian e-commerce dataset (SQLite).
Two roles: `end_user` (Dashboard, Ask Me Anything) and `developer` (+ Developer page).
Access has two parts: **role** (which pages) and **data scope** (which rows; row-level
security comes in v1). Never assume a user can see all rows. Keep data access in
`core/` so filters can be added in one place.
Stack: Python 3.14 · Streamlit · SQLite · Plotly · LangChain + OpenAI (from v1) · Ruff.
Kunal is the architect: he decides, approves every edit and merges. You build.

## Commands (run from the repo root)
- Activate env: `source .venv/bin/activate`
- Run the app: `streamlit run app.py`
- Rebuild the database: `python load_data.py` (needs the 9 Olist CSVs in `data/raw/`)
- Lint + format: `ruff check .` and `ruff format .`
- Tests: `pytest` (once tests exist; every new `core/` function gets tests)

## Structure and boundaries
- `core/`: all logic and **all SQL**. Pure functions where possible; no Streamlit UI calls.
- `pages/`: Streamlit screens only. They call `core/`; they never contain SQL.
- `app.py`: login gate + navigation only.
- `tests/`: pytest tests mirroring `core/` (e.g. `tests/test_kpis.py`).
- `data/`: never edit, never commit. `olist.db` is rebuilt by `load_data.py`.
- `specs/` and `.specify/`: Spec Kit files. Follow them; don't rewrite them unless asked.

## Coding standards
- Imports: standard library → third-party → own code (`from core...`).
- Paths with `pathlib`, anchored to `Path(__file__).resolve().parent`.
- Type hints on every function; a one-line docstring on every function and module.
- Comments explain *why*, not *what*. Add them where the reason isn't obvious.
- Guard clauses (return early) instead of deep nesting.
- Catch specific exceptions, never bare `except:`. Helpful error messages.
- Always close resources (`try/finally` or `with`). One DB connection helper in `core/`.
- Constants in CAPITALS for repeated values (e.g. role names), no magic strings.
- Cache expensive Streamlit data loads with `@st.cache_data`.

## Data rules
- SQL is **read-only** (`SELECT` only). Never `INSERT/UPDATE/DELETE/DROP/ALTER`.
- Use parameterised queries (`?` placeholders), never string-formatted SQL.
- Revenue excludes orders with `order_status` in ('canceled', 'unavailable').
- Olist has no returns table; don't invent net revenue.

## How we work
- Every feature goes through Spec Kit: spec → clarify → plan → tasks → implement.
- Plan first and wait for approval. Small steps; one task at a time.
- Work only on a feature branch, never on `main`.
- Commit messages: `[claude-code] <what changed>` (later per subagent, e.g. `[test-writer]`).
- Mark each finished task in the Spec Kit tasks file.
- Small chores (tests for existing code, config, docs) don't need Spec Kit; features and behaviour changes do.
- Never commit unless Kunal asks; when he does, use the commit message format above.

## Never do (ask Kunal first, or don't)
- Push, merge or force-push anything; never touch `main` directly.
- Edit or print `.env`, `.streamlit/secrets.toml`, or any API key or password.
- Delete files or folders, `rm -rf`, or delete `data/olist.db`.
- Install, upgrade or remove packages.
- Disable or skip tests, lint rules or hooks to make something "pass".

## Definition of done
1. `ruff check .` and `ruff format --check .` are clean.
2. All tests pass, and new `core/` code has tests.
3. Every new function and module has type hints and a docstring; non-obvious lines have "why" comments.
4. The Spec Kit task is marked done.
5. You give a short summary: what changed, which files, why, and anything Kunal should check.
