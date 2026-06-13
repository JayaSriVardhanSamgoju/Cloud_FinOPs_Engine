"""
CloudPulse AI
Model Drift Detection Script
----------------------------
Measures RMSE between predictions from 30+ minutes ago
and the actual telemetry data that has now matured.
"""

import sys
import logging
from pathlib import Path
from sqlalchemy import text
import pandas as pd
import numpy as np
import datetime

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from configs.db_config import engine

# Configuration
RMSE_DRIFT_THRESHOLD = 7.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def detect_drift():
    logger.info("Starting drift detection analysis...")

    query = """
        SELECT 
            p.prediction_timestamp,
            p.predicted_cpu,
            AVG(m.cpu_usage) as actual_cpu
        FROM model_predictions p
        JOIN telemetry_metrics m 
            ON m.timestamp = p.prediction_timestamp + interval '30 minutes'
        WHERE p.prediction_timestamp >= NOW() - interval '24 hours'
        GROUP BY p.prediction_timestamp, p.predicted_cpu
    """

    df = pd.read_sql(query, engine)
    
    if df.empty:
        logger.warning("No mature predictions found to analyze drift. (Need predictions older than 30 mins)")
        return
    
    # Calculate RMSE
    df["squared_error"] = (df["predicted_cpu"] - df["actual_cpu"]) ** 2
    rmse = np.sqrt(df["squared_error"].mean())
    
    logger.info(f"Analyzed {len(df)} predictions. Current RMSE: {rmse:.2f}")
    
    drift_detected = bool(rmse > RMSE_DRIFT_THRESHOLD)
    
    if drift_detected:
        logger.warning(f"DRIFT DETECTED! RMSE {rmse:.2f} exceeds threshold {RMSE_DRIFT_THRESHOLD}.")
    else:
        logger.info("Model performance is stable.")
        
    # Log to database
    report_path = f"artifacts/reports/drift_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    insert_query = text("""
        INSERT INTO drift_reports (drift_score, drift_detected, report_path)
        VALUES (:score, :detected, :path)
    """)
    
    with engine.begin() as conn:
        conn.execute(insert_query, {
            "score": float(rmse),
            "detected": drift_detected,
            "path": report_path
        })
        
    logger.info("Drift report saved to database.")

if __name__ == "__main__":
    detect_drift()
