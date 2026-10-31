"""Tests for core.db, the single read-only door to the database (FR-015)."""

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from core import db

FIXTURE_ORDER_COUNT = 8  # rows in the ORDERS list in tests/conftest.py
CANCELED_STATUS = "canceled"


def test_run_query_returns_dataframe(fixture_db_path: Path) -> None:
    """A SELECT comes back as a pandas DataFrame with the expected value."""
    result = db.run_query("SELECT COUNT(*) AS n FROM orders", db_path=fixture_db_path)

    assert isinstance(result, pd.DataFrame)
    assert result.loc[0, "n"] == FIXTURE_ORDER_COUNT


def test_run_query_uses_parameters(fixture_db_path: Path) -> None:
    """Values passed as ? parameters are used in the query."""
    result = db.run_query(
        "SELECT COUNT(*) AS n FROM orders WHERE order_status = ?",
        (CANCELED_STATUS,),
        db_path=fixture_db_path,
    )

    assert result.loc[0, "n"] == 1


def test_connection_is_read_only(fixture_db_path: Path) -> None:
    """SQLite itself refuses to write through our connection."""
    conn = db.get_connection(fixture_db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO orders (order_id) VALUES ('NEW')")
    finally:
        conn.close()


def test_get_connection_missing_file_raises(missing_db_path: Path) -> None:
    """Opening a database that doesn't exist raises DataUnavailableError."""
    with pytest.raises(db.DataUnavailableError):
        db.get_connection(missing_db_path)


def test_missing_database_raises_and_creates_no_file(missing_db_path: Path) -> None:
    """A missing database gives a clear error and is NOT silently created."""
    with pytest.raises(db.DataUnavailableError):
        db.run_query("SELECT 1", db_path=missing_db_path)

    # Plain sqlite3.connect would create an empty file here, and the dashboard
    # would then show zeros instead of an error (FR-013).
    assert not missing_db_path.exists()


def test_bad_sql_keeps_original_error_as_cause(fixture_db_path: Path) -> None:
    """A broken query still shows the real SQLite error as the cause."""
    with pytest.raises(db.DataUnavailableError) as error_info:
        db.run_query("SELECT no_such_column FROM orders", db_path=fixture_db_path)

    # `raise ... from err` stores the original error in __cause__, so a bug in
    # our own SQL is still visible in the terminal traceback (research R2).
    assert isinstance(error_info.value.__cause__, sqlite3.Error)


def test_db_path_points_at_olist_db() -> None:
    """The default database is data/olist.db in the repo."""
    assert db.DB_PATH.parts[-2:] == ("data", "olist.db")
