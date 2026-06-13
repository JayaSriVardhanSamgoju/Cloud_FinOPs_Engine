"""
CloudPulse AI Dashboard
-----------------------
Step 13 - Part 1

Features:
1. PostgreSQL Connection
2. KPI Cards
3. Prediction Loading
4. Recommendation Loading
5. Executive Dashboard
"""


from streamlit_autorefresh import (
    st_autorefresh
)
import json
import pandas as pd
import streamlit as st
import plotly.express as px
import sys
from pathlib import Path

# Add project root to sys.path so 'configs' module can be found
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from configs.db_config import engine


PREDICTION_PATH = (
    "artifacts/inference/"
    "latest_prediction.json"
)

RECOMMENDATION_PATH = (
    "artifacts/inference/"
    "scaling_recommendation.json"
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="CloudPulse AI",
    layout="wide"
)

# ============================================================
# AUTO REFRESH
# ============================================================

st_autorefresh(
    interval=30000,
    key="cloudpulse_refresh"
)

st.title(
    "☁️ CloudPulse AI"
)

st.subheader(
    "Predictive Infrastructure "
    "Intelligence Platform"
)
from datetime import datetime

st.caption(
    f"Last Updated: "
    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)

st.markdown("---")


# ============================================================
# LOAD TELEMETRY
# ============================================================

@st.cache_data(ttl=60)
def load_latest_metrics():

    query = """
    SELECT *
    FROM telemetry_metrics
    ORDER BY timestamp DESC
    LIMIT 1
    """

    df = pd.read_sql(
        query,
        engine
    )

    return df


def load_prediction():
    import requests
    try:
        response = requests.get("http://127.0.0.1:8000/predict")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to connect to API: {e}")
        return {
            "predicted_cpu_30min": 0.0,
            "recommendation": {
                "recommendation": "unknown",
                "reason": "API unreachable"
            }
        }

@st.cache_data(ttl=60)
def load_recent_telemetry():

    query = """
    SELECT *
    FROM telemetry_metrics
    ORDER BY timestamp DESC
    LIMIT 500
    """

    df = pd.read_sql(
        query,
        engine
    )

    df = df.sort_values(
        "timestamp"
    )

    return df


@st.cache_data(ttl=60)
def load_region_analytics():

    query = """
    SELECT
        region,
        AVG(cpu_usage)
            AS avg_cpu,
        AVG(request_rate)
            AS avg_requests,
        AVG(cost_per_hour)
            AS avg_cost,
        AVG(response_latency_ms)
            AS avg_latency
    FROM telemetry_metrics
    GROUP BY region
    """

    return pd.read_sql(
        query,
        engine
    )


@st.cache_data(ttl=60)
def load_workload_analytics():

    query = """
    SELECT
        workload_type,
        AVG(cpu_usage)
            AS avg_cpu,
        AVG(request_rate)
            AS avg_requests,
        AVG(cost_per_hour)
            AS avg_cost,
        AVG(response_latency_ms)
            AS avg_latency
    FROM telemetry_metrics
    GROUP BY workload_type
    """

    return pd.read_sql(
        query,
        engine
    )

prediction = (
    load_prediction()
)

recommendation = prediction.get("recommendation", {
    "recommendation": "unknown",
    "reason": "API unreachable"
})

latest = (
    load_latest_metrics().iloc[0]
)
recent_df = (
    load_recent_telemetry()
)

region_df = (
    load_region_analytics()
)

workload_df = (
    load_workload_analytics()
)



# ============================================================
# KPI SECTION
# ============================================================

st.subheader(
    "📊 Executive Infrastructure KPIs"
)

col1, col2, col3 = (
    st.columns(3)
)

col4, col5, col6 = (
    st.columns(3)
)


# CPU
with col1:

    st.metric(
        "Current CPU (%)",
        f"{latest['cpu_usage']:.2f}"
    )


# Predicted CPU
with col2:

    st.metric(
        "Predicted CPU (30 min)",
        f"{prediction['predicted_cpu_30min']:.2f}"
    )


# SLA Risk
with col3:

    st.metric(
        "SLA Breach Risk",
        f"{latest['sla_breach_risk']:.2f}"
    )


# Cost
with col4:

    st.metric(
        "Infra Cost ($/hr)",
        f"{latest['cost_per_hour']:.2f}"
    )


# Active Instances
with col5:

    st.metric(
        "Active Instances",
        int(
            latest[
                "active_instances"
            ]
        )
    )


# Recommendation
with col6:

    st.metric(
        "AI Recommendation",
        recommendation[
            "recommendation"
        ]
    )


st.markdown("---")

# ============================================================
# HEALTH STATUS
# ============================================================

st.subheader(
    "🟢 Infrastructure Health"
)

predicted_cpu = (
    prediction[
        "predicted_cpu_30min"
    ]
)

sla_risk = (
    latest[
        "sla_breach_risk"
    ]
)

if (
    predicted_cpu < 60
    and sla_risk < 30
):

    health = (
        "Healthy"
    )

    st.success(
        "System Status: Healthy"
    )

elif (
    predicted_cpu < 80
):

    health = (
        "Moderate Risk"
    )

    st.warning(
        "System Status: Moderate Risk"
    )

else:

    health = (
        "Critical"
    )

    st.error(
        "System Status: Critical"
    )

# ============================================================
# TELEMETRY TRENDS
# ============================================================

st.subheader(
    "📈 Infrastructure Trends"
)

col1, col2 = st.columns(2)


# CPU TREND
with col1:

    cpu_fig = px.area(
        recent_df,
        x="timestamp",
        y="cpu_usage",
        title="CPU Usage Trend"
    )
    cpu_fig.add_hline(
    y=80,
    line_dash="dash",
    annotation_text=(
        "Scaling Threshold"
    )
)


    st.plotly_chart(
        cpu_fig,
        use_container_width=True
    )


# LATENCY TREND
with col2:

    latency_fig = px.line(
        recent_df,
        x="timestamp",
        y="response_latency_ms",
        title="Latency Trend"
    )

    st.plotly_chart(
        latency_fig,
        use_container_width=True
    )


# ============================================================
# SYSTEM SNAPSHOT
# ============================================================

st.subheader(
    "🖥️ Infrastructure Snapshot"
)

snapshot = pd.DataFrame({

    "Metric": [

        "CPU Usage",

        "RAM Usage",

        "Latency (ms)",

        "Request Rate",

        "Region",

        "Workload Type"
    ],

    "Value": [

        latest["cpu_usage"],

        latest["ram_usage"],

        latest[
            "response_latency_ms"
        ],

        latest["request_rate"],

        latest["region"],

        latest[
            "workload_type"
        ]
    ]
})

snapshot["Value"] = snapshot["Value"].astype(str)

st.dataframe(
    snapshot,
    use_container_width=True
)


st.markdown("---")


# ============================================================
# AI RECOMMENDATION
# ============================================================

st.subheader(
    "🤖 AI Scaling Recommendation"
)

# ============================================================
# STATUS COLORS
# ============================================================

recommendation_type = (
    recommendation[
        "recommendation"
    ]
)

if recommendation_type == (
    "urgent_scale_up"
):

    recommendation_box = (
        st.error
    )

elif recommendation_type == (
    "scale_up"
):

    recommendation_box = (
        st.warning
    )

elif recommendation_type == (
    "monitor"
):

    recommendation_box = (
        st.info
    )

elif recommendation_type == (
    "scale_down"
):

    recommendation_box = (
        st.warning
    )

else:

    recommendation_box = (
        st.success
    )


# ============================================================
# REGION ANALYTICS
# ============================================================

st.markdown("---")

st.subheader(
    "🌍 Regional Intelligence"
)

col1, col2 = st.columns(2)


# REGION CPU
with col1:

    region_cpu_fig = px.bar(
        region_df,
        x="region",
        y="avg_cpu",
        title="Average CPU by Region"
    )

    st.plotly_chart(
        region_cpu_fig,
        use_container_width=True
    )


# REGION COST
with col2:

    region_cost_fig = px.bar(
        region_df,
        x="region",
        y="avg_cost",
        title="Average Cost by Region"
    )

    st.plotly_chart(
        region_cost_fig,
        use_container_width=True
    )

# ============================================================
# WORKLOAD ANALYTICS
# ============================================================

st.markdown("---")

st.subheader(
    "⚙️ Workload Intelligence"
)

col1, col2 = st.columns(2)


# WORKLOAD CPU
with col1:

    workload_cpu_fig = px.bar(
        workload_df,
        x="workload_type",
        y="avg_cpu",
        title="CPU by Workload"
    )

    st.plotly_chart(
        workload_cpu_fig,
        use_container_width=True
    )


# WORKLOAD LATENCY
with col2:

    workload_latency_fig = px.bar(
        workload_df,
        x="workload_type",
        y="avg_latency",
        title="Latency by Workload"
    )

    st.plotly_chart(
        workload_latency_fig,
        use_container_width=True
    )

# ============================================================
# FINOPS
# ============================================================

st.markdown("---")

st.subheader(
    "💰 FinOps Analytics"
)

cost_fig = px.area(
    recent_df,
    x="timestamp",
    y="cost_per_hour",
    title="Infrastructure Cost Trend"
)

st.plotly_chart(
    cost_fig,
    use_container_width=True
)

st.markdown("---")

st.caption(
    "CloudPulse AI | "
    "Predictive Infrastructure "
    "Intelligence Platform"
)