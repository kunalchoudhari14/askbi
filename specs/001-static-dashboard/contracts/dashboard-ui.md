# Contract: Dashboard page layout (`pages/dashboard.py`)

**Feature**: [../spec.md](../spec.md) | **Core API**: [core-api.md](core-api.md)

What a logged-in user of **either role** sees, top to bottom. The page only
calls `core/` and Streamlit; it contains no SQL and no calculations.

## Layout

```text
Dashboard                                                     (st.title)
┌──────────────┬──────────────┬────────────────────┬────────────────────┐
│ Revenue    ? │ Orders     ? │ Average order    ? │ Late-delivery %  ? │  st.columns(4) + st.metric(help=…)
│ R$ 13.49M    │ 99,441       │ value  R$ 137.41   │ 6.8%               │
│ R$ 13,494,…  │ 1,234 cancel-│                    │ 8 delivered orders │  st.caption
│   (full)     │ ed or unav.  │                    │ excluded (no date) │
└──────────────┴──────────────┴────────────────────┴────────────────────┘
▸ How these numbers are defined                                 (st.expander, 6 definitions)

Monthly revenue                                          (line chart, full width)
Top 10 product categories by revenue                     (horizontal bars, full width)
```

## Rules

| # | Rule | Spec |
|---|------|------|
| UI-1 | Same content for `end_user` and `developer`. | FR-001, SC-006 |
| UI-2 | Card labels exactly: "Revenue", "Orders", "Average order value", "Late-delivery %". | US1-1 |
| UI-3 | Revenue card: abbreviated value; caption shows the full value to the cent. | FR-011 |
| UI-4 | Orders caption: "{n} canceled or unavailable". | FR-004 |
| UI-5 | Late-delivery caption: "{n} delivered orders excluded (no delivery date)"; shown even when n = 0. | FR-006, edge case |
| UI-6 | Each card's `help` text = `KPI_DEFINITIONS[key]`; expander lists all six. | FR-012 |
| UI-7 | `None` values show "—". | FR-014 |
| UI-8 | No filters, date pickers, status chart or AI features. | FR-016 |
| UI-9 | Data load is wrapped in a page function with `@st.cache_data`. | SC-001 |

## Error state (FR-013)

If `load_dashboard_data()` raises `DataUnavailableError`:
- Everyone sees `st.error("The data is unavailable right now, so the dashboard can't be shown.")`.
- A developer (`st.session_state["role"] == ROLE_DEVELOPER`) also sees
  `st.info("Rebuild the database with `python load_data.py`.")`.
- Then `st.stop()`: no cards or charts with zeros are drawn.
