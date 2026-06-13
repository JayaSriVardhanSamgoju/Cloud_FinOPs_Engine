"""
Integration tests to verify database persistence.
Requires a running PostgreSQL instance (via docker-compose).
Skipped automatically if the DB is unreachable.
"""

import pytest
import datetime
from sqlalchemy import text
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.main import app, check_db_connection
from configs.db_config import engine

# Skip all tests in this module if DB is not available
pytestmark = pytest.mark.skipif(
    not check_db_connection(),
    reason="PostgreSQL database not available for integration tests"
)

client = TestClient(app)


def test_prediction_and_recommendation_saved_to_db():
    """
    Integration test:
    1. Call /predict endpoint
    2. Verify a row is written to model_predictions
    3. Verify a row is written to scaling_recommendations
    """
    # 1. Trigger prediction
    response = client.get("/predict?region=us-east-1")
    
    # If 400 (no telemetry), we can't test persistence. Just pass.
    if response.status_code == 400:
        pytest.skip("No telemetry data in DB to run prediction.")
        
    assert response.status_code == 200
    data = response.json()
    
    timestamp_str = data["timestamp"]
    predicted_cpu = data["predicted_cpu_30min"]
    
    # Check if data was written within the last minute to avoid race conditions
    # We query by checking the most recent records
    
    with engine.connect() as conn:
        # 2. Check model_predictions
        pred_query = text("""
            SELECT predicted_cpu, model_version
            FROM model_predictions
            ORDER BY prediction_timestamp DESC
            LIMIT 1
        """)
        pred_row = conn.execute(pred_query).fetchone()
        
        assert pred_row is not None, "No prediction found in DB"
        # Rounding for float comparison
        assert abs(pred_row[0] - predicted_cpu) < 0.1, "Saved CPU does not match API response"
        
        # 3. Check scaling_recommendations
        rec_query = text("""
            SELECT predicted_cpu, decision_type
            FROM scaling_recommendations
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        rec_row = conn.execute(rec_query).fetchone()
        
        assert rec_row is not None, "No recommendation found in DB"
        assert abs(rec_row[0] - predicted_cpu) < 0.1, "Recommendation CPU does not match"
