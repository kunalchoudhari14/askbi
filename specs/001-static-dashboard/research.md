# Research: Default Dashboard (v0-c)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-31

Each section: **Decision** (what we chose), **Rationale** (why), **Alternatives
considered** (what we rejected and why). All facts about the data were checked
with read-only queries against `data/olist.db` on 2026-10-31.

## Facts about the data (baseline for tests and the quickstart)

| Fact | Value |
|------|-------|
| All orders | 99,441 |
| Canceled + unavailable | 1,234 |
| Valid orders | 98,207 |
| Revenue (item prices, valid orders) | R$ 13,494,400.74 (1,349,440,074 cents) |
| AOV | R$ 137.41 |
| Delivered orders | 96,478 (8 with no delivery date) |
| Late (delivered on a later calendar day than estimate) | 6,534 of 96,470 → 6.8% |
| Purchase-date range | 2016-09-04 → 2018-10-17 (26 calendar months) |
| Months with no orders at all inside range | 2016-11 |
| Months with orders but zero valid revenue | 2018-10 (4 orders, all canceled) |
| Valid orders with no items | 8 |
| Prices with more than 2 decimals | 0 |
| Items whose product is missing from `products` | 0 |
| Categories after grouping | 74; "Unknown Category" ranks 21st |
| Untranslated categories | `pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos` |
| Top 10 (highest first) | health_beauty, watches_gifts, bed_bath_table, sports_leisure, computers_accessories, furniture_decor, housewares, cool_stuff, auto, garden_tools |
| Indexes in the database | none (queries still run in < 0.1 s each) |

Dates are stored as text like `2017-10-02 10:56:33`; estimated dates are
midnight timestamps like `2017-10-18 00:00:00`.

## R1. How to open the database read-only

**Decision**: One helper, `core/db.py::get_connection()`, opens
`data/olist.db` with an SQLite URI in read-only mode
(`file:<path>?mode=ro`, `uri=True`). Every query goes through
`core/db.py::run_query(sql, params)`, which opens a connection, runs one
`SELECT` with `?` parameters, returns a pandas DataFrame and always closes the
connection (`try/finally`).

**Rationale**: `mode=ro` makes SQLite itself refuse any write, so "read-only"
is enforced by the database engine, not just by our good behaviour. It also
means a missing file raises an error instead of silently creating an empty
`olist.db` (the default `sqlite3.connect` would create one, and the dashboard
would then show zeros, which FR-013 forbids). One `run_query` function is the
single "front door" for data (FR-015): v0-d filters and v1 row-level security
plug in there.

**Alternatives considered**:
- Plain `sqlite3.connect(path)`: can write and creates missing files. Rejected.
- `PRAGMA query_only = ON` alone: blocks writes but still creates a missing
  file. Rejected as the main guard (could be added later as a second layer).
- Keeping one connection open in Streamlit with `@st.cache_resource`: faster,
  but SQLite connections are tied to one thread by default and Streamlit
  serves each session in its own thread. Opening per call costs milliseconds.
  Rejected for now.

## R2. Errors when the data is missing or broken

**Decision**: `core/db.py` defines `DataUnavailableError`. `run_query` catches
`sqlite3.OperationalError` and `sqlite3.DatabaseError` (file missing,
unreadable, table missing) and re-raises them as `DataUnavailableError` with a
plain message, **keeping the original error attached**:
`raise DataUnavailableError("...") from err`. The page catches only that error and shows `st.error(...)`; a
developer also sees "rebuild it with `python load_data.py`".

**Rationale**: The page shouldn't need to know SQLite's error types. One named
error keeps the page code simple and matches "catch specific exceptions".
`from err` keeps the real SQLite cause (for example "no such column") in the
terminal traceback, so a bug in our own SQL is still easy to find even though
the user only sees the friendly message. *(Decided by Kunal, 2026-10-31.)*

**Alternatives considered**: Returning `None` from every function (forces
`if x is None` checks everywhere, easy to forget). Letting the raw error crash
the page (FR-013 forbids it).

## R3. Exact money: making "monthly total = Revenue card" hold to the cent

**Decision**: Do money sums in **integer cents** inside SQL:
`SUM(CAST(ROUND(price * 100) AS INTEGER))`. Core functions return cents as
`int`; only the formatting step turns cents into "R$ …". AOV is computed with
`decimal.Decimal` (cents ÷ valid orders, rounded half-up to the cent).

**Rationale**: Prices are stored as floating-point numbers (`REAL`). Floats
can't hold most decimals exactly, so adding the same prices in a different
grouping (by month vs. all at once) can differ in the last digit. Whole
numbers add exactly, so FR-008 / SC-003 (difference R$ 0.00) is guaranteed by
arithmetic, not by luck. We confirmed no price has more than 2 decimals, so
converting to cents loses nothing.

**Alternatives considered**: Summing floats and rounding at the end (usually
equal, not guaranteed). Deriving the Revenue card *from* the monthly sum
(hides a real mismatch instead of preventing it; we still test both agree).

## R4. One definition of "valid order", reused everywhere

**Decision**: `core/kpis.py` holds the status rules as constants
(`INVALID_STATUSES = ("canceled", "unavailable")`, `DELIVERED_STATUS =
"delivered"`) and one shared SQL fragment for "item lines of valid orders",
used by the Revenue, monthly and category queries. Status values are passed as
`?` parameters, never pasted into the SQL text.

**Rationale**: FR-002 says one set of definitions everywhere. If the rule
lives in one place, the three money numbers can't drift apart.

**Alternatives considered**: A SQL `VIEW` in the database (needs a write to
create; we're read-only, and `load_data.py` would have to own it). Repeating
the `WHERE` in each query (drift risk).

## R5. Late-delivery %

**Decision**: Over orders with status `delivered`:
`judged = delivered date IS NOT NULL`, `late = date(delivered) >
date(estimated)`, `unknown = delivered date IS NULL`. Rate = late ÷ judged,
or `None` when judged is 0. One query returns all three counts.

**Rationale**: SQLite's `date()` drops the time of day, which implements
"same calendar day counts as on time" (spec assumption). Returning the
counts (not just the %) lets the card show the "8 excluded" line and lets
tests check each part.

**Alternatives considered**: Comparing full timestamps (would mark a
same-day 15:00 delivery against a 00:00 estimate as late; wrong per spec).

## R6. Monthly trend with zero months filled in

**Decision**: Two queries: (a) the first and last purchase month across **all**
orders; (b) revenue in cents per purchase month for valid orders. pandas
builds the complete list of months between (a)'s bounds
(`pd.period_range(..., freq="M")`) and fills missing months with 0.

**Rationale**: SQL `GROUP BY` can only return months that have rows, so gaps
(2016-11) and all-canceled months (2018-10) would disappear. The spec defines
the range by all orders, not only valid ones. pandas is already installed.

**Alternatives considered**: A recursive SQL CTE that generates months (works,
but harder to read and test for a learner).

## R7. Top 10 categories and labels

**Decision**: Group item lines of valid orders by
`COALESCE(english name, original name, 'unknown_category')`, using LEFT JOINs
to `products` and the translation table so no revenue is dropped. Order by
revenue descending, then name ascending (so ties are stable), `LIMIT ?` with
10. A pure function `format_category_label()` turns `bed_bath_table` into
"Bed Bath Table" (`replace("_", " ")` then capitalise each word). The
fallback `unknown_category` becomes "Unknown Category" through the same rule.

**Rationale**: One label rule for all three cases (translated, untranslated,
missing) keeps labels consistent and never blank (SC-005). LEFT JOIN keeps
the door open for products with no row (none today, but safe).

**Alternatives considered**: `str.title()` (turns "pc's" into "Pc'S" and
similar oddities; a split-and-capitalise per word is more predictable).

## R8. Number formatting

**Decision**: Pure functions in `core/formatting.py`:
- `format_brl(cents, abbreviate=False)` → "R$ 13,494,400.74"; with
  `abbreviate=True` → "R$ 13.49M" (K/M/B, 2 decimals).
- `format_count(n)` → "99,441".
- `format_percent(rate)` → "6.8%" (one decimal).
- Any `None` → "—" (FR-014).

English-style separators (comma for thousands, dot for decimals), matching the
spec's own example "R$ 13.2M" and the English UI.

**Rationale**: Pure functions are easy to test and keep the page free of
logic. The abbreviated value goes on the card; the full value goes in the
caption under it (FR-011).

**Alternatives considered**: Brazilian style "R$ 13.494.400,74" via
`locale` (depends on the Mac's installed locales and behaves differently in
CI).

**Status: decided by Kunal (2026-10-31)**: keep English style,
"R$ 13,494,400.74".

## R9. Charts

**Decision**: Plotly figures built by pure functions in `core/charts.py`:
- Monthly revenue: **line chart with markers** (`plotly.graph_objects`),
  x = month, y = revenue in R$; hover shows "Mon YYYY" and R$ with 2 decimals.
- Top 10: **horizontal bar chart**, highest at the top, title "Top 10 product
  categories by revenue", hover shows R$.

The page only calls `st.plotly_chart(fig)`.

**Rationale**: A line shows trend over time best; horizontal bars fit long
category names. Building figures in `core/` (no Streamlit calls) means tests
can check "10 bars, title contains Top 10, order is descending" without a
browser.

**Alternatives considered**: Vertical bars for categories (long labels get
rotated and hard to read). `plotly.express` (fine, but `graph_objects` gives
explicit hover templates with fewer surprises). Building figures in the page
(not testable).

## R10. Showing definitions (FR-012, SC-004)

**Decision**: Two layers, both from one text source (`core/definitions.py`,
a dict of plain-language definitions keyed by KPI/chart):
1. Each KPI card passes its definition as `help=` to `st.metric` (a "?" icon
   that shows the text on hover: zero clicks).
2. One `st.expander("How these numbers are defined")` below the cards lists
   all six definitions (one click).

**Rationale**: Hover is fastest for one card; the expander is the place to
read everything together, and it covers the charts. One source of text means
the tooltip and the expander can't disagree.

**Alternatives considered**: Always-visible paragraphs (clutters the page);
a separate "Definitions" page (more than one click).

## R11. Caching and speed (SC-001)

**Decision**: The page wraps one call, `core.dashboard.load_dashboard_data()`,
in a page-level function decorated with `@st.cache_data` (no TTL, because the
data is a static snapshot). Errors are not cached (Streamlit doesn't cache a
function that raised), so a fixed database is picked up on the next reload.

**Rationale**: All queries together take well under 1 second on the real data;
caching makes repeat visits instant. `@st.cache_data` lives in the page
because `core/` must not import Streamlit UI.

**Alternatives considered**: Caching inside `core/` (would tie core to
Streamlit). Adding indexes (needs a write; not required for speed today).

## R12. Testing without the real database

**Decision**: `tests/conftest.py` builds a **tiny SQLite file** in pytest's
`tmp_path` with the same table and column names as the real database and a
handful of hand-made rows that hit every edge case (canceled, unavailable,
same-day delivery, missing delivery date, valid order with no items, missing
category, untranslated category, a gap month, freight that must be ignored,
12 categories so the Top 10 cut is tested). Every core function takes an
optional `db_path` argument (default: the real `data/olist.db`), so tests
pass the fixture path.

**Rationale**: CI never has `olist.db` (it's git-ignored and 100+ MB). Small
hand-made data also lets us know the right answer by hand, which is the point
of a test. Checks against the real numbers live in the quickstart instead.

**Alternatives considered**: Tests that `skip` when `olist.db` is missing
(AGENTS.md: don't skip tests to make them pass; and CI would never run them).
Committing a sample database (AGENTS.md: never commit `data/`).

## R13. Role-aware error hint

**Decision**: Add `ROLE_END_USER` and `ROLE_DEVELOPER` constants to
`core/auth.py`. The dashboard uses `ROLE_DEVELOPER` to decide whether to add
the "rebuild with `python load_data.py`" hint. `app.py` **must** also switch
to `ROLE_DEVELOPER` / `ROLE_END_USER` in this same feature, so no role name is
typed as a raw string anywhere. *(Decided by Kunal, 2026-10-31.)*

**Rationale**: AGENTS.md asks for constants instead of repeated magic strings.
The KPI content is identical for both roles (FR-001); only the error hint
differs (spec edge case).
