# Data Model: Default Dashboard (v0-c)

**Feature**: [spec.md](spec.md) | **Research**: [research.md](research.md)

The dashboard only **reads** data. This file has two parts: the source tables
it reads (already in `data/olist.db`, unchanged), and the result objects that
`core/` hands to the page.

## Part 1: Source tables (read-only)

Only the columns the dashboard uses are listed. All are stored as `TEXT` or
`REAL` by `load_data.py`; there are no indexes or foreign keys.

| Table | Columns used | Notes |
|-------|--------------|-------|
| `orders` | `order_id`, `order_status`, `order_purchase_timestamp`, `order_delivered_customer_date`, `order_estimated_delivery_date` | One row per order. Dates are text `YYYY-MM-DD HH:MM:SS`; delivered date can be NULL. |
| `order_items` | `order_id`, `product_id`, `price` | One row per item line. `freight_value` is deliberately **not** used (freight is not revenue). |
| `products` | `product_id`, `product_category_name` | Category can be NULL (≈610 products). |
| `product_category_name_translation` | `product_category_name`, `product_category_name_english` | Two categories have no row here. |

Relationships: `orders 1 ── * order_items * ── 1 products * ── 0..1 translation`.

### Derived rules (FR-002), defined once in `core/kpis.py`

| Term | Rule |
|------|------|
| Valid order | `order_status NOT IN ('canceled', 'unavailable')` (values passed as `?` parameters) |
| Revenue | `SUM` of `price` in **integer cents** over item lines of valid orders |
| Delivered order | `order_status = 'delivered'` |
| Late | delivered, delivered date not NULL, `date(delivered) > date(estimated)` |
| Lateness unknown | delivered, delivered date NULL |
| Order month | `strftime('%Y-%m', order_purchase_timestamp)` |
| Category key | `COALESCE(english name, original name, 'unknown_category')` |

## Part 2: Result objects (returned by `core/`)

Plain, immutable Python dataclasses (`@dataclass(frozen=True)`) or pandas
DataFrames. No Streamlit types. Money is always **integer cents** until the
formatting step.

### `OrderCounts`

| Field | Type | Meaning | Rule |
|-------|------|---------|------|
| `total` | `int` | All orders, every status | ≥ 0 |
| `invalid` | `int` | Canceled + unavailable | 0 ≤ invalid ≤ total |
| `valid` | `int` (property) | `total - invalid` | ≥ 0 |

### `LateDelivery`

| Field | Type | Meaning | Rule |
|-------|------|---------|------|
| `late` | `int` | Delivered later than estimate (calendar day) | 0 ≤ late ≤ judged |
| `judged` | `int` | Delivered with a known delivery date | ≥ 0 |
| `unknown` | `int` | Delivered with no delivery date (excluded) | ≥ 0 |
| `rate` | `float \| None` (property) | `late / judged` | `None` when `judged == 0` (shows "—") |

### `DashboardData`

Everything the page needs, from one call (`load_dashboard_data()`).

| Field | Type | Meaning |
|-------|------|---------|
| `revenue_cents` | `int` | Revenue card |
| `orders` | `OrderCounts` | Orders card (+ secondary line) |
| `aov_cents` | `int \| None` | AOV card; `None` when `orders.valid == 0` |
| `late_delivery` | `LateDelivery` | Late-delivery card (+ "N excluded" line) |
| `monthly_revenue` | `pd.DataFrame` | Columns `month` (`pd.Period`, monthly), `revenue_cents` (`int`); one row per calendar month first→last, zero-filled, ascending |
| `top_categories` | `pd.DataFrame` | Columns `category` (stored key, e.g. `health_beauty`), `revenue_cents` (`int`); ≤ 10 rows, highest first, ties broken by name |

**Invariants (tested)**:
- `monthly_revenue["revenue_cents"].sum() == revenue_cents` (FR-008).
- `aov_cents == round_half_up(revenue_cents / orders.valid)`.
- `top_categories` is sorted descending and has `min(10, number of categories)` rows.
- Sum over **all** categories (no limit) `== revenue_cents` (no revenue dropped).

### `KPI_DEFINITIONS`

A constant `dict[str, str]` in `core/definitions.py`, keyed by
`"revenue"`, `"orders"`, `"aov"`, `"late_delivery"`, `"monthly_revenue"`,
`"top_categories"`. Each value is one or two plain-English sentences that
restate the rules above (FR-012). Used for both the card tooltips and the
definitions expander.

### Display labels (not stored)

`format_category_label(key)`: underscores → spaces, each word capitalised.
`health_beauty` → "Health Beauty", `pc_gamer` → "Pc Gamer",
`unknown_category` → "Unknown Category". Stored names never change.

## State transitions

None. The data is a static snapshot and the dashboard never writes.
