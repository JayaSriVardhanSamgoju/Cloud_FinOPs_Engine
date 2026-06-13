"""
CloudPulse AI — Predictive Infrastructure Intelligence API
-----------------------------------------------------------
v2.0.0

Endpoints:
    GET  /health                  — System health, model version, uptime
    GET  /predict                 — Real-time CPU prediction + scaling recommendation
    GET  /predictions/history     — Historical predictions vs actuals
    GET  /recommendations/history — Scaling decision log
    GET  /telemetry/history       — Time-series telemetry for charts
    GET  /telemetry/regional-summary  — Per-region aggregates
    GET  /telemetry/workload-summary  — Per-workload aggregates
    GET  /drift/status            — Latest drift report
    POST /drift/run               — Trigger drift detection
    GET  /model/info              — Model metadata from training logs
"""

import sys
import json
import logging
import traceback
import datetime
from typing import Optional

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
import pandas as pd
import numpy as np

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from ml.inference.realtime_inference import RealtimeInferencePipeline
from configs.db_config import engine

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── Rate Limiter ──────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── App ───────────────────────────────────────────────────────
app = FastAPI(
    title="CloudPulse AI — Predictive Infrastructure Intelligence API",
    description="Real-time CPU forecasting and scaling recommendations for multi-region cloud infrastructure.",
    version="2.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Redis (graceful fallback) ─────────────────────────────────
redis_client = None
try:
    import redis as redis_lib
    redis_client = redis_lib.Redis(
        host="127.0.0.1", port=6379,
        decode_responses=True, socket_connect_timeout=2
    )
    redis_client.ping()
    logger.info("Redis connected successfully.")
except Exception:
    logger.warning("Redis unavailable — caching disabled.")
    redis_client = None

# ── Pipeline & Model ─────────────────────────────────────────
pipeline = RealtimeInferencePipeline()
model = pipeline.load_model()

# Attach metadata for /health and /model/info
pipeline.model_version = "best_model_v1"
pipeline.loaded_at = datetime.datetime.utcnow()


# ── Startup ───────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    app.state.start_time = datetime.datetime.utcnow()
    logger.info("CloudPulse AI API started.")


# ── Helpers ───────────────────────────────────────────────────
def check_db_connection() -> bool:
    """Ping PostgreSQL with SELECT 1."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_last_prediction_timestamp() -> Optional[str]:
    """Fetch most recent prediction timestamp."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT prediction_timestamp FROM model_predictions "
                "ORDER BY prediction_timestamp DESC LIMIT 1"
            ))
            row = result.fetchone()
            return row[0].isoformat() if row else None
    except Exception:
        return None


# ── Schemas ───────────────────────────────────────────────────
class PredictionResponse(BaseModel):
    timestamp: str
    predicted_cpu_30min: float
    recommendation: dict


class HealthResponse(BaseModel):
    status: str
    model_version: str
    model_loaded_at: str
    uptime_seconds: float
    db_connected: bool
    last_prediction_at: Optional[str]


# ══════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════


# ── 1. Health Check ───────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["system"])
def health_check():
    """System health: model version, uptime, last prediction time, DB connectivity."""
    uptime = (datetime.datetime.utcnow() - app.state.start_time).total_seconds()
    return HealthResponse(
        status="operational" if check_db_connection() else "degraded",
        model_version=pipeline.model_version,
        model_loaded_at=pipeline.loaded_at.isoformat(),
        uptime_seconds=round(uptime, 1),
        db_connected=check_db_connection(),
        last_prediction_at=get_last_prediction_timestamp(),
    )


# ── 2. Predict ────────────────────────────────────────────────
@app.get("/predict", response_model=PredictionResponse, tags=["predictions"])
@limiter.limit("30/minute")
def predict(request: Request, response: Response, region: Optional[str] = Query(default=None)):
    """
    Real-time CPU prediction with scaling recommendation.
    Results are cached in Redis for 60 seconds per region.
    """
    try:
        cache_key = f"predict:{region or 'all'}"

        # Check Redis cache
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    response.headers["X-Cache"] = "HIT"
                    return PredictionResponse(**json.loads(cached))
            except Exception:
                pass

        response.headers["X-Cache"] = "MISS"

        latest_df = pipeline.load_latest_features(region=region)
        if latest_df.empty:
            raise HTTPException(
                status_code=400,
                detail="No recent telemetry data available for prediction."
            )

        X = pipeline.prepare_features(latest_df, model)
        predicted_cpu = pipeline.predict_future_cpu(model, X)
        recommendation = pipeline.generate_scaling_recommendation(latest_df, predicted_cpu)

        now = datetime.datetime.now()

        # Persist to database
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO model_predictions
                (prediction_timestamp, horizon_minutes, predicted_cpu, model_version)
                VALUES (:ts, 30, :cpu, 'best_model')
            """), {"ts": now, "cpu": float(predicted_cpu)})

            cur_instances = recommendation.get("current_instances", 0)
            rec_instances = recommendation.get("target_instances", cur_instances)
            decision = recommendation.get("recommendation", "monitor")
            reason = recommendation.get("reason", "No reason provided")

            conn.execute(text("""
                INSERT INTO scaling_recommendations
                (timestamp, current_instances, recommended_instances,
                 predicted_cpu, decision_type, reason, confidence_score)
                VALUES (:ts, :cur, :rec, :cpu, :decision, :reason, 0.95)
            """), {
                "ts": now, "cur": cur_instances, "rec": rec_instances,
                "cpu": float(predicted_cpu), "decision": decision, "reason": reason,
            })

        result = PredictionResponse(
            timestamp=now.isoformat(),
            predicted_cpu_30min=round(float(predicted_cpu), 2),
            recommendation=recommendation,
        )

        # Write to Redis cache (60s TTL)
        if redis_client:
            try:
                redis_client.setex(cache_key, 60, result.model_dump_json())
            except Exception:
                pass

        return result

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── 3. Telemetry History ──────────────────────────────────────
@app.get("/telemetry/history", tags=["telemetry"])
def telemetry_history(
    region: str = Query(default="us-east-1"),
    hours: int = Query(default=24, le=168),
):
    """
    Returns time-series telemetry for charts.
    Resampled to ~5-minute intervals for the last N hours.
    """
    try:
        query = text("""
            SELECT timestamp, cpu_usage, ram_usage, request_rate,
                   response_latency_ms, cost_per_hour, is_anomaly,
                   resource_pressure_score, sla_breach_risk,
                   active_instances, special_event
            FROM telemetry_metrics
            WHERE region = :region
              AND timestamp >= (
                  SELECT MAX(timestamp) - INTERVAL ':hours hours'
                  FROM telemetry_metrics
              )
            ORDER BY timestamp ASC
        """)

        # Use raw string interpolation for interval since parameterized intervals
        # are not supported by all drivers
        raw_query = f"""
            SELECT timestamp, cpu_usage, ram_usage, request_rate,
                   response_latency_ms, cost_per_hour, is_anomaly,
                   resource_pressure_score, sla_breach_risk,
                   active_instances, special_event
            FROM telemetry_metrics
            WHERE region = :region
              AND timestamp >= (
                  SELECT MAX(timestamp) - INTERVAL '{hours} hours'
                  FROM telemetry_metrics
              )
            ORDER BY timestamp ASC
        """

        df = pd.read_sql(text(raw_query), engine, params={"region": region})

        if df.empty:
            return {"data": [], "region": region, "hours": hours}

        # Convert timestamps to ISO strings
        records = df.to_dict(orient="records")
        for r in records:
            if pd.notna(r.get("timestamp")):
                r["timestamp"] = r["timestamp"].isoformat()
            # Convert numpy types to native Python
            for k, v in r.items():
                if isinstance(v, (np.integer,)):
                    r[k] = int(v)
                elif isinstance(v, (np.floating,)):
                    r[k] = float(v)
                elif isinstance(v, (np.bool_,)):
                    r[k] = bool(v)
                elif pd.isna(v):
                    r[k] = None

        return {"data": records, "region": region, "hours": hours, "count": len(records)}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── 4. Regional Summary ──────────────────────────────────────
@app.get("/telemetry/regional-summary", tags=["telemetry"])
def regional_summary():
    """
    Per-region aggregates: avg CPU, cost, request rate, anomaly count,
    plus a 24-hour CPU sparkline (24 hourly points) per region.
    """
    try:
        # Aggregates
        agg_query = text("""
            SELECT region,
                   AVG(cpu_usage) AS avg_cpu,
                   AVG(cost_per_hour) AS avg_cost,
                   AVG(request_rate) AS avg_request_rate,
                   AVG(response_latency_ms) AS avg_latency,
                   SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) AS anomaly_count,
                   COUNT(*) AS total_records
            FROM telemetry_metrics
            GROUP BY region
            ORDER BY region
        """)
        agg_df = pd.read_sql(agg_query, engine)

        # Sparkline: last 24 hours, 1 point per hour per region
        spark_query = text("""
            SELECT region,
                   date_trunc('hour', timestamp) AS hour,
                   AVG(cpu_usage) AS avg_cpu
            FROM telemetry_metrics
            WHERE timestamp >= (SELECT MAX(timestamp) - INTERVAL '24 hours' FROM telemetry_metrics)
            GROUP BY region, date_trunc('hour', timestamp)
            ORDER BY region, hour
        """)
        spark_df = pd.read_sql(spark_query, engine)

        # Build response
        regions = []
        for _, row in agg_df.iterrows():
            r_name = row["region"]
            sparkline = spark_df[spark_df["region"] == r_name]["avg_cpu"].tolist()
            regions.append({
                "region": r_name,
                "avg_cpu": round(float(row["avg_cpu"]), 2),
                "avg_cost": round(float(row["avg_cost"]), 2),
                "avg_request_rate": round(float(row["avg_request_rate"]), 2),
                "avg_latency": round(float(row["avg_latency"]), 2),
                "anomaly_count": int(row["anomaly_count"]),
                "total_records": int(row["total_records"]),
                "cpu_sparkline": [round(float(v), 2) for v in sparkline],
            })

        return {"regions": regions}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── 5. Workload Summary ──────────────────────────────────────
@app.get("/telemetry/workload-summary", tags=["telemetry"])
def workload_summary(region: Optional[str] = Query(default=None)):
    """
    Per-workload-type aggregates: avg CPU, request rate, latency, disk I/O,
    network out, cost. Optional region filter.
    """
    try:
        region_filter = ""
        params = {}
        if region:
            region_filter = "WHERE region = :region"
            params["region"] = region

        raw = f"""
            SELECT workload_type,
                   AVG(cpu_usage) AS avg_cpu,
                   AVG(request_rate) AS avg_request_rate,
                   AVG(response_latency_ms) AS avg_latency,
                   AVG(disk_io) AS avg_disk_io,
                   AVG(network_out) AS avg_network_out,
                   AVG(cost_per_hour) AS avg_cost
            FROM telemetry_metrics
            {region_filter}
            GROUP BY workload_type
            ORDER BY workload_type
        """

        df = pd.read_sql(text(raw), engine, params=params)

        workloads = []
        for _, row in df.iterrows():
            workloads.append({
                "workload_type": row["workload_type"],
                "avg_cpu": round(float(row["avg_cpu"]), 2),
                "avg_request_rate": round(float(row["avg_request_rate"]), 2),
                "avg_latency": round(float(row["avg_latency"]), 2),
                "avg_disk_io": round(float(row["avg_disk_io"]), 2),
                "avg_network_out": round(float(row["avg_network_out"]), 2),
                "avg_cost": round(float(row["avg_cost"]), 2),
            })

        return {"workloads": workloads, "region_filter": region}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── 6. Predictions History ───────────────────────────────────
@app.get("/predictions/history", tags=["predictions"])
def predictions_history(
    region: str = Query(default="us-east-1"),
    limit: int = Query(default=100, le=500),
):
    """
    Last N predictions with actual CPU values (if matured).
    Joins model_predictions with telemetry_metrics on timestamp + 30min.
    """
    try:
        query = text("""
            SELECT
                p.prediction_timestamp,
                p.predicted_cpu,
                p.model_version,
                m.cpu_usage AS actual_cpu
            FROM model_predictions p
            LEFT JOIN telemetry_metrics m
                ON m.timestamp = p.prediction_timestamp + INTERVAL '30 minutes'
                AND m.region = :region
            ORDER BY p.prediction_timestamp DESC
            LIMIT :limit
        """)

        df = pd.read_sql(query, engine, params={"region": region, "limit": limit})

        records = []
        for _, row in df.iterrows():
            records.append({
                "timestamp": row["prediction_timestamp"].isoformat() if pd.notna(row["prediction_timestamp"]) else None,
                "predicted_cpu": round(float(row["predicted_cpu"]), 2) if pd.notna(row["predicted_cpu"]) else None,
                "actual_cpu": round(float(row["actual_cpu"]), 2) if pd.notna(row["actual_cpu"]) else None,
                "model_version": row["model_version"],
            })

        return {"predictions": records, "count": len(records), "region": region}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── 7. Recommendations History ────────────────────────────────
@app.get("/recommendations/history", tags=["predictions"])
def recommendations_history(
    limit: int = Query(default=20, le=100),
):
    """Last N scaling recommendations for the AI Decision Log."""
    try:
        query = text("""
            SELECT timestamp, current_instances, recommended_instances,
                   predicted_cpu, decision_type, reason, confidence_score
            FROM scaling_recommendations
            ORDER BY timestamp DESC
            LIMIT :limit
        """)

        df = pd.read_sql(query, engine, params={"limit": limit})

        records = []
        for _, row in df.iterrows():
            records.append({
                "timestamp": row["timestamp"].isoformat() if pd.notna(row["timestamp"]) else None,
                "current_instances": int(row["current_instances"]) if pd.notna(row["current_instances"]) else None,
                "recommended_instances": int(row["recommended_instances"]) if pd.notna(row["recommended_instances"]) else None,
                "predicted_cpu": round(float(row["predicted_cpu"]), 2) if pd.notna(row["predicted_cpu"]) else None,
                "decision_type": row["decision_type"],
                "reason": row["reason"],
                "confidence_score": round(float(row["confidence_score"]), 2) if pd.notna(row["confidence_score"]) else None,
            })

        return {"recommendations": records, "count": len(records)}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── 8. Drift Status ──────────────────────────────────────────
@app.get("/drift/status", tags=["monitoring"])
def drift_status():
    """Returns the latest drift report: drift score, detected flag, checked timestamp."""
    try:
        query = text("""
            SELECT drift_score, drift_detected, created_at
            FROM drift_reports
            ORDER BY created_at DESC
            LIMIT 1
        """)

        df = pd.read_sql(query, engine)

        if df.empty:
            return {
                "drift_score": None,
                "drift_detected": None,
                "checked_at": None,
                "threshold": 7.0,
                "message": "No drift reports available yet.",
            }

        row = df.iloc[0]
        return {
            "drift_score": round(float(row["drift_score"]), 2) if pd.notna(row["drift_score"]) else None,
            "drift_detected": bool(row["drift_detected"]),
            "checked_at": row["created_at"].isoformat() if pd.notna(row["created_at"]) else None,
            "threshold": 7.0,
            "message": "Drift detected — model retraining recommended." if row["drift_detected"] else "Model performance stable.",
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── 9. Trigger Drift Check ───────────────────────────────────
@app.post("/drift/run", tags=["monitoring"])
@limiter.limit("5/minute")
def trigger_drift_check(request: Request):
    """Synchronously runs drift detection and returns the result."""
    try:
        from ml.monitoring.drift_detection import detect_drift
        detect_drift()

        # Return the freshly-created report
        query = text("""
            SELECT drift_score, drift_detected, created_at
            FROM drift_reports
            ORDER BY created_at DESC
            LIMIT 1
        """)
        df = pd.read_sql(query, engine)

        if df.empty:
            return {"message": "Drift check completed but no report was generated."}

        row = df.iloc[0]
        return {
            "drift_score": round(float(row["drift_score"]), 2) if pd.notna(row["drift_score"]) else None,
            "drift_detected": bool(row["drift_detected"]),
            "checked_at": row["created_at"].isoformat() if pd.notna(row["created_at"]) else None,
            "message": "Drift check completed successfully.",
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── 10. Model Info ────────────────────────────────────────────
@app.get("/model/info", tags=["monitoring"])
def model_info():
    """Model metadata from the latest training log entry."""
    try:
        query = text("""
            SELECT model_name, rmse, mae, mape, training_time,
                   model_version, dataset_version, created_at
            FROM model_training_logs
            ORDER BY created_at DESC
            LIMIT 1
        """)

        df = pd.read_sql(query, engine)

        if df.empty:
            # Return sensible defaults from the loaded model
            feature_count = len(getattr(model, "feature_names_in_", []))
            return {
                "model_name": "xgboost",
                "model_version": pipeline.model_version,
                "training_date": None,
                "feature_count": feature_count,
                "rmse": None,
                "mae": None,
                "mape": None,
                "training_time_seconds": None,
                "message": "No training logs found in database. Showing loaded model info.",
            }

        row = df.iloc[0]
        feature_count = len(getattr(model, "feature_names_in_", []))
        return {
            "model_name": row["model_name"],
            "model_version": row["model_version"] or pipeline.model_version,
            "training_date": row["created_at"].isoformat() if pd.notna(row["created_at"]) else None,
            "feature_count": feature_count,
            "rmse": round(float(row["rmse"]), 4) if pd.notna(row["rmse"]) else None,
            "mae": round(float(row["mae"]), 4) if pd.notna(row["mae"]) else None,
            "mape": round(float(row["mape"]), 4) if pd.notna(row["mape"]) else None,
            "training_time_seconds": round(float(row["training_time"]), 2) if pd.notna(row["training_time"]) else None,
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
