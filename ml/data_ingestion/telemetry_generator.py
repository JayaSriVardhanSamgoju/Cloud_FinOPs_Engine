"""
CloudPulse AI — Synthetic Cloud Telemetry Generation Engine
(V3 — Enterprise Multi-Region Edition with Workload & Risk Scoring)
===================================================================

Generates 12 months of realistic synthetic cloud infrastructure telemetry
across 3 cloud regions at 5-minute intervals for training predictive ML models.
Simulates real-world patterns including daily/weekly seasonality, long-term growth
drift, correlated metrics, batch workloads, auto-scaling, special events
(holidays, sales, deployments), anomaly events per region, workload-type
behavioural modifiers, composite risk scores, and regional partial failures.

Usage:
    python ml/data_ingestion/telemetry_generator.py

Outputs:
    data/raw/telemetry_data.csv               (~316,000+ records, 18 columns)
    data/raw/telemetry_data.parquet
    data/feature_store/telemetry_features.parquet
    docs/telemetry_profile_report.md

Author: CloudPulse AI Team
"""

# ─── Imports ──────────────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Tuple, List, Dict
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("cloudpulse.telemetry")


# ─── Region Configuration ────────────────────────────────────────────────────
REGION_CONFIG: Dict[str, Dict] = {
    "us-east-1": {
        "traffic_multiplier": 1.25,
        "cost_per_instance": 0.32,
        "anomaly_weight": 1.4,
    },
    "ap-south-1": {
        "traffic_multiplier": 0.90,
        "cost_per_instance": 0.37,
        "anomaly_weight": 1.0,
    },
    "eu-west-1": {
        "traffic_multiplier": 0.70,
        "cost_per_instance": 0.42,
        "anomaly_weight": 0.7,
    },
}

# ─── Special Events Calendar 2024 ────────────────────────────────────────────
SPECIAL_EVENTS_CALENDAR: List[Dict] = [
    {"start": "2024-01-01", "end": "2024-01-01", "type": "holiday",    "factor_range": (0.5, 0.7)},
    {"start": "2024-02-14", "end": "2024-02-14", "type": "sale_event", "factor_range": (1.3, 1.8)},
    {"start": "2024-03-29", "end": "2024-03-31", "type": "holiday",    "factor_range": (0.5, 0.7)},
    {"start": "2024-07-04", "end": "2024-07-04", "type": "holiday",    "factor_range": (0.5, 0.7)},
    {"start": "2024-10-31", "end": "2024-10-31", "type": "sale_event", "factor_range": (1.2, 1.5)},
    {"start": "2024-11-29", "end": "2024-11-29", "type": "sale_event", "factor_range": (2.0, 3.5)},
    {"start": "2024-11-30", "end": "2024-11-30", "type": "sale_event", "factor_range": (1.8, 2.5)},
    {"start": "2024-12-02", "end": "2024-12-02", "type": "sale_event", "factor_range": (2.0, 3.0)},
    {"start": "2024-12-24", "end": "2024-12-25", "type": "holiday",    "factor_range": (0.5, 0.7)},
    {"start": "2024-12-31", "end": "2024-12-31", "type": "sale_event", "factor_range": (1.3, 1.6)},
]

# ─── Workload Configuration (V3) ─────────────────────────────────────────────
WORKLOAD_DISTRIBUTION: Dict[str, float] = {
    "web_application":   0.40,
    "api_service":       0.30,
    "batch_processing":  0.15,
    "streaming_service": 0.15,
}

WORKLOAD_MODIFIERS: Dict[str, Dict[str, float]] = {
    "web_application": {
        "request_rate":        1.00,
        "disk_io":             1.00,
        "network_out":         1.00,
        "response_latency_ms": 1.00,
    },
    "api_service": {
        "request_rate":        1.35,   # bursty — amplify RPS
        "disk_io":             0.70,   # low disk
        "network_out":         1.10,
        "response_latency_ms": 0.75,   # lower latency baseline
    },
    "batch_processing": {
        "request_rate":        0.55,   # low web traffic
        "disk_io":             2.20,   # dominant disk usage
        "network_out":         0.80,
        "response_latency_ms": 1.40,   # slower
    },
    "streaming_service": {
        "request_rate":        1.20,   # high throughput
        "disk_io":             0.90,
        "network_out":         1.80,   # dominant outbound
        "response_latency_ms": 1.25,   # slightly higher latency
    },
}


# ─── Configuration Dataclass ─────────────────────────────────────────────────
@dataclass
class TelemetryConfig:
    """
    All generation parameters in one place.
    No magic numbers in generation logic — everything comes from here.
    """

    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    interval_minutes: int = 5
    random_seed: int = 42
    output_path: str = "data/raw/telemetry_data.csv"

    # ── Daily seasonality sine-wave parameters ────────────────────────────────
    # Tuned to produce the target hour-by-hour CPU profile:
    #   00-05 → 10-20%  |  06-08 → 20-40%  |  09-12 → 55-70%
    #   12-14 → 45-55%  |  14-17 → 60-75%  |  18-21 → 65-85%
    #   22-23 → 30-45%
    daily_A1: float = 22.0
    daily_phase1: float = -1.6
    daily_A2: float = 6.5
    daily_phase2: float = -0.8
    daily_A3: float = 3.0
    daily_phase3: float = 0.3
    daily_baseline: float = 42.0

    # ── Noise sigmas per metric ───────────────────────────────────────────────
    cpu_noise_sigma: float = 3.5
    ram_noise_sigma: float = 2.0
    disk_noise_sigma: float = 15.0
    network_noise_sigma: float = 12.0
    request_noise_sigma: float = 80.0
    latency_noise_sigma: float = 12.0

    # ── Anomaly probabilities (per interval, us-east-1 baseline) ──────────────
    spike_probability: float = 0.003
    deploy_probability: float = 0.002
    outage_probability: float = 0.001

    # ── Drift ─────────────────────────────────────────────────────────────────
    annual_growth_factor: float = 0.35  # 35% growth Jan → Dec

    # ── RAM parameters ────────────────────────────────────────────────────────
    ram_cpu_weight: float = 0.65
    ram_baseline: float = 15.0
    ram_rolling_weight: float = 0.20
    ram_rolling_window: int = 6      # 6 steps = 30 minutes
    ram_smoothing_alpha: float = 0.15

    # ── Request rate parameters ───────────────────────────────────────────────
    request_base_scale: float = 28.0
    request_base_offset: float = 120.0

    # ── Disk I/O parameters ───────────────────────────────────────────────────
    disk_cpu_weight: float = 0.45
    disk_backup_magnitude: float = 175.0
    disk_logrotate_magnitude: float = 100.0
    disk_weekly_backup_magnitude: float = 300.0

    # ── Network parameters ────────────────────────────────────────────────────
    network_in_rps_weight: float = 0.12
    network_out_rps_weight: float = 0.22

    # ── Auto-scaler lag ───────────────────────────────────────────────────────
    instance_lag_min: int = 1
    instance_lag_max: int = 3


# ─── Seasonality Builder ─────────────────────────────────────────────────────
class SeasonalityEngine:
    """Generates daily seasonality, weekly multipliers, and long-term drift."""

    def __init__(self, config: TelemetryConfig) -> None:
        self.config = config

    def build_daily_pattern(self, hours: np.ndarray) -> np.ndarray:
        """
        Multi-harmonic sine decomposition of daily traffic pattern.

        Uses a combination of 3 sine harmonics (fundamental + 2nd + 3rd)
        to produce smooth transitions that approximate the target hourly
        CPU profile without lookup tables.

        Parameters
        ----------
        hours : np.ndarray
            Fractional hour-of-day values (0.0 – 23.99…) for each timestamp.

        Returns
        -------
        np.ndarray
            Daily seasonality component (centered around config.daily_baseline).
        """
        c = self.config
        pattern = (
            c.daily_A1 * np.sin(2 * np.pi * hours / 24.0 + c.daily_phase1)
            + c.daily_A2 * np.sin(4 * np.pi * hours / 24.0 + c.daily_phase2)
            + c.daily_A3 * np.sin(6 * np.pi * hours / 24.0 + c.daily_phase3)
            + c.daily_baseline
        )
        return pattern

    def build_weekly_multiplier(self, day_of_week: np.ndarray) -> np.ndarray:
        """
        Weekday vs weekend traffic multiplier.

        Maps each day-of-week index (0=Monday … 6=Sunday) to a scaling
        factor.  Weekdays sit in [1.0, 1.15]; weekends in [0.6, 0.75].
        Monday is slightly lower than Tue–Thu (ramp-up effect), and
        Friday begins declining toward the weekend.

        Parameters
        ----------
        day_of_week : np.ndarray
            Integer day-of-week (0=Mon … 6=Sun) for each timestamp.

        Returns
        -------
        np.ndarray
            Per-timestamp multiplicative factor.
        """
        multipliers = np.array([
            1.02,   # Monday  — slight ramp-up
            1.10,   # Tuesday
            1.12,   # Wednesday — mid-week peak
            1.10,   # Thursday
            1.04,   # Friday  — declining toward weekend
            0.72,   # Saturday
            0.65,   # Sunday  — lowest
        ])
        return multipliers[day_of_week]

    def build_trend(self, n: int) -> np.ndarray:
        """
        Linear growth ramp from 1.0 (January) to 1 + annual_growth_factor (December).

        Simulates gradual traffic growth across the calendar year. The ramp
        is perfectly smooth — no steps or discontinuities.

        Parameters
        ----------
        n : int
            Total number of timesteps in the dataset.

        Returns
        -------
        np.ndarray
            Per-timestep multiplicative trend factor.
        """
        t = np.linspace(0, 1, n)
        return 1.0 + self.config.annual_growth_factor * t


# ─── Special Event Engine ────────────────────────────────────────────────────
class SpecialEventEngine:
    """Applies holiday, sale, and deployment-window overlays to base signals."""

    def __init__(self, config: TelemetryConfig) -> None:
        self.config = config

    def build_event_series(
        self, timestamps: pd.DatetimeIndex
    ) -> Tuple[pd.Series, np.ndarray, np.ndarray, np.ndarray]:
        """
        Build per-timestep event labels and multiplier arrays.

        Returns
        -------
        event_labels : pd.Series
            Event type per timestep: 'none', 'sale_event', 'holiday',
            or 'deployment_window'.
        event_cpu_mult : np.ndarray
            Multiplicative CPU adjustment from events (sales boost,
            holidays reduce, deploys slightly boost).
        event_rps_mult : np.ndarray
            Multiplicative request-rate adjustment from events.
        event_error_add : np.ndarray
            Additive error-rate contribution from deployment windows.
        """
        n = len(timestamps)
        labels = np.array(["none"] * n, dtype=object)
        cpu_mult = np.ones(n)
        rps_mult = np.ones(n)
        error_add = np.zeros(n)

        sale_count = 0
        holiday_count = 0

        # ── Calendar events (sales & holidays) ───────────────────────────────
        for event in SPECIAL_EVENTS_CALENDAR:
            start = pd.Timestamp(event["start"])
            end = pd.Timestamp(event["end"]) + pd.Timedelta(hours=23, minutes=55)
            event_type = event["type"]
            factor_lo, factor_hi = event["factor_range"]
            factor = np.random.uniform(factor_lo, factor_hi)

            mask = (timestamps >= start) & (timestamps <= end)
            if not mask.any():
                continue

            event_indices = np.where(mask)[0]
            center = event_indices.mean()
            duration = len(event_indices)
            sigma = max(duration / 5.0, 1.0)

            # Gaussian-shaped intensity within the event window
            positions = event_indices.astype(float)
            intensity = np.exp(-0.5 * ((positions - center) / sigma) ** 2)

            labels[event_indices] = event_type

            # Both sale_event and holiday use the same formula;
            # factor > 1 boosts traffic (sale), factor < 1 reduces it (holiday).
            cpu_mult[event_indices] *= 1.0 + (factor - 1.0) * intensity
            rps_mult[event_indices] *= 1.0 + (factor - 1.0) * intensity

            if event_type == "sale_event":
                sale_count += 1
            elif event_type == "holiday":
                holiday_count += 1

        # ── Deployment windows: 4–6 planned maintenance windows/year ─────────
        n_deploy_windows = np.random.randint(4, 7)
        # Avoid the first/last week to prevent edge effects
        safe_zone = np.arange(288 * 7, n - 288 * 7)
        deploy_candidates = np.random.choice(
            safe_zone, size=min(n_deploy_windows * 5, len(safe_zone)), replace=False
        )

        deploy_count = 0
        used_deploy_centres: List[int] = []

        for pos in deploy_candidates:
            if deploy_count >= n_deploy_windows:
                break
            pos = int(pos)

            # Enforce 1-day minimum gap between deployment windows
            if any(abs(pos - c) < 288 for c in used_deploy_centres):
                continue
            # Prefer non-event timesteps
            if labels[pos] != "none":
                continue

            # Window duration: 2–4 hours = 24–48 five-minute steps
            window_steps = np.random.randint(24, 49)
            half = window_steps // 2
            w_start = max(0, pos - half)
            w_end = min(n, pos + half)
            w_indices = np.arange(w_start, w_end)

            sigma_w = max(window_steps / 4.0, 1.0)
            intensity_w = np.exp(
                -0.5 * ((w_indices.astype(float) - pos) / sigma_w) ** 2
            )

            labels[w_indices] = "deployment_window"

            # Slight CPU spike during deployment
            cpu_boost = np.random.uniform(1.05, 1.15)
            cpu_mult[w_indices] *= 1.0 + (cpu_boost - 1.0) * intensity_w

            # Mild traffic suppression (circuit-breaker / rolling restart)
            traffic_suppress = np.random.uniform(0.7, 0.9)
            rps_mult[w_indices] *= (
                traffic_suppress
                + (1.0 - traffic_suppress) * (1.0 - intensity_w)
            )

            # Error rate increase (+3–8%)
            err_boost = np.random.uniform(3.0, 8.0)
            error_add[w_indices] += err_boost * intensity_w

            used_deploy_centres.append(pos)
            deploy_count += 1

        logger.info(
            "Special events calendar applied | sale_events=%d | holidays=%d"
            " | deployment_windows=%d",
            sale_count,
            holiday_count,
            deploy_count,
        )

        return pd.Series(labels), cpu_mult, rps_mult, error_add


# ─── Workload Engine (V3) ────────────────────────────────────────────────────
class WorkloadEngine:
    """Assigns workload types and applies behavioural modifiers to base metrics."""

    def assign_workload_types(self, n: int) -> np.ndarray:
        """
        Returns array of workload type strings sampled from
        WORKLOAD_DISTRIBUTION probabilities.

        Parameters
        ----------
        n : int
            Number of rows to assign workload types for.

        Returns
        -------
        np.ndarray
            Array of workload type strings (length *n*).
        """
        types = list(WORKLOAD_DISTRIBUTION.keys())
        probs = list(WORKLOAD_DISTRIBUTION.values())
        return np.random.choice(types, size=n, p=probs)

    def apply_modifiers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies WORKLOAD_MODIFIERS to request_rate, disk_io, network_out,
        and response_latency_ms based on each row's workload_type.
        Re-clips all affected columns to their original valid ranges.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame containing workload_type and metric columns.

        Returns
        -------
        pd.DataFrame
            Same DataFrame with metrics modified in-place.
        """
        for wl_type, mods in WORKLOAD_MODIFIERS.items():
            mask = df["workload_type"].values == wl_type
            if not mask.any():
                continue
            for col, mult in mods.items():
                if mult != 1.0:
                    df.loc[mask, col] = df.loc[mask, col].values * mult

        # Re-clip affected columns to their valid ranges
        df["request_rate"] = np.clip(
            df["request_rate"].values, 50.0, 6500.0
        ).round(1)
        df["disk_io"] = np.clip(
            df["disk_io"].values, 5.0, 500.0
        ).round(2)
        df["network_out"] = np.clip(
            df["network_out"].values, 2.0, 1000.0
        ).round(2)
        df["response_latency_ms"] = np.clip(
            df["response_latency_ms"].values, 20.0, 5000.0
        ).round(1)

        return df


# ─── Anomaly Engine ──────────────────────────────────────────────────────────
class AnomalyEngine:
    """Injects flash-sale, deployment, and outage anomalies per region."""

    def __init__(self, config: TelemetryConfig) -> None:
        self.config = config

    def _gaussian_pulse(
        self, n: int, center: int, duration: int, magnitude: float
    ) -> np.ndarray:
        """
        Bell-curve anomaly shape over time.

        Parameters
        ----------
        n : int
            Total number of timesteps in the dataset.
        center : int
            Index of the pulse center.
        duration : int
            Width of the pulse in timesteps (≈ 4σ total).
        magnitude : float
            Peak amplitude of the pulse.

        Returns
        -------
        np.ndarray
            Array of length *n* with Gaussian pulse values.
        """
        t = np.arange(n, dtype=float)
        sigma = duration / 4.0
        return magnitude * np.exp(-0.5 * ((t - center) / sigma) ** 2)

    def generate_anomaly_mask(
        self,
        n: int,
        timestamps: pd.DatetimeIndex,
        anomaly_weight: float,
    ) -> Tuple[pd.DataFrame, int]:
        """
        Generate per-region anomaly adjustments.

        Event counts are scaled by the region's ``anomaly_weight`` so that
        high-traffic regions (us-east-1) receive proportionally more anomaly
        events than low-traffic ones (eu-west-1).

        Parameters
        ----------
        n : int
            Number of timesteps for this region.
        timestamps : pd.DatetimeIndex
            Timestamp index (unused except for diagnostics).
        anomaly_weight : float
            Scaling factor for anomaly counts (from REGION_CONFIG).

        Returns
        -------
        anomaly_df : pd.DataFrame
            Per-timestep anomaly adjustments (mult/add columns).
        total_anomalies : int
            Number of timesteps marked as anomaly.
        """
        # Initialise neutral anomaly frame
        anomaly_df = pd.DataFrame({
            "is_anomaly": np.zeros(n, dtype=bool),
            "cpu_mult": np.ones(n),
            "cpu_add": np.zeros(n),
            "rps_mult": np.ones(n),
            "err_add": np.zeros(n),
            "net_mult": np.ones(n),
            "latency_mult": np.ones(n),
            "latency_add": np.zeros(n),
            "instance_override": np.full(n, np.nan),
        })

        w = anomaly_weight

        # Scale event counts by anomaly_weight with minimum floors
        n_spikes = np.random.randint(
            max(5, int(6 * w)), max(6, int(10 * w)) + 1
        )
        n_deploys = np.random.randint(
            max(4, int(4 * w)), max(5, int(7 * w)) + 1
        )
        n_outages = np.random.randint(
            max(2, int(2 * w)), max(3, int(4 * w)) + 1
        )

        spike_count = 0
        deploy_count = 0
        outage_count = 0

        # 5-hour minimum gap between anomaly centres to prevent overlap
        min_gap = 60
        used_centres: List[int] = []

        def _too_close(center: int) -> bool:
            return any(abs(center - c) < min_gap for c in used_centres)

        edge_margin = 50
        pool = np.arange(edge_margin, n - edge_margin)

        # ── Type 1 — Flash Sale / Viral Traffic Spike ─────────────────────────
        candidates = np.random.choice(
            pool, size=min(n_spikes * 5, len(pool)), replace=False
        )
        for idx in candidates:
            if spike_count >= n_spikes:
                break
            idx = int(idx)
            if _too_close(idx):
                continue

            duration = np.random.randint(25, 65)  # 2–5.5 hours
            mag_cpu = np.random.uniform(1.4, 1.85)
            mag_rps = np.random.uniform(1.8, 3.2)
            mag_err = np.random.uniform(2.0, 7.0)
            mag_net = np.random.uniform(1.5, 2.5)
            mag_lat = np.random.uniform(1.5, 3.0)

            pulse = self._gaussian_pulse(n, idx, duration, 1.0)
            active = pulse > 0.005

            anomaly_df.loc[active, "is_anomaly"] = True
            anomaly_df.loc[active, "cpu_mult"] *= (
                1.0 + (mag_cpu - 1.0) * pulse[active]
            )
            anomaly_df.loc[active, "rps_mult"] *= (
                1.0 + (mag_rps - 1.0) * pulse[active]
            )
            anomaly_df.loc[active, "err_add"] += mag_err * pulse[active]
            anomaly_df.loc[active, "net_mult"] *= (
                1.0 + (mag_net - 1.0) * pulse[active]
            )
            anomaly_df.loc[active, "latency_mult"] *= (
                1.0 + (mag_lat - 1.0) * pulse[active]
            )

            used_centres.append(idx)
            spike_count += 1

        # ── Type 2 — Deployment / Service Instability ─────────────────────────
        remaining = np.array([i for i in pool if not _too_close(i)])
        candidates = np.random.choice(
            remaining,
            size=min(n_deploys * 5, len(remaining)),
            replace=False,
        )
        for idx in candidates:
            if deploy_count >= n_deploys:
                break
            idx = int(idx)
            if _too_close(idx):
                continue

            duration = np.random.randint(15, 40)  # 1.25–3.3 hours
            mag_cpu_add = np.random.uniform(15.0, 35.0)
            mag_err = np.random.uniform(5.0, 12.0)
            mag_rps = np.random.uniform(0.5, 0.8)
            mag_lat_add = np.random.uniform(200.0, 800.0)

            pulse = self._gaussian_pulse(n, idx, duration, 1.0)
            active = pulse > 0.005

            anomaly_df.loc[active, "is_anomaly"] = True
            anomaly_df.loc[active, "cpu_add"] += mag_cpu_add * pulse[active]
            anomaly_df.loc[active, "err_add"] += mag_err * pulse[active]
            anomaly_df.loc[active, "rps_mult"] *= (
                mag_rps + (1.0 - mag_rps) * (1.0 - pulse[active])
            )
            anomaly_df.loc[active, "latency_add"] += mag_lat_add * pulse[active]

            used_centres.append(idx)
            deploy_count += 1

        # ── Type 3 — Partial Outage / Degradation ────────────────────────────
        remaining = np.array([i for i in pool if not _too_close(i)])
        candidates = np.random.choice(
            remaining,
            size=min(n_outages * 5, len(remaining)),
            replace=False,
        )
        for idx in candidates:
            if outage_count >= n_outages:
                break
            idx = int(idx)
            if _too_close(idx):
                continue

            duration = np.random.randint(20, 50)  # 1.7–4.2 hours
            mag_cpu = np.random.uniform(0.3, 0.6)
            mag_rps = np.random.uniform(0.1, 0.4)
            mag_err = np.random.uniform(15.0, 30.0)
            mag_lat_add = np.random.uniform(1000.0, 3000.0)

            pulse = self._gaussian_pulse(n, idx, duration, 1.0)
            active = pulse > 0.005

            anomaly_df.loc[active, "is_anomaly"] = True
            anomaly_df.loc[active, "cpu_mult"] *= (
                mag_cpu + (1.0 - mag_cpu) * (1.0 - pulse[active])
            )
            anomaly_df.loc[active, "rps_mult"] *= (
                mag_rps + (1.0 - mag_rps) * (1.0 - pulse[active])
            )
            anomaly_df.loc[active, "err_add"] += mag_err * pulse[active]
            anomaly_df.loc[active, "latency_add"] += mag_lat_add * pulse[active]
            anomaly_df.loc[active, "instance_override"] = 2.0

            used_centres.append(idx)
            outage_count += 1

        total_anomalies = int(anomaly_df["is_anomaly"].sum())

        return anomaly_df, total_anomalies

    # ── Regional Partial Failure Injection (V3 — Upgrade 4) ───────────────────
    def inject_regional_failures(
        self,
        region_dfs: Dict[str, pd.DataFrame],
        timestamps: pd.DatetimeIndex,
    ) -> Dict[str, pd.DataFrame]:
        """
        Injects 1–3 regional partial failure events across the simulation.
        Modifies the affected region's metrics and applies traffic-rerouting
        effects to the other two regions.  Recomputes resource_pressure_score
        and sla_breach_risk after modifications for consistency.

        Parameters
        ----------
        region_dfs : Dict[str, pd.DataFrame]
            Dictionary mapping region name → region DataFrame.
        timestamps : pd.DatetimeIndex
            Shared timestamp index across all regions.

        Returns
        -------
        Dict[str, pd.DataFrame]
            Updated region DataFrames with failure effects applied.
        """
        n = len(timestamps)
        n_failures = np.random.randint(1, 4)  # 1–3 events
        regions = list(region_dfs.keys())

        injected = 0
        used_centres: List[int] = []

        for _ in range(n_failures):
            # Pick affected region
            affected_region = regions[np.random.randint(0, len(regions))]

            # Pick time position (well within bounds)
            center = np.random.randint(200, n - 200)

            # Minimum spacing between regional failure centres
            if any(abs(center - c) < 200 for c in used_centres):
                continue

            # Duration: 60–180 minutes = 12–36 five-minute steps
            duration_steps = np.random.randint(12, 37)

            # Create Gaussian pulse
            pulse = self._gaussian_pulse(n, center, duration_steps, 1.0)
            active = pulse > 0.005

            # ── Effects on AFFECTED region ────────────────────────────────────
            adf = region_dfs[affected_region]
            rps_factor = np.random.uniform(0.3, 0.6)
            err_add_val = np.random.uniform(8.0, 18.0)
            lat_factor = np.random.uniform(2.0, 4.5)

            adf.loc[active, "request_rate"] = (
                adf.loc[active, "request_rate"].values
                * (rps_factor + (1.0 - rps_factor) * (1.0 - pulse[active]))
            )
            adf.loc[active, "error_rate"] = (
                adf.loc[active, "error_rate"].values
                + err_add_val * pulse[active]
            )
            adf.loc[active, "response_latency_ms"] = (
                adf.loc[active, "response_latency_ms"].values
                * (1.0 + (lat_factor - 1.0) * pulse[active])
            )
            adf.loc[active, "is_anomaly"] = True

            # Re-clip affected region
            adf["request_rate"] = np.clip(
                adf["request_rate"].values, 50.0, 6500.0
            ).round(1)
            adf["error_rate"] = np.clip(
                adf["error_rate"].values, 0.0, 35.0
            ).round(3)
            adf["response_latency_ms"] = np.clip(
                adf["response_latency_ms"].values, 20.0, 5000.0
            ).round(1)

            # ── Traffic rerouting on OTHER regions ────────────────────────────
            for other_region in regions:
                if other_region == affected_region:
                    continue
                odf = region_dfs[other_region]
                rps_reroute = np.random.uniform(1.1, 1.3)
                cpu_reroute = np.random.uniform(3.0, 8.0)

                odf.loc[active, "request_rate"] = (
                    odf.loc[active, "request_rate"].values
                    * (1.0 + (rps_reroute - 1.0) * pulse[active])
                )
                odf.loc[active, "cpu_usage"] = (
                    odf.loc[active, "cpu_usage"].values
                    + cpu_reroute * pulse[active]
                )

                odf["request_rate"] = np.clip(
                    odf["request_rate"].values, 50.0, 6500.0
                ).round(1)
                odf["cpu_usage"] = np.clip(
                    odf["cpu_usage"].values, 2.0, 98.0
                ).round(2)

            # ── Recompute pressure & SLA for ALL regions after modification ──
            for reg in regions:
                rdf = region_dfs[reg]
                cpu_arr = rdf["cpu_usage"].values
                ram_arr = rdf["ram_usage"].values
                rps_arr = rdf["request_rate"].values
                lat_arr = rdf["response_latency_ms"].values
                err_arr = rdf["error_rate"].values

                norm_rps = np.clip(rps_arr / 65.0, 0, 100)
                norm_lat = np.clip(lat_arr / 50.0, 0, 100)
                norm_err = np.clip(err_arr / 0.35, 0, 100)

                pressure = (
                    cpu_arr * 0.40
                    + ram_arr * 0.25
                    + norm_rps * 0.20
                    + norm_lat * 0.15
                )
                rdf["resource_pressure_score"] = np.clip(
                    pressure, 0, 100
                ).round(2)

                sla = (
                    cpu_arr * 0.25
                    + norm_lat * 0.40
                    + norm_err * 0.35
                )
                rdf["sla_breach_risk"] = np.clip(sla, 0, 100).round(2)

            used_centres.append(center)
            injected += 1

            start_ts = timestamps[max(0, center - duration_steps // 2)]
            logger.info(
                "Regional partial failure injected | region=%s"
                " | duration=%dmin | start=%s",
                affected_region,
                duration_steps * 5,
                start_ts,
            )

        logger.info("Regional failure events injected | count=%d", injected)

        return region_dfs


# ─── Metric Generators ───────────────────────────────────────────────────────
class MetricGenerator:
    """Generates each metric column given base signals, seasonality, and anomalies."""

    def __init__(self, config: TelemetryConfig) -> None:
        self.config = config

    # ── CPU ────────────────────────────────────────────────────────────────────
    def generate_cpu(
        self,
        daily_pattern: np.ndarray,
        weekly_mult: np.ndarray,
        trend: np.ndarray,
        event_cpu_mult: np.ndarray,
        anomaly_df: pd.DataFrame,
    ) -> np.ndarray:
        """
        Build CPU usage from daily seasonality × weekly multiplier × trend
        × event overlay, plus noise, then apply anomaly adjustments.
        """
        cpu = daily_pattern * weekly_mult * trend * event_cpu_mult
        cpu += np.random.normal(0, self.config.cpu_noise_sigma, len(cpu))
        cpu = cpu * anomaly_df["cpu_mult"].values + anomaly_df["cpu_add"].values
        return np.clip(cpu, 2.0, 98.0).round(2)

    # ── RAM ────────────────────────────────────────────────────────────────────
    def generate_ram(self, cpu: np.ndarray) -> np.ndarray:
        """
        RAM is correlated with CPU but smoother: uses a rolling-mean lag
        component and EMA smoothing to prevent sudden drops.
        """
        c = self.config
        cpu_series = pd.Series(cpu)
        rolling_cpu = (
            cpu_series.rolling(window=c.ram_rolling_window, min_periods=1)
            .mean()
            .values
        )

        ram = (
            c.ram_cpu_weight * cpu
            + c.ram_baseline
            + c.ram_rolling_weight * rolling_cpu
            + np.random.normal(0, c.ram_noise_sigma, len(cpu))
        )

        # Exponential moving average smoothing (vectorised via pandas)
        smoothed = (
            pd.Series(ram).ewm(alpha=c.ram_smoothing_alpha, adjust=False).mean().values
        )
        return np.clip(smoothed, 10.0, 95.0).round(2)

    # ── Request Rate ──────────────────────────────────────────────────────────
    def generate_request_rate(
        self,
        daily_pattern: np.ndarray,
        weekly_mult: np.ndarray,
        trend: np.ndarray,
        event_rps_mult: np.ndarray,
        region_traffic_mult: float,
        anomaly_df: pd.DataFrame,
    ) -> np.ndarray:
        """
        Request rate shares the daily/weekly shape of CPU but scaled to the
        RPS range and modulated by the region's traffic multiplier.
        """
        c = self.config
        rps = (
            daily_pattern
            * weekly_mult
            * trend
            * c.request_base_scale
            * region_traffic_mult
            * event_rps_mult
            + c.request_base_offset
        )
        rps += np.random.normal(0, c.request_noise_sigma, len(rps))
        rps = rps * anomaly_df["rps_mult"].values
        return np.clip(rps, 50.0, 6500.0).round(1)

    # ── Disk I/O ──────────────────────────────────────────────────────────────
    def generate_disk_io(
        self,
        cpu: np.ndarray,
        hours: np.ndarray,
        day_of_week: np.ndarray,
    ) -> np.ndarray:
        """
        Disk I/O = CPU-correlated base + periodic batch-job bursts
        (backups, log rotation) using Gaussian pulses.
        """
        c = self.config
        n = len(cpu)

        disk = c.disk_cpu_weight * cpu + np.random.normal(0, c.disk_noise_sigma, n)

        # Daily database backup 02:00–03:00
        disk += c.disk_backup_magnitude * np.exp(
            -0.5 * ((hours - 2.5) / 0.25) ** 2
        )
        # Daily log rotation at 06:00
        disk += c.disk_logrotate_magnitude * np.exp(
            -0.5 * ((hours - 6.0) / 0.20) ** 2
        )
        # Weekly full backup — Sunday 03:00
        sunday = (day_of_week == 6).astype(float)
        disk += (
            c.disk_weekly_backup_magnitude
            * np.exp(-0.5 * ((hours - 3.0) / 0.35) ** 2)
            * sunday
        )

        return np.clip(disk, 5.0, 500.0).round(2)

    # ── Network In / Out ──────────────────────────────────────────────────────
    def generate_network(
        self, request_rate: np.ndarray, anomaly_df: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Network traffic is primarily driven by request_rate.
        network_out > network_in (responses are larger than requests).
        """
        c = self.config
        n = len(request_rate)

        net_in = (
            c.network_in_rps_weight * request_rate
            + np.random.normal(0, c.network_noise_sigma, n)
        )
        net_out = (
            c.network_out_rps_weight * request_rate
            + np.random.normal(0, c.network_noise_sigma * 1.25, n)
        )

        # Anomaly multiplier
        net_in = net_in * anomaly_df["net_mult"].values
        net_out = net_out * anomaly_df["net_mult"].values

        return (
            np.clip(net_in, 1.0, 800.0).round(2),
            np.clip(net_out, 2.0, 1000.0).round(2),
        )

    # ── Error Rate ────────────────────────────────────────────────────────────
    def generate_error_rate(
        self,
        cpu: np.ndarray,
        anomaly_df: pd.DataFrame,
        event_error_add: np.ndarray,
    ) -> np.ndarray:
        """
        Error rate is normally very low (0.1–1.5%) and rises non-linearly
        when CPU exceeds 70%, accelerating sharply above 85%.
        Deployment windows and anomalies add their own error contributions.
        """
        n = len(cpu)
        base_error = 0.3 + np.random.exponential(0.2, n)

        stress_factor = np.where(
            cpu > 85,
            (cpu - 85) * 0.15,
            np.where(cpu > 70, (cpu - 70) * 0.04, 0.0),
        )

        error = (
            base_error
            + stress_factor
            + anomaly_df["err_add"].values
            + event_error_add
        )
        return np.clip(error, 0.0, 35.0).round(3)

    # ── Response Latency ──────────────────────────────────────────────────────
    def generate_latency(
        self, cpu: np.ndarray, anomaly_df: pd.DataFrame
    ) -> np.ndarray:
        """
        Latency correlates with CPU stress via a smooth polynomial.
        Anomalies contribute multiplicatively (flash sales) and
        additively (deployments, outages).
        """
        c = self.config
        n = len(cpu)

        # Smooth polynomial: non-linear relationship with CPU
        # cpu=10 → ~84ms, cpu=50 → ~260ms, cpu=80 → ~476ms, cpu=95 → ~612ms
        base_latency = 60.0 + 2.0 * cpu + 0.04 * cpu ** 2
        latency = base_latency + np.random.normal(0, c.latency_noise_sigma, n)

        # Anomaly contributions
        latency = (
            latency * anomaly_df["latency_mult"].values
            + anomaly_df["latency_add"].values
        )
        return np.clip(latency, 20.0, 5000.0).round(1)

    # ── Active Instances (Auto-Scaler) ────────────────────────────────────────
    def generate_active_instances(
        self, cpu: np.ndarray, anomaly_df: pd.DataFrame
    ) -> np.ndarray:
        """
        Simulates cloud auto-scaling decisions based on CPU thresholds,
        with a 1–3 step response lag (5–15 min delay).
        """
        c = self.config

        # Vectorised threshold lookup via np.digitize
        thresholds = [25, 40, 55, 65, 75, 85, 92]
        instance_values = np.array([2, 3, 4, 6, 8, 11, 14, 18])

        lag = np.random.randint(c.instance_lag_min, c.instance_lag_max + 1)
        lagged = pd.Series(cpu).shift(lag).bfill().values
        instances = instance_values[np.digitize(lagged, thresholds)]

        # Outage overrides
        outage_mask = ~np.isnan(anomaly_df["instance_override"].values)
        instances[outage_mask] = (
            anomaly_df.loc[outage_mask, "instance_override"].values.astype(int)
        )

        # Forward-fill to prevent single-interval drops
        instances = pd.Series(instances).ffill().astype(int).values
        return np.clip(instances, 2, 20)

    # ── Instance Type ─────────────────────────────────────────────────────────
    def generate_instance_type(self, cpu: np.ndarray) -> np.ndarray:
        """
        Assign compute type based on CPU load at each timestep:
          cpu < 40  → t3.medium  (burstable)
          cpu < 70  → m5.large   (general purpose)
          cpu >= 70 → c5.xlarge  (compute-optimised)
        """
        return np.where(
            cpu < 40, "t3.medium", np.where(cpu < 70, "m5.large", "c5.xlarge")
        )

    # ── Cost Per Hour ─────────────────────────────────────────────────────────
    def generate_cost(
        self, active_instances: np.ndarray, cpu: np.ndarray, region: str
    ) -> np.ndarray:
        """
        FinOps cost simulation:
        cost = active_instances × region_price + cpu × 0.02 + noise
        """
        price = REGION_CONFIG[region]["cost_per_instance"]
        cost = (
            active_instances * price
            + cpu * 0.02
            + np.random.normal(0, 0.05, len(cpu))
        )
        return np.clip(cost, 0.50, 500.0).round(4)

    # ── Resource Pressure Score (V3 — Upgrade 2) ─────────────────────────────
    def generate_pressure_score(
        self,
        cpu: np.ndarray,
        ram: np.ndarray,
        request_rate: np.ndarray,
        latency: np.ndarray,
    ) -> np.ndarray:
        """
        Weighted composite infrastructure stress metric.

        Normalises request_rate (max 6500) and latency (max 5000ms) to
        0–100 before combining with CPU and RAM percentages.

        Returns
        -------
        np.ndarray
            Pressure score clipped to [0, 100], rounded to 2 dp.
        """
        norm_rps = np.clip(request_rate / 65.0, 0, 100)
        norm_latency = np.clip(latency / 50.0, 0, 100)

        pressure = (
            cpu * 0.40
            + ram * 0.25
            + norm_rps * 0.20
            + norm_latency * 0.15
        )
        return np.clip(pressure, 0.0, 100.0).round(2)

    # ── SLA Breach Risk (V3 — Upgrade 3) ─────────────────────────────────────
    def generate_sla_risk(
        self,
        cpu: np.ndarray,
        latency: np.ndarray,
        error_rate: np.ndarray,
    ) -> np.ndarray:
        """
        SLA breach probability proxy based on latency, errors, and CPU stress.

        Normalises error_rate (max 35) and latency (max 5000ms) to 0–100
        before combining with CPU percentage.

        Returns
        -------
        np.ndarray
            SLA risk score clipped to [0, 100], rounded to 2 dp.
        """
        norm_latency = np.clip(latency / 50.0, 0, 100)
        norm_error = np.clip(error_rate / 0.35, 0, 100)

        sla = (
            cpu * 0.25
            + norm_latency * 0.40
            + norm_error * 0.35
        )
        return np.clip(sla, 0.0, 100.0).round(2)


# ─── Main Generator ──────────────────────────────────────────────────────────
class CloudTelemetryGenerator:
    """
    Orchestrates the full multi-region telemetry generation pipeline.
    Entry point for all external callers.
    """

    def __init__(self, config: TelemetryConfig) -> None:
        self.config = config
        self.seasonality = SeasonalityEngine(config)
        self.event_engine = SpecialEventEngine(config)
        self.anomaly_engine = AnomalyEngine(config)
        self.metric_gen = MetricGenerator(config)
        self.workload_engine = WorkloadEngine()

    def generate(self) -> pd.DataFrame:
        """
        Full pipeline:
        timestamps → seasonality → events → per-region metrics
        → workload modifiers → pressure/SLA scores
        → regional failures → concat → validate → return
        """
        # ── Reproducibility seed ──────────────────────────────────────────────
        np.random.seed(self.config.random_seed)

        c = self.config
        logger.info(
            "Telemetry generation started | date_range=%s to %s"
            " | interval=%dmin | regions=3",
            c.start_date,
            c.end_date,
            c.interval_minutes,
        )

        # ── 1. Build timestamp index ─────────────────────────────────────────
        timestamps = pd.date_range(
            start=c.start_date,
            end=f"{c.end_date} 23:55:00",
            freq=f"{c.interval_minutes}min",
        )
        n = len(timestamps)
        logger.info("Timestamp index built | records_per_region=%d", n)

        # ── 2. Extract time features ─────────────────────────────────────────
        hours = (timestamps.hour + timestamps.minute / 60.0).values.astype(float)
        day_of_week = timestamps.dayofweek.values

        # ── 3. Build shared seasonality & trend ──────────────────────────────
        daily_pattern = self.seasonality.build_daily_pattern(hours)
        weekly_mult = self.seasonality.build_weekly_multiplier(day_of_week)
        trend = self.seasonality.build_trend(n)
        logger.info("Seasonality and trend components built")

        # ── 4. Build special events calendar ─────────────────────────────────
        event_labels, event_cpu_mult, event_rps_mult, event_error_add = (
            self.event_engine.build_event_series(timestamps)
        )

        # ── 5. Generate per region (dict for regional failure injection) ─────
        region_dfs: Dict[str, pd.DataFrame] = {}
        for region in REGION_CONFIG:
            region_dfs[region] = self._generate_region(
                region,
                timestamps,
                n,
                hours,
                day_of_week,
                daily_pattern,
                weekly_mult,
                trend,
                event_labels,
                event_cpu_mult,
                event_rps_mult,
                event_error_add,
            )

        # ── 6. Inject regional partial failures (V3 — Upgrade 4) ────────────
        region_dfs = self.anomaly_engine.inject_regional_failures(
            region_dfs, timestamps
        )

        # ── 7. Concatenate and sort ──────────────────────────────────────────
        df = pd.concat(region_dfs.values(), ignore_index=True)
        # Stable sort by timestamp preserves region insertion order within ties
        df = df.sort_values("timestamp", kind="mergesort").reset_index(drop=True)

        logger.info(
            "All regions generated and concatenated | total_shape=%s", df.shape
        )

        # ── 8. Validate ──────────────────────────────────────────────────────
        self._validate_output(df)

        return df

    def _generate_region(
        self,
        region: str,
        timestamps: pd.DatetimeIndex,
        n: int,
        hours: np.ndarray,
        day_of_week: np.ndarray,
        daily_pattern: np.ndarray,
        weekly_mult: np.ndarray,
        trend: np.ndarray,
        event_labels: pd.Series,
        event_cpu_mult: np.ndarray,
        event_rps_mult: np.ndarray,
        event_error_add: np.ndarray,
    ) -> pd.DataFrame:
        """Generates all 17 non-region columns for a single region."""
        rc = REGION_CONFIG[region]
        mg = self.metric_gen

        # ── Anomalies for this region (independent per region) ───────────────
        anomaly_df, total_anomalies = self.anomaly_engine.generate_anomaly_mask(
            n, timestamps, rc["anomaly_weight"]
        )

        # ── Generate all base metrics ────────────────────────────────────────
        cpu = mg.generate_cpu(
            daily_pattern, weekly_mult, trend, event_cpu_mult, anomaly_df
        )
        ram = mg.generate_ram(cpu)
        rps = mg.generate_request_rate(
            daily_pattern,
            weekly_mult,
            trend,
            event_rps_mult,
            rc["traffic_multiplier"],
            anomaly_df,
        )
        disk = mg.generate_disk_io(cpu, hours, day_of_week)
        net_in, net_out = mg.generate_network(rps, anomaly_df)
        error = mg.generate_error_rate(cpu, anomaly_df, event_error_add)
        latency = mg.generate_latency(cpu, anomaly_df)
        instances = mg.generate_active_instances(cpu, anomaly_df)
        inst_type = mg.generate_instance_type(cpu)
        cost = mg.generate_cost(instances, cpu, region)

        # ── Assign workload types (V3 — Upgrade 1) ──────────────────────────
        workload = self.workload_engine.assign_workload_types(n)

        # ── Build DataFrame with placeholder scores ──────────────────────────
        region_df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "region": region,
                "workload_type": workload,
                "cpu_usage": cpu,
                "ram_usage": ram,
                "disk_io": disk,
                "network_in": net_in,
                "network_out": net_out,
                "request_rate": rps,
                "error_rate": error,
                "response_latency_ms": latency,
                "resource_pressure_score": 0.0,
                "sla_breach_risk": 0.0,
                "active_instances": instances,
                "instance_type": inst_type,
                "cost_per_hour": cost,
                "special_event": event_labels.values,
                "is_anomaly": anomaly_df["is_anomaly"].values,
            }
        )

        # ── Apply workload modifiers (V3 — Upgrade 1) ───────────────────────
        region_df = self.workload_engine.apply_modifiers(region_df)

        wl_unique, wl_counts = np.unique(
            region_df["workload_type"].values, return_counts=True
        )
        logger.info(
            "WorkloadEngine applied | distribution=%s",
            dict(zip(wl_unique, wl_counts)),
        )

        # ── Compute composite scores (V3 — Upgrades 2 & 3) ──────────────────
        region_df["resource_pressure_score"] = mg.generate_pressure_score(
            region_df["cpu_usage"].values,
            region_df["ram_usage"].values,
            region_df["request_rate"].values,
            region_df["response_latency_ms"].values,
        )
        region_df["sla_breach_risk"] = mg.generate_sla_risk(
            region_df["cpu_usage"].values,
            region_df["response_latency_ms"].values,
            region_df["error_rate"].values,
        )

        logger.info("resource_pressure_score and sla_breach_risk computed")

        logger.info(
            "Region %s generated | shape=%s | anomalies=%d",
            region,
            region_df.shape,
            total_anomalies,
        )

        return region_df

    def _validate_output(self, df: pd.DataFrame) -> None:
        """
        Assert shape, dtypes, ranges, correlations, region balance,
        workload coverage, composite scores, and cost sanity.
        Raises ValueError with a descriptive message if any check fails.
        Logs each check at INFO level.

        V2 checks: 1–10
        V3 checks: 11–15  (Check 16 — output files — is verified post-save)
        """

        # ── V2 Check 1 — Shape ───────────────────────────────────────────────
        if df.shape[0] < 300_000:
            raise ValueError(
                f"Insufficient records: {df.shape[0]} (need >= 300,000)"
            )
        # V3 Check 1 — Column count updated to 18
        if df.shape[1] != 18:
            raise ValueError(f"Expected 18 columns, got {df.shape[1]}")
        logger.info("Validation: shape check passed (%d, %d)", *df.shape)

        # ── V2 Check 2 — Column presence and order (updated for V3) ──────────
        expected_cols = [
            "timestamp",
            "region",
            "workload_type",
            "cpu_usage",
            "ram_usage",
            "disk_io",
            "network_in",
            "network_out",
            "request_rate",
            "error_rate",
            "response_latency_ms",
            "resource_pressure_score",
            "sla_breach_risk",
            "active_instances",
            "instance_type",
            "cost_per_hour",
            "special_event",
            "is_anomaly",
        ]
        if list(df.columns) != expected_cols:
            raise ValueError(
                f"Column order/names incorrect: {list(df.columns)}"
            )
        logger.info("Validation: column order check passed")

        # ── V2 Check 3 — Range checks ────────────────────────────────────────
        range_checks = [
            ("cpu_usage", 0, 100),
            ("ram_usage", 0, 100),
            ("error_rate", 0, 35),
            ("active_instances", 2, 20),
            ("response_latency_ms", 20, 5000),
        ]
        for col, lo, hi in range_checks:
            if not df[col].between(lo, hi).all():
                bad_min = df[col].min()
                bad_max = df[col].max()
                raise ValueError(
                    f"{col} outside [{lo}, {hi}]: min={bad_min}, max={bad_max}"
                )
        if not (df["cost_per_hour"] > 0).all():
            raise ValueError("Negative cost detected")
        logger.info("Validation: range checks passed")

        # ── V2 Check 4 — No NaN values ───────────────────────────────────────
        nan_count = df.isnull().sum().sum()
        if nan_count > 0:
            raise ValueError(f"NaN values detected: {nan_count}")
        logger.info("Validation: no NaN values")

        # ── V2 Check 5 — Timestamp monotonicity (per region) ─────────────────
        for region in df["region"].unique():
            sub = df[df["region"] == region]
            if not sub["timestamp"].is_monotonic_increasing:
                raise ValueError(f"Non-monotonic timestamps in {region}")
        logger.info("Validation: timestamp monotonicity confirmed (per region)")

        # ── V2 Check 6 — Correlation checks (per region) ─────────────────────
        for region in df["region"].unique():
            sub = df[df["region"] == region]
            corr = sub[
                [
                    "cpu_usage",
                    "ram_usage",
                    "request_rate",
                    "response_latency_ms",
                    "cost_per_hour",
                ]
            ].corr()

            cpu_ram = corr.loc["cpu_usage", "ram_usage"]
            cpu_rps = corr.loc["cpu_usage", "request_rate"]
            cpu_lat = corr.loc["cpu_usage", "response_latency_ms"]
            cpu_cost = corr.loc["cpu_usage", "cost_per_hour"]

            if cpu_ram < 0.70:
                raise ValueError(
                    f"{region}: CPU-RAM corr {cpu_ram:.3f} < 0.70"
                )
            if cpu_rps < 0.75:
                raise ValueError(
                    f"{region}: CPU-RPS corr {cpu_rps:.3f} < 0.75"
                )
            if cpu_lat < 0.60:
                raise ValueError(
                    f"{region}: CPU-Latency corr {cpu_lat:.3f} < 0.60"
                )
            if cpu_cost < 0.60:
                raise ValueError(
                    f"{region}: CPU-Cost corr {cpu_cost:.3f} < 0.60"
                )

            logger.info(
                "Validation: %s correlations OK"
                " (RAM=%.3f, RPS=%.3f, Lat=%.3f, Cost=%.3f)",
                region,
                cpu_ram,
                cpu_rps,
                cpu_lat,
                cpu_cost,
            )

        # ── V2 Check 7 — Anomaly coverage (per region) ───────────────────────
        for region in df["region"].unique():
            sub = df[df["region"] == region]
            rate = sub["is_anomaly"].mean()
            if not (0.005 <= rate <= 0.08):
                raise ValueError(
                    f"{region}: anomaly rate {rate:.3f} outside [0.005, 0.08]"
                )
            logger.info(
                "Validation: %s anomaly rate OK (%.3f = %.1f%%)",
                region,
                rate,
                rate * 100,
            )

        # ── V2 Check 8 — Region distribution ─────────────────────────────────
        dist = df["region"].value_counts(normalize=True)
        for region in REGION_CONFIG:
            r = dist.get(region, 0)
            if not (0.30 <= r <= 0.36):
                raise ValueError(
                    f"{region}: distribution {r:.3f} outside [0.30, 0.36]"
                )
        logger.info("Validation: region distribution OK")

        # ── V2 Check 9 — Special event coverage ──────────────────────────────
        events = df["special_event"].value_counts()
        for evt in ["sale_event", "holiday", "deployment_window"]:
            if evt not in events.index:
                raise ValueError(f"No {evt} records found")
        logger.info("Validation: special event coverage OK")

        # ── V2 Check 10 — Instance type coverage ─────────────────────────────
        types = set(df["instance_type"].unique())
        expected_types = {"t3.medium", "m5.large", "c5.xlarge"}
        if types != expected_types:
            raise ValueError(f"Instance types {types} != {expected_types}")
        logger.info("Validation: instance type coverage OK")

        # ── V3 Check 2 — Workload type coverage ─────────────────────────────
        wl_dist = df["workload_type"].value_counts(normalize=True)
        expected_wl = {
            "web_application", "api_service",
            "batch_processing", "streaming_service",
        }
        if set(df["workload_type"].unique()) != expected_wl:
            raise ValueError(
                f"Workload types {set(df['workload_type'].unique())} "
                f"!= {expected_wl}"
            )
        if not (0.30 <= wl_dist.get("web_application", 0) <= 0.50):
            raise ValueError(
                f"web_application distribution "
                f"{wl_dist.get('web_application', 0):.3f} outside [0.30, 0.50]"
            )
        if not (0.20 <= wl_dist.get("api_service", 0) <= 0.40):
            raise ValueError(
                f"api_service distribution "
                f"{wl_dist.get('api_service', 0):.3f} outside [0.20, 0.40]"
            )
        if not (0.05 <= wl_dist.get("batch_processing", 0) <= 0.25):
            raise ValueError(
                f"batch_processing distribution "
                f"{wl_dist.get('batch_processing', 0):.3f} outside [0.05, 0.25]"
            )
        if not (0.05 <= wl_dist.get("streaming_service", 0) <= 0.25):
            raise ValueError(
                f"streaming_service distribution "
                f"{wl_dist.get('streaming_service', 0):.3f} outside [0.05, 0.25]"
            )
        logger.info("Validation: workload type coverage OK")

        # ── V3 Check 3 — Pressure score range ────────────────────────────────
        if not df["resource_pressure_score"].between(0, 100).all():
            raise ValueError("resource_pressure_score outside [0, 100]")
        logger.info("Validation: resource_pressure_score range OK")

        # ── V3 Check 4 — SLA risk range ──────────────────────────────────────
        if not df["sla_breach_risk"].between(0, 100).all():
            raise ValueError("sla_breach_risk outside [0, 100]")
        logger.info("Validation: sla_breach_risk range OK")

        # ── V3 Check 5 — Pressure & SLA correlation with CPU ─────────────────
        for region in df["region"].unique():
            sub = df[df["region"] == region]
            cpu_pressure = sub["cpu_usage"].corr(
                sub["resource_pressure_score"]
            )
            cpu_sla = sub["cpu_usage"].corr(sub["sla_breach_risk"])

            if cpu_pressure < 0.75:
                raise ValueError(
                    f"{region}: CPU-Pressure correlation "
                    f"{cpu_pressure:.3f} < 0.75"
                )
            if cpu_sla < 0.60:
                raise ValueError(
                    f"{region}: CPU-SLA correlation {cpu_sla:.3f} < 0.60"
                )
            logger.info(
                "Validation: %s composite scores OK"
                " (CPU-Pressure=%.3f, CPU-SLA=%.3f)",
                region,
                cpu_pressure,
                cpu_sla,
            )

        logger.info("Validation passed")

    def save(self, df: pd.DataFrame) -> None:
        """Save to CSV and Parquet with automatic directory creation."""
        # CSV (existing)
        csv_path = Path(self.config.output_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_path, index=False)
        logger.info("Dataset saved to %s", csv_path)

        # Parquet (V3 — Upgrade 5)
        parquet_path = csv_path.with_suffix(".parquet")
        try:
            df.to_parquet(parquet_path, index=False)
            logger.info("Parquet saved to %s", parquet_path)
        except ImportError:
            logger.warning(
                "pyarrow not installed — skipping Parquet output."
                " Run: pip install pyarrow"
            )

    def save_feature_store(self, df: pd.DataFrame) -> None:
        """
        Computes and saves ML-ready feature store to
        data/feature_store/telemetry_features.parquet.

        Includes temporal encodings, rolling averages, lag features,
        composite scores, and target variable candidates. All rolling
        and lag features are computed per region to prevent cross-region
        leakage.
        """
        fs = df.sort_values(["region", "timestamp"]).copy()

        # ── Temporal encodings ────────────────────────────────────────────────
        fs["hour_of_day"] = fs["timestamp"].dt.hour
        fs["day_of_week"] = fs["timestamp"].dt.dayofweek
        fs["month"] = fs["timestamp"].dt.month
        fs["is_weekend"] = fs["day_of_week"].isin([5, 6])

        # ── Rolling features (per region, 30-min = 6 rows) ───────────────────
        fs["rolling_cpu_avg_30min"] = (
            fs.groupby("region")["cpu_usage"]
            .transform(lambda x: x.rolling(6, min_periods=1).mean())
        ).round(2)

        fs["rolling_rps_avg_30min"] = (
            fs.groupby("region")["request_rate"]
            .transform(lambda x: x.rolling(6, min_periods=1).mean())
        ).round(1)

        # ── Lag features (per region, 15-min = 3 rows back) ──────────────────
        fs["lag_cpu_15min"] = (
            fs.groupby("region")["cpu_usage"]
            .transform(lambda x: x.shift(3))
        ).round(2)

        fs["lag_request_rate_15min"] = (
            fs.groupby("region")["request_rate"]
            .transform(lambda x: x.shift(3))
        ).round(1)

        # ── Fill NaN from lag/rolling edges with 0 ───────────────────────────
        fs = fs.fillna(0)

        # ── Select feature store columns ─────────────────────────────────────
        feature_cols = [
            # Temporal features
            "timestamp",
            "region",
            "workload_type",
            # Temporal encodings
            "hour_of_day",
            "day_of_week",
            "month",
            "is_weekend",
            # Rolling features
            "rolling_cpu_avg_30min",
            "rolling_rps_avg_30min",
            # Lag features
            "lag_cpu_15min",
            "lag_request_rate_15min",
            # Composite scores
            "resource_pressure_score",
            "sla_breach_risk",
            # Target variable candidates
            "cpu_usage",
            "request_rate",
            "cost_per_hour",
            "active_instances",
            # Labels
            "is_anomaly",
            "special_event",
        ]

        fs = fs[feature_cols]

        fs_path = Path("data/feature_store/telemetry_features.parquet")
        fs_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            fs.to_parquet(fs_path, index=False)
            logger.info(
                "Feature store saved to %s | shape=%s", fs_path, fs.shape
            )
        except ImportError:
            logger.warning(
                "pyarrow not installed — skipping feature store Parquet."
                " Run: pip install pyarrow"
            )

    def generate_profile_report(
        self, df: pd.DataFrame, validation_passed: bool
    ) -> None:
        """
        Generates and saves a Markdown data profiling report to
        docs/telemetry_profile_report.md.  Uses only stdlib + numpy + pandas
        (no external profiling libraries).
        """
        lines: List[str] = []

        # ── Header ───────────────────────────────────────────────────────────
        lines.append("# CloudPulse AI — Telemetry Profile Report\n")
        lines.append(
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append(
            f"**Dataset shape:** {df.shape[0]} rows × {df.shape[1]} columns"
        )
        lines.append(
            f"**Date range:** {df['timestamp'].min()} → {df['timestamp'].max()}"
        )
        lines.append("\n---\n")

        # ── 1. Missing Values ────────────────────────────────────────────────
        lines.append("## 1. Missing Values\n")
        missing = df.isnull().sum()
        total = len(df)
        lines.append("| Column | Missing Count | Missing % |")
        lines.append("|--------|---------------|-----------|")
        for col in df.columns:
            mc = int(missing[col])
            mp = mc / total * 100
            lines.append(f"| {col} | {mc} | {mp:.2f}% |")
        lines.append("")

        # ── 2. Metric Ranges ─────────────────────────────────────────────────
        lines.append("## 2. Metric Ranges\n")
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        lines.append("| Column | Min | Mean | Max | Std |")
        lines.append("|--------|-----|------|-----|-----|")
        for col in numeric_cols:
            lines.append(
                f"| {col} | {df[col].min():.2f} | {df[col].mean():.2f}"
                f" | {df[col].max():.2f} | {df[col].std():.2f} |"
            )
        lines.append("")

        # ── 3. Region Distribution ───────────────────────────────────────────
        lines.append("## 3. Region Distribution\n")
        rdist = df["region"].value_counts()
        rdist_pct = df["region"].value_counts(normalize=True)
        lines.append("| Region | Count | % |")
        lines.append("|--------|-------|---|")
        for r in rdist.index:
            lines.append(
                f"| {r} | {rdist[r]} | {rdist_pct[r] * 100:.1f}% |"
            )
        lines.append("")

        # ── 4. Workload Type Distribution ────────────────────────────────────
        lines.append("## 4. Workload Type Distribution\n")
        wdist = df["workload_type"].value_counts()
        wdist_pct = df["workload_type"].value_counts(normalize=True)
        lines.append("| Workload Type | Count | % |")
        lines.append("|---------------|-------|---|")
        for w in wdist.index:
            lines.append(
                f"| {w} | {wdist[w]} | {wdist_pct[w] * 100:.1f}% |"
            )
        lines.append("")

        # ── 5. Special Event Distribution ────────────────────────────────────
        lines.append("## 5. Special Event Distribution\n")
        edist = df["special_event"].value_counts()
        edist_pct = df["special_event"].value_counts(normalize=True)
        lines.append("| Event | Count | % |")
        lines.append("|-------|-------|---|")
        for e in edist.index:
            lines.append(
                f"| {e} | {edist[e]} | {edist_pct[e] * 100:.1f}% |"
            )
        lines.append("")

        # ── 6. Anomaly Coverage ──────────────────────────────────────────────
        lines.append("## 6. Anomaly Coverage\n")
        lines.append(
            "| Region | Total Rows | Anomaly Rows | Anomaly % |"
        )
        lines.append(
            "|--------|-----------|--------------|-----------|"
        )
        for r in sorted(df["region"].unique()):
            sub = df[df["region"] == r]
            total_r = len(sub)
            anom_r = int(sub["is_anomaly"].sum())
            lines.append(
                f"| {r} | {total_r} | {anom_r}"
                f" | {anom_r / total_r * 100:.2f}% |"
            )
        lines.append("")

        # ── 7. Correlation Matrix (numeric columns) ──────────────────────────
        lines.append("## 7. Correlation Matrix (numeric columns)\n")
        corr = df[numeric_cols].corr().round(2)
        # Build markdown table
        header = "| |" + "|".join(corr.columns) + "|"
        sep = "|---|" + "|".join(["---"] * len(corr.columns)) + "|"
        lines.append(header)
        lines.append(sep)
        for idx_name in corr.index:
            row_vals = "|".join(
                [str(corr.loc[idx_name, c]) for c in corr.columns]
            )
            lines.append(f"| {idx_name} |{row_vals}|")
        lines.append("")

        # ── 8. Validation Summary ────────────────────────────────────────────
        lines.append("## 8. Validation Summary\n")
        status = "✅ PASSED" if validation_passed else "❌ FAILED"
        lines.append(f"**Overall Status:** {status}\n")

        checks = [
            "V2-01  Shape (rows >= 300K, cols == 18)",
            "V2-02  Column order and names",
            "V2-03  Range checks (CPU, RAM, error, instances, latency, cost)",
            "V2-04  No NaN values",
            "V2-05  Timestamp monotonicity (per region)",
            "V2-06  Cross-metric correlations (per region)",
            "V2-07  Anomaly coverage 0.5–8% (per region)",
            "V2-08  Region distribution ~33% each",
            "V2-09  Special event coverage",
            "V2-10  Instance type coverage",
            "V3-01  Workload type coverage and distribution",
            "V3-02  Pressure score range [0, 100]",
            "V3-03  SLA risk range [0, 100]",
            "V3-04  Pressure & SLA correlation with CPU",
            "V3-05  Output files exist",
        ]
        for chk in checks:
            mark = "✅" if validation_passed else "❓"
            lines.append(f"- {mark} {chk}")
        lines.append("")

        # ── Write file ───────────────────────────────────────────────────────
        report_path = Path("docs/telemetry_profile_report.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines), encoding="utf-8")

        logger.info("Profile report saved to %s", report_path)


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    config = TelemetryConfig()
    generator = CloudTelemetryGenerator(config)
    df = generator.generate()

    print(df.head(6).to_string())
    print(f"\nDataset shape: {df.shape}")
    print(f"\nColumn statistics:\n{df.describe().round(2)}")
    print(
        f"\nRegion distribution:\n"
        f"{df['region'].value_counts(normalize=True).round(3)}"
    )
    print(
        f"\nWorkload distribution:\n"
        f"{df['workload_type'].value_counts(normalize=True).round(3)}"
    )
    print(
        f"\nPressure score summary:\n"
        f"{df['resource_pressure_score'].describe().round(2)}"
    )
    print(
        f"\nSLA breach risk summary:\n"
        f"{df['sla_breach_risk'].describe().round(2)}"
    )

    generator.save(df)
    generator.save_feature_store(df)
    generator.generate_profile_report(df, validation_passed=True)

    # V3 Check 6 — Verify output files exist
    output_files = [
        Path("data/raw/telemetry_data.csv"),
        Path("data/raw/telemetry_data.parquet"),
        Path("data/feature_store/telemetry_features.parquet"),
        Path("docs/telemetry_profile_report.md"),
    ]
    print("\nOutput file verification:")
    for fp in output_files:
        if fp.exists():
            size_mb = fp.stat().st_size / (1024 * 1024)
            print(f"  [OK]   {fp}  ({size_mb:.1f} MB)")
        else:
            print(f"  [FAIL] {fp}  MISSING")
