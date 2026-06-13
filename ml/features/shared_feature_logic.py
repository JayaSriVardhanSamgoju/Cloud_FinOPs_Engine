"""
CloudPulse AI — Shared Feature Computation Logic
-------------------------------------------------
S6 Fix: Train-Serving Skew Prevention

This module contains the SINGLE source of truth for computing
rolling, lag, and temporal features from raw telemetry data.
Both the training pipeline (time_features.py) and the real-time
inference pipeline (realtime_inference.py) import from here.

Usage:
    from ml.features.shared_feature_logic import compute_features
"""

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger("cloudpulse.features.shared")


# ── Feature computation constants ─────────────────────────────
LAG_STEPS = [1, 3, 6, 12, 24]

ROLLING_WINDOWS = [3, 6, 12, 24]

LAG_COLUMNS = [
    "cpu_usage",
    "request_rate",
    "response_latency_ms",
    "resource_pressure_score",
    "sla_breach_risk",
    "cost_per_hour",
]

ROLLING_COLUMNS = [
    "cpu_usage",
    "request_rate",
    "response_latency_ms",
]

TREND_COLUMNS = [
    "cpu_usage",
    "request_rate",
    "response_latency_ms",
]


def compute_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add time-based features from the timestamp column."""
    df = df.copy()
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["month"] = df["timestamp"].dt.month
    df["quarter"] = df["timestamp"].dt.quarter
    df["week_of_year"] = df["timestamp"].dt.isocalendar().week.astype(int)
    df["day_of_month"] = df["timestamp"].dt.day
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["is_business_hour"] = ((df["hour"] >= 9) & (df["hour"] <= 18)).astype(int)
    return df


def compute_cyclical_features(df: pd.DataFrame) -> pd.DataFrame:
    """Encode cyclical time features using sin/cos transforms."""
    df = df.copy()
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["day_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["day_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    return df


def compute_lag_features(
    df: pd.DataFrame,
    region_grouped: bool = True,
) -> pd.DataFrame:
    """
    Compute lag features for key metrics.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe sorted by [region, timestamp].
    region_grouped : bool
        If True, compute lags per region (training mode).
        If False, assume single-region data (inference mode).
    """
    df = df.copy()
    for col in LAG_COLUMNS:
        if col not in df.columns:
            continue
        for lag in LAG_STEPS:
            col_name = f"{col}_lag_{lag}"
            if region_grouped:
                df[col_name] = df.groupby("region")[col].shift(lag)
            else:
                df[col_name] = df[col].shift(lag)
    return df


def compute_rolling_features(
    df: pd.DataFrame,
    region_grouped: bool = True,
) -> pd.DataFrame:
    """
    Compute rolling mean, std, min, max for key metrics.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe sorted by [region, timestamp].
    region_grouped : bool
        If True, compute rolling stats per region (training mode).
        If False, assume single-region data (inference mode).
    """
    df = df.copy()
    for col in ROLLING_COLUMNS:
        if col not in df.columns:
            continue
        for window in ROLLING_WINDOWS:
            for stat_name, stat_func in [
                ("mean", "mean"),
                ("std", "std"),
                ("min", "min"),
                ("max", "max"),
            ]:
                col_name = f"{col}_rolling_{stat_name}_{window}"
                if region_grouped:
                    df[col_name] = (
                        df.groupby("region")[col]
                        .transform(lambda x: getattr(x.rolling(window), stat_func)())
                    )
                else:
                    df[col_name] = getattr(df[col].rolling(window), stat_func)()
    return df


def compute_trend_features(
    df: pd.DataFrame,
    region_grouped: bool = True,
) -> pd.DataFrame:
    """Compute delta and pct_change features."""
    df = df.copy()
    for col in TREND_COLUMNS:
        if col not in df.columns:
            continue
        if region_grouped:
            df[f"{col}_delta"] = df.groupby("region")[col].diff()
            df[f"{col}_pct_change"] = df.groupby("region")[col].pct_change()
        else:
            df[f"{col}_delta"] = df[col].diff()
            df[f"{col}_pct_change"] = df[col].pct_change()
    return df


def compute_features(
    df: pd.DataFrame,
    region_grouped: bool = True,
) -> pd.DataFrame:
    """
    Full feature computation pipeline — shared between training and inference.

    Parameters
    ----------
    df : pd.DataFrame
        Raw telemetry data with 'timestamp' column.
        Must be sorted by [region, timestamp] if region_grouped=True,
        or by timestamp alone if region_grouped=False.
    region_grouped : bool
        True for training (multi-region), False for inference (single-region).

    Returns
    -------
    pd.DataFrame
        DataFrame with all engineered features appended.
    """
    df = df.copy()

    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Sort
    if region_grouped:
        df = df.sort_values(["region", "timestamp"]).reset_index(drop=True)
    else:
        df = df.sort_values("timestamp").reset_index(drop=True)

    # Feature computation pipeline
    df = compute_temporal_features(df)
    df = compute_cyclical_features(df)
    df = compute_lag_features(df, region_grouped=region_grouped)
    df = compute_rolling_features(df, region_grouped=region_grouped)
    df = compute_trend_features(df, region_grouped=region_grouped)

    logger.info(
        f"Features computed | shape={df.shape} | "
        f"region_grouped={region_grouped}"
    )

    return df


# Minimum lookback required for inference (in minutes)
# Covers: max rolling window (24 steps × 5min = 120min) + max lag (24 steps × 5min = 120min)
LOOKBACK_MINUTES = 150
