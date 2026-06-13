"""
API endpoint tests using FastAPI TestClient with a mocked inference pipeline.
These tests verify HTTP contract (status codes, JSON schema) without needing
a real model or database.
"""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


@pytest.fixture
def mock_pipeline():
    """Create a mock inference pipeline."""
    mock = MagicMock()
    mock.model_version = "test_v1"
    mock.loaded_at = datetime.datetime(2024, 1, 1, 12, 0, 0)

    # Mock load_latest_features to return a valid DataFrame
    mock.load_latest_features.return_value = pd.DataFrame({
        "cpu_usage": [55.0],
        "ram_usage": [40.0],
        "request_rate": [500.0],
        "response_latency_ms": [100.0],
        "cost_per_hour": [2.5],
        "active_instances": [4],
        "sla_breach_risk": [25.0],
        "resource_pressure_score": [40.0],
    })

    # Mock prepare_features
    mock.prepare_features.return_value = pd.DataFrame(
        np.random.rand(1, 10),
        columns=[f"feature_{i}" for i in range(10)]
    )

    # Mock predict
    mock.predict_future_cpu.return_value = 62.5

    # Mock recommendation
    mock.generate_scaling_recommendation.return_value = {
        "recommendation": "monitor",
        "reason": "Moderate load predicted",
        "urgency": "medium",
    }

    return mock


@pytest.fixture
def mock_engine():
    """Create a mock SQLAlchemy engine."""
    mock = MagicMock()
    # Mock the context managers
    mock.begin.return_value.__enter__ = MagicMock()
    mock.begin.return_value.__exit__ = MagicMock(return_value=False)
    mock.connect.return_value.__enter__ = MagicMock()
    mock.connect.return_value.__exit__ = MagicMock(return_value=False)
    return mock


@pytest.fixture
def client(mock_pipeline, mock_engine):
    """Create a TestClient with mocked dependencies."""
    with patch.dict("sys.modules", {}):
        with patch("app.main.pipeline", mock_pipeline), \
             patch("app.main.model", MagicMock()), \
             patch("app.main.engine", mock_engine), \
             patch("app.main.redis_client", None):
            from fastapi.testclient import TestClient
            from app.main import app
            app.state.start_time = datetime.datetime.utcnow()
            yield TestClient(app)


def test_health_endpoint(client):
    """GET /health should return 200 with required fields."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "model_version" in data
    assert "uptime_seconds" in data
    assert "db_connected" in data


def test_predict_returns_valid_schema(client):
    """GET /predict should return the expected JSON structure."""
    response = client.get("/predict")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "predicted_cpu_30min" in data
    assert "recommendation" in data
    assert isinstance(data["predicted_cpu_30min"], (int, float))
    assert isinstance(data["recommendation"], dict)


def test_predict_with_region(client):
    """GET /predict?region=ap-south-1 should work with region parameter."""
    response = client.get("/predict", params={"region": "ap-south-1"})
    assert response.status_code == 200
    data = response.json()
    assert "predicted_cpu_30min" in data


def test_predict_empty_data(client, mock_pipeline):
    """GET /predict should return 400 when no telemetry data is available."""
    mock_pipeline.load_latest_features.return_value = pd.DataFrame()
    response = client.get("/predict")
    assert response.status_code == 400
    assert "No recent telemetry" in response.json()["detail"]
