import pytest
import pandas as pd
import numpy as np
from ml.features.shared_feature_logic import compute_features
from ml.feature_engineering.time_features import TimeSeriesFeatureEngineering

def test_feature_logic_leakage():
    # Setup mock data for a single region
    np.random.seed(42)
    timestamps = pd.date_range("2025-01-01", periods=100, freq="5min")
    
    df = pd.DataFrame({
        "timestamp": timestamps,
        "region": "us-east-1",
        "cpu_usage": np.linspace(10, 100, 100),
        "request_rate": np.linspace(100, 1000, 100),
        "response_latency_ms": np.linspace(20, 200, 100),
        "resource_pressure_score": np.linspace(30, 90, 100),
        "sla_breach_risk": np.linspace(10, 50, 100),
        "cost_per_hour": np.linspace(1, 5, 100)
    })
    
    # Run the shared feature computation (generates lags/rolling)
    processed_df = compute_features(df, region_grouped=True)
    
    # Now create target variables using the training pipeline class
    pipeline = TimeSeriesFeatureEngineering()
    final_df = pipeline.create_target_variables(processed_df)
    
    # We should drop all NaNs introduced by lag/rolling features 
    # to mimic the rest of the pipeline's behavior
    final_df = final_df.dropna().reset_index(drop=True)
    
    # After dropna, there should be no NaNs
    assert not final_df.isnull().any().any()
    
    # Targets are 30min (6 steps) and 1hr (12 steps) ahead
    # We should have fewer rows than original df
    assert len(final_df) < len(df)
    
    # Verify the target is strictly future data
    # cpu_usage increases monotonically in our mock data
    assert final_df.iloc[0]["target_cpu_30min"] > final_df.iloc[0]["cpu_usage"]
