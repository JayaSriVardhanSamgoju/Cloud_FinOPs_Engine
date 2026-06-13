# ☁️ CloudPulse AI

## Predictive Infrastructure Intelligence Platform

CloudPulse AI is a production-inspired machine learning system that predicts future cloud infrastructure demand and proactively recommends intelligent scaling actions before performance degradation occurs.

Traditional auto-scaling systems are reactive.

CloudPulse AI is **predictive**.

It forecasts future workload behavior using telemetry intelligence and machine learning to prevent SLA breaches, optimize infrastructure costs, and improve reliability.

---

# 🚀 Problem Statement

Traditional cloud auto-scaling systems work like:

```text
CPU > 80%
→ Add Instances
```

Problem:

- Reactive scaling
- SLA degradation before scaling
- Resource inefficiency
- Infrastructure cost wastage

CloudPulse AI solves this problem through:

### Predictive Auto Scaling

Example:

```text
Current CPU = 65%

Forecasted CPU (30 min) = 91%

Recommendation:
Scale Up Before Failure
```

---

# 🎯 Project Objectives

CloudPulse AI predicts:

- Future CPU demand
- Infrastructure workload spikes
- SLA breach risk
- Scaling requirements
- Infrastructure cost patterns

And recommends:

- Scale Up
- Maintain
- Monitor
- Scale Down
- Emergency Scale Up

---

# 🏗️ System Architecture

```text
Telemetry Simulation
        ↓
PostgreSQL Database
        ↓
EDA & Telemetry Intelligence
        ↓
Feature Engineering Pipeline
        ↓
Forecasting Models
(XGBoost / LightGBM / RF)
        ↓
Real-Time Inference Engine
        ↓
Scaling Recommendation System
        ↓
Streamlit Dashboard
```

---

# ✨ Key Features

## Infrastructure Telemetry Simulation

Simulates:

- Multi-region cloud infrastructure
- SLA risks
- Workload traffic
- CPU spikes
- Cost fluctuations
- Resource pressure
- Anomaly behavior

Regions:

```text
us-east-1
eu-west-1
ap-south-1
```

Workloads:

```text
api_service
web_application
batch_processing
streaming_service
```

---

## Telemetry Intelligence EDA

Built a production-grade telemetry intelligence profiling system for:

- workload intelligence
- regional intelligence
- SLA analysis
- anomaly analysis
- cost intelligence
- correlation validation

Generated:

### 20+ observability visualizations

---

## Feature Engineering

Built advanced forecasting features:

### Temporal Features

```text
hour
month
day_of_week
business_hours
```

### Lag Features

```text
5 min
15 min
30 min
1 hour
2 hour
```

### Rolling Window Features

```text
rolling_mean
rolling_std
rolling_min
rolling_max
```

### Trend Features

```text
delta
percentage_change
```

### Cyclical Time Encoding

```text
sin()
cos()
```

---

## Forecasting Models

Compared:

- Linear Regression
- Random Forest
- XGBoost
- LightGBM

Used:

### Chronological Time-Series Split

To avoid:

```text
Temporal Leakage
```

Metrics:

- RMSE
- MAE
- R² Score

---

## Real-Time Inference Engine

CloudPulse AI predicts:

```text
CPU usage after 30 minutes
```

and recommends:

```text
scale_up
maintain
monitor
scale_down
urgent_scale_up
```

based on:

- predicted CPU
- SLA risk
- active instances
- infrastructure cost

---

## Dashboard

Built a real-time Streamlit dashboard featuring:

- Infrastructure KPIs
- CPU trend analytics
- SLA monitoring
- Region analytics
- Workload analytics
- FinOps analytics
- AI recommendation engine

---

# 🛠️ Tech Stack

### Programming

- Python

### Machine Learning

- Scikit-Learn
- XGBoost
- LightGBM

### Data Engineering

- PostgreSQL
- SQLAlchemy
- Pandas

### MLOps

- MLflow
- Docker
- Docker Compose

### Dashboard

- Streamlit
- Plotly

### Infrastructure

- Docker Desktop
- Redis
- pgAdmin

---

# 📁 Project Structure

```text
CloudPulse-AI/
│
├── dashboard/
│   └── app.py
│
├── ml/
│   ├── eda/
│   ├── forecasting/
│   ├── feature_engineering/
│   └── inference/
│
├── configs/
│
├── artifacts/
│
├── reports/
│
├── data/
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

# ⚙️ Installation

Clone repository:

```bash
git clone <your_repo_url>
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# ▶️ Run Project

Generate telemetry:

```bash
python telemetry/generate_telemetry.py
```

Feature engineering:

```bash
python ml/feature_engineering/time_series_feature_engineering.py
```

Train forecasting model:

```bash
python ml/forecasting/train_forecasting_models.py
```

Run inference:

```bash
python ml/inference/realtime_inference.py
```

Run dashboard:

```bash
streamlit run dashboard/app.py
```

---

# 🐳 Docker Setup

Run everything:

```bash
docker compose up --build
```

Services:

```text
Dashboard → localhost:8501
pgAdmin → localhost:5050
MLflow → localhost:5001
Postgres → localhost:5432
```

---

# 📊 Results

CloudPulse AI successfully:

✅ Forecasted future infrastructure demand

✅ Predicted CPU spikes

✅ Generated proactive scaling recommendations

✅ Simulated enterprise telemetry

✅ Built a production-style ML system

---

# 🔮 Future Improvements

- Kubernetes deployment
- Real cloud telemetry ingestion
- Kafka streaming
- Real-time retraining
- Drift detection
- Reinforcement learning scaling agent

---

# 💼 Resume Impact

This project demonstrates:

- Machine Learning Engineering
- Time Series Forecasting
- MLOps
- Data Engineering
- System Design
- Predictive Infrastructure Intelligence
- Production-grade ML Pipelines

---

# 👨‍💻 Author

**Jaya Sri Vardhan Samgoju**

Machine Learning Engineer Aspirant