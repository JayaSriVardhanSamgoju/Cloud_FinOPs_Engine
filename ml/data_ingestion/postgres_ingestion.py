import pandas as pd
from sqlalchemy import text
from tqdm import tqdm

import sys
from pathlib import Path

# Add the project root directory to sys.path so 'configs' can be resolved
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from configs.db_config import engine

CSV_PATH = "data/raw/telemetry_data.csv"


def load_csv():

    print("Loading telemetry dataset...")

    df = pd.read_csv(
        CSV_PATH,
        parse_dates=["timestamp"]
    )

    print(f"Dataset Loaded: {df.shape}")

    return df


def truncate_existing_data():

    print("Clearing old telemetry data...")

    with engine.connect() as conn:
        conn.execute(
            text(
                "DROP TABLE IF EXISTS telemetry_metrics CASCADE;"
            )
        )
        conn.commit()

    print("Old data removed.")


def ingest_to_postgres(df):

    batch_size = 10000

    print("\nStarting ingestion...")

    for i in tqdm(
        range(0, len(df), batch_size)
    ):

        batch = df.iloc[i:i + batch_size]

        batch.to_sql(
            "telemetry_metrics",
            engine,
            if_exists="append",
            index=False,
            method="multi"
        )

    print("\nIngestion completed successfully!")


if __name__ == "__main__":

    df = load_csv()

    truncate_existing_data()

    ingest_to_postgres(df)

    print("\nCloudPulse telemetry loaded into PostgreSQL!")