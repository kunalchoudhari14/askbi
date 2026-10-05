"""Load the Olist CSVs into a SQLite database (data/olist.db).

How to run (from the askbi folder, with the venv active):
    python load_data.py

Before the first run: download the Olist dataset from Kaggle
(kaggle.com/datasets/olistbr/brazilian-ecommerce) and unzip the 9 CSVs
into data/raw/.

Safe to re-run ("idempotent"): each table is dropped and rebuilt, so
running it twice never duplicates rows. data/raw/ and olist.db are
git-ignored; this script is how anyone rebuilds the database.
"""

import sqlite3  # 1) standard library (built into Python)
from pathlib import Path

import pandas as pd  # 2) third-party (installed via requirements.txt)

# Paths are anchored to this file's folder, so the script works no matter
# which folder you run it from.
BASE_DIR = Path(__file__).resolve().parent  # the folder load_data.py lives in
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"  # input: the 9 Olist CSVs
DB_PATH = DATA_DIR / "olist.db"  # output: one SQLite file, one table per CSV


def main() -> None:
    """Load every CSV in RAW_DIR into its own table in DB_PATH."""
    # Guard clause: check inputs BEFORE opening resources, and fail with a
    # helpful message instead of silently doing nothing.
    if not any(RAW_DIR.glob("*.csv")):
        raise FileNotFoundError(
            f"No CSVs in {RAW_DIR}. Download Olist from Kaggle first."
        )

    conn = sqlite3.connect(DB_PATH)  # creates the .db file if it doesn't exist
    try:
        # sorted() → same load order on every machine
        for csv_path in sorted(RAW_DIR.glob("*.csv")):
            # "olist_orders_dataset.csv" → "orders"
            table_name = csv_path.stem.replace("olist_", "").replace("_dataset", "")
            df = pd.read_csv(csv_path)
            # if_exists="replace": drop + rebuild the table (safe re-runs)
            # index=False: don't save pandas' row numbers as a column
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            print(f"Loaded {table_name}: {len(df):,} rows")  # :, → 1,000,163
    finally:
        conn.close()  # runs even if a CSV fails mid-loop


# Runs only when you execute this file directly (python load_data.py),
# never when another file imports it.
if __name__ == "__main__":
    main()
