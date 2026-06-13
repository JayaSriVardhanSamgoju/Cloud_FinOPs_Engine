# CloudPulse AI Model Comparison

## All Results (including Persistence Baseline)

| model                |   rmse |    mae |   r2_score |   improvement_pct |
|:---------------------|-------:|-------:|-----------:|------------------:|
| xgboost              | 5.4335 | 4.1717 |     0.9472 |             38.45 |
| lightgbm             | 5.4471 | 4.197  |     0.9469 |             38.3  |
| lightgbm_no_pressure | 5.4919 | 4.2217 |     0.9461 |             37.79 |
| random_forest        | 5.584  | 4.2614 |     0.9442 |             36.74 |
| linear_regression    | 6.0259 | 4.6864 |     0.9351 |             31.74 |
| PersistenceBaseline  | 8.8277 | 6.9264 |     0.8606 |              0    |

## Best ML Model

**Best Model:** xgboost

**R² Score:** 0.9472

**RMSE Improvement vs Persistence:** 38.45%

## S5 Ablation Study

LightGBM trained without `resource_pressure_score` and `sla_breach_risk` features:

| model                |   rmse |    mae |   r2_score |   improvement_pct |
|:---------------------|-------:|-------:|-----------:|------------------:|
| lightgbm_no_pressure | 5.4919 | 4.2217 |     0.9461 |             37.79 |
