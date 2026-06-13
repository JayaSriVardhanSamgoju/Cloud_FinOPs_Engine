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
import mlflow
import mlflow.sklearn

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

        df = df.reset_index(drop=True)

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

    def chronological_split_per_region(
        self,
        X,
        y,
        original_df
    ):

        logger.info(
            "Creating chronological "
            "train/validation/test split..."
        )

        train_idx, val_idx, test_idx = [], [], []
        
        for region in original_df["region"].unique():
            reg_indices = original_df[original_df["region"] == region].index.values
            total_rows = len(reg_indices)
            train_end = int(total_rows * self.config.train_size)
            val_end = int(total_rows * (self.config.train_size + self.config.validation_size))
            
            train_idx.extend(reg_indices[:train_end])
            val_idx.extend(reg_indices[train_end:val_end])
            test_idx.extend(reg_indices[val_end:])
            
        X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
        X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
        X_test, y_test = X.iloc[test_idx], y.iloc[test_idx]

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
    # MLFLOW PIPELINE (Fix 2 + Fix 5 + S5)
    # ========================================================

    def run_mlflow_pipeline(self, X_train, X_val, X_test, y_train, y_val, y_test):
        """
        Unified training + evaluation pipeline with:
        - Persistence baseline (Fix 2)
        - Full MLflow experiment tracking (Fix 5)
        - Pressure-score ablation study (S5)
        """
        mlflow.set_tracking_uri(
            os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5001")
        )
        mlflow.set_experiment("cloudpulse-cpu-forecasting")
        results = []

        # ── 1. Persistence Baseline (Fix 2) ────────────────────────
        # Naive baseline: predicts target = current cpu_usage value
        baseline_preds = X_val["cpu_usage"].values
        baseline_rmse = np.sqrt(mean_squared_error(y_val, baseline_preds))
        baseline_mae = mean_absolute_error(y_val, baseline_preds)
        baseline_r2 = r2_score(y_val, baseline_preds)

        results.append({
            "model": "PersistenceBaseline",
            "rmse": round(baseline_rmse, 4),
            "mae": round(baseline_mae, 4),
            "r2_score": round(baseline_r2, 4),
            "improvement_pct": 0.0,
        })
        logger.info(
            f"PersistenceBaseline | RMSE: {baseline_rmse:.4f} "
            f"| MAE: {baseline_mae:.4f} | R²: {baseline_r2:.4f}"
        )

        # ── 2. ML Models ───────────────────────────────────────────
        models = {
            "linear_regression": LinearRegression(),
            "random_forest": RandomForestRegressor(
                n_estimators=100, max_depth=12,
                random_state=self.config.random_seed, n_jobs=-1
            ),
            "xgboost": XGBRegressor(
                n_estimators=200, learning_rate=0.05, max_depth=8,
                subsample=0.8, colsample_bytree=0.8,
                random_state=self.config.random_seed, n_jobs=-1
            ),
            "lightgbm": LGBMRegressor(
                n_estimators=200, learning_rate=0.05, max_depth=8,
                random_state=self.config.random_seed
            ),
            # S5: Ablation study — same model but without pressure/SLA features
            "lightgbm_no_pressure": LGBMRegressor(
                n_estimators=200, learning_rate=0.05, max_depth=8,
                random_state=self.config.random_seed
            ),
        }

        target_col = self.config.target_column

        for name, model in models.items():
            with mlflow.start_run(run_name=f"{name}_{target_col}"):
                logger.info(f"Training {name}...")

                # S5: Drop pressure/SLA features for ablation variant
                if name == "lightgbm_no_pressure":
                    drop_cols = ["resource_pressure_score", "sla_breach_risk"]
                    X_tr = X_train.drop(columns=[c for c in drop_cols if c in X_train.columns])
                    X_v = X_val.drop(columns=[c for c in drop_cols if c in X_val.columns])
                    X_te = X_test.drop(columns=[c for c in drop_cols if c in X_test.columns])
                else:
                    X_tr, X_v, X_te = X_train, X_val, X_test

                # ── Log params (Fix 5 audit requirement) ───────────
                mlflow.log_param("model_type", name)
                mlflow.log_param("target", target_col)
                mlflow.log_param("n_features", X_tr.shape[1])
                mlflow.log_param("train_rows", len(X_tr))
                mlflow.log_param("test_rows", len(X_te))
                mlflow.log_param("random_seed", self.config.random_seed)

                model.fit(X_tr, y_train)
                preds = model.predict(X_v)

                rmse = np.sqrt(mean_squared_error(y_val, preds))
                mae = mean_absolute_error(y_val, preds)
                r2 = r2_score(y_val, preds)
                improvement_pct = (
                    (baseline_rmse - rmse) / baseline_rmse * 100
                )

                # ── Log metrics (Fix 5 audit requirement) ──────────
                mlflow.log_metric("rmse", rmse)
                mlflow.log_metric("mae", mae)
                mlflow.log_metric("r2", r2)
                mlflow.log_metric("baseline_rmse", baseline_rmse)
                mlflow.log_metric("improvement_pct", improvement_pct)

                results.append({
                    "model": name,
                    "rmse": round(rmse, 4),
                    "mae": round(mae, 4),
                    "r2_score": round(r2, 4),
                    "improvement_pct": round(improvement_pct, 2),
                })

                logger.info(
                    f"{name} vs PersistenceBaseline | target={target_col} | "
                    f"RMSE improvement={improvement_pct:.2f}%"
                )

                # Fix 2: Warn if model barely beats persistence
                if improvement_pct < 5.0:
                    logger.warning(
                        f"{name} provides negligible improvement over persistence "
                        f"for {target_col}. Consider whether this target is "
                        f"forecastable at 30-min horizon, or whether the model "
                        f"is just learning persistence via resource_pressure_score "
                        f"(see Fix 5/S5)."
                    )

                # ── Feature importance + S5 dominance check ────────
                if hasattr(model, "feature_importances_"):
                    importance_df = pd.DataFrame({
                        "feature": X_tr.columns,
                        "importance": model.feature_importances_
                    }).sort_values("importance", ascending=False)

                    importance_path = f"artifacts/models/{name}_feature_importance.csv"
                    importance_df.to_csv(importance_path, index=False)
                    mlflow.log_artifact(importance_path)

                    # S5: Pressure score dominance check
                    top_feature = importance_df.iloc[0]
                    if (
                        top_feature["feature"] == "resource_pressure_score"
                        and top_feature["importance"] > 0.5
                    ):
                        logger.warning(
                            f"resource_pressure_score accounts for "
                            f"{top_feature['importance']:.1%} of importance "
                            f"for {target_col}. Consider re-running without "
                            f"this feature to check if model performance is "
                            f"meaningfully different from persistence-equivalent "
                            f"behavior."
                        )

                # ── Log model to MLflow registry (Fix 5) ───────────
                try:
                    mlflow.sklearn.log_model(
                        model,
                        artifact_path="model",
                        registered_model_name=f"cloudpulse-{name}-{target_col}",
                    )
                except Exception as e:
                    # Model registry may not be available (e.g., no backend store)
                    # Fall back to logging without registration
                    logger.warning(f"Model registry unavailable, logging without registration: {e}")
                    mlflow.sklearn.log_model(model, artifact_path="model")

                logger.info(
                    f"MLflow run logged | model={name} | target={target_col} "
                    f"| run_id={mlflow.active_run().info.run_id}"
                )

        results_df = pd.DataFrame(results)
        logger.info(f"\n{results_df.sort_values('rmse').to_string(index=False)}")
        return results_df


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

        # Exclude baseline from "best model" selection
        ml_models = results_df[results_df["model"] != "PersistenceBaseline"]

        best_model = (
            ml_models
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
                "## All Results (including Persistence Baseline)\n\n"
            )

            f.write(
                results_df
                .sort_values("rmse")
                .to_markdown(
                    index=False
                )
            )

            f.write("\n\n")

            f.write(
                "## Best ML Model\n\n"
            )

            f.write(
                f"**Best Model:** "
                f"{best_model['model']}\n\n"
            )

            f.write(
                f"**R² Score:** "
                f"{best_model['r2_score']:.4f}\n\n"
            )

            if "improvement_pct" in best_model.index:
                f.write(
                    f"**RMSE Improvement vs Persistence:** "
                    f"{best_model['improvement_pct']:.2f}%\n\n"
                )

            # Note about ablation study
            ablation = results_df[results_df["model"] == "lightgbm_no_pressure"]
            if not ablation.empty:
                f.write("## S5 Ablation Study\n\n")
                f.write(
                    "LightGBM trained without `resource_pressure_score` and "
                    "`sla_breach_risk` features:\n\n"
                )
                f.write(ablation.to_markdown(index=False))
                f.write("\n")

        logger.info(
            f"Report saved to {report_path}"
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
        .chronological_split_per_region(
            X,
            y,
            df
        )
    )

    results_df = pipeline.run_mlflow_pipeline(
        X_train, X_val, X_test,
        y_train, y_val, y_test
    )
    pipeline.save_report(results_df)

    logger.info(
        "\nStep 11 "
        "Completed Successfully!"
    )