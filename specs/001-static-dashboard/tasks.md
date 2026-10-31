---

description: "Task list for the Default Dashboard (v0-c)"
---

# Tasks: Default Dashboard (v0-c)

**Input**: Design documents from `specs/001-static-dashboard/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/core-api.md](contracts/core-api.md), [contracts/dashboard-ui.md](contracts/dashboard-ui.md), [quickstart.md](quickstart.md)

**Tests**: Required. AGENTS.md says every new `core/` function gets pytest tests, and Kunal asked for **each test task before its code task** (test-first: write the test, see it fail, then write the code that makes it pass).

**Organization**: Phases follow the plan's **9-step build order** (layer by layer), as Kunal asked. Every task inside a step still carries a `[US#]` label, so it can be traced back to its user story. Cross-cutting tasks (database helper, role constants, final checks) have no label.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can be done in parallel (different file, no dependency on an unfinished task)
- **[Story]**: US1 = KPI cards, US2 = monthly trend, US3 = Top 10 categories, US4 = definitions
- Every task names its exact file. Work one task at a time; Kunal reviews each before the next.

## Rules for every task

- **Test tasks**: write the tests, run `pytest`, and confirm the new tests **fail** (usually an `ImportError` or `AttributeError`, because the code doesn't exist yet). Don't write any app code in a test task.
- **Code tasks**: write only enough code to make that test task pass. Then `pytest` must be fully green and `ruff check .` and `ruff format --check .` must be clean.
- Follow AGENTS.md: type hints and a one-line docstring on every function and module, "why" comments, constants in CAPITALS, `?` placeholders only, `SELECT` only, `pathlib` paths, no Streamlit UI calls in `core/`.
- Test data lives only in pytest's `tmp_path`. Never read or write `data/olist.db` in tests.
- No new packages. No commits unless Kunal asks.

---

## Phase 1: Setup (Step 1a: test fixture database)

**Purpose**: A tiny hand-made database so every expected number can be worked out by hand and CI runs without `olist.db` ([research.md](research.md) R12).

- [ ] T001 Create `tests/conftest.py` with three pytest fixtures, using the **Fixture data** in the appendix at the end of this file:
  - `fixture_db_path`: writes a SQLite file in `tmp_path` with the four tables `orders`, `order_items`, `products` and `product_category_name_translation`. It uses the real column names from [data-model.md](data-model.md) Part 1, plus `freight_value` on `order_items`.
  - `empty_db_path`: the same four tables, but with no rows.
  - `missing_db_path`: a `tmp_path` path where no file exists.

  The fixtures may write freely, because they only touch `tmp_path`. Give the file a module docstring and give each fixture a type hint and a docstring.

---

## Phase 2: Foundational (Step 1b: read-only data access)

**Purpose**: The single front door for data (FR-015). **Every later phase depends on this.**

- [ ] T002 Write `tests/test_db.py` (red) for [contracts/core-api.md](contracts/core-api.md) § `core/db.py`:
  - `run_query("SELECT COUNT(*) AS n FROM orders", db_path=fixture_db_path)` returns a `pd.DataFrame` with `n == 8`.
  - A `?` parameter works: counting orders with `order_status = ?` and `("canceled",)` gives 1.
  - A write fails: `get_connection(fixture_db_path)` followed by an `INSERT INTO orders ...` raises `sqlite3.OperationalError`. Close the connection in `finally`.
  - Missing file: `run_query(..., db_path=missing_db_path)` raises `DataUnavailableError`, **and `missing_db_path.exists()` is still `False` afterwards**.
  - Bad SQL keeps its cause: `run_query("SELECT no_such_column FROM orders", db_path=fixture_db_path)` raises `DataUnavailableError` whose `__cause__` is an instance of `sqlite3.Error` (Kunal's decision, research R2).
  - `DB_PATH` ends with `data/olist.db`.
- [ ] T003 Implement `core/db.py` so that T002 passes:
  - `DB_PATH`, anchored with `Path(__file__).resolve().parent.parent`.
  - `class DataUnavailableError(Exception)`.
  - `get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection`, which opens `file:{path}?mode=ro` with `uri=True`.
  - `run_query(sql: str, params: Sequence[object] = (), db_path: Path = DB_PATH) -> pd.DataFrame`, which uses `pd.read_sql_query`, closes the connection in `try/finally`, and catches `sqlite3.Error` and re-raises it as `raise DataUnavailableError("...") from err`.
  - Add a comment explaining that `run_query` is where v0-d filters and v1 row-level security will go.

**Checkpoint**: The read-only data helper is proven by tests. User story work can start.

---

## Phase 3: Step 2: KPI queries in `core/kpis.py` (US1, US2, US3)

**Goal**: Every number on the dashboard comes from one tested function. Money is in integer cents ([research.md](research.md) R3, R4).

**Independent test**: `pytest tests/test_kpis.py` is green, and every value matches the hand-worked fixture answers in the appendix.

### Revenue and order counts (US1)

- [ ] T004 [US1] Write tests in `tests/test_kpis.py` (red):
  - `get_revenue_cents(fixture_db_path) == 81025`. This proves canceled and unavailable items and freight are excluded, and the 10.25 price is exact.
  - `get_revenue_cents(empty_db_path) == 0`.
  - `get_order_counts(fixture_db_path)` returns `OrderCounts(total=8, invalid=2)` with `.valid == 6`.
  - `OrderCounts` is frozen: assigning to a field raises `dataclasses.FrozenInstanceError`.
  - `get_order_counts(empty_db_path).valid == 0`.
- [ ] T005 [US1] Implement in `core/kpis.py`:
  - The constants `INVALID_STATUSES = ("canceled", "unavailable")`, `DELIVERED_STATUS = "delivered"`, `TOP_CATEGORY_LIMIT = 10` and `UNKNOWN_CATEGORY = "unknown_category"`.
  - One shared SQL fragment for "item lines of valid orders" (research R4), with statuses passed as `?` parameters.
  - Money summed as `SUM(CAST(ROUND(price * 100) AS INTEGER))`.
  - The frozen dataclass `OrderCounts(total: int, invalid: int)` with the property `valid` = `total - invalid` ("0 ≤ invalid ≤ total").
  - `get_revenue_cents(db_path: Path = DB_PATH) -> int`, returning 0 when SQL gives NULL.
  - `get_order_counts(db_path: Path = DB_PATH) -> OrderCounts`.

  All queries go through `core.db.run_query`.

### Average order value (US1)

- [ ] T006 [US1] Add tests to `tests/test_kpis.py` (red):
  - `calculate_aov_cents(81025, 6) == 13504`.
  - `calculate_aov_cents(5, 2) == 3`. This checks half-up rounding: 2.5 → 3, not 2.
  - `calculate_aov_cents(0, 0) is None`.
  - `calculate_aov_cents(100, 0) is None`.
- [ ] T007 [US1] Implement the pure function `calculate_aov_cents(revenue_cents: int, valid_orders: int) -> int | None` in `core/kpis.py`. It uses `decimal.Decimal` with `ROUND_HALF_UP` and returns `None` when `valid_orders == 0` (FR-005, FR-014). Add a why-comment explaining that Python's `round()` rounds 2.5 to 2.

### Late-delivery % (US1)

- [ ] T008 [US1] Add tests to `tests/test_kpis.py` (red):
  - `get_late_delivery(fixture_db_path) == LateDelivery(late=1, judged=3, unknown=1)`.
  - `.rate == pytest.approx(1 / 3)`.
  - Same-day order O1 does **not** count as late. This is covered by `late == 1`; put a comment on the assertion saying so.
  - `LateDelivery(late=0, judged=0, unknown=0).rate is None`.
  - `get_late_delivery(empty_db_path) == LateDelivery(0, 0, 0)`.
- [ ] T009 [US1] Implement in `core/kpis.py`:
  - The frozen dataclass `LateDelivery(late: int, judged: int, unknown: int)` with the property `rate -> float | None` ("`None` when `judged == 0`").
  - `get_late_delivery(db_path: Path = DB_PATH) -> LateDelivery`. One query over `order_status = ?` (`DELIVERED_STATUS`) compares `date(order_delivered_customer_date) > date(order_estimated_delivery_date)`. Add a why-comment explaining that `date()` drops the time of day, so same-day deliveries count as on time.

### Monthly revenue (US2)

- [ ] T010 [US2] Add tests to `tests/test_kpis.py` (red). For `get_monthly_revenue(fixture_db_path)`:
  - The columns are exactly `["month", "revenue_cents"]`.
  - `month` holds `pd.Period("2017-01", "M")`, `("2017-02")` and `("2017-03")`, in that order.
  - `revenue_cents` is `[42000, 0, 39025]`. February is zero-filled.
  - The sum `== get_revenue_cents(fixture_db_path)` (FR-008).

  `get_monthly_revenue(empty_db_path)` is empty and has the same two columns.
- [ ] T011 [US2] Implement `get_monthly_revenue(db_path: Path = DB_PATH) -> pd.DataFrame` in `core/kpis.py`:
  - Query A: the first and last `strftime('%Y-%m', order_purchase_timestamp)` across **all** orders.
  - Query B: cents per month for valid orders.
  - Fill the gaps with `pd.period_range(..., freq="M")`, reindex with 0 and keep `revenue_cents` as an integer (research R6).
  - Return an empty frame with the same columns when there are no orders.

### Category revenue (US3)

- [ ] T012 [US3] Add tests to `tests/test_kpis.py` (red):
  - `get_category_revenue(db_path=fixture_db_path)` has the columns `["category", "revenue_cents"]` and exactly 10 rows. In order, the categories are `health_beauty, watches_gifts, pc_gamer, unknown_category, bed_bath_table, sports_leisure, computers_accessories, furniture_decor, housewares, auto`, and the cents are `12000, 11000, 10000, 9000, 8000, 7000, 6000, 5000, 4000, 3000`.
  - The tie-break works: `auto` (3000) is in the list and `cool_stuff` (3000) is not, because ties sort by name.
  - `get_category_revenue(limit=None, db_path=fixture_db_path)` has 13 rows whose cents sum to `81025`, so no revenue is dropped.
  - `get_category_revenue(limit=3, ...)` returns 3 rows.
- [ ] T013 [US3] Implement `get_category_revenue(limit: int | None = TOP_CATEGORY_LIMIT, db_path: Path = DB_PATH) -> pd.DataFrame` in `core/kpis.py`:
  - LEFT JOIN `products` and `product_category_name_translation`.
  - Group by `COALESCE(english, original, ?)` with `UNKNOWN_CATEGORY` passed as a parameter.
  - `ORDER BY revenue_cents DESC, category ASC`.
  - Apply `LIMIT ?` only when `limit` is not `None`. Build the two fixed SQL variants as constants; don't format the SQL text (research R7).

**Checkpoint**: All six numbers are correct on the fixture.

---

## Phase 4: Step 3: Formatting in `core/formatting.py` (US1, US3)

**Goal**: All display text is decided in one tested place ([research.md](research.md) R8, English style decided by Kunal).

**Independent test**: `pytest tests/test_formatting.py` is green.

- [ ] T014 [P] [US1] Write `tests/test_formatting.py` (red) using `pytest.mark.parametrize`:
  - `format_brl`:
    - `1349440074` → `"R$ 13,494,400.74"`
    - `13741` → `"R$ 137.41"`
    - `0` → `"R$ 0.00"`
    - `None` → `"—"`
  - `format_brl(..., abbreviate=True)`:
    - `1349440074` → `"R$ 13.49M"`
    - `123456` → `"R$ 1.23K"`
    - `250000000000` → `"R$ 2.50B"`
    - `13741` → `"R$ 137.41"` (under 1,000 isn't abbreviated)
    - `None` → `"—"`
  - `format_count`: `99441` → `"99,441"`, `0` → `"0"`.
  - `format_percent`:
    - `0.067731` → `"6.8%"`
    - `1/3` → `"33.3%"`
    - `0.0` → `"0.0%"`
    - `None` → `"—"`
- [ ] T015 [US1] Implement `format_brl(cents: int | None, abbreviate: bool = False) -> str`, `format_count(n: int) -> str` and `format_percent(rate: float | None) -> str` in `core/formatting.py`. Add a constant `NO_VALUE = "—"` and work with whole cents, not floats, for the unabbreviated value.
- [ ] T016 [US3] Add tests to `tests/test_formatting.py` (red) for `format_category_label`:
  - `"bed_bath_table"` → `"Bed Bath Table"`
  - `"health_beauty"` → `"Health Beauty"`
  - `"pc_gamer"` → `"Pc Gamer"`
  - `"unknown_category"` → `"Unknown Category"`
  - `"auto"` → `"Auto"`
  - `"portateis_cozinha_e_preparadores_de_alimentos"` → `"Portateis Cozinha E Preparadores De Alimentos"`
- [ ] T017 [US3] Implement `format_category_label(key: str) -> str` in `core/formatting.py`. Split on `_` and capitalise each word (not `str.title()`; see research R7). Stored names are unchanged.

---

## Phase 5: Step 4: Definitions in `core/definitions.py` (US4)

**Goal**: One source of plain-English definitions for tooltips and the expander ([research.md](research.md) R10, FR-012).

**Independent test**: `pytest tests/test_definitions.py` is green.

- [ ] T018 [P] [US4] Write `tests/test_definitions.py` (red):
  - `KPI_DEFINITIONS` has exactly the keys `{"revenue", "orders", "aov", "late_delivery", "monthly_revenue", "top_categories"}`, and every value is a non-empty `str`.
  - `revenue` mentions "canceled", "unavailable" and "freight".
  - `orders` mentions "all".
  - `aov` mentions "valid orders".
  - `late_delivery` mentions "same day" and "no delivery date".
  - `monthly_revenue` mentions "purchase date".
  - `top_categories` mentions "Top 10" and "Unknown Category".

  The checks are case-insensitive.
- [ ] T019 [US4] Implement `core/definitions.py` with the `KPI_DEFINITIONS: dict[str, str]` constant. Write one or two sentences per key that restate FR-002 to FR-010 in plain English.

---

## Phase 6: Step 5: Charts in `core/charts.py` (US2, US3)

**Goal**: Plotly figures built and tested without a browser ([research.md](research.md) R9).

**Independent test**: `pytest tests/test_charts.py` is green.

- [ ] T020 [P] [US2] Write `tests/test_charts.py` (red) for `build_monthly_revenue_chart(monthly)`. Build `monthly` by hand as a 3-row DataFrame using the T010 values. Check that:
  - it returns a `go.Figure` with exactly one `go.Scatter` trace whose `mode` contains `"lines"` and `"markers"`;
  - it has 3 points in month order;
  - y is `[420.00, 0.00, 390.25]` (cents ÷ 100);
  - `hovertemplate` contains `"R$"`.
- [ ] T021 [US2] Implement `build_monthly_revenue_chart(monthly: pd.DataFrame) -> go.Figure` in `core/charts.py`:
  - x = month start dates, y = revenue in R$.
  - Hover shows the month as "Mon YYYY" and R$ with thousands separators and 2 decimals.
  - Axis titles are "Month" and "Revenue (R$)".
- [ ] T022 [US3] Add tests to `tests/test_charts.py` (red) for `build_top_categories_chart(categories)`. Build `categories` by hand as a 10-row frame using the T012 values. Check that:
  - there is exactly one `go.Bar` trace with `orientation == "h"` and 10 bars;
  - the labels are formatted (`"Health Beauty"`, `"Pc Gamer"` and `"Unknown Category"` are present, with no `_` in any label);
  - the highest bar is at the top: the first y label is `"Health Beauty"` and `layout.yaxis.autorange == "reversed"`;
  - `layout.title.text` contains `"Top 10"`;
  - `hovertemplate` contains `"R$"`.
- [ ] T023 [US3] Implement `build_top_categories_chart(categories: pd.DataFrame) -> go.Figure` in `core/charts.py`. Labels go through `format_category_label` and values are cents ÷ 100. Use the title "Top 10 product categories by revenue" and `yaxis.autorange="reversed"`, with a why-comment explaining that Plotly draws the first bar at the bottom by default.

---

## Phase 7: Step 6: One bundle for the page in `core/dashboard.py` (US1)

**Goal**: The page makes one call and gets everything ([data-model.md](data-model.md) `DashboardData`). It is labelled US1 because the cards need it first; the bundle also carries the US2 and US3 data.

**Independent test**: `pytest tests/test_dashboard.py` is green.

- [ ] T024 [US1] Write `tests/test_dashboard.py` (red). For `load_dashboard_data(fixture_db_path)`, check:
  - `revenue_cents == 81025`
  - `orders == OrderCounts(8, 2)`
  - `aov_cents == 13504`
  - `late_delivery == LateDelivery(1, 3, 1)`
  - the invariant `monthly_revenue["revenue_cents"].sum() == revenue_cents`
  - `len(top_categories) == 10`, sorted descending
  - the dataclass is frozen

  `load_dashboard_data(empty_db_path).aov_cents is None`, and `load_dashboard_data(missing_db_path)` raises `DataUnavailableError`.
- [ ] T025 [US1] Implement `core/dashboard.py`:
  - The frozen dataclass `DashboardData` with the fields `revenue_cents: int`, `orders: OrderCounts`, `aov_cents: int | None`, `late_delivery: LateDelivery`, `monthly_revenue: pd.DataFrame` and `top_categories: pd.DataFrame`.
  - `load_dashboard_data(db_path: Path = DB_PATH) -> DashboardData`, which calls the `core/kpis.py` functions and lets `DataUnavailableError` pass through unchanged.

**Checkpoint**: All `core/` logic is done and tested. Only the drawing remains.

---

## Phase 8: Step 7: Role constants in `core/auth.py`

**Purpose**: No raw role strings anywhere ([research.md](research.md) R13).

- [ ] T026 [P] Update `tests/test_auth.py` (red):
  - Add `test_role_constants` asserting `auth.ROLE_END_USER == "end_user"` and `auth.ROLE_DEVELOPER == "developer"`.
  - Replace the test file's local `END_USER = "end_user"` with `auth.ROLE_END_USER`.

  The three existing tests must keep their meaning.
- [ ] T027 Add `ROLE_END_USER = "end_user"` and `ROLE_DEVELOPER = "developer"` to `core/auth.py`, and use them in its module docstring and `__main__` comments where the strings appear. `check_login` behaviour is unchanged.

---

## Phase 9: Step 8: The page `pages/dashboard.py` (US1–US4)

**Goal**: Draw `DashboardData` exactly as [contracts/dashboard-ui.md](contracts/dashboard-ui.md) describes. The page holds UI only: no SQL and no calculations.

**About tests here**: The plan keeps the page thin and checks it by hand with [quickstart.md](quickstart.md), because AGENTS.md requires automated tests for `core/` code. For each page task, the "test before code" is the **quickstart check named in the task**: read it first, build the task, then run the check. *Decided by Kunal (2026-10-31): no AppTest in v0-c; added to the Build queue as a follow-up chore.*

- [ ] T028 [US1] Replace the placeholder in `pages/dashboard.py`. Do the following:
  - Update the module docstring.
  - Order imports stdlib → third-party → `core`.
  - Add `st.title("Dashboard")`.
  - Add a page function `load_data() -> DashboardData` decorated with `@st.cache_data` that calls `load_dashboard_data()` (UI-9).
  - Add the error state: catch `DataUnavailableError`, then show `st.error("The data is unavailable right now, so the dashboard can't be shown.")`. If `st.session_state.get("role") == ROLE_DEVELOPER`, also show `st.info` with the `python load_data.py` hint. Then call `st.stop()` (FR-013).

  Check: quickstart §4 "Data missing" row (rename the database and rename it back). The error appears and no zeros are drawn.
- [ ] T029 [US1] Add the four KPI cards in `pages/dashboard.py` with `st.columns(4)` and `st.metric(label, value, help=KPI_DEFINITIONS[key])`:
  - Labels exactly "Revenue", "Orders", "Average order value" and "Late-delivery %" (UI-2).
  - Revenue value is `format_brl(..., abbreviate=True)`, with the full `format_brl(...)` in `st.caption` (UI-3).
  - Orders caption is `"{format_count(invalid)} canceled or unavailable"` (UI-4).
  - Late-delivery caption is `"{format_count(unknown)} delivered orders excluded (no delivery date)"`, always shown (UI-5).
  - `None` shows "—" through the formatters (UI-7).

  Check: the four card rows in quickstart §3, for both roles.
- [ ] T030 [US4] Add `st.expander("How these numbers are defined")` below the cards in `pages/dashboard.py`. It lists all six `KPI_DEFINITIONS` entries with readable headings (UI-6). Check: the quickstart §4 "Definitions" row (≤ 1 click, SC-004).
- [ ] T031 [US2] Add the monthly revenue chart to `pages/dashboard.py` with `st.plotly_chart(build_monthly_revenue_chart(data.monthly_revenue))`, under a "Monthly revenue" subheader. Check: the quickstart §3 "Monthly chart" row (26 points, Nov 2016 and Oct 2018 at R$ 0) and the §4 "Hover" row.
- [ ] T032 [US3] Add the Top 10 chart to `pages/dashboard.py` with `st.plotly_chart(build_top_categories_chart(data.top_categories))`. Check: the quickstart §3 "Top 10 chart" row (exact order) and the §4 "Hover" row.

**Checkpoint**: The dashboard is complete for both roles.

---

## Phase 10: Step 9: `app.py` uses role constants (required)

- [ ] T033 Update `app.py`: import `ROLE_DEVELOPER` (and `ROLE_END_USER` where a role string appears in code) from `core.auth`, and replace `st.session_state["role"] == "developer"` with the constant. Don't leave unused imports (Ruff F401). Navigation logic is otherwise unchanged. Check: log in as each role. The end user sees Dashboard + Ask; the developer also sees Developer; Log out still works.

---

## Phase 11: Polish and Definition of Done

- [ ] T034 [P] Update the `core/__init__.py` module docstring so it lists the new modules (`db`, `kpis`, `dashboard`, `formatting`, `charts`, `definitions`) in one line each.
- [ ] T035 Rule check by search, reporting results to Kunal:
  - `grep -rniE "select|sqlite3" pages/ app.py` finds nothing (no SQL outside `core/`).
  - `grep -rnE "\"(developer|end_user)\"" app.py pages/` finds nothing (no raw role strings).
  - `grep -rn "import streamlit" core/` shows only `core/auth.py`, which already existed (no Streamlit in new `core/` modules).
  - `grep -rniE "insert|update|delete|drop|alter" core/` finds nothing outside comments and docstrings.
- [ ] T036 Run the Definition of Done checks: `ruff check .`, `ruff format --check .` and `pytest`. All must be clean and green.
- [ ] T037 Run the manual validation in [quickstart.md](quickstart.md) §3–§4 for **both roles**, and record each actual value next to the expected one in the summary for Kunal.
- [ ] T038 Mark every finished task `[X]` in this file, then give Kunal the short summary (AGENTS.md Definition of Done §5): what changed, which files, why, and anything to check.

---

## Dependencies & Execution Order

### Phase dependencies

```text
Phase 1 (T001) → Phase 2 (T002–T003) → Phase 3 (T004–T013)
                                     ↘ Phase 4 (T014–T017)   ┐
                                     ↘ Phase 5 (T018–T019)   ├→ Phase 7 (T024–T025) → Phase 9 (T028–T032) → Phase 10 (T033) → Phase 11
                     Phase 4 (T017) → Phase 6 (T020–T023)    ┘
Phase 8 (T026–T027) can be done any time before Phase 9 (the page imports ROLE_DEVELOPER).
```

- Phase 3 tasks run in order (they share `core/kpis.py` and `tests/test_kpis.py`).
- Phase 6 needs `format_category_label` (T017) for the Top 10 chart.
- Phase 7 needs Phases 3–6. Phase 9 needs Phases 7 and 8. T033 needs T027.
- Within each pair, the **test task comes first** and must be red before its code task.

### User story traceability

| Story | Tasks |
|-------|-------|
| US1 KPI cards (P1) | T004–T009, T014–T015, T024–T025, T028–T029 |
| US2 Monthly trend (P2) | T010–T011, T020–T021, T031 |
| US3 Top 10 categories (P3) | T012–T013, T016–T017, T022–T023, T032 |
| US4 Definitions (P2) | T018–T019, T030 |
| Cross-cutting | T001–T003, T026–T027, T033–T038 |

## Parallel Opportunities

Kunal reviews one task at a time, so the default is to work in order. Tasks marked `[P]` touch their own file and could be done alongside the current phase:

```text
After T003:  T014 (tests/test_formatting.py), T018 (tests/test_definitions.py), T020 (tests/test_charts.py)
Any time:    T026 (tests/test_auth.py) → T027 (core/auth.py)
Phase 11:    T034 (core/__init__.py) alongside T035
```

## Implementation Strategy

1. **Foundation first** (T001–T003): the read-only helper is proven before any number is written.
2. **Numbers next, test-first** (T004–T025): each KPI is a red→green pair small enough to review in one sitting. The fixture's hand-worked answers are the yardstick.
3. **Stop and validate before the UI**: after T025, `pytest` proves every requirement that can be automated (FR-002 to FR-010, FR-013 to FR-015 at the `core/` level).
4. **Draw the page** (T028–T032): one visible piece per task, each checked against the quickstart.
5. **Finish** (T033–T038): constants in `app.py`, rule checks, Definition of Done, summary.

Note: because the build goes by layer, the first thing visible in the browser arrives in Phase 9. The earlier phases are verified by tests. The first useful version (MVP) is US1: T001–T009, T014–T015, T024–T025 and T028–T029, plus T026–T027 for the role constant.

---

## Appendix: Fixture data (for T001)

All dates are text in `YYYY-MM-DD HH:MM:SS` format. Every `order_items` row has `freight_value = 10.00`, which must never count. `order_item_id` is 1, 2, … within each order.

### `orders`

| order_id | order_status | order_purchase_timestamp | order_delivered_customer_date | order_estimated_delivery_date | Why it's here |
|---|---|---|---|---|---|
| O1 | delivered | 2017-01-10 10:00:00 | 2017-01-20 15:00:00 | 2017-01-20 00:00:00 | Same day, later time → **on time** |
| O2 | delivered | 2017-01-15 09:00:00 | 2017-01-25 09:00:00 | 2017-01-24 00:00:00 | Next day → **late** |
| O3 | delivered | 2017-03-05 12:00:00 | 2017-03-10 12:00:00 | 2017-03-20 00:00:00 | Early |
| O4 | delivered | 2017-03-06 12:00:00 | NULL | 2017-03-25 00:00:00 | **Lateness unknown** |
| O5 | shipped | 2017-03-07 12:00:00 | NULL | 2017-03-28 00:00:00 | Valid, not delivered |
| O6 | canceled | 2017-01-12 12:00:00 | NULL | 2017-01-30 00:00:00 | Invalid, **has items** |
| O7 | unavailable | 2017-03-08 12:00:00 | NULL | 2017-03-30 00:00:00 | Invalid, **has items** |
| O8 | processing | 2017-03-09 12:00:00 | NULL | 2017-03-31 00:00:00 | Valid, **no items** |

There are no February orders, so February must be zero-filled.

### `products` and `product_category_name_translation`

| product_id | product_category_name | English name in translation table |
|---|---|---|
| P01 | beleza_saude | health_beauty |
| P02 | relogios_presentes | watches_gifts |
| P03 | cama_mesa_banho | bed_bath_table |
| P04 | esporte_lazer | sports_leisure |
| P05 | informatica_acessorios | computers_accessories |
| P06 | moveis_decoracao | furniture_decor |
| P07 | utilidades_domesticas | housewares |
| P08 | cool_stuff | cool_stuff |
| P09 | automotivo | auto |
| P10 | ferramentas_jardim | garden_tools |
| P11 | pc_gamer | *(no row: untranslated)* |
| P12 | NULL | *(no category)* |
| P13 | brinquedos | toys |

### `order_items`

| order_id | product_id | price |
|---|---|---|
| O1 | P01 | 120.00 |
| O1 | P02 | 110.00 |
| O2 | P11 | 100.00 |
| O2 | P12 | 90.00 |
| O3 | P03 | 80.00 |
| O3 | P04 | 70.00 |
| O3 | P13 | 10.25 |
| O4 | P05 | 60.00 |
| O4 | P06 | 50.00 |
| O5 | P07 | 40.00 |
| O5 | P08 | 30.00 |
| O5 | P09 | 30.00 |
| O5 | P10 | 20.00 |
| O6 | P01 | 500.00 |
| O7 | P13 | 400.00 |

### Hand-worked answers

| Item | Answer |
|---|---|
| Orders total / invalid / valid | 8 / 2 / 6 |
| Revenue | 81,025 cents (R$ 810.25). O6's 500.00 and O7's 400.00 are excluded. |
| AOV | 81025 ÷ 6 = 13,504.17 → **13,504 cents** |
| Late / judged / unknown | 1 / 3 / 1 → 33.3% |
| Monthly cents | 2017-01: 42,000 · 2017-02: 0 · 2017-03: 39,025 (sum 81,025) |
| Top 10 | health_beauty 12000, watches_gifts 11000, pc_gamer 10000, unknown_category 9000, bed_bath_table 8000, sports_leisure 7000, computers_accessories 6000, furniture_decor 5000, housewares 4000, auto 3000 |
| Outside the Top 10 | cool_stuff 3000 (loses the tie by name), garden_tools 2000, toys 1025 |
