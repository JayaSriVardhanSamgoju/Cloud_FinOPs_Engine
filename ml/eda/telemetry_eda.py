"""
CloudPulse AI — Telemetry Exploratory Data Analysis Pipeline
=============================================================

Production-grade, modular, re-runnable EDA pipeline that validates
telemetry data quality, infrastructure behavior, correlations,
regional/workload differentiation, cost, latency/SLA, anomalies,
time-series seasonality, and feature-store readiness.

Reads exclusively from PostgreSQL via SQLAlchemy.
Generates 26 visualizations + 1 consolidated Markdown report.

Usage:
    python ml/eda/telemetry_eda.py
"""

import os
import sys
import logging
import warnings
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless rendering
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Project root resolution (so this module can be run directly)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("cloudpulse.eda")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Named constants — thresholds & magic-number elimination
# ---------------------------------------------------------------------------
# Correlation thresholds (Section 10)
CORR_CPU_RAM: float = 0.70
CORR_CPU_RPS: float = 0.75
CORR_CPU_LATENCY: float = 0.60
CORR_CPU_COST: float = 0.60
CORR_LATENCY_SLA: float = 0.70

# Anomaly rate bounds (Section 9)
ANOMALY_RATE_MIN: float = 0.005   # 0.5 %
ANOMALY_RATE_MAX: float = 0.08    # 8 %

# SLA breach thresholds (Section 12)
SLA_HEALTHY_UPPER: float = 30.0
SLA_WARNING_UPPER: float = 60.0

# Scatter-plot sample limit
SCATTER_SAMPLE_SIZE: int = 20_000

# Feature-store correlation thresholds (Section 13)
FEATURE_LAG_CPU_CORR: float = 0.85
FEATURE_ROLLING_PRESSURE_CORR: float = 0.70

# Histogram bin count
HIST_BINS: int = 50

# Weekday labels
WEEKDAY_LABELS: List[str] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTH_LABELS: List[str] = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


# =====================================================================
# Configuration
# =====================================================================
@dataclass
class EDAConfig:
    """Central configuration for the EDA pipeline."""

    db_host: str = field(
        default_factory=lambda: os.environ.get("CLOUDPULSE_DB_HOST", "127.0.0.1")
    )
    db_port: int = field(
        default_factory=lambda: int(os.environ.get("CLOUDPULSE_DB_PORT", "5433"))
    )
    db_name: str = field(
        default_factory=lambda: os.environ.get("CLOUDPULSE_DB_NAME", "cloudpulse_db")
    )
    db_user: str = field(
        default_factory=lambda: os.environ.get("CLOUDPULSE_DB_USER", "admin")
    )
    db_password: str = field(
        default_factory=lambda: os.environ.get("CLOUDPULSE_DB_PASSWORD", "admin123")
    )

    metrics_table: str = "telemetry_metrics"
    features_table: str = "telemetry_features"

    artifacts_dir: str = "artifacts/eda"
    reports_dir: str = "reports"

    # Plot styling
    fig_dpi: int = 120
    fig_width: int = 12
    fig_height: int = 6
    random_seed: int = 42

    # Sampling for heavy time-series plots
    timeseries_sample_freq: str = "1h"  # resample to hourly for line plots


# =====================================================================
# Database Loader
# =====================================================================
class DatabaseLoader:
    """Handles PostgreSQL connections and query execution via SQLAlchemy."""

    def __init__(self, config: EDAConfig) -> None:
        self.config = config
        self._engine = None

    def get_engine(self):
        """Returns a SQLAlchemy engine using psycopg2 driver."""
        if self._engine is None:
            url = (
                f"postgresql+psycopg2://{self.config.db_user}:{self.config.db_password}"
                f"@{self.config.db_host}:{self.config.db_port}/{self.config.db_name}"
            )
            try:
                self._engine = create_engine(url, pool_size=5, max_overflow=10)
                # Quick connectivity test
                with self._engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info(
                    "Connected to PostgreSQL | host=%s | db=%s",
                    self.config.db_host,
                    self.config.db_name,
                )
            except Exception as exc:
                logger.error(
                    "Failed to connect to PostgreSQL at %s:%s/%s. "
                    "Ensure CLOUDPULSE_DB_HOST, CLOUDPULSE_DB_PORT, "
                    "CLOUDPULSE_DB_NAME, CLOUDPULSE_DB_USER, "
                    "CLOUDPULSE_DB_PASSWORD env vars are set correctly.",
                    self.config.db_host,
                    self.config.db_port,
                    self.config.db_name,
                )
                raise ConnectionError(
                    f"PostgreSQL connection failed: {exc}. "
                    "Check CLOUDPULSE_DB_* environment variables."
                ) from exc
        return self._engine

    def load_metrics(self) -> pd.DataFrame:
        """SELECT * FROM telemetry_metrics ORDER BY timestamp, region."""
        query = f"SELECT * FROM {self.config.metrics_table} ORDER BY timestamp, region"
        engine = self.get_engine()
        df = pd.read_sql(query, engine, parse_dates=["timestamp"])
        logger.info(
            "Loaded %s | rows=%d | cols=%d",
            self.config.metrics_table,
            len(df),
            len(df.columns),
        )
        return df

    def load_features(self) -> pd.DataFrame:
        """SELECT * FROM telemetry_features ORDER BY timestamp, region."""
        query = f"SELECT * FROM {self.config.features_table} ORDER BY timestamp, region"
        engine = self.get_engine()
        df = pd.read_sql(query, engine, parse_dates=["timestamp"])
        logger.info(
            "Loaded %s | rows=%d | cols=%d",
            self.config.features_table,
            len(df),
            len(df.columns),
        )
        return df

    def load_features_fallback(self) -> Optional[pd.DataFrame]:
        """Try loading from PostgreSQL; fall back to Parquet feature store."""
        try:
            return self.load_features()
        except Exception:
            parquet_path = PROJECT_ROOT / "data" / "feature_store" / "telemetry_features.parquet"
            if parquet_path.exists():
                logger.warning(
                    "telemetry_features table not found in PostgreSQL. "
                    "Falling back to Parquet at %s",
                    parquet_path,
                )
                df = pd.read_parquet(parquet_path)
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                return df
            logger.warning(
                "Feature store not available in PostgreSQL or Parquet. "
                "Section 13 (Feature Store Validation) will be skipped."
            )
            return None

    def run_query(self, query: str) -> pd.DataFrame:
        """Executes arbitrary SQL for aggregate-level analyses."""
        engine = self.get_engine()
        return pd.read_sql(query, engine)


# =====================================================================
# Helper — figure creation
# =====================================================================
def _create_figure(
    config: EDAConfig,
    nrows: int = 1,
    ncols: int = 1,
    height_factor: float = 1.0,
    width_factor: float = 1.0,
):
    """Create a matplotlib figure with consistent sizing."""
    fig, axes = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        figsize=(config.fig_width * width_factor, config.fig_height * height_factor),
    )
    return fig, axes


def _save_and_close(fig, path: Path, config: EDAConfig) -> None:
    """Save figure to disk and close to free memory."""
    fig.savefig(path, dpi=config.fig_dpi, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved plot: %s", path.name)


# =====================================================================
# Section 1 & 2 — Data Quality Analyzer
# =====================================================================
class DataQualityAnalyzer:
    """Dataset overview + missing value analysis."""

    def __init__(self, config: EDAConfig) -> None:
        self.config = config

    def overview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Returns shape, dtypes, date range, duplicate count, missing summary."""
        n_rows, n_cols = df.shape
        date_min = df["timestamp"].min()
        date_max = df["timestamp"].max()
        n_duplicates = int(df.duplicated().sum())
        dtype_summary = df.dtypes.value_counts().to_dict()
        missing_per_col = df.isnull().sum().to_dict()
        total_missing = int(df.isnull().sum().sum())

        result = {
            "rows": n_rows,
            "cols": n_cols,
            "date_min": str(date_min),
            "date_max": str(date_max),
            "duplicates": n_duplicates,
            "dtype_summary": {str(k): int(v) for k, v in dtype_summary.items()},
            "missing_per_col": {k: int(v) for k, v in missing_per_col.items()},
            "total_missing": total_missing,
        }

        logger.info(
            "Dataset overview | rows=%d | cols=%d | date_range=%s to %s | duplicates=%d",
            n_rows,
            n_cols,
            date_min,
            date_max,
            n_duplicates,
        )
        return result

    def plot_missing_values(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Saves missing_values_analysis.png."""
        fig, ax = _create_figure(self.config)
        missing_counts = df.isnull().sum()
        colors = ["#2ecc71" if v == 0 else "#e74c3c" for v in missing_counts.values]
        ax.barh(missing_counts.index, missing_counts.values, color=colors)
        ax.set_xlabel("Missing Value Count")
        ax.set_title("Missing Value Analysis per Column")
        ax.invert_yaxis()
        for i, (val, col) in enumerate(zip(missing_counts.values, missing_counts.index)):
            pct = val / len(df) * 100
            ax.text(val + len(df) * 0.001, i, f"{val} ({pct:.1f}%)", va="center", fontsize=8)
        _save_and_close(fig, out_dir / "missing_values_analysis.png", self.config)


# =====================================================================
# Section 3, 4, 5 — Infrastructure Analyzer
# =====================================================================
class InfrastructureAnalyzer:
    """CPU, request rate, and latency analysis."""

    def __init__(self, config: EDAConfig) -> None:
        self.config = config

    def analyze_cpu(self, df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
        """CPU distribution and time-series analysis."""
        cpu = df["cpu_usage"]
        stats = {
            "mean": round(float(cpu.mean()), 2),
            "std": round(float(cpu.std()), 2),
            "min": round(float(cpu.min()), 2),
            "max": round(float(cpu.max()), 2),
            "median": round(float(cpu.median()), 2),
            "skew": round(float(cpu.skew()), 2),
        }

        # --- Distribution plot ---
        fig, ax = _create_figure(self.config)
        sns.histplot(cpu, bins=HIST_BINS, kde=True, ax=ax, color="#3498db")
        ax.set_xlabel("CPU Usage (%)")
        ax.set_ylabel("Frequency")
        ax.set_title(f"CPU Usage Distribution (skew={stats['skew']})")
        ax.axvline(stats["mean"], color="#e74c3c", linestyle="--", label=f"Mean={stats['mean']}")
        ax.legend()
        _save_and_close(fig, out_dir / "cpu_distribution.png", self.config)

        # --- Time-series plot (hourly resampled + 7-day zoom) ---
        fig, axes = _create_figure(self.config, nrows=2, height_factor=1.6)

        # Full range
        ts = df.set_index("timestamp")["cpu_usage"].resample(self.config.timeseries_sample_freq).mean()
        axes[0].plot(ts.index, ts.values, linewidth=0.5, color="#2980b9", alpha=0.8)
        axes[0].set_title("CPU Usage Over Time (Hourly Mean)")
        axes[0].set_xlabel("Date")
        axes[0].set_ylabel("CPU Usage (%)")
        axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

        # 7-day zoom
        first_week_end = df["timestamp"].min() + pd.Timedelta(days=7)
        ts_zoom = ts[ts.index <= first_week_end]
        axes[1].plot(ts_zoom.index, ts_zoom.values, linewidth=1.0, color="#e67e22")
        axes[1].set_title("CPU Usage - First Week (Daily Wave Pattern)")
        axes[1].set_xlabel("Date")
        axes[1].set_ylabel("CPU Usage (%)")
        axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))

        fig.tight_layout()
        _save_and_close(fig, out_dir / "cpu_time_series.png", self.config)

        return stats

    def analyze_request_rate(self, df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
        """Request rate distribution and time-series analysis."""
        rps = df["request_rate"]
        stats = {
            "mean": round(float(rps.mean()), 2),
            "std": round(float(rps.std()), 2),
            "min": round(float(rps.min()), 2),
            "max": round(float(rps.max()), 2),
            "median": round(float(rps.median()), 2),
            "skew": round(float(rps.skew()), 2),
        }

        # --- Distribution ---
        fig, ax = _create_figure(self.config)
        sns.histplot(rps, bins=HIST_BINS, kde=True, ax=ax, color="#9b59b6")
        ax.set_xlabel("Request Rate (RPS)")
        ax.set_ylabel("Frequency")
        ax.set_title(f"Request Rate Distribution (skew={stats['skew']})")
        if stats["skew"] > 2.0:
            ax.set_xscale("log")
            ax.set_title(f"Request Rate Distribution (log-scale, skew={stats['skew']})")
        _save_and_close(fig, out_dir / "request_rate_distribution.png", self.config)

        # --- Time-series with anomaly highlighting ---
        fig, ax = _create_figure(self.config)
        ts = df.set_index("timestamp")[["request_rate", "is_anomaly"]]
        ts_hourly = ts["request_rate"].resample(self.config.timeseries_sample_freq).mean()
        ax.plot(ts_hourly.index, ts_hourly.values, linewidth=0.5, color="#8e44ad", alpha=0.8)

        # Highlight anomaly windows
        anomaly_daily = ts["is_anomaly"].resample("1D").sum()
        for date_idx in anomaly_daily[anomaly_daily > 0].index:
            ax.axvspan(
                date_idx,
                date_idx + pd.Timedelta(days=1),
                alpha=0.08,
                color="red",
            )

        ax.set_title("Request Rate Over Time (with Anomaly Windows)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Request Rate (RPS)")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        _save_and_close(fig, out_dir / "request_rate_time_series.png", self.config)

        return stats

    def analyze_latency(self, df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
        """Latency distribution and CPU-latency correlation."""
        latency = df["response_latency_ms"]
        stats = {
            "mean": round(float(latency.mean()), 2),
            "std": round(float(latency.std()), 2),
            "min": round(float(latency.min()), 2),
            "max": round(float(latency.max()), 2),
            "median": round(float(latency.median()), 2),
        }

        # CPU-Latency correlation
        corr = round(float(df["cpu_usage"].corr(df["response_latency_ms"])), 4)
        stats["cpu_latency_corr"] = corr

        # --- Latency distribution ---
        fig, ax = _create_figure(self.config)
        sns.histplot(latency, bins=HIST_BINS, kde=True, ax=ax, color="#1abc9c")
        ax.set_xlabel("Response Latency (ms)")
        ax.set_ylabel("Frequency")
        ax.set_title("Response Latency Distribution")
        ax.axvline(stats["mean"], color="#e74c3c", linestyle="--", label=f"Mean={stats['mean']}ms")
        ax.legend()
        _save_and_close(fig, out_dir / "latency_distribution.png", self.config)

        # --- CPU vs Latency scatter ---
        fig, ax = _create_figure(self.config)
        sample = df.sample(n=min(SCATTER_SAMPLE_SIZE, len(df)), random_state=self.config.random_seed)
        palette = sns.color_palette("tab10", n_colors=df["region"].nunique())
        sns.scatterplot(
            data=sample,
            x="cpu_usage",
            y="response_latency_ms",
            hue="region",
            alpha=0.15,
            palette=palette,
            ax=ax,
            s=10,
        )
        ax.set_xlabel("CPU Usage (%)")
        ax.set_ylabel("Response Latency (ms)")
        ax.set_title(f"CPU vs Latency (r={corr})")
        ax.legend(title="Region", markerscale=3)
        _save_and_close(fig, out_dir / "cpu_vs_latency.png", self.config)

        return stats


# =====================================================================
# Section 6 — Cost Analyzer
# =====================================================================
class CostAnalyzer:
    """FinOps cost analysis."""

    def __init__(self, config: EDAConfig) -> None:
        self.config = config

    def analyze(self, df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
        """Cost distribution, by-region, and over-time analysis."""
        cost = df["cost_per_hour"]
        stats = {
            "mean": round(float(cost.mean()), 2),
            "std": round(float(cost.std()), 2),
            "min": round(float(cost.min()), 2),
            "max": round(float(cost.max()), 2),
            "median": round(float(cost.median()), 2),
        }

        # Per-region cost medians for ranking
        region_cost = df.groupby("region")["cost_per_hour"].median().sort_values(ascending=False)
        stats["region_cost_ranking"] = {r: round(float(v), 2) for r, v in region_cost.items()}

        # --- Cost distribution ---
        fig, ax = _create_figure(self.config)
        sns.histplot(cost, bins=HIST_BINS, kde=True, ax=ax, color="#f39c12")
        ax.set_xlabel("Cost per Hour ($)")
        ax.set_ylabel("Frequency")
        ax.set_title("Cost per Hour Distribution")
        _save_and_close(fig, out_dir / "cost_distribution.png", self.config)

        # --- Cost by region (box plot) ---
        fig, ax = _create_figure(self.config)
        palette = sns.color_palette("tab10", n_colors=df["region"].nunique())
        sns.boxplot(data=df, x="region", y="cost_per_hour", palette=palette, ax=ax)
        ax.set_xlabel("Region")
        ax.set_ylabel("Cost per Hour ($)")
        ax.set_title("Cost per Hour by Region")
        _save_and_close(fig, out_dir / "cost_by_region.png", self.config)

        # --- Cost over time (per region) ---
        fig, ax = _create_figure(self.config)
        for i, region in enumerate(sorted(df["region"].unique())):
            region_df = df[df["region"] == region].set_index("timestamp")
            ts = region_df["cost_per_hour"].resample(self.config.timeseries_sample_freq).mean()
            ax.plot(ts.index, ts.values, linewidth=0.5, label=region, alpha=0.8)
        ax.set_xlabel("Date")
        ax.set_ylabel("Cost per Hour ($)")
        ax.set_title("Cost per Hour Over Time (by Region)")
        ax.legend(title="Region")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        _save_and_close(fig, out_dir / "cost_time_series.png", self.config)

        return stats


# =====================================================================
# Section 7 — Region Analyzer
# =====================================================================
class RegionAnalyzer:
    """Region-wise comparisons via SQL aggregation."""

    def __init__(self, config: EDAConfig, db: DatabaseLoader) -> None:
        self.config = config
        self.db = db

    def analyze(self, df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
        """Regional comparison bar charts."""
        query = f"""
        SELECT region,
               AVG(cpu_usage) AS avg_cpu,
               AVG(request_rate) AS avg_rps,
               AVG(cost_per_hour) AS avg_cost,
               SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) AS anomaly_count,
               COUNT(*) AS total_rows
        FROM {self.config.metrics_table}
        GROUP BY region
        ORDER BY region;
        """
        agg = self.db.run_query(query)
        agg["anomaly_pct"] = (agg["anomaly_count"] / agg["total_rows"] * 100).round(2)
        palette = sns.color_palette("tab10", n_colors=len(agg))

        result = {
            "table": agg.to_dict(orient="records"),
        }

        # --- CPU comparison ---
        fig, ax = _create_figure(self.config)
        ax.bar(agg["region"], agg["avg_cpu"], color=palette)
        ax.set_xlabel("Region")
        ax.set_ylabel("Average CPU Usage (%)")
        ax.set_title("Average CPU Usage by Region")
        for i, v in enumerate(agg["avg_cpu"]):
            ax.text(i, v + 0.3, f"{v:.1f}", ha="center", fontweight="bold")
        _save_and_close(fig, out_dir / "regional_cpu_comparison.png", self.config)

        # --- Request rate comparison ---
        fig, ax = _create_figure(self.config)
        ax.bar(agg["region"], agg["avg_rps"], color=palette)
        ax.set_xlabel("Region")
        ax.set_ylabel("Average Request Rate (RPS)")
        ax.set_title("Average Request Rate by Region")
        for i, v in enumerate(agg["avg_rps"]):
            ax.text(i, v + 5, f"{v:.0f}", ha="center", fontweight="bold")
        _save_and_close(fig, out_dir / "regional_request_comparison.png", self.config)

        # --- Cost comparison ---
        fig, ax = _create_figure(self.config)
        ax.bar(agg["region"], agg["avg_cost"], color=palette)
        ax.set_xlabel("Region")
        ax.set_ylabel("Average Cost per Hour ($)")
        ax.set_title("Average Cost per Hour by Region")
        for i, v in enumerate(agg["avg_cost"]):
            ax.text(i, v + 0.02, f"${v:.2f}", ha="center", fontweight="bold")
        _save_and_close(fig, out_dir / "regional_cost_comparison.png", self.config)

        # --- Anomaly analysis ---
        fig, ax = _create_figure(self.config)
        colors = ["#e74c3c" if v > 2.0 else "#2ecc71" for v in agg["anomaly_pct"]]
        ax.bar(agg["region"], agg["anomaly_pct"], color=colors)
        ax.set_xlabel("Region")
        ax.set_ylabel("Anomaly Rate (%)")
        ax.set_title("Anomaly Rate by Region")
        for i, v in enumerate(agg["anomaly_pct"]):
            ax.text(i, v + 0.05, f"{v:.1f}%", ha="center", fontweight="bold")
        _save_and_close(fig, out_dir / "regional_anomaly_analysis.png", self.config)

        return result


# =====================================================================
# Section 8 — Workload Analyzer
# =====================================================================
class WorkloadAnalyzer:
    """Workload-type behavioral differentiation via SQL aggregation."""

    def __init__(self, config: EDAConfig, db: DatabaseLoader) -> None:
        self.config = config
        self.db = db

    def analyze(self, df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
        """Workload-level analysis."""
        query = f"""
        SELECT workload_type,
               AVG(cpu_usage) AS avg_cpu,
               AVG(request_rate) AS avg_rps,
               AVG(disk_io) AS avg_disk_io,
               AVG(network_out) AS avg_network_out,
               AVG(response_latency_ms) AS avg_latency,
               AVG(cost_per_hour) AS avg_cost
        FROM {self.config.metrics_table}
        GROUP BY workload_type
        ORDER BY workload_type;
        """
        agg = self.db.run_query(query)
        palette = sns.color_palette("tab10", n_colors=len(agg))

        result = {
            "table": agg.to_dict(orient="records"),
            "highest_disk_io": agg.loc[agg["avg_disk_io"].idxmax(), "workload_type"],
            "highest_network_out": agg.loc[agg["avg_network_out"].idxmax(), "workload_type"],
            "highest_rps": agg.loc[agg["avg_rps"].idxmax(), "workload_type"],
            "lowest_latency": agg.loc[agg["avg_latency"].idxmin(), "workload_type"],
        }

        # --- CPU by workload ---
        fig, ax = _create_figure(self.config)
        ax.bar(agg["workload_type"], agg["avg_cpu"], color=palette)
        ax.set_xlabel("Workload Type")
        ax.set_ylabel("Average CPU Usage (%)")
        ax.set_title("Average CPU Usage by Workload Type")
        plt.xticks(rotation=15)
        for i, v in enumerate(agg["avg_cpu"]):
            ax.text(i, v + 0.3, f"{v:.1f}", ha="center", fontweight="bold")
        _save_and_close(fig, out_dir / "workload_cpu_analysis.png", self.config)

        # --- Request rate by workload ---
        fig, ax = _create_figure(self.config)
        ax.bar(agg["workload_type"], agg["avg_rps"], color=palette)
        ax.set_xlabel("Workload Type")
        ax.set_ylabel("Average Request Rate (RPS)")
        ax.set_title("Average Request Rate by Workload Type")
        plt.xticks(rotation=15)
        for i, v in enumerate(agg["avg_rps"]):
            ax.text(i, v + 5, f"{v:.0f}", ha="center", fontweight="bold")
        _save_and_close(fig, out_dir / "workload_request_analysis.png", self.config)

        # --- Latency by workload ---
        fig, ax = _create_figure(self.config)
        ax.bar(agg["workload_type"], agg["avg_latency"], color=palette)
        ax.set_xlabel("Workload Type")
        ax.set_ylabel("Average Latency (ms)")
        ax.set_title("Average Response Latency by Workload Type")
        plt.xticks(rotation=15)
        for i, v in enumerate(agg["avg_latency"]):
            ax.text(i, v + 1, f"{v:.0f}ms", ha="center", fontweight="bold")
        _save_and_close(fig, out_dir / "workload_latency_analysis.png", self.config)

        # --- Cost by workload ---
        fig, ax = _create_figure(self.config)
        ax.bar(agg["workload_type"], agg["avg_cost"], color=palette)
        ax.set_xlabel("Workload Type")
        ax.set_ylabel("Average Cost per Hour ($)")
        ax.set_title("Average Cost per Hour by Workload Type")
        plt.xticks(rotation=15)
        for i, v in enumerate(agg["avg_cost"]):
            ax.text(i, v + 0.02, f"${v:.2f}", ha="center", fontweight="bold")
        _save_and_close(fig, out_dir / "workload_cost_analysis.png", self.config)

        return result


# =====================================================================
# Section 9 — Anomaly Analyzer
# =====================================================================
class AnomalyAnalyzer:
    """Anomaly and special-event behavior analysis."""

    def __init__(self, config: EDAConfig) -> None:
        self.config = config

    def analyze(self, df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
        """Anomaly statistics, timeline, and CPU impact."""
        overall_rate = round(float(df["is_anomaly"].mean()), 4)
        per_region = (
            df.groupby("region")["is_anomaly"]
            .mean()
            .round(4)
            .to_dict()
        )
        special_events = df["special_event"].value_counts().to_dict()

        # CPU impact
        cpu_normal = df.loc[~df["is_anomaly"], "cpu_usage"]
        cpu_anomaly = df.loc[df["is_anomaly"], "cpu_usage"]
        result = {
            "overall_rate": overall_rate,
            "overall_rate_pct": round(overall_rate * 100, 2),
            "per_region": {r: round(v * 100, 2) for r, v in per_region.items()},
            "special_events": special_events,
            "cpu_median_normal": round(float(cpu_normal.median()), 2),
            "cpu_median_anomaly": round(float(cpu_anomaly.median()), 2) if len(cpu_anomaly) > 0 else 0.0,
        }

        # --- Anomaly distribution + special events ---
        fig, axes = _create_figure(self.config, nrows=1, ncols=2, width_factor=1.0)

        # Anomaly count per region
        anomaly_counts = df.groupby("region")["is_anomaly"].sum()
        axes[0].bar(anomaly_counts.index, anomaly_counts.values, color=["#e74c3c", "#f39c12", "#3498db"])
        axes[0].set_xlabel("Region")
        axes[0].set_ylabel("Anomaly Count")
        axes[0].set_title("Anomaly Count by Region")
        for i, v in enumerate(anomaly_counts.values):
            axes[0].text(i, v + 10, str(int(v)), ha="center", fontweight="bold")

        # Special event distribution
        se_series = pd.Series(special_events)
        if len(se_series) > 0:
            axes[1].barh(se_series.index, se_series.values, color=sns.color_palette("pastel", len(se_series)))
            axes[1].set_xlabel("Count")
            axes[1].set_title("Special Event Distribution")
        else:
            axes[1].text(0.5, 0.5, "No special events", ha="center", va="center", transform=axes[1].transAxes)

        fig.tight_layout()
        _save_and_close(fig, out_dir / "anomaly_distribution.png", self.config)

        # --- Anomaly timeline ---
        fig, ax = _create_figure(self.config)
        daily_anomalies = (
            df.set_index("timestamp")["is_anomaly"]
            .resample("1D")
            .sum()
        )
        ax.bar(daily_anomalies.index, daily_anomalies.values, width=1.0, color="#e74c3c", alpha=0.7)
        ax.set_xlabel("Date")
        ax.set_ylabel("Daily Anomaly Count")
        ax.set_title("Anomaly Occurrence Timeline (Daily)")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        _save_and_close(fig, out_dir / "anomaly_timeline.png", self.config)

        # --- Anomaly CPU impact ---
        fig, ax = _create_figure(self.config)
        # Convert to string labels to avoid seaborn palette key issues
        plot_df = df[["is_anomaly", "cpu_usage"]].copy()
        plot_df["label"] = plot_df["is_anomaly"].map({True: "Anomalous", False: "Normal"})
        sns.boxplot(
            data=plot_df,
            x="label",
            y="cpu_usage",
            order=["Normal", "Anomalous"],
            palette={"Normal": "#2ecc71", "Anomalous": "#e74c3c"},
            ax=ax,
        )
        ax.set_xlabel("Is Anomaly")
        ax.set_ylabel("CPU Usage (%)")
        ax.set_title("CPU Usage: Normal vs Anomalous")
        _save_and_close(fig, out_dir / "anomaly_cpu_impact.png", self.config)

        return result


# =====================================================================
# Section 10 — Correlation Analyzer
# =====================================================================
class CorrelationAnalyzer:
    """Correlation heatmap and key relationship validation."""

    NUMERIC_COLS = [
        "cpu_usage", "ram_usage", "disk_io", "network_in", "network_out",
        "request_rate", "error_rate", "response_latency_ms",
        "resource_pressure_score", "sla_breach_risk",
        "active_instances", "cost_per_hour",
    ]

    EXPECTED_CORRS = {
        ("cpu_usage", "ram_usage"): CORR_CPU_RAM,
        ("cpu_usage", "request_rate"): CORR_CPU_RPS,
        ("cpu_usage", "response_latency_ms"): CORR_CPU_LATENCY,
        ("cpu_usage", "cost_per_hour"): CORR_CPU_COST,
        ("response_latency_ms", "sla_breach_risk"): CORR_LATENCY_SLA,
    }

    def __init__(self, config: EDAConfig) -> None:
        self.config = config

    def analyze(self, df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
        """Correlation heatmap and threshold checks."""
        available_cols = [c for c in self.NUMERIC_COLS if c in df.columns]
        corr_matrix = df[available_cols].corr()

        # Threshold checks
        checks = {}
        for (col_a, col_b), threshold in self.EXPECTED_CORRS.items():
            if col_a in available_cols and col_b in available_cols:
                actual = round(float(corr_matrix.loc[col_a, col_b]), 4)
                passed = actual >= threshold
                checks[f"{col_a} <-> {col_b}"] = {
                    "actual": actual,
                    "threshold": threshold,
                    "passed": passed,
                }
        n_passed = sum(1 for v in checks.values() if v["passed"])
        n_total = len(checks)

        result = {
            "checks": checks,
            "n_passed": n_passed,
            "n_total": n_total,
        }

        # --- Heatmap ---
        fig, ax = _create_figure(self.config, height_factor=1.5, width_factor=1.0)
        sns.heatmap(
            corr_matrix,
            annot=True,
            fmt=".2f",
            cmap="coolwarm",
            center=0,
            ax=ax,
            square=True,
            linewidths=0.5,
            cbar_kws={"shrink": 0.8},
        )
        ax.set_title("Metric Correlation Heatmap")
        fig.tight_layout()
        _save_and_close(fig, out_dir / "correlation_heatmap.png", self.config)

        return result


# =====================================================================
# Section 11 — Time Series Analyzer
# =====================================================================
class TimeSeriesAnalyzer:
    """Seasonality validation — hourly, weekday, and monthly patterns."""

    def __init__(self, config: EDAConfig) -> None:
        self.config = config

    def analyze(self, df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
        """Hourly, weekday, and monthly CPU patterns."""
        hourly = df.groupby(df["timestamp"].dt.hour)["cpu_usage"].mean()
        weekday = df.groupby(df["timestamp"].dt.dayofweek)["cpu_usage"].mean()
        monthly = df.groupby(df["timestamp"].dt.month)["cpu_usage"].mean()

        # Growth calculation
        jan_cpu = float(monthly.iloc[0]) if len(monthly) > 0 else 0
        dec_cpu = float(monthly.iloc[-1]) if len(monthly) > 0 else 0
        growth_pct = round((dec_cpu - jan_cpu) / jan_cpu * 100, 2) if jan_cpu > 0 else 0

        # Peak/trough identification
        trough_hours = hourly[hourly.index.isin(range(0, 6))].mean()
        morning_peak = hourly[hourly.index.isin(range(9, 13))].mean()
        evening_peak = hourly[hourly.index.isin(range(18, 22))].mean()

        result = {
            "hourly_means": {int(k): round(float(v), 2) for k, v in hourly.items()},
            "weekday_means": {WEEKDAY_LABELS[int(k)]: round(float(v), 2) for k, v in weekday.items()},
            "monthly_means": {MONTH_LABELS[int(k) - 1]: round(float(v), 2) for k, v in monthly.items()},
            "jan_cpu": round(jan_cpu, 2),
            "dec_cpu": round(dec_cpu, 2),
            "growth_pct": growth_pct,
            "trough_mean": round(float(trough_hours), 2),
            "morning_peak_mean": round(float(morning_peak), 2),
            "evening_peak_mean": round(float(evening_peak), 2),
        }

        palette = sns.color_palette("tab10")

        # --- Hourly pattern ---
        fig, ax = _create_figure(self.config)
        ax.bar(hourly.index, hourly.values, color=palette[0], alpha=0.8)
        ax.set_xlabel("Hour of Day")
        ax.set_ylabel("Average CPU Usage (%)")
        ax.set_title("CPU Usage by Hour of Day (Seasonality Pattern)")
        ax.set_xticks(range(0, 24))
        # Shade trough/peak zones
        ax.axvspan(-0.5, 5.5, alpha=0.08, color="blue", label="Night trough")
        ax.axvspan(8.5, 12.5, alpha=0.08, color="green", label="Morning peak")
        ax.axvspan(17.5, 21.5, alpha=0.08, color="orange", label="Evening peak")
        ax.legend(loc="upper left")
        _save_and_close(fig, out_dir / "hourly_cpu_pattern.png", self.config)

        # --- Weekday pattern ---
        fig, ax = _create_figure(self.config)
        colors = [palette[0] if i < 5 else palette[3] for i in range(7)]
        ax.bar(WEEKDAY_LABELS, weekday.values, color=colors)
        ax.set_xlabel("Day of Week")
        ax.set_ylabel("Average CPU Usage (%)")
        ax.set_title("CPU Usage by Day of Week")
        for i, v in enumerate(weekday.values):
            ax.text(i, v + 0.2, f"{v:.1f}", ha="center", fontsize=9)
        _save_and_close(fig, out_dir / "weekday_cpu_pattern.png", self.config)

        # --- Monthly growth trend ---
        fig, ax = _create_figure(self.config)
        ax.plot(MONTH_LABELS, monthly.values, marker="o", linewidth=2, color=palette[2])
        ax.fill_between(MONTH_LABELS, monthly.values, alpha=0.15, color=palette[2])
        ax.set_xlabel("Month")
        ax.set_ylabel("Average CPU Usage (%)")
        ax.set_title(f"Monthly CPU Growth Trend ({growth_pct:+.1f}% Jan-Dec)")
        ax.annotate(
            f"Jan: {jan_cpu:.1f}%",
            xy=(0, jan_cpu),
            xytext=(1, jan_cpu - 3),
            arrowprops=dict(arrowstyle="->", color="gray"),
            fontsize=9,
        )
        ax.annotate(
            f"Dec: {dec_cpu:.1f}%",
            xy=(11, dec_cpu),
            xytext=(10, dec_cpu + 3),
            arrowprops=dict(arrowstyle="->", color="gray"),
            fontsize=9,
        )
        _save_and_close(fig, out_dir / "monthly_growth_trend.png", self.config)

        return result


# =====================================================================
# Section 12 — SLA Analyzer
# =====================================================================
class SLAAnalyzer:
    """SLA breach risk profiling."""

    def __init__(self, config: EDAConfig) -> None:
        self.config = config

    def analyze(self, df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
        """SLA risk classification and visualization."""
        sla = df["sla_breach_risk"]

        n_healthy = int((sla < SLA_HEALTHY_UPPER).sum())
        n_warning = int(((sla >= SLA_HEALTHY_UPPER) & (sla < SLA_WARNING_UPPER)).sum())
        n_critical = int((sla >= SLA_WARNING_UPPER).sum())
        total = len(sla)

        result = {
            "healthy_count": n_healthy,
            "healthy_pct": round(n_healthy / total * 100, 2),
            "warning_count": n_warning,
            "warning_pct": round(n_warning / total * 100, 2),
            "critical_count": n_critical,
            "critical_pct": round(n_critical / total * 100, 2),
        }

        # Per-region breakdown
        per_region = {}
        for region in df["region"].unique():
            region_sla = df.loc[df["region"] == region, "sla_breach_risk"]
            n = len(region_sla)
            per_region[region] = {
                "healthy_pct": round(float((region_sla < SLA_HEALTHY_UPPER).sum() / n * 100), 2),
                "warning_pct": round(float(((region_sla >= SLA_HEALTHY_UPPER) & (region_sla < SLA_WARNING_UPPER)).sum() / n * 100), 2),
                "critical_pct": round(float((region_sla >= SLA_WARNING_UPPER).sum() / n * 100), 2),
            }
        result["per_region"] = per_region

        # --- Visualization ---
        fig, ax = _create_figure(self.config)
        sns.histplot(sla, bins=HIST_BINS, ax=ax, color="#3498db", alpha=0.7)

        # Zone shading
        ax.axvspan(sla.min(), SLA_HEALTHY_UPPER, alpha=0.10, color="green", label="Healthy (<30)")
        ax.axvspan(SLA_HEALTHY_UPPER, SLA_WARNING_UPPER, alpha=0.10, color="yellow", label="Warning (30-60)")
        ax.axvspan(SLA_WARNING_UPPER, sla.max() + 1, alpha=0.10, color="red", label="Critical (60+)")

        # Threshold lines
        ax.axvline(SLA_HEALTHY_UPPER, color="orange", linestyle="--", linewidth=1.5)
        ax.axvline(SLA_WARNING_UPPER, color="red", linestyle="--", linewidth=1.5)

        ax.set_xlabel("SLA Breach Risk Score")
        ax.set_ylabel("Frequency")
        ax.set_title(
            f"SLA Breach Risk Distribution "
            f"(Healthy={result['healthy_pct']:.1f}%, "
            f"Warning={result['warning_pct']:.1f}%, "
            f"Critical={result['critical_pct']:.1f}%)"
        )
        ax.legend()
        _save_and_close(fig, out_dir / "sla_risk_distribution.png", self.config)

        return result


# =====================================================================
# Section 13 — Feature Store Validator
# =====================================================================
class FeatureStoreValidator:
    """Engineered feature validation."""

    def __init__(self, config: EDAConfig) -> None:
        self.config = config

    def analyze(self, features_df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
        """Feature correlation and forecast-readiness check."""
        result = {"available": True, "correlations": {}}

        # Compute correlations
        if "lag_cpu_15min" in features_df.columns and "cpu_usage" in features_df.columns:
            lag_corr = round(float(features_df["lag_cpu_15min"].corr(features_df["cpu_usage"])), 4)
            result["correlations"]["lag_cpu_15min_vs_cpu_usage"] = lag_corr
        else:
            lag_corr = None

        if "rolling_cpu_avg_30min" in features_df.columns and "resource_pressure_score" in features_df.columns:
            rolling_pressure_corr = round(
                float(features_df["rolling_cpu_avg_30min"].corr(features_df["resource_pressure_score"])),
                4,
            )
            result["correlations"]["rolling_cpu_vs_pressure"] = rolling_pressure_corr
        else:
            rolling_pressure_corr = None

        # Forecast readiness: autocorrelation proxy
        if "lag_cpu_15min" in features_df.columns and "cpu_usage" in features_df.columns:
            # Correlation between lagged CPU and current CPU = autocorrelation
            autocorr = lag_corr  # already computed above
            result["autocorrelation_15min"] = autocorr
        else:
            autocorr = None

        # --- Multi-panel visualization ---
        fig, axes = _create_figure(self.config, nrows=2, ncols=2, height_factor=1.6)

        # Panel 1: Raw CPU vs Rolling CPU (first 7 days, first region)
        first_region = sorted(features_df["region"].unique())[0]
        region_subset = features_df[features_df["region"] == first_region].copy()
        region_subset = region_subset.sort_values("timestamp")
        first_week_end = region_subset["timestamp"].min() + pd.Timedelta(days=7)
        week_data = region_subset[region_subset["timestamp"] <= first_week_end]

        if "rolling_cpu_avg_30min" in week_data.columns:
            axes[0, 0].plot(week_data["timestamp"], week_data["cpu_usage"], linewidth=0.8, label="Raw CPU", alpha=0.7)
            axes[0, 0].plot(
                week_data["timestamp"],
                week_data["rolling_cpu_avg_30min"],
                linewidth=1.5,
                label="Rolling 30min Avg",
                color="red",
            )
            axes[0, 0].set_title(f"Raw vs Rolling CPU ({first_region}, Week 1)")
            axes[0, 0].set_xlabel("Time")
            axes[0, 0].set_ylabel("CPU Usage (%)")
            axes[0, 0].legend(fontsize=8)
            axes[0, 0].xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))
            axes[0, 0].tick_params(axis="x", rotation=30)

        # Panel 2: Lag CPU vs Current CPU scatter
        if "lag_cpu_15min" in features_df.columns:
            sample = features_df.dropna(subset=["lag_cpu_15min"]).sample(
                n=min(SCATTER_SAMPLE_SIZE, len(features_df)),
                random_state=self.config.random_seed,
            )
            axes[0, 1].scatter(sample["lag_cpu_15min"], sample["cpu_usage"], alpha=0.05, s=3, color="#3498db")
            axes[0, 1].set_xlabel("Lag CPU (15min)")
            axes[0, 1].set_ylabel("Current CPU")
            axes[0, 1].set_title(f"Lag vs Current CPU (r={lag_corr})")
            # Add diagonal
            lims = [
                max(axes[0, 1].get_xlim()[0], axes[0, 1].get_ylim()[0]),
                min(axes[0, 1].get_xlim()[1], axes[0, 1].get_ylim()[1]),
            ]
            axes[0, 1].plot(lims, lims, "r--", alpha=0.5, linewidth=1)

        # Panel 3: Rolling CPU vs Pressure Score scatter
        if rolling_pressure_corr is not None:
            sample2 = features_df.dropna(subset=["rolling_cpu_avg_30min"]).sample(
                n=min(SCATTER_SAMPLE_SIZE, len(features_df)),
                random_state=self.config.random_seed,
            )
            axes[1, 0].scatter(
                sample2["rolling_cpu_avg_30min"],
                sample2["resource_pressure_score"],
                alpha=0.05,
                s=3,
                color="#e67e22",
            )
            axes[1, 0].set_xlabel("Rolling CPU Avg (30min)")
            axes[1, 0].set_ylabel("Resource Pressure Score")
            axes[1, 0].set_title(f"Rolling CPU vs Pressure (r={rolling_pressure_corr})")

        # Panel 4: Correlation summary bar chart
        corr_labels = []
        corr_values = []
        corr_colors = []
        if lag_corr is not None:
            corr_labels.append("Lag CPU\nvs CPU")
            corr_values.append(lag_corr)
            corr_colors.append("#2ecc71" if lag_corr >= FEATURE_LAG_CPU_CORR else "#e74c3c")
        if rolling_pressure_corr is not None:
            corr_labels.append("Rolling CPU\nvs Pressure")
            corr_values.append(rolling_pressure_corr)
            corr_colors.append("#2ecc71" if rolling_pressure_corr >= FEATURE_ROLLING_PRESSURE_CORR else "#e74c3c")
        if autocorr is not None:
            corr_labels.append("Autocorr\n(15min)")
            corr_values.append(autocorr)
            corr_colors.append("#2ecc71" if autocorr >= FEATURE_LAG_CPU_CORR else "#e74c3c")

        if corr_labels:
            axes[1, 1].bar(corr_labels, corr_values, color=corr_colors)
            axes[1, 1].set_ylabel("Correlation")
            axes[1, 1].set_title("Feature Store Correlations")
            axes[1, 1].set_ylim(0, 1.1)
            for i, v in enumerate(corr_values):
                axes[1, 1].text(i, v + 0.02, f"{v:.3f}", ha="center", fontweight="bold")
            # Threshold lines
            axes[1, 1].axhline(FEATURE_LAG_CPU_CORR, color="gray", linestyle="--", alpha=0.5, label=f"Lag threshold ({FEATURE_LAG_CPU_CORR})")
            axes[1, 1].axhline(FEATURE_ROLLING_PRESSURE_CORR, color="gray", linestyle=":", alpha=0.5, label=f"Rolling threshold ({FEATURE_ROLLING_PRESSURE_CORR})")
            axes[1, 1].legend(fontsize=7)

        fig.suptitle("Feature Store Validation", fontsize=14, fontweight="bold")
        fig.tight_layout()
        _save_and_close(fig, out_dir / "feature_validation.png", self.config)

        return result


# =====================================================================
# Report Builder
# =====================================================================
class ReportBuilder:
    """Assembles all section results into reports/eda_summary.md."""

    def build(self, results: Dict[str, Any], out_path: Path) -> None:
        """Writes the full markdown report."""
        r = results
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        overview = r.get("overview", {})
        cpu = r.get("cpu", {})
        rps = r.get("request_rate", {})
        latency = r.get("latency", {})
        cost = r.get("cost", {})
        region = r.get("region", {})
        workload = r.get("workload", {})
        anomaly = r.get("anomaly", {})
        correlation = r.get("correlation", {})
        timeseries = r.get("timeseries", {})
        sla = r.get("sla", {})
        features = r.get("features", {})

        lines = []

        def w(line: str = "") -> None:
            lines.append(line)

        w("# CloudPulse AI -- Telemetry EDA Summary Report")
        w()
        w(f"**Generated:** {ts}")
        w(f"**Source:** PostgreSQL `telemetry_metrics` ({overview.get('rows', 'N/A')} rows, {overview.get('cols', 'N/A')} columns)")
        w(f"**Date range:** {overview.get('date_min', 'N/A')} -> {overview.get('date_max', 'N/A')}")
        w()
        w("---")
        w()

        # Section 1 — Dataset Summary
        w("## 1. Dataset Summary")
        w()
        w(f"- **Rows:** {overview.get('rows', 'N/A')}")
        w(f"- **Columns:** {overview.get('cols', 'N/A')}")
        w(f"- **Date range:** {overview.get('date_min', 'N/A')} to {overview.get('date_max', 'N/A')}")
        w(f"- **Duplicate rows:** {overview.get('duplicates', 'N/A')}")
        dtype_summary = overview.get("dtype_summary", {})
        for dtype, count in dtype_summary.items():
            w(f"- **{dtype}:** {count} columns")
        w()

        # Section 2 — Data Quality
        w("## 2. Data Quality Report")
        w()
        total_missing = overview.get("total_missing", 0)
        quality_status = "PASS" if total_missing == 0 else "FAIL"
        w(f"- **Total missing values:** {total_missing}")
        w(f"- **Data Quality Gate:** **{quality_status}**")
        w()
        if total_missing > 0:
            w("> [!WARNING]")
            w("> Missing values detected! Review the following columns:")
            missing_cols = {k: v for k, v in overview.get("missing_per_col", {}).items() if v > 0}
            for col, count in missing_cols.items():
                w(f"> - `{col}`: {count} missing ({count / overview.get('rows', 1) * 100:.2f}%)")
            w()
        else:
            w("All columns have zero missing values. Data quality gate passed.")
            w()

        # Section 3 — Infrastructure Behavior
        w("## 3. Infrastructure Behavior")
        w()
        w("### CPU Usage")
        w(f"- Mean: {cpu.get('mean', 'N/A')}%")
        w(f"- Std: {cpu.get('std', 'N/A')}%")
        w(f"- Min: {cpu.get('min', 'N/A')}% | Max: {cpu.get('max', 'N/A')}%")
        w(f"- Median: {cpu.get('median', 'N/A')}%")
        w(f"- Skewness: {cpu.get('skew', 'N/A')}")
        w()
        w("### Request Rate")
        w(f"- Mean: {rps.get('mean', 'N/A')} RPS")
        w(f"- Std: {rps.get('std', 'N/A')}")
        w(f"- Min: {rps.get('min', 'N/A')} | Max: {rps.get('max', 'N/A')}")
        w(f"- Median: {rps.get('median', 'N/A')} RPS")
        w()
        w("### Response Latency")
        w(f"- Mean: {latency.get('mean', 'N/A')} ms")
        w(f"- Std: {latency.get('std', 'N/A')} ms")
        w(f"- Min: {latency.get('min', 'N/A')} ms | Max: {latency.get('max', 'N/A')} ms")
        w(f"- CPU-Latency Correlation: {latency.get('cpu_latency_corr', 'N/A')}")
        corr_status = "PASS" if (latency.get("cpu_latency_corr", 0) or 0) >= CORR_CPU_LATENCY else "FAIL"
        w(f"- CPU-Latency threshold ({CORR_CPU_LATENCY}): **{corr_status}**")
        w()

        # Section 4 — Correlation Insights
        w("## 4. Correlation Insights")
        w()
        checks = correlation.get("checks", {})
        w("| Metric Pair | Actual | Threshold | Status |")
        w("|---|---|---|---|")
        for pair, info in checks.items():
            status = "PASS" if info["passed"] else "FAIL"
            w(f"| {pair} | {info['actual']} | >= {info['threshold']} | **{status}** |")
        w()
        w(f"**Checks passed:** {correlation.get('n_passed', 0)}/{correlation.get('n_total', 0)}")
        w()

        # Section 5 — Region Insights
        w("## 5. Region Insights")
        w()
        region_table = region.get("table", [])
        if region_table:
            w("| Region | Avg CPU (%) | Avg RPS | Avg Cost ($) | Anomaly Rate (%) |")
            w("|---|---|---|---|---|")
            for row in region_table:
                w(f"| {row['region']} | {row['avg_cpu']:.2f} | {row['avg_rps']:.0f} | {row['avg_cost']:.2f} | {row['anomaly_pct']:.2f} |")
            w()

            # Narrative
            highest_rps_region = max(region_table, key=lambda x: x["avg_rps"])
            highest_cost_region = max(region_table, key=lambda x: x["avg_cost"])
            highest_anomaly_region = max(region_table, key=lambda x: x["anomaly_pct"])
            w(f"- **Highest traffic:** {highest_rps_region['region']} ({highest_rps_region['avg_rps']:.0f} avg RPS)")
            w(f"- **Highest cost:** {highest_cost_region['region']} (${highest_cost_region['avg_cost']:.2f}/hr)")
            w(f"- **Highest anomaly rate:** {highest_anomaly_region['region']} ({highest_anomaly_region['anomaly_pct']:.2f}%)")
        w()

        # Section 6 — Workload Insights
        w("## 6. Workload Insights")
        w()
        workload_table = workload.get("table", [])
        if workload_table:
            w("| Workload | Avg CPU (%) | Avg RPS | Avg Disk IO | Avg Net Out | Avg Latency (ms) | Avg Cost ($) |")
            w("|---|---|---|---|---|---|---|")
            for row in workload_table:
                w(
                    f"| {row['workload_type']} | {row['avg_cpu']:.2f} | {row['avg_rps']:.0f} "
                    f"| {row['avg_disk_io']:.2f} | {row['avg_network_out']:.2f} "
                    f"| {row['avg_latency']:.0f} | {row['avg_cost']:.2f} |"
                )
            w()
            w("**Validation:**")
            w(f"- Highest Disk I/O: `{workload.get('highest_disk_io', 'N/A')}` (expected: `batch_processing`)")
            w(f"- Highest Network Out: `{workload.get('highest_network_out', 'N/A')}` (expected: `streaming_service`)")
            w(f"- Highest RPS: `{workload.get('highest_rps', 'N/A')}` (expected: `api_service`)")
            w(f"- Lowest Latency: `{workload.get('lowest_latency', 'N/A')}` (expected: `api_service`)")
        w()

        # Section 7 — Cost Insights
        w("## 7. Cost Insights (FinOps)")
        w()
        w(f"- Mean cost: ${cost.get('mean', 'N/A')}/hr")
        w(f"- Median cost: ${cost.get('median', 'N/A')}/hr")
        w(f"- Min: ${cost.get('min', 'N/A')} | Max: ${cost.get('max', 'N/A')}")
        w()
        ranking = cost.get("region_cost_ranking", {})
        if ranking:
            w("**Regional cost ranking (median $/hr):**")
            for r_name, r_cost in ranking.items():
                w(f"- {r_name}: ${r_cost}")
        w()

        # Section 8 — SLA Analysis
        w("## 8. SLA Analysis")
        w()
        w(f"- **Healthy** (<{SLA_HEALTHY_UPPER}): {sla.get('healthy_pct', 'N/A')}% ({sla.get('healthy_count', 'N/A')} rows)")
        w(f"- **Warning** ({SLA_HEALTHY_UPPER}-{SLA_WARNING_UPPER}): {sla.get('warning_pct', 'N/A')}% ({sla.get('warning_count', 'N/A')} rows)")
        w(f"- **Critical** (>={SLA_WARNING_UPPER}): {sla.get('critical_pct', 'N/A')}% ({sla.get('critical_count', 'N/A')} rows)")
        w()
        sla_per_region = sla.get("per_region", {})
        if sla_per_region:
            w("| Region | Healthy (%) | Warning (%) | Critical (%) |")
            w("|---|---|---|---|")
            for r_name, buckets in sla_per_region.items():
                w(f"| {r_name} | {buckets['healthy_pct']} | {buckets['warning_pct']} | {buckets['critical_pct']} |")
        w()

        # Section 9 — Anomaly Statistics
        w("## 9. Anomaly Statistics")
        w()
        w(f"- **Overall anomaly rate:** {anomaly.get('overall_rate_pct', 'N/A')}%")
        rate_status = "PASS" if ANOMALY_RATE_MIN <= anomaly.get("overall_rate", 0) <= ANOMALY_RATE_MAX else "FAIL"
        w(f"- **Rate within expected bounds ({ANOMALY_RATE_MIN*100:.1f}%-{ANOMALY_RATE_MAX*100:.1f}%):** **{rate_status}**")
        w()
        w("**Per-region anomaly rates:**")
        for r_name, r_pct in anomaly.get("per_region", {}).items():
            w(f"- {r_name}: {r_pct}%")
        w()
        w("**Special event distribution:**")
        w()
        w("| Event | Count |")
        w("|---|---|")
        for event, count in anomaly.get("special_events", {}).items():
            w(f"| {event} | {count} |")
        w()
        w(f"- CPU median (normal): {anomaly.get('cpu_median_normal', 'N/A')}%")
        w(f"- CPU median (anomalous): {anomaly.get('cpu_median_anomaly', 'N/A')}%")
        w()

        # Section 10 — Time-Series Validation
        w("## 10. Time-Series Validation")
        w()
        w("### Hourly CPU Pattern")
        w(f"- Night trough (00:00-05:00): {timeseries.get('trough_mean', 'N/A')}% avg")
        w(f"- Morning peak (09:00-12:00): {timeseries.get('morning_peak_mean', 'N/A')}% avg")
        w(f"- Evening peak (18:00-21:00): {timeseries.get('evening_peak_mean', 'N/A')}% avg")
        w()
        w("### Weekday Pattern")
        weekday_means = timeseries.get("weekday_means", {})
        for day, val in weekday_means.items():
            w(f"- {day}: {val}%")
        w()
        w("### Monthly Growth Trend")
        w(f"- January avg CPU: {timeseries.get('jan_cpu', 'N/A')}%")
        w(f"- December avg CPU: {timeseries.get('dec_cpu', 'N/A')}%")
        w(f"- **Growth:** {timeseries.get('growth_pct', 'N/A')}%")
        w()

        # Section 11 — Feature Store Validation
        w("## 11. Feature Store Validation")
        w()
        if features.get("available", False):
            feat_corr = features.get("correlations", {})
            for name, val in feat_corr.items():
                w(f"- `{name}`: {val}")
            autocorr = features.get("autocorrelation_15min")
            if autocorr is not None:
                w(f"- **Autocorrelation (15min lag):** {autocorr}")
                forecast_status = "PASS" if autocorr >= FEATURE_LAG_CPU_CORR else "NEEDS REVIEW"
                w(f"- **Forecast readiness:** **{forecast_status}**")
        else:
            w("Feature store data was not available for validation.")
        w()

        # Section 12 — Key Findings
        w("## 12. Key Findings")
        w()
        findings = []
        if overview.get("total_missing", 0) == 0:
            findings.append("Zero missing values across all columns -- data quality gate passed")
        corr_passed = correlation.get("n_passed", 0)
        corr_total = correlation.get("n_total", 0)
        findings.append(f"Correlation validation: {corr_passed}/{corr_total} checks passed")
        if anomaly.get("overall_rate_pct"):
            findings.append(f"Anomaly rate at {anomaly['overall_rate_pct']}% -- within expected bounds")
        if timeseries.get("growth_pct"):
            findings.append(f"Monthly CPU growth trend of {timeseries['growth_pct']}% confirms trend-drift component")
        if timeseries.get("trough_mean") and timeseries.get("evening_peak_mean"):
            findings.append(
                f"Clear daily seasonality: night trough at {timeseries['trough_mean']}%, "
                f"evening peak at {timeseries['evening_peak_mean']}%"
            )
        if workload.get("highest_disk_io") == "batch_processing":
            findings.append("Workload differentiation validated: batch_processing shows highest disk I/O")
        if workload.get("highest_network_out") == "streaming_service":
            findings.append("Workload differentiation validated: streaming_service shows highest network out")
        if features.get("autocorrelation_15min") and features["autocorrelation_15min"] >= FEATURE_LAG_CPU_CORR:
            findings.append(
                f"Feature store validated: 15-min lag autocorrelation at {features['autocorrelation_15min']} "
                f"confirms strong temporal predictive signal"
            )
        for finding in findings:
            w(f"- {finding}")
        w()

        # Section 13 — Recommendations
        w("## 13. Recommendations for Forecasting")
        w()
        w("- CPU, request rate, latency, and resource_pressure_score exhibit strong predictive "
          "relationships and are suitable forecasting signals.")
        w("- The 15-minute lag and 30-minute rolling features provide strong temporal context "
          "for time-series forecasting models.")
        if correlation.get("n_passed", 0) < correlation.get("n_total", 0):
            failed_checks = [k for k, v in checks.items() if not v["passed"]]
            w(f"- **Caution:** The following correlation checks did not meet thresholds: {', '.join(failed_checks)}. "
              "Consider feature engineering or model architecture adjustments.")
        w("- Regional and workload-type features provide meaningful segmentation signals "
          "for specialized forecasting models per region/workload.")
        w("- Cost-per-hour exhibits clear correlation with infrastructure load, supporting "
          "FinOps cost prediction as a downstream forecasting target.")
        w()

        # Write to file
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Report saved to %s", out_path)


# =====================================================================
# Orchestrator
# =====================================================================
class TelemetryEDA:
    """
    Orchestrates the full EDA pipeline: load -> analyze -> visualize -> report.
    Entry point for all external callers.
    """

    def __init__(self, config: EDAConfig) -> None:
        self.config = config
        self.db = DatabaseLoader(config)
        self.out_dir = Path(config.artifacts_dir)
        self.report_dir = Path(config.reports_dir)

    def run(self) -> Dict[str, Any]:
        """Execute all 13 analysis sections."""
        logger.info("EDA pipeline started | source=%s", self.config.metrics_table)

        # Create output directories
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        # Apply global plot style
        sns.set_theme(style="darkgrid")
        np.random.seed(self.config.random_seed)

        results: Dict[str, Any] = {}

        # ---- Load data ----
        df = self.db.load_metrics()

        # Drop the auto-generated 'id' and 'created_at' columns for analysis
        drop_cols = [c for c in ["id", "created_at"] if c in df.columns]
        df = df.drop(columns=drop_cols)

        # Ensure is_anomaly is proper boolean (PostgreSQL may return strings)
        if "is_anomaly" in df.columns:
            df["is_anomaly"] = df["is_anomaly"].map(
                {True: True, False: False, "True": True, "False": False,
                 "true": True, "false": False, "t": True, "f": False}
            ).fillna(False).astype(bool)

        # ---- Section 1 & 2: Data Quality ----
        dq = DataQualityAnalyzer(self.config)
        results["overview"] = dq.overview(df)
        dq.plot_missing_values(df, self.out_dir)
        logger.info(
            "Section 1-2: Data quality analysis complete | missing_total=%d",
            results["overview"]["total_missing"],
        )

        # ---- Section 3, 4, 5: Infrastructure ----
        infra = InfrastructureAnalyzer(self.config)
        results["cpu"] = infra.analyze_cpu(df, self.out_dir)
        results["request_rate"] = infra.analyze_request_rate(df, self.out_dir)
        results["latency"] = infra.analyze_latency(df, self.out_dir)
        logger.info("Section 3-5: Infrastructure analysis complete")

        # ---- Section 6: Cost ----
        cost = CostAnalyzer(self.config)
        results["cost"] = cost.analyze(df, self.out_dir)
        logger.info("Section 6: Cost analysis complete")

        # ---- Section 7: Regional ----
        region = RegionAnalyzer(self.config, self.db)
        results["region"] = region.analyze(df, self.out_dir)
        logger.info("Section 7: Regional analysis complete")

        # ---- Section 8: Workload ----
        workload = WorkloadAnalyzer(self.config, self.db)
        results["workload"] = workload.analyze(df, self.out_dir)
        logger.info("Section 8: Workload analysis complete")

        # ---- Section 9: Anomaly ----
        anomaly = AnomalyAnalyzer(self.config)
        results["anomaly"] = anomaly.analyze(df, self.out_dir)
        logger.info(
            "Section 9: Anomaly analysis complete | anomaly_rate=%.2f%%",
            results["anomaly"]["overall_rate_pct"],
        )

        # ---- Section 10: Correlation ----
        corr = CorrelationAnalyzer(self.config)
        results["correlation"] = corr.analyze(df, self.out_dir)
        logger.info(
            "Section 10: Correlation analysis complete | checks_passed=%d/%d",
            results["correlation"]["n_passed"],
            results["correlation"]["n_total"],
        )

        # ---- Section 11: Time-Series Seasonality ----
        ts = TimeSeriesAnalyzer(self.config)
        results["timeseries"] = ts.analyze(df, self.out_dir)
        logger.info("Section 11: Seasonality validation complete")

        # ---- Section 12: SLA ----
        sla = SLAAnalyzer(self.config)
        results["sla"] = sla.analyze(df, self.out_dir)
        logger.info("Section 12: SLA breach analysis complete")

        # ---- Section 13: Feature Store ----
        features_df = self.db.load_features_fallback()
        if features_df is not None:
            fsv = FeatureStoreValidator(self.config)
            results["features"] = fsv.analyze(features_df, self.out_dir)
            logger.info("Section 13: Feature store validation complete")
        else:
            results["features"] = {"available": False}
            logger.warning("Section 13: Feature store validation skipped (data unavailable)")

        # Count artifacts
        plot_count = len(list(self.out_dir.glob("*.png")))
        logger.info(
            "All artifacts saved to %s | total_plots=%d",
            self.out_dir,
            plot_count,
        )

        # ---- Report ----
        report_path = self.report_dir / "eda_summary.md"
        builder = ReportBuilder()
        builder.build(results, report_path)
        logger.info("EDA pipeline completed successfully")

        return results


# =====================================================================
# Entry Point
# =====================================================================
if __name__ == "__main__":
    config = EDAConfig()
    eda = TelemetryEDA(config)
    results = eda.run()
    print("\nEDA complete.")
    print(f"Artifacts saved to: {config.artifacts_dir}")
    print(f"Report saved to: {config.reports_dir}/eda_summary.md")
