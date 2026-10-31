# Contract: `core/` functions used by the Dashboard

**Feature**: [../spec.md](../spec.md) | **Types**: [../data-model.md](../data-model.md)

This is the promise between `core/` and `pages/dashboard.py`: names, inputs,
outputs and errors. Bodies are written during implementation, not here.
Every function gets type hints, a one-line docstring and pytest tests.

`DB_PATH` (default for every `db_path` argument) =
`Path(__file__).resolve().parent.parent / "data" / "olist.db"`.

## `core/db.py`: the single data-access point (FR-015)

| Name | Signature | Behaviour |
|------|-----------|-----------|
| `DB_PATH` | `Path` constant | Location of `olist.db`. |
| `DataUnavailableError` | `class DataUnavailableError(Exception)` | Raised when the database can't be opened or queried. Message is plain English. |
| `get_connection` | `(db_path: Path = DB_PATH) -> sqlite3.Connection` | Opens **read-only** (`file:…?mode=ro`, `uri=True`). Never creates a file. Missing/unreadable file → `DataUnavailableError`. Caller must close it. |
| `run_query` | `(sql: str, params: Sequence[object] = (), db_path: Path = DB_PATH) -> pd.DataFrame` | Runs one parameterised `SELECT`, returns the rows as a DataFrame, always closes the connection. `sqlite3` errors → `raise DataUnavailableError(...) from err` (original error kept as the cause). Future home of filters (v0-d) and row-level security (v1). |

Guarantees: any write statement fails (SQLite refuses in `mode=ro`);
calling with a missing path leaves no file behind; a raised
`DataUnavailableError` always has the original `sqlite3` error as its
`__cause__` (tested), so the real reason shows in the terminal traceback.

## `core/kpis.py`: the numbers

Constants: `INVALID_STATUSES = ("canceled", "unavailable")`,
`DELIVERED_STATUS = "delivered"`, `TOP_CATEGORY_LIMIT = 10`,
`UNKNOWN_CATEGORY = "unknown_category"`.

| Function | Signature | Returns |
|----------|-----------|---------|
| `get_revenue_cents` | `(db_path: Path = DB_PATH) -> int` | Revenue in cents (FR-003). 0 if no valid items. |
| `get_order_counts` | `(db_path: Path = DB_PATH) -> OrderCounts` | Total and invalid counts (FR-004). |
| `calculate_aov_cents` | `(revenue_cents: int, valid_orders: int) -> int \| None` | Pure. Half-up rounded cents; `None` if `valid_orders == 0` (FR-005, FR-014). |
| `get_late_delivery` | `(db_path: Path = DB_PATH) -> LateDelivery` | Late / judged / unknown counts (FR-006). |
| `get_monthly_revenue` | `(db_path: Path = DB_PATH) -> pd.DataFrame` | Zero-filled months, see data model (FR-007, FR-008). Empty DataFrame (same columns) if there are no orders. |
| `get_category_revenue` | `(limit: int \| None = TOP_CATEGORY_LIMIT, db_path: Path = DB_PATH) -> pd.DataFrame` | Categories by revenue, highest first; `limit=None` returns all (used by the "nothing dropped" test) (FR-009, FR-010). |

## `core/dashboard.py`: one call for the page

| Function | Signature | Returns |
|----------|-----------|---------|
| `load_dashboard_data` | `(db_path: Path = DB_PATH) -> DashboardData` | Calls the `kpis` functions above and bundles the results. Raises `DataUnavailableError` unchanged. |

`OrderCounts`, `LateDelivery` and `DashboardData` are defined in
`core/kpis.py` / `core/dashboard.py` as frozen dataclasses (see data model).

## `core/formatting.py`: text for display (pure)

| Function | Signature | Examples |
|----------|-----------|----------|
| `format_brl` | `(cents: int \| None, abbreviate: bool = False) -> str` | `1349440074` → "R$ 13,494,400.74"; abbreviated → "R$ 13.49M"; `13741` → "R$ 137.41"; `None` → "—" |
| `format_count` | `(n: int) -> str` | `99441` → "99,441" |
| `format_percent` | `(rate: float \| None) -> str` | `0.067731` → "6.8%"; `None` → "—" |
| `format_category_label` | `(key: str) -> str` | `bed_bath_table` → "Bed Bath Table"; `unknown_category` → "Unknown Category" |

## `core/charts.py`: Plotly figures (pure, no Streamlit)

| Function | Signature | Promise |
|----------|-----------|---------|
| `build_monthly_revenue_chart` | `(monthly: pd.DataFrame) -> go.Figure` | One line trace with markers; one point per row, in order; y in R$ (cents ÷ 100); hover "Mon YYYY: R$ 1,234.56". |
| `build_top_categories_chart` | `(categories: pd.DataFrame) -> go.Figure` | One horizontal bar trace; labels via `format_category_label`; highest at the top; title contains "Top 10"; hover shows R$. |

## `core/definitions.py`

| Name | Type | Promise |
|------|------|---------|
| `KPI_DEFINITIONS` | `dict[str, str]` | Six keys (see data model); text matches FR-002 to FR-010 (tested by checking key phrases such as "canceled", "unavailable", "freight", "same day"). |

## `core/auth.py` (small addition)

| Name | Type | Promise |
|------|------|---------|
| `ROLE_END_USER` | `str` constant `"end_user"` | Replaces the magic string. |
| `ROLE_DEVELOPER` | `str` constant `"developer"` | Used by the dashboard's error hint. |

`check_login` is unchanged. `app.py` must use these constants instead of the
raw strings (e.g. `if st.session_state["role"] == ROLE_DEVELOPER`).
