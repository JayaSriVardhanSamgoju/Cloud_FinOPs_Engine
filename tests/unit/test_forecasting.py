import pytest
import pandas as pd
import numpy as np

# We'll use absolute imports assuming pytest is run from the project root
from ml.forecasting.train_forecasting_models import ForecastingPipeline

def test_chronological_split_per_region():
    # Setup mock data
    np.random.seed(42)
    regions = ["us-east-1", "eu-west-1"]
    
    data = []
    for r in regions:
        for i in range(100):
            data.append({
                "timestamp": pd.Timestamp("2025-01-01") + pd.Timedelta(hours=i),
                "region": r,
                "target": np.random.rand(),
                "feature1": np.random.rand()
            })
            
    df = pd.DataFrame(data)
    X = df[["feature1"]]
    y = df["target"]
    
    # Initialize pipeline
    pipeline = ForecastingPipeline()
    pipeline.config.train_size = 0.7
    pipeline.config.validation_size = 0.15
    pipeline.config.test_size = 0.15
    
    X_train, X_val, X_test, y_train, y_val, y_test = pipeline.chronological_split_per_region(X, y, df)
    
    # Assertions for dimensions
    assert len(X_train) == 140  # 70 from us, 70 from eu
    assert len(X_val) == 30
    assert len(X_test) == 30
    
    # Verify chronological order preservation per region
    # For us-east-1 (indices 0-99)
    # Train should be 0-69, Val 70-84, Test 85-99
    # The actual train indices in the split output might be interleaved if we didn't slice cleanly, 
    # but the logic appends reg_indices[:train_end] so it's clean.
    train_us_idx = [i for i in X_train.index if df.loc[i, "region"] == "us-east-1"]
    val_us_idx = [i for i in X_val.index if df.loc[i, "region"] == "us-east-1"]
    test_us_idx = [i for i in X_test.index if df.loc[i, "region"] == "us-east-1"]
    
    assert max(train_us_idx) < min(val_us_idx)
    assert max(val_us_idx) < min(test_us_idx)
