"""Shared pytest fixtures: tiny hand-made Olist databases for the core/ tests.

pytest loads this file automatically before any test in tests/ runs, and any
test can ask for a fixture just by naming it as an argument.

Why a fake database: CI never has data/olist.db (it's git-ignored and huge),
and with a few hand-picked rows we can work out every right answer by hand.
The rows and the expected answers are listed in the "Fixture data" appendix
of specs/001-static-dashboard/tasks.md. Change both together.

Every file is written under pytest's tmp_path (a fresh temporary folder per
test), so the real data/olist.db is never opened or touched.
"""

import sqlite3
from pathlib import Path

import pytest

FIXTURE_DB_NAME = "olist_fixture.db"
EMPTY_DB_NAME = "olist_empty.db"
MISSING_DB_NAME = "does_not_exist.db"

# Same table and column names as the real database (see data-model.md), but
# only the columns the dashboard reads, plus freight_value so tests can prove
# freight is NOT counted as revenue.
SCHEMA_SQL = """
CREATE TABLE orders (
    order_id TEXT,
    customer_id TEXT,
    order_status TEXT,
    order_purchase_timestamp TEXT,
    order_delivered_customer_date TEXT,
    order_estimated_delivery_date TEXT
);
CREATE TABLE order_items (
    order_id TEXT,
    order_item_id INTEGER,
    product_id TEXT,
    price REAL,
    freight_value REAL
);
CREATE TABLE products (
    product_id TEXT,
    product_category_name TEXT
);
CREATE TABLE product_category_name_translation (
    product_category_name TEXT,
    product_category_name_english TEXT
);
"""

# (order_id, customer_id, status, purchased, delivered, estimated)
ORDERS = [
    # Same day as the estimate but later in the day → counts as ON TIME.
    (
        "O1",
        "C1",
        "delivered",
        "2017-01-10 10:00:00",
        "2017-01-20 15:00:00",
        "2017-01-20 00:00:00",
    ),
    # Delivered the day after the estimate → LATE.
    (
        "O2",
        "C2",
        "delivered",
        "2017-01-15 09:00:00",
        "2017-01-25 09:00:00",
        "2017-01-24 00:00:00",
    ),
    (
        "O3",
        "C3",
        "delivered",
        "2017-03-05 12:00:00",
        "2017-03-10 12:00:00",
        "2017-03-20 00:00:00",
    ),
    # Delivered but no delivery date → lateness UNKNOWN (excluded from the %).
    ("O4", "C4", "delivered", "2017-03-06 12:00:00", None, "2017-03-25 00:00:00"),
    ("O5", "C5", "shipped", "2017-03-07 12:00:00", None, "2017-03-28 00:00:00"),
    # Invalid orders that DO have items, so tests prove those items are excluded.
    ("O6", "C6", "canceled", "2017-01-12 12:00:00", None, "2017-01-30 00:00:00"),
    ("O7", "C7", "unavailable", "2017-03-08 12:00:00", None, "2017-03-30 00:00:00"),
    # Valid order with no items: adds no revenue but still counts in AOV.
    ("O8", "C8", "processing", "2017-03-09 12:00:00", None, "2017-03-31 00:00:00"),
]
# No February orders on purpose: the monthly trend must fill 2017-02 with zero.

# (product_id, original Portuguese category)
PRODUCTS = [
    ("P01", "beleza_saude"),
    ("P02", "relogios_presentes"),
    ("P03", "cama_mesa_banho"),
    ("P04", "esporte_lazer"),
    ("P05", "informatica_acessorios"),
    ("P06", "moveis_decoracao"),
    ("P07", "utilidades_domesticas"),
    ("P08", "cool_stuff"),
    ("P09", "automotivo"),
    ("P10", "ferramentas_jardim"),
    ("P11", "pc_gamer"),  # no translation row → falls back to the original name
    ("P12", None),  # no category → grouped as "unknown_category"
    ("P13", "brinquedos"),
]

# (original category, English category). pc_gamer is left out on purpose.
TRANSLATIONS = [
    ("beleza_saude", "health_beauty"),
    ("relogios_presentes", "watches_gifts"),
    ("cama_mesa_banho", "bed_bath_table"),
    ("esporte_lazer", "sports_leisure"),
    ("informatica_acessorios", "computers_accessories"),
    ("moveis_decoracao", "furniture_decor"),
    ("utilidades_domesticas", "housewares"),
    ("cool_stuff", "cool_stuff"),
    ("automotivo", "auto"),
    ("ferramentas_jardim", "garden_tools"),
    ("brinquedos", "toys"),
]

# Every item pays the same freight, which must never show up in revenue.
FREIGHT_VALUE = 10.00

# (order_id, order_item_id, product_id, price)
ORDER_ITEMS = [
    ("O1", 1, "P01", 120.00),
    ("O1", 2, "P02", 110.00),
    ("O2", 1, "P11", 100.00),
    ("O2", 2, "P12", 90.00),
    ("O3", 1, "P03", 80.00),
    ("O3", 2, "P04", 70.00),
    ("O3", 3, "P13", 10.25),  # not a round number: checks money is exact to the cent
    ("O4", 1, "P05", 60.00),
    ("O4", 2, "P06", 50.00),
    ("O5", 1, "P07", 40.00),
    # cool_stuff and auto tie at 30.00; "auto" wins the 10th place by name.
    ("O5", 2, "P08", 30.00),
    ("O5", 3, "P09", 30.00),
    ("O5", 4, "P10", 20.00),
    ("O6", 1, "P01", 500.00),  # canceled order → must NOT count
    ("O7", 1, "P13", 400.00),  # unavailable order → must NOT count
]


def _create_database(db_path: Path, with_rows: bool) -> None:
    """Write a SQLite file with the Olist tables, optionally filled with fixture rows."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        if with_rows:
            conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", ORDERS)
            conn.executemany("INSERT INTO products VALUES (?, ?)", PRODUCTS)
            conn.executemany(
                "INSERT INTO product_category_name_translation VALUES (?, ?)",
                TRANSLATIONS,
            )
            conn.executemany(
                "INSERT INTO order_items VALUES (?, ?, ?, ?, ?)",
                [(*item, FREIGHT_VALUE) for item in ORDER_ITEMS],
            )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def fixture_db_path(tmp_path: Path) -> Path:
    """Return the path to a small database filled with the hand-made fixture rows."""
    db_path = tmp_path / FIXTURE_DB_NAME
    _create_database(db_path, with_rows=True)
    return db_path


@pytest.fixture
def empty_db_path(tmp_path: Path) -> Path:
    """Return the path to a database with the same tables but no rows."""
    # Used for the "zero valid orders / zero delivered orders" cases (FR-014).
    db_path = tmp_path / EMPTY_DB_NAME
    _create_database(db_path, with_rows=False)
    return db_path


@pytest.fixture
def missing_db_path(tmp_path: Path) -> Path:
    """Return a path where no database file exists."""
    # Used to prove the app reports "data unavailable" and creates no file.
    return tmp_path / MISSING_DB_NAME
