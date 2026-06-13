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
import matplotlib.pyplot as plt
import joblib

from sklearn.linear_model import (
    LinearRegression
)

from sklearn.ensemble import (
    RandomForestRegressor
)

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

from xgboost import (
    XGBRegressor
)

from lightgbm import (
    LGBMRegressor
)

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
        # ========================================================
    # TRAIN MODELS
    # ========================================================

    def train_models(
        self,
        X_train,
        y_train
    ):

        logger.info(
            "Initializing models..."
        )

        models = {

            "linear_regression":
            LinearRegression(),

            "random_forest":
            RandomForestRegressor(
                n_estimators=100,
                max_depth=12,
                random_state=42,
                n_jobs=-1
            ),

            "xgboost":
            XGBRegressor(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=8,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1
            ),

            "lightgbm":
            LGBMRegressor(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=8,
                random_state=42
            )
        }

        trained_models = {}

        for name, model in (
            models.items()
        ):

            logger.info(
                f"Training {name}..."
            )

            model.fit(
                X_train,
                y_train
            )

            trained_models[
                name
            ] = model

            logger.info(
                f"{name} trained."
            )

        return trained_models


    # ========================================================
    # EVALUATION
    # ========================================================

    def evaluate_models(
        self,
        models,
        X_val,
        y_val
    ):

        logger.info(
            "Evaluating models..."
        )

        results = []

        for name, model in (
            models.items()
        ):

            preds = model.predict(
                X_val
            )

            rmse = np.sqrt(
                mean_squared_error(
                    y_val,
                    preds
                )
            )

            mae = (
                mean_absolute_error(
                    y_val,
                    preds
                )
            )

            r2 = (
                r2_score(
                    y_val,
                    preds
                )
            )

            results.append({
                "model": name,
                "rmse": rmse,
                "mae": mae,
                "r2_score": r2
            })

            logger.info(
                f"{name}"
                f" | RMSE: {rmse:.4f}"
                f" | MAE: {mae:.4f}"
                f" | R²: {r2:.4f}"
            )

        results_df = pd.DataFrame(
            results
        )

        return results_df


    # ========================================================
    # SAVE MODELS
    # ========================================================

    def save_models(
        self,
        models
    ):

        logger.info(
            "Saving models..."
        )

        for name, model in (
            models.items()
        ):

            model_path = (
                f"{self.config.model_dir}/"
                f"{name}.pkl"
            )

            joblib.dump(
                model,
                model_path
            )

            logger.info(
                f"Saved: "
                f"{model_path}"
            )


    # ========================================================
    # SAVE REPORT
    # ========================================================

    def save_report(
        self,
        results_df
    ):

        report_path = (
            f"{self.config.report_dir}/"
            "model_comparison.md"
        )

        best_model = (
            results_df
            .sort_values(
                "r2_score",
                ascending=False
            )
            .iloc[0]
        )

        with open(
            report_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "# CloudPulse AI "
                "Model Comparison\n\n"
            )

            f.write(
                "## Model Metrics\n\n"
            )

            f.write(
                results_df
                .to_markdown(
                    index=False
                )
            )

            f.write("\n\n")

            f.write(
                "## Best Model\n\n"
            )

            f.write(
                f"Best Model: "
                f"{best_model['model']}\n\n"
            )

            f.write(
                f"R² Score: "
                f"{best_model['r2_score']:.4f}"
            )

        logger.info(
            "Report saved."
        )
        # ========================================================
    # TEST SET EVALUATION
    # ========================================================

    def evaluate_best_model(
        self,
        models,
        results_df,
        X_test,
        y_test
    ):

        logger.info(
            "Selecting best model..."
        )

        best_model_name = (
            results_df
            .sort_values(
                "r2_score",
                ascending=False
            )
            .iloc[0]["model"]
        )

        best_model = (
            models[best_model_name]
        )

        logger.info(
            f"Best Model: "
            f"{best_model_name}"
        )

        predictions = (
            best_model.predict(
                X_test
            )
        )

        rmse = np.sqrt(
            mean_squared_error(
                y_test,
                predictions
            )
        )

        mae = mean_absolute_error(
            y_test,
            predictions
        )

        r2 = r2_score(
            y_test,
            predictions
        )

        logger.info(
            f"Test RMSE: "
            f"{rmse:.4f}"
        )

        logger.info(
            f"Test MAE: "
            f"{mae:.4f}"
        )

        logger.info(
            f"Test R²: "
            f"{r2:.4f}"
        )

        return (
            best_model_name,
            best_model,
            predictions
        )


    # ========================================================
    # FEATURE IMPORTANCE
    # ========================================================

    def generate_feature_importance(
        self,
        model,
        X_train,
        model_name
    ):

        logger.info(
            "Generating feature "
            "importance..."
        )

        if hasattr(
            model,
            "feature_importances_"
        ):

            importance_df = (
                pd.DataFrame({
                    "feature":
                    X_train.columns,
                    "importance":
                    model.feature_importances_
                })
                .sort_values(
                    "importance",
                    ascending=False
                )
                .head(20)
            )

            plt.figure(
                figsize=(12, 8)
            )

            plt.barh(
                importance_df[
                    "feature"
                ],
                importance_df[
                    "importance"
                ]
            )

            plt.xlabel(
                "Importance"
            )

            plt.title(
                f"{model_name} "
                "Feature Importance"
            )

            plt.gca().invert_yaxis()

            plt.tight_layout()

            plt.savefig(
                "artifacts/models/"
                "feature_importance.png"
            )

            plt.close()

            logger.info(
                "Feature importance "
                "saved."
            )


    # ========================================================
    # PREDICTION VISUALIZATION
    # ========================================================

    def visualize_predictions(
        self,
        y_test,
        predictions
    ):

        logger.info(
            "Generating prediction "
            "visualization..."
        )

        plt.figure(
            figsize=(15, 6)
        )

        sample_size = 500

        plt.plot(
            y_test.iloc[
                :sample_size
            ].values,
            label="Actual"
        )

        plt.plot(
            predictions[
                :sample_size
            ],
            label="Predicted"
        )

        plt.xlabel(
            "Time"
        )

        plt.ylabel(
            "CPU Usage"
        )

        plt.title(
            "Actual vs "
            "Predicted CPU"
        )

        plt.legend()

        plt.tight_layout()

        plt.savefig(
            "artifacts/models/"
            "prediction_plot.png"
        )

        plt.close()

        logger.info(
            "Prediction plot saved."
        )


    # ========================================================
    # SAVE BEST MODEL
    # ========================================================

    def save_best_model(
        self,
        model,
        model_name
    ):

        model_path = (
            f"{self.config.model_dir}/"
            "best_model.pkl"
        )

        joblib.dump(
            model,
            model_path
        )

        logger.info(
            f"Best model saved: "
            f"{model_name}"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    logger.info("=" * 60)

    logger.info(
        "CloudPulse AI "
        "Forecasting Pipeline Started"
    )

    logger.info("=" * 60)

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

    models = (
        pipeline
        .train_models(
            X_train,
            y_train
        )
    )

    results_df = (
        pipeline
        .evaluate_models(
            models,
            X_val,
            y_val
        )
    )

    pipeline.save_models(
        models
    )

    pipeline.save_report(
        results_df
    )

    (
        best_model_name,
        best_model,
        predictions
    ) = (
        pipeline
        .evaluate_best_model(
            models,
            results_df,
            X_test,
            y_test
        )
    )

    pipeline.generate_feature_importance(
        best_model,
        X_train,
        best_model_name
    )

    pipeline.visualize_predictions(
        y_test,
        predictions
    )

    pipeline.save_best_model(
        best_model,
        best_model_name
    )

    logger.info(
        "\nStep 11 "
        "Completed Successfully!"
    )