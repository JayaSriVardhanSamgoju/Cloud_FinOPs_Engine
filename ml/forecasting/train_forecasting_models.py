"""
CloudPulse AI
Production Forecasting Pipeline
--------------------------------
Step 11 - Part 1

Features:
1. Config Architecture
2. Data Loading
3. Feature Selection
4. Leakage Prevention
5. Chronological Split
"""

import os
import logging
from dataclasses import dataclass

import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split

import sys
from pathlib import Path

# Add project root to sys.path so 'configs' module can be found
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from configs.db_config import engine


# ============================================================
# CONFIG
# ============================================================

@dataclass
class ForecastingConfig:

    feature_table: str = (
        "telemetry_features"
    )

    target_column: str = (
        "target_cpu_30min"
    )

    model_dir: str = (
        "artifacts/models"
    )

    report_dir: str = (
        "reports"
    )

    random_seed: int = 42

    train_size: float = 0.70

    validation_size: float = 0.15

    test_size: float = 0.15


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
# FORECASTING PIPELINE
# ============================================================

class ForecastingPipeline:

    def __init__(self):

        self.config = (
            ForecastingConfig()
        )

        os.makedirs(
            self.config.model_dir,
            exist_ok=True
        )

        os.makedirs(
            self.config.report_dir,
            exist_ok=True
        )

    # ========================================================
    # LOAD FEATURES
    # ========================================================

    def load_feature_store(self):

        logger.info(
            "Loading features "
            "from PostgreSQL..."
        )

        query = f"""
        SELECT *
        FROM {
            self.config.feature_table
        }
        ORDER BY timestamp
        """

        df = pd.read_sql(
            query,
            engine
        )

        logger.info(
            f"Dataset loaded: "
            f"{df.shape}"
        )

        return df


    # ========================================================
    # FEATURE SELECTION
    # ========================================================

    def prepare_features(
        self,
        df
    ):

        logger.info(
            "Preparing features..."
        )

        leakage_columns = [

            # IDs
            "id",

            # timestamp
            "timestamp",

            # Targets
            "target_cpu_30min",
            "target_cpu_1hour",
            "target_request_rate_30min",
            "target_latency_30min",

            # created metadata
            "created_at"
        ]

        target = (
            self.config
            .target_column
        )

        y = df[target]

        X = df.drop(
            columns=[
                col
                for col
                in leakage_columns
                if col in df.columns
            ],
            errors="ignore"
        )

        # Convert categorical columns
        X = pd.get_dummies(
            X,
            drop_first=True
        )

        logger.info(
            f"Feature Count: "
            f"{X.shape[1]}"
        )

        logger.info(
            f"Target: {target}"
        )

        return X, y


    # ========================================================
    # TIME SERIES SPLIT
    # ========================================================

    def chronological_split(
        self,
        X,
        y
    ):

        logger.info(
            "Creating chronological "
            "train/validation/test split..."
        )

        total_rows = len(X)

        train_end = int(
            total_rows
            * self.config.train_size
        )

        val_end = int(
            total_rows
            * (
                self.config.train_size
                +
                self.config.validation_size
            )
        )

        # Train
        X_train = (
            X.iloc[:train_end]
        )

        y_train = (
            y.iloc[:train_end]
        )

        # Validation
        X_val = (
            X.iloc[
                train_end:val_end
            ]
        )

        y_val = (
            y.iloc[
                train_end:val_end
            ]
        )

        # Test
        X_test = (
            X.iloc[val_end:]
        )

        y_test = (
            y.iloc[val_end:]
        )

        logger.info(
            f"Train Shape: "
            f"{X_train.shape}"
        )

        logger.info(
            f"Validation Shape: "
            f"{X_val.shape}"
        )

        logger.info(
            f"Test Shape: "
            f"{X_test.shape}"
        )

        return (
            X_train,
            X_val,
            X_test,
            y_train,
            y_val,
            y_test
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    logger.info(
        "=" * 60
    )

    logger.info(
        "CloudPulse AI "
        "Forecasting Pipeline Started"
    )

    logger.info(
        "=" * 60
    )

    pipeline = (
        ForecastingPipeline()
    )

    df = (
        pipeline
        .load_feature_store()
    )

    X, y = (
        pipeline
        .prepare_features(df)
    )

    (
        X_train,
        X_val,
        X_test,
        y_train,
        y_val,
        y_test
    ) = (
        pipeline
        .chronological_split(
            X,
            y
        )
    )

    logger.info(
        "\nPart 1 completed "
        "successfully!"
    )