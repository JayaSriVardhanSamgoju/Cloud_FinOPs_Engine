"""
CloudPulse AI
Real-Time Inference Engine
--------------------------
Step 12 - Part 1

Features:
1. Load Best Model
2. Load Latest Telemetry Features
3. Real-Time CPU Prediction
4. Prediction Output
"""

import os
import json
import logging
import joblib
import pandas as pd

from dataclasses import dataclass

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
class InferenceConfig:

    model_path: str = (
        "artifacts/models/"
        "best_model.pkl"
    )

    feature_table: str = (
        "telemetry_features"
    )

    output_dir: str = (
        "artifacts/inference"
    )

    prediction_file: str = (
        "latest_prediction.json"
    )


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
# INFERENCE PIPELINE
# ============================================================

class RealtimeInferencePipeline:

    def __init__(self):

        self.config = (
            InferenceConfig()
        )

        os.makedirs(
            self.config.output_dir,
            exist_ok=True
        )

    # ========================================================
    # LOAD MODEL
    # ========================================================

    def load_model(self):

        logger.info(
            "Loading best model..."
        )

        model = joblib.load(
            self.config.model_path
        )

        logger.info(
            "Model loaded successfully."
        )

        return model


    # ========================================================
    # LOAD LATEST FEATURES
    # ========================================================

    def load_latest_features(self):

        logger.info(
            "Loading latest telemetry "
            "features..."
        )

        query = f"""
        SELECT *
        FROM {self.config.feature_table}
        ORDER BY timestamp DESC
        LIMIT 1
        """

        df = pd.read_sql(
            query,
            engine
        )

        logger.info(
            "Latest telemetry row loaded."
        )

        return df


    # ========================================================
    # PREPARE FEATURES
    # ========================================================

    def prepare_features(
        self,
        df,
        model
    ):

        logger.info(
            "Preparing features..."
        )

        remove_columns = [

            "id",
            "timestamp",
            "created_at",

            "target_cpu_30min",
            "target_cpu_1hour",
            "target_request_rate_30min",
            "target_latency_30min"
        ]

        X = df.drop(
            columns=[
                col
                for col
                in remove_columns
                if col in df.columns
            ],
            errors="ignore"
        )

        # Create dummies for all categories present (don't drop first for single row)
        X = pd.get_dummies(X)

        # Align columns to what the model expects
        expected_features = getattr(model, "feature_names_in_", None)
        if expected_features is not None:
            # Reindex will keep matching columns, drop extra ones, and fill missing ones with False/0
            X = X.reindex(columns=expected_features, fill_value=0)

        # Ensure all booleans are converted to ints to prevent dtype mismatch with xgboost
        X = X.astype(float)

        logger.info(
            f"Feature shape: "
            f"{X.shape}"
        )

        return X


    # ========================================================
    # PREDICT
    # ========================================================

    def predict_future_cpu(
        self,
        model,
        X
    ):

        logger.info(
            "Generating prediction..."
        )

        prediction = (
            model.predict(X)[0]
        )

        logger.info(
            f"Predicted CPU "
            f"(30 min): "
            f"{prediction:.2f}"
        )

        return prediction


    # ========================================================
    # SAVE PREDICTION
    # ========================================================

    def save_prediction(
        self,
        prediction
    ):

        output_path = (
            f"{self.config.output_dir}/"
            f"{self.config.prediction_file}"
        )

        prediction_dict = {

            "predicted_cpu_30min":
            round(
                float(prediction),
                2
            )
        }

        with open(
            output_path,
            "w"
        ) as f:

            json.dump(
                prediction_dict,
                f,
                indent=4
            )

        logger.info(
            "Prediction saved."
        )
        # ========================================================
    # SCALING RECOMMENDATION ENGINE
    # ========================================================

    def generate_scaling_recommendation(
        self,
        latest_df,
        prediction
    ):

        logger.info(
            "Generating scaling "
            "recommendation..."
        )

        current_cpu = (
            latest_df[
                "cpu_usage"
            ].iloc[0]
        )

        sla_risk = (
            latest_df[
                "sla_breach_risk"
            ].iloc[0]
        )

        active_instances = (
            latest_df[
                "active_instances"
            ].iloc[0]
        )

        cost = (
            latest_df[
                "cost_per_hour"
            ].iloc[0]
        )

        recommendation = {}

        # ====================================================
        # URGENT SCALE UP
        # ====================================================
        print("\nDEBUG VALUES")
        print("Predicted CPU:", prediction)
        print("Current CPU:", current_cpu)
        print("SLA Risk:", sla_risk)
        print("Cost Per Hour:", cost)
        print("Instances:", active_instances)
        
        if (
            prediction > 85
            or
            sla_risk > 70
        ):

            recommendation = {

                "recommendation":
                "urgent_scale_up",

                "reason":
                (
                    "Predicted "
                    "resource overload "
                    "or SLA degradation"
                ),

                "instances_to_add":
                3,

                "current_instances":
                int(active_instances),

                "target_instances":
                int(
                    active_instances + 3
                ),

                "urgency":
                "critical"
            }

        # ====================================================
        # SCALE UP
        # ====================================================

        elif prediction >= 75:

            recommendation = {

                "recommendation":
                "scale_up",

                "reason":
                (
                    "Predicted "
                    "high CPU load"
                ),

                "instances_to_add":
                2,

                "current_instances":
                int(active_instances),

                "target_instances":
                int(
                    active_instances + 2
                ),

                "urgency":
                "high"
            }

        # ====================================================
        # MONITOR
        # ====================================================

        elif prediction >= 60:

            recommendation = {

                "recommendation":
                "monitor",

                "reason":
                (
                    "Moderate load "
                    "predicted"
                ),

                "action":
                (
                    "Prepare "
                    "autoscaling"
                ),

                "urgency":
                "medium"
            }

        # ====================================================
        # SCALE DOWN
        # ====================================================

        elif (
            prediction < 35
            and
            cost > 3
        ):

            recommendation = {

                "recommendation":
                "scale_down",

                "reason":
                (
                    "Low predicted "
                    "usage and "
                    "high infra cost"
                ),

                "instances_to_remove":
                1,

                "current_instances":
                int(active_instances),

                "target_instances":
                max(
                    1,
                    int(
                        active_instances - 1
                    )
                ),

                "urgency":
                "low"
            }

        # ====================================================
        # HEALTHY
        # ====================================================

        else:

            recommendation = {

                "recommendation":
                "maintain",

                "reason":
                (
                    "Infrastructure "
                    "healthy"
                ),

                "urgency":
                "low"
            }

        logger.info(
            f"Recommendation: "
            f"{recommendation['recommendation']}"
        )

        return recommendation


    # ========================================================
    # SAVE RECOMMENDATION
    # ========================================================

    def save_recommendation(
        self,
        recommendation
    ):

        output_path = (
            f"{self.config.output_dir}/"
            "scaling_recommendation.json"
        )

        with open(
            output_path,
            "w"
        ) as f:

            json.dump(
                recommendation,
                f,
                indent=4
            )

        logger.info(
            "Scaling recommendation "
            "saved."
        )



# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    logger.info("=" * 60)

    logger.info(
        "CloudPulse AI "
        "Inference Pipeline Started"
    )

    logger.info("=" * 60)

    pipeline = (
        RealtimeInferencePipeline()
    )

    model = (
        pipeline.load_model()
    )

    latest_df = (
        pipeline
        .load_latest_features()
    )

    X = (
        pipeline
        .prepare_features(
            latest_df,
            model
        )
    )

    prediction = (
        pipeline
        .predict_future_cpu(
            model,
            X
        )
    )

    pipeline.save_prediction(
        prediction
    )

    recommendation = (
        pipeline
        .generate_scaling_recommendation(
            latest_df,
            prediction
        )
    )

    pipeline.save_recommendation(
        recommendation
    )

    logger.info(
        "\nStep 12 "
        "Completed Successfully!"
    )