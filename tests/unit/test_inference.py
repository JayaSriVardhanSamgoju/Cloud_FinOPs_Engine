"""
Tests for RealtimeInferencePipeline — feature preparation and prediction logic.
These tests use mock data and mock models to avoid requiring a database or model file.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.inference.realtime_inference import RealtimeInferencePipeline


@pytest.fixture
def pipeline():
    """Create a pipeline instance without loading a real model."""
    with patch.object(RealtimeInferencePipeline, '__init__', lambda self: None):
        p = RealtimeInferencePipeline.__new__(RealtimeInferencePipeline)
        p.config = MagicMock()
        p.config.output_dir = "test_output"
        return p


@pytest.fixture
def mock_model():
    """Create a mock model with feature_names_in_ attribute."""
    model = MagicMock()
    model.feature_names_in_ = np.array([
        "cpu_usage", "ram_usage", "request_rate", "response_latency_ms",
        "cost_per_hour", "active_instances", "hour", "day_of_week",
        "is_weekend", "region_us-east-1",
    ])
    model.predict.return_value = np.array([72.5])
    return model


@pytest.fixture
def sample_df():
    """Create a sample telemetry DataFrame mimicking inference pipeline output."""
    return pd.DataFrame({
        "id": [1],
        "timestamp": [pd.Timestamp("2024-06-15 14:30:00")],
        "created_at": [pd.Timestamp("2024-06-15 14:30:00")],
        "region": ["us-east-1"],
        "cpu_usage": [65.0],
        "ram_usage": [45.0],
        "request_rate": [850.0],
        "response_latency_ms": [120.0],
        "cost_per_hour": [3.5],
        "active_instances": [5],
        "hour": [14],
        "day_of_week": [5],
        "is_weekend": [1],
        "resource_pressure_score": [55.0],
        "sla_breach_risk": [30.0],
        "target_cpu_30min": [70.0],
        "target_cpu_1hour": [75.0],
        "target_request_rate_30min": [900.0],
        "target_latency_30min": [130.0],
    })


def test_prepare_features_drops_target_columns(pipeline, mock_model, sample_df):
    """Verify that target columns and metadata columns are removed before prediction."""
    X = pipeline.prepare_features(sample_df, mock_model)

    # Target columns must not appear in prepared features
    forbidden_cols = ["target_cpu_30min", "target_cpu_1hour",
                      "target_request_rate_30min", "target_latency_30min",
                      "id", "timestamp", "created_at"]
    for col in forbidden_cols:
        assert col not in X.columns, f"Column '{col}' should be dropped but was present"


def test_prepare_features_aligns_to_model(pipeline, mock_model, sample_df):
    """Verify that output columns match model.feature_names_in_ exactly."""
    X = pipeline.prepare_features(sample_df, mock_model)

    assert list(X.columns) == list(mock_model.feature_names_in_), \
        "Feature columns should match model's expected features"
    # Missing features should be filled with 0
    assert X.shape[1] == len(mock_model.feature_names_in_)


def test_prepare_features_all_float(pipeline, mock_model, sample_df):
    """Verify all output features are float (required for xgboost)."""
    X = pipeline.prepare_features(sample_df, mock_model)

    for col in X.columns:
        assert X[col].dtype == np.float64, f"Column '{col}' should be float64"


def test_predict_returns_scalar(pipeline, mock_model):
    """Verify predict_future_cpu returns a single numeric value."""
    X = pd.DataFrame(np.random.rand(1, 10), columns=[f"f{i}" for i in range(10)])
    result = pipeline.predict_future_cpu(mock_model, X)

    assert isinstance(result, (float, np.floating)), "Prediction should be a scalar float"
    mock_model.predict.assert_called_once()
