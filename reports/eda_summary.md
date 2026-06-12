# CloudPulse AI -- Telemetry EDA Summary Report

**Generated:** 2026-06-12 17:19:26
**Source:** PostgreSQL `telemetry_metrics` (316224 rows, 18 columns)
**Date range:** 2024-01-01 00:00:00 -> 2024-12-31 23:55:00

---

## 1. Dataset Summary

- **Rows:** 316224
- **Columns:** 18
- **Date range:** 2024-01-01 00:00:00 to 2024-12-31 23:55:00
- **Duplicate rows:** 0
- **float64:** 11 columns
- **str:** 4 columns
- **datetime64[us]:** 1 columns
- **int64:** 1 columns
- **bool:** 1 columns

## 2. Data Quality Report

- **Total missing values:** 0
- **Data Quality Gate:** **PASS**

All columns have zero missing values. Data quality gate passed.

## 3. Infrastructure Behavior

### CPU Usage
- Mean: 47.74%
- Std: 21.92%
- Min: 2.0% | Max: 98.0%
- Median: 46.84%
- Skewness: 0.09

### Request Rate
- Mean: 1491.49 RPS
- Std: 847.4
- Min: 50.0 | Max: 6500.0
- Median: 1342.8 RPS

### Response Latency
- Mean: 274.42 ms
- Std: 158.1 ms
- Min: 24.8 ms | Max: 3882.2 ms
- CPU-Latency Correlation: 0.8432
- CPU-Latency threshold (0.6): **PASS**

## 4. Correlation Insights

| Metric Pair | Actual | Threshold | Status |
|---|---|---|---|
| cpu_usage <-> ram_usage | 0.979 | >= 0.7 | **PASS** |
| cpu_usage <-> request_rate | 0.7357 | >= 0.75 | **FAIL** |
| cpu_usage <-> response_latency_ms | 0.8432 | >= 0.6 | **PASS** |
| cpu_usage <-> cost_per_hour | 0.932 | >= 0.6 | **PASS** |
| response_latency_ms <-> sla_breach_risk | 0.9077 | >= 0.7 | **PASS** |

**Checks passed:** 4/5

## 5. Region Insights

| Region | Avg CPU (%) | Avg RPS | Avg Cost ($) | Anomaly Rate (%) |
|---|---|---|---|---|
| ap-south-1 | 47.73 | 1419 | 2.89 | 0.68 |
| eu-west-1 | 47.73 | 1132 | 3.15 | 0.83 |
| us-east-1 | 47.75 | 1924 | 2.63 | 1.36 |

- **Highest traffic:** us-east-1 (1924 avg RPS)
- **Highest cost:** eu-west-1 ($3.15/hr)
- **Highest anomaly rate:** us-east-1 (1.36%)

## 6. Workload Insights

| Workload | Avg CPU (%) | Avg RPS | Avg Disk IO | Avg Net Out | Avg Latency (ms) | Avg Cost ($) |
|---|---|---|---|---|---|---|
| api_service | 47.78 | 1889 | 22.09 | 338.73 | 201 | 2.89 |
| batch_processing | 47.68 | 768 | 67.93 | 246.12 | 375 | 2.89 |
| streaming_service | 47.64 | 1674 | 28.05 | 541.04 | 335 | 2.89 |
| web_application | 47.76 | 1399 | 31.17 | 308.11 | 268 | 2.89 |

**Validation:**
- Highest Disk I/O: `batch_processing` (expected: `batch_processing`)
- Highest Network Out: `streaming_service` (expected: `streaming_service`)
- Highest RPS: `api_service` (expected: `api_service`)
- Lowest Latency: `api_service` (expected: `api_service`)

## 7. Cost Insights (FinOps)

- Mean cost: $2.89/hr
- Median cost: $2.41/hr
- Min: $0.57 | Max: $9.67

**Regional cost ranking (median $/hr):**
- eu-west-1: $2.61
- ap-south-1: $2.41
- us-east-1: $2.21

## 8. SLA Analysis

- **Healthy** (<30.0): 98.96% (312940 rows)
- **Warning** (30.0-60.0): 1.04% (3284 rows)
- **Critical** (>=60.0): 0.0% (0 rows)

| Region | Healthy (%) | Warning (%) | Critical (%) |
|---|---|---|---|
| ap-south-1 | 98.97 | 1.03 | 0.0 |
| eu-west-1 | 99.02 | 0.98 | 0.0 |
| us-east-1 | 98.89 | 1.11 | 0.0 |

## 9. Anomaly Statistics

- **Overall anomaly rate:** 0.96%
- **Rate within expected bounds (0.5%-8.0%):** **PASS**

**Per-region anomaly rates:**
- ap-south-1: 0.68%
- eu-west-1: 0.83%
- us-east-1: 1.36%

**Special event distribution:**

| Event | Count |
|---|---|
| none | 304374 |
| holiday | 6048 |
| sale_event | 5184 |
| deployment_window | 618 |

- CPU median (normal): 46.8%
- CPU median (anomalous): 51.2%

## 10. Time-Series Validation

### Hourly CPU Pattern
- Night trough (00:00-05:00): 34.87% avg
- Morning peak (09:00-12:00): 65.65% avg
- Evening peak (18:00-21:00): 34.71% avg

### Weekday Pattern
- Mon: 50.55%
- Tue: 54.29%
- Wed: 55.34%
- Thu: 54.2%
- Fri: 51.63%
- Sat: 35.82%
- Sun: 32.14%

### Monthly Growth Trend
- January avg CPU: 41.3%
- December avg CPU: 54.04%
- **Growth:** 30.84%

## 11. Feature Store Validation

- `lag_cpu_15min_vs_cpu_usage`: 0.9722
- `rolling_cpu_vs_pressure`: 0.9904
- **Autocorrelation (15min lag):** 0.9722
- **Forecast readiness:** **PASS**

## 12. Key Findings

- Zero missing values across all columns -- data quality gate passed
- Correlation validation: 4/5 checks passed
- Anomaly rate at 0.96% -- within expected bounds
- Monthly CPU growth trend of 30.84% confirms trend-drift component
- Clear daily seasonality: night trough at 34.87%, evening peak at 34.71%
- Workload differentiation validated: batch_processing shows highest disk I/O
- Workload differentiation validated: streaming_service shows highest network out
- Feature store validated: 15-min lag autocorrelation at 0.9722 confirms strong temporal predictive signal

## 13. Recommendations for Forecasting

- CPU, request rate, latency, and resource_pressure_score exhibit strong predictive relationships and are suitable forecasting signals.
- The 15-minute lag and 30-minute rolling features provide strong temporal context for time-series forecasting models.
- **Caution:** The following correlation checks did not meet thresholds: cpu_usage <-> request_rate. Consider feature engineering or model architecture adjustments.
- Regional and workload-type features provide meaningful segmentation signals for specialized forecasting models per region/workload.
- Cost-per-hour exhibits clear correlation with infrastructure load, supporting FinOps cost prediction as a downstream forecasting target.
