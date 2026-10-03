import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent  # the folder load_data.py lives in
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "olist.db"


def main():
    if not any(RAW_DIR.glob("*.csv")):
        raise FileNotFoundError(
            f"No CSVs in {RAW_DIR}. Download Olist from Kaggle first."
        )

    conn = sqlite3.connect(DB_PATH)
    try:
        for csv_path in sorted(RAW_DIR.glob("*.csv")):
            table_name = csv_path.stem.replace("olist_", "").replace("_dataset", "")
            df = pd.read_csv(csv_path)
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            print(f"Loaded {table_name}: {len(df):,} rows")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
