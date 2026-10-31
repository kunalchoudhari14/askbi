# Implementation Plan: Default Dashboard (v0-c)

**Branch**: `v0c-static-dashboard` (Spec Kit feature folder `001-static-dashboard`) | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-static-dashboard/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Replace the Dashboard placeholder with 4 KPI cards (Revenue, Orders, AOV,
Late-delivery %), a monthly revenue line chart and a Top 10 categories bar
chart, plus on-page definitions. Same page for both roles.

Technical approach: all SQL lives in new `core/` modules behind **one
read-only connection helper** (`core/db.py`, SQLite `mode=ro`). Money is
summed in **integer cents** so the monthly chart adds up to the Revenue card
exactly. Formatting, definitions and Plotly figures are pure functions in
`core/`, so they can be tested without a browser. `pages/dashboard.py` only
loads one cached `DashboardData` object and draws it. Tests run against a tiny
hand-made SQLite fixture, so CI works without `olist.db`. Details and reasons:
[research.md](research.md).

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Streamlit 1.65.0, pandas 3.0.6, Plotly 7.1.0 (all already pinned in `requirements.txt`; **no new packages**). Standard library: `sqlite3`, `pathlib`, `decimal`, `dataclasses`.

**Storage**: SQLite file `data/olist.db` (built by `load_data.py`), opened read-only.

**Testing**: pytest 9.1.1 with a temporary fixture database (`tests/conftest.py`); Ruff 0.17.1 for lint and format.

**Target Platform**: Local Streamlit app on macOS (Kunal's laptop); CI on GitHub Actions `ubuntu-latest`.

**Project Type**: Single-project Streamlit web app (`app.py` + `pages/` + `core/`).

**Performance Goals**: First dashboard load < 3 s, repeat load < 1 s (SC-001). Measured: each query < 0.1 s on the real data, no indexes needed.

**Constraints**: Read-only SQL, `?` parameters only, SQL only in `core/`, no Streamlit UI calls in `core/`, no writes to `data/`, no new packages.

**Scale/Scope**: ~99k orders, ~113k item lines, 74 categories; 1 page, 6 small `core/` modules, ~6 test files.

No NEEDS CLARIFICATION items remain (see [research.md](research.md)).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the **unfilled template**, so the
gates below come from **AGENTS.md**, which is the project's working rulebook.
(Suggestion: run `/speckit-constitution` later to copy these rules in.)

| Gate (from AGENTS.md) | Pre-research | Post-design | How the design meets it |
|---|---|---|---|
| All SQL in `core/`; pages have no SQL | ✅ | ✅ | SQL only in `core/kpis.py`, executed via `core/db.py` |
| One DB connection helper in `core/` | ✅ | ✅ | `core/db.py::get_connection` / `run_query` |
| SQL is read-only (`SELECT` only) | ✅ | ✅ | `mode=ro` URI; test proves writes fail |
| Parameterised queries, no string-formatted SQL | ✅ | ✅ | Statuses and `LIMIT` passed as `?` |
| Revenue excludes canceled/unavailable; no net revenue | ✅ | ✅ | `INVALID_STATUSES` constant, one shared fragment |
| Data access in one place (future row-level security) | ✅ | ✅ | `run_query` is the single front door (FR-015) |
| `core/` has no Streamlit UI calls | ✅ | ✅ | Caching (`@st.cache_data`) lives in the page |
| Every new `core/` function has tests | ✅ | ✅ | `tests/test_db.py`, `test_kpis.py`, `test_formatting.py`, `test_charts.py`, `test_definitions.py`, `test_dashboard.py` |
| Type hints + one-line docstrings; constants in CAPITALS; `pathlib` paths | ✅ | ✅ | Specified in [contracts/core-api.md](contracts/core-api.md) |
| Specific exceptions; resources always closed | ✅ | ✅ | `DataUnavailableError` raised `from err` (cause kept); `try/finally` close in `run_query` |
| Constants instead of magic strings (role names) | ✅ | ✅ | `ROLE_*` constants used in `core/auth.py`, `app.py` and the dashboard |
| No new packages; don't touch `data/`, secrets, `main` | ✅ | ✅ | Uses existing pins only; fixture DB lives in `tmp_path` |

**Result: PASS** (no violations; Complexity Tracking is empty).

## Project Structure

### Documentation (this feature)

```text
specs/001-static-dashboard/
├── spec.md              # Feature spec (done, clarified)
├── plan.md              # This file
├── research.md          # Phase 0: decisions + real-data baseline numbers
├── data-model.md        # Phase 1: source tables + result objects
├── quickstart.md        # Phase 1: how to validate the feature
├── contracts/
│   ├── core-api.md      # Phase 1: core/ function signatures and promises
│   └── dashboard-ui.md  # Phase 1: page layout, labels, error state
├── checklists/
│   └── requirements.md  # From /speckit-specify
└── tasks.md             # Phase 2: created by /speckit-tasks (not by this command)
```

### Source Code (repository root)

```text
core/
├── __init__.py          # (unchanged)
├── auth.py              # + ROLE_END_USER, ROLE_DEVELOPER constants
├── db.py                # NEW: DB_PATH, DataUnavailableError, get_connection, run_query
├── kpis.py              # NEW: status constants, OrderCounts, LateDelivery, the 6 KPI/chart queries
├── dashboard.py         # NEW: DashboardData + load_dashboard_data()
├── formatting.py        # NEW: format_brl, format_count, format_percent, format_category_label
├── charts.py            # NEW: build_monthly_revenue_chart, build_top_categories_chart
└── definitions.py       # NEW: KPI_DEFINITIONS text

pages/
└── dashboard.py         # REWRITE: cached load → 4 metrics, expander, 2 charts, error state

tests/
├── conftest.py          # NEW: tiny fixture olist.db in tmp_path
├── test_auth.py         # (unchanged)
├── test_db.py           # NEW
├── test_kpis.py         # NEW
├── test_dashboard.py    # NEW
├── test_formatting.py   # NEW
├── test_charts.py       # NEW
└── test_definitions.py  # NEW

app.py                   # UPDATE: use ROLE_DEVELOPER / ROLE_END_USER constants
```

**Structure Decision**: Keep the existing single-project layout from AGENTS.md.
New logic is split into small `core/` modules by job (data access, numbers,
formatting, charts, text) so each is easy to read and test on its own. The
page stays a thin drawing layer.

## Build order (for `/speckit-tasks`)

Each step is small and testable on its own; tests come with (or before) each
module.

1. `core/db.py` + `tests/conftest.py` + `tests/test_db.py` (read-only proof, missing-file error, original error kept as `__cause__`).
2. `core/kpis.py` + `tests/test_kpis.py`, one KPI at a time: revenue → order counts → AOV → late delivery → monthly → categories. *(US1–US3 numbers)*
3. `core/formatting.py` + tests.
4. `core/definitions.py` + tests. *(US4)*
5. `core/charts.py` + tests. *(US2, US3)*
6. `core/dashboard.py` + tests (bundle + invariants: monthly sum = revenue).
7. `core/auth.py` role constants (existing auth tests must still pass).
8. `pages/dashboard.py` rewrite, then manual checks from [quickstart.md](quickstart.md).
9. `app.py` uses `ROLE_DEVELOPER` / `ROLE_END_USER` (required; then re-check login and navigation for both roles).

### Test fixture design (`tests/conftest.py`)

A pytest fixture writes a small SQLite file to `tmp_path` with the real table
and column names and hand-picked rows, so every expected value can be worked
out by hand:

- Orders across 3 months with **one empty month in between** (zero-fill test).
- One `canceled` and one `unavailable` order **with items** (must not count in revenue).
- Delivered orders: one late (next day), one **same day but later time** (on time), one early, one with **NULL delivery date** (unknown).
- One valid order with **no items** (counts in AOV denominator).
- `freight_value` set on every item (must be ignored).
- A product with **NULL category**, one with an **untranslated** category.
- 12 categories in total, so the Top 10 cut and tie-break order are tested.

A second fixture returns a path that does not exist (error tests).

## Risks and things for Kunal to check

- **Number style**: decided (2026-10-31): English separators, "R$ 13,494,400.74" (research R8).
- **Spec example vs. data**: the spec's example "R$ 13.2M" is only an
  illustration; the real card will read "R$ 13.49M".
- **Constitution file is empty**: gates used AGENTS.md. Consider `/speckit-constitution`.
- **Branch naming**: Spec Kit's folder is `001-static-dashboard`; the git branch is `v0c-static-dashboard`. Works as is (Spec Kit reads `.specify/feature.json`).

## Complexity Tracking

No violations to justify.
