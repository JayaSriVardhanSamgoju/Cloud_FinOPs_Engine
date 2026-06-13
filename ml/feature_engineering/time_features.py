"""
CloudPulse AI
Production Time Series Feature Engineering Pipeline
---------------------------------------------------
Step 10 - Part 1

Features Implemented:
1. Database Loading
2. Config Architecture
3. Logging
4. Temporal Features
5. Cyclical Features
"""

import os
import logging
from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd
from sqlalchemy import text

import sys
from pathlib import Path

# Add project root to sys.path so 'configs' module can be found
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from configs.db_config import engine


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class FeatureEngineeringConfig:
    """
    Configuration for feature engineering.
    """

    table_name: str = "telemetry_metrics"

    processed_dir: str = "data/processed"

    report_dir: str = "reports"

    random_seed: int = 42

    telemetry_interval_minutes: int = 5

    lag_steps: List[int] = None

    rolling_windows: List[int] = None

    target_horizons: dict = None

    def __post_init__(self):

        self.lag_steps = [
            1,   # 5 min
            3,   # 15 min
            6,   # 30 min
            12,  # 1 hour
            24   # 2 hour
        ]

        self.rolling_windows = [
            3,
            6,
            12,
            24
        ]

        self.target_horizons = {
            "30min": 6,
            "1hour": 12
        }


# ============================================================
# LOGGING
# ============================================================

def setup_logging():

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s "
            "- %(levelname)s "
            "- %(message)s"
        )
    )

    return logging.getLogger(__name__)


logger = setup_logging()


# ============================================================
# FEATURE ENGINEERING PIPELINE
# ============================================================

class TimeSeriesFeatureEngineering:

    def __init__(self):

        self.config = (
            FeatureEngineeringConfig()
        )

        np.random.seed(
            self.config.random_seed
        )

        os.makedirs(
            self.config.processed_dir,
            exist_ok=True
        )

        os.makedirs(
            self.config.report_dir,
            exist_ok=True
        )

    # ========================================================
    # LOAD TELEMETRY DATA
    # ========================================================

    def load_telemetry_data(self):

        logger.info(
            "Loading telemetry data "
            "from PostgreSQL..."
        )

        query = f"""
        SELECT *
        FROM {self.config.table_name}
        ORDER BY timestamp
        """

        df = pd.read_sql(
            query,
            engine
        )

        df["timestamp"] = pd.to_datetime(
            df["timestamp"]
        )

        logger.info(
            f"Dataset loaded: "
            f"{df.shape}"
        )

        logger.info(
            f"Date Range: "
            f"{df['timestamp'].min()} "
            f"→ "
            f"{df['timestamp'].max()}"
        )

        return df

    # ========================================================
    # BASIC PREPROCESSING
    # ========================================================

    def preprocess_data(self, df):

        logger.info(
            "Preprocessing telemetry..."
        )

        df = df.sort_values(
            ["region", "timestamp"]
        )

        df = df.reset_index(
            drop=True
        )

        logger.info(
            "Dataset sorted by "
            "region and timestamp."
        )

        return df

    # ========================================================
    # TEMPORAL FEATURES
    # ========================================================

    def create_temporal_features(
        self,
        df
    ):

        logger.info(
            "Creating temporal features..."
        )

        df["hour"] = (
            df["timestamp"]
            .dt.hour
        )

        df["day_of_week"] = (
            df["timestamp"]
            .dt.dayofweek
        )

        df["month"] = (
            df["timestamp"]
            .dt.month
        )

        df["quarter"] = (
            df["timestamp"]
            .dt.quarter
        )

        df["week_of_year"] = (
            df["timestamp"]
            .dt.isocalendar()
            .week
            .astype(int)
        )

        df["day_of_month"] = (
            df["timestamp"]
            .dt.day
        )

        df["is_weekend"] = (
            df["day_of_week"] >= 5
        ).astype(int)

        df["is_business_hour"] = (
            (
                df["hour"] >= 9
            )
            &
            (
                df["hour"] <= 18
            )
        ).astype(int)

        logger.info(
            "Temporal features created."
        )

        return df

    # ========================================================
    # CYCLICAL FEATURES
    # ========================================================

    def create_cyclical_features(
        self,
        df
    ):

        logger.info(
            "Creating cyclical features..."
        )

        # Hour encoding
        df["hour_sin"] = np.sin(
            2 * np.pi
            * df["hour"]
            / 24
        )

        df["hour_cos"] = np.cos(
            2 * np.pi
            * df["hour"]
            / 24
        )

        # Weekday encoding
        df["day_sin"] = np.sin(
            2 * np.pi
            * df["day_of_week"]
            / 7
        )

        df["day_cos"] = np.cos(
            2 * np.pi
            * df["day_of_week"]
            / 7
        )

        # Month encoding
        df["month_sin"] = np.sin(
            2 * np.pi
            * df["month"]
            / 12
        )

        df["month_cos"] = np.cos(
            2 * np.pi
            * df["month"]
            / 12
        )

        logger.info(
            "Cyclical features created."
        )

        return df

        # ========================================================
    # LAG FEATURES
    # ========================================================

    def create_lag_features(
        self,
        df
    ):

        logger.info(
            "Creating lag features..."
        )

        lag_columns = [
            "cpu_usage",
            "request_rate",
            "response_latency_ms",
            "resource_pressure_score",
            "sla_breach_risk",
            "cost_per_hour"
        ]

        for col in lag_columns:

            for lag in (
                self.config.lag_steps
            ):

                df[
                    f"{col}_lag_{lag}"
                ] = (
                    df
                    .groupby("region")[col]
                    .shift(lag)
                )

        logger.info(
            "Lag features created."
        )

        return df


    # ========================================================
    # ROLLING FEATURES
    # ========================================================

    def create_rolling_features(
        self,
        df
    ):

        logger.info(
            "Creating rolling features..."
        )

        rolling_columns = [
            "cpu_usage",
            "request_rate",
            "response_latency_ms"
        ]

        for col in (
            rolling_columns
        ):

            for window in (
                self.config
                .rolling_windows
            ):

                # Rolling Mean
                df[
                    f"{col}"
                    f"_rolling_mean_"
                    f"{window}"
                ] = (
                    df
                    .groupby("region")[col]
                    .transform(
                        lambda x:
                        x.rolling(
                            window
                        ).mean()
                    )
                )

                # Rolling Std
                df[
                    f"{col}"
                    f"_rolling_std_"
                    f"{window}"
                ] = (
                    df
                    .groupby("region")[col]
                    .transform(
                        lambda x:
                        x.rolling(
                            window
                        ).std()
                    )
                )

                # Rolling Min
                df[
                    f"{col}"
                    f"_rolling_min_"
                    f"{window}"
                ] = (
                    df
                    .groupby("region")[col]
                    .transform(
                        lambda x:
                        x.rolling(
                            window
                        ).min()
                    )
                )

                # Rolling Max
                df[
                    f"{col}"
                    f"_rolling_max_"
                    f"{window}"
                ] = (
                    df
                    .groupby("region")[col]
                    .transform(
                        lambda x:
                        x.rolling(
                            window
                        ).max()
                    )
                )

        logger.info(
            "Rolling features created."
        )

        return df


    # ========================================================
    # TREND FEATURES
    # ========================================================

    def create_trend_features(
        self,
        df
    ):

        logger.info(
            "Creating trend features..."
        )

        trend_columns = [
            "cpu_usage",
            "request_rate",
            "response_latency_ms"
        ]

        for col in (
            trend_columns
        ):

            df[
                f"{col}_delta"
            ] = (
                df
                .groupby("region")[col]
                .diff()
            )

            df[
                f"{col}_pct_change"
            ] = (
                df
                .groupby("region")[col]
                .pct_change()
            )

        logger.info(
            "Trend features created."
        )

        return df

        # ========================================================
    # TARGET FEATURES
    # ========================================================

    def create_target_variables(
        self,
        df
    ):

        logger.info(
            "Creating target variables..."
        )

        TARGET_SHIFTS = {
            "target_cpu_30min":          ("cpu_usage", -6),    # 6 * 5min = 30min
            "target_cpu_1hour":          ("cpu_usage", -12),   # 12 * 5min = 60min
            "target_request_rate_30min": ("request_rate", -6),
            "target_latency_30min":      ("response_latency_ms", -6),
        }

        df = df.sort_values(["region", "timestamp"]).reset_index(drop=True)

        for target_col, (source_col, shift_steps) in TARGET_SHIFTS.items():
            df[target_col] = df.groupby("region")[source_col].shift(shift_steps)

        # Drop ALL rows where ANY target is NaN — these are the trailing rows
        # of each region where no future value exists
        before_rows = len(df)
        df = df.dropna(subset=list(TARGET_SHIFTS.keys())).reset_index(drop=True)
        after_rows = len(df)

        logger.info(
            f"Target generation | rows_before={before_rows} | rows_after={after_rows} | "
            f"dropped={before_rows - after_rows} (expected ≈ 12 rows/region × n_regions for the 1hr target)"
        )
        
        self.validate_target_generation(df)

        logger.info(
            "Target variables created."
        )

        return df


    # ========================================================
    # VALIDATION
    # ========================================================

    def validate_features(
        self,
        df
    ):

        logger.info(
            "Running validation..."
        )

        null_count = (
            df.isnull()
            .sum()
            .sum()
        )

        logger.info(
            f"Total null values: "
            f"{null_count}"
        )

        target_columns = [
            "target_cpu_30min",
            "target_cpu_1hour",
            "target_request_rate_30min",
            "target_latency_30min"
        ]

        for col in (
            target_columns
        ):

            missing = (
                df[col]
                .isnull()
                .sum()
            )

            logger.info(
                f"{col} "
                f"missing rows: "
                f"{missing}"
            )

        logger.info(
            f"Feature Count: "
            f"{len(df.columns)}"
        )

        logger.info(
            "Validation completed."
        )

    def validate_target_generation(self, df: pd.DataFrame) -> None:
        """Confirms no cross-region leakage in target columns."""
        for region in df["region"].unique():
            sub = df[df["region"] == region].sort_values("timestamp")
            # Spot-check: target_cpu_30min at row i should equal cpu_usage at row i+6
            # within the SAME region only
            shifted = sub["cpu_usage"].shift(-6)
            
            # Because df already had trailing NaNs dropped for the 1-hour target,
            # shifted will have 6 NaNs at the end that we must exclude from the comparison.
            n_valid = len(shifted.dropna())
            
            match = np.allclose(
                sub["target_cpu_30min"].values[:n_valid],
                shifted.values[:n_valid],
                atol=1e-6
            )
            assert match, f"Target leakage detected in region {region}"

        # Confirm no NaNs remain in target columns
        target_cols = [c for c in df.columns if c.startswith("target_")]
        assert df[target_cols].isnull().sum().sum() == 0, "NaNs remain in target columns"

        logger.info("Target generation validation passed | no cross-region leakage | no NaN targets")

    def prune_correlated_features(self, df: pd.DataFrame, threshold: float = 0.95) -> pd.DataFrame:
        """Removes features with correlation > threshold, excluding targets and base columns."""
        logger.info("Pruning highly correlated features...")
        
        # Identify features (exclude targets, base metrics, categorical)
        exclude_cols = ['timestamp', 'region', 'workload_type', 'instance_type', 'special_event',
                        'is_anomaly', 'is_rerouted_traffic', 'target_cpu_30min', 'target_cpu_1hour', 
                        'target_request_rate_30min', 'target_latency_30min',
                        'cpu_usage', 'ram_usage', 'request_rate', 'response_latency_ms',
                        'network_in', 'network_out', 'disk_io', 'error_rate', 
                        'resource_pressure_score', 'sla_breach_risk']
                        
        feature_cols = [c for c in df.columns if c not in exclude_cols and np.issubdtype(df[c].dtype, np.number)]
        
        corr_matrix = df[feature_cols].corr().abs()
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        
        to_drop = [column for column in upper.columns if any(upper[column] > threshold)]
        
        df = df.drop(columns=to_drop)
        logger.info(f"Pruned {len(to_drop)} highly correlated features. Remaining features: {df.shape[1]}")
        return df


    # ========================================================
    # CLEAN DATASET
    # ========================================================

    def clean_dataset(
        self,
        df
    ):

        logger.info(
            "Cleaning dataset..."
        )

        before = len(df)

        df = df.dropna()

        after = len(df)

        removed = (
            before - after
        )

        logger.info(
            f"Removed "
            f"{removed} rows"
        )

        logger.info(
            f"Final shape: "
            f"{df.shape}"
        )

        return df


    # ========================================================
    # SAVE DATASET
    # ========================================================

    def save_outputs(
        self,
        df
    ):

        logger.info(
            "Saving outputs..."
        )

        csv_path = (
            f"{self.config.processed_dir}/"
            "forecasting_features.csv"
        )

        parquet_path = (
            f"{self.config.processed_dir}/"
            "forecasting_features.parquet"
        )

        df.to_csv(
            csv_path,
            index=False
        )

        df.to_parquet(
            parquet_path,
            index=False
        )

        logger.info(
            "Files saved successfully."
        )

        logger.info(csv_path)
        logger.info(parquet_path)


    # ========================================================
    # POSTGRES INGESTION
    # ========================================================

    def push_to_postgres(
        self,
        df
    ):

        logger.info(
            "Pushing features "
            "to PostgreSQL..."
        )

        table_name = (
            "telemetry_features"
        )

        with engine.connect() as conn:

            conn.execute(
                text(
                    f"""
                    DROP TABLE
                    IF EXISTS
                    {table_name};
                    """
                )
            )

            conn.commit()

        df.to_sql(
            table_name,
            engine,
            if_exists="replace",
            index=False,
            chunksize=10000,
            method="multi"
        )

        logger.info(
            "Feature store "
            "created successfully."
        )


    # ========================================================
    # REPORT GENERATION
    # ========================================================

    def generate_report(
        self,
        df
    ):

        logger.info(
            "Generating report..."
        )

        report_path = (
            f"{self.config.report_dir}/"
            "feature_engineering_report.md"
        )

        with open(
            report_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "# CloudPulse AI "
                "Feature Engineering Report\n\n"
            )

            f.write(
                f"Dataset Shape: "
                f"{df.shape}\n\n"
            )

            f.write(
                "## Total Features\n"
            )

            f.write(
                f"{len(df.columns)}\n\n"
            )

            f.write(
                "## Target Variables\n"
            )

            targets = [
                "target_cpu_30min",
                "target_cpu_1hour",
                "target_request_rate_30min",
                "target_latency_30min"
            ]

            for t in targets:
                f.write(
                    f"- {t}\n"
                )

            f.write(
                "\n## Missing Values\n"
            )

            f.write(
                str(
                    df.isnull()
                    .sum()
                )
            )

        logger.info(
            "Report generated."
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    logger.info("=" * 60)

    logger.info(
        "CloudPulse AI "
        "Feature Engineering "
        "Pipeline Started"
    )

    logger.info("=" * 60)

    pipeline = (
        TimeSeriesFeatureEngineering()
    )

    df = (
        pipeline
        .load_telemetry_data()
    )

    df = (
        pipeline
        .preprocess_data(df)
    )

    df = (
        pipeline
        .create_temporal_features(df)
    )

    df = (
        pipeline
        .create_cyclical_features(df)
    )

    df = (
        pipeline
        .create_lag_features(df)
    )

    df = (
        pipeline
        .create_rolling_features(df)
    )

    df = (
        pipeline
        .create_trend_features(df)
    )

    df = (
        pipeline
        .create_target_variables(df)
    )

    df = pipeline.prune_correlated_features(df, threshold=0.95)

    pipeline.validate_features(df)

    df = (
        pipeline
        .clean_dataset(df)
    )

    pipeline.save_outputs(df)

    pipeline.push_to_postgres(df)

    pipeline.generate_report(df)

    logger.info(
        "\nFeature Engineering "
        "Completed Successfully!"
    )