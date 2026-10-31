"""The single, read-only door to the AskBI database (data/olist.db).

Every query in the app goes through run_query(), so later rules about which
rows a user may see (v0-d filters, v1 row-level security) can be added here,
in one place.
"""

import sqlite3
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

# core/db.py → core/ → repo root → data/olist.db
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "olist.db"

UNAVAILABLE_MESSAGE = "The AskBI database could not be read"


class DataUnavailableError(Exception):
    """Raised when the database is missing, unreadable or a query fails."""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the database read-only; the caller must close the connection."""
    # mode=ro makes SQLite itself refuse every write, and it also stops a
    # missing file from being silently created as an empty database (which
    # would make the dashboard show zeros instead of an error).
    # as_uri() turns the path into a "file:///..." URI with any spaces escaped.
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    try:
        return sqlite3.connect(uri, uri=True)
    except sqlite3.Error as err:
        raise DataUnavailableError(f"{UNAVAILABLE_MESSAGE}: {db_path}") from err


def run_query(
    sql: str, params: Sequence[object] = (), db_path: Path = DB_PATH
) -> pd.DataFrame:
    """Run one parameterised SELECT and return the rows as a DataFrame."""
    # Future home of data-scope rules: v0-d filters and v1 row-level security
    # will narrow the rows here, so no other code needs to change.
    conn = get_connection(db_path)
    try:
        # We use the sqlite3 cursor directly instead of pd.read_sql_query,
        # because pandas wraps SQLite errors in its own type and the real cause
        # would no longer be a sqlite3.Error.
        cursor = conn.execute(sql, tuple(params))
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
    except sqlite3.Error as err:
        # "from err" keeps the original SQLite error attached, so a bug in our
        # own SQL still shows its real cause in the terminal traceback.
        raise DataUnavailableError(f"{UNAVAILABLE_MESSAGE}: {err}") from err
    finally:
        conn.close()
    return pd.DataFrame.from_records(rows, columns=columns)
