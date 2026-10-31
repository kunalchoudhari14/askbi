# Quickstart: validate the Default Dashboard (v0-c)

**Feature**: [spec.md](spec.md) | **Contracts**: [contracts/](contracts/) | **Data model**: [data-model.md](data-model.md)

How to prove the feature works once it's built. Run everything from the
repo root.

## Prerequisites

- `.venv` set up with `requirements-dev.txt` (no new packages for this feature).
- `data/olist.db` built with `python load_data.py` (only for steps 3–4).
- `.streamlit/secrets.toml` with one `end_user` and one `developer` login.

```bash
source .venv/bin/activate
```

## 1. Quality gate (same as CI)

```bash
ruff check .
ruff format --check .
pytest
```

**Expected**: all clean, all tests pass. Tests use a tiny fixture database,
so they also pass in CI where `olist.db` doesn't exist.

## 2. Read-only and error-handling checks (covered by tests)

`tests/test_db.py` must show that:
- an `INSERT` through `get_connection()` fails;
- opening a missing path raises `DataUnavailableError` **and creates no file**;
- a bad query (e.g. a misspelled column) raises `DataUnavailableError` whose
  `__cause__` is the original `sqlite3` error.

## 3. Numbers against the real data

Start the app, log in as each role and open **Dashboard**:

```bash
streamlit run app.py
```

| Item | Expected (data as of 2026-10-31) |
|------|-----------------------------------|
| Revenue | R$ 13.49M; caption R$ 13,494,400.74 |
| Orders | 99,441; caption "1,234 canceled or unavailable" |
| Average order value | R$ 137.41 |
| Late-delivery % | 6.8%; caption "8 delivered orders excluded (no delivery date)" |
| Monthly chart | 26 points, Sep 2016 → Oct 2018; Nov 2016 and Oct 2018 at R$ 0 |
| Top 10 chart | Health Beauty, Watches Gifts, Bed Bath Table, Sports Leisure, Computers Accessories, Furniture Decor, Housewares, Cool Stuff, Auto, Garden Tools (in that order); title contains "Top 10" |

Independent hand check of the totals (read-only, optional):

```bash
python -c "import sqlite3; c=sqlite3.connect('file:data/olist.db?mode=ro', uri=True); print(c.execute(\"select sum(cast(round(i.price*100) as integer)) from order_items i join orders o on o.order_id=i.order_id where o.order_status not in ('canceled','unavailable')\").fetchone()); c.close()"
```

**Expected**: `(1349440074,)` = R$ 13,494,400.74, the same as the card.

## 4. Behaviour checks in the browser

| Scenario | Steps | Expected |
|----------|-------|----------|
| Definitions | Hover the "?" on each card; open "How these numbers are defined" | All 4 KPIs + 2 charts explained in ≤ 1 click (SC-004) |
| Same for both roles | Compare end_user and developer screens | Identical numbers and charts (SC-006) |
| Speed | Reload the page, then navigate away and back | First load < 3 s, repeat < 1 s (SC-001) |
| Hover | Hover a month and a bar | Month name + R$ value shown |
| Data missing | Temporarily rename `data/olist.db` to `data/olist.db.bak`, reload (clear cache with `C` in the app menu), then rename it back | Friendly error; developer also sees the `load_data.py` hint; no zeros shown (FR-013) |

The rename in the last row is fully undoable (rename back), and nothing is
deleted.
