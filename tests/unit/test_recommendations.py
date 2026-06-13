"""
Tests for scaling recommendation logic — all 5 decision paths with boundary values.
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
        return p


def make_latest_df(cpu_usage=50.0, sla_risk=30.0, active_instances=5, cost=3.0):
    """Helper to create a single-row DataFrame mimicking latest features."""
    return pd.DataFrame({
        "cpu_usage": [cpu_usage],
        "sla_breach_risk": [sla_risk],
        "active_instances": [active_instances],
        "cost_per_hour": [cost],
    })


# ── URGENT SCALE UP ──────────────────────────────────────────

def test_urgent_scale_up_high_cpu(pipeline):
    """prediction > 85 → urgent_scale_up"""
    df = make_latest_df(cpu_usage=80, sla_risk=30)
    rec = pipeline.generate_scaling_recommendation(df, prediction=86)
    assert rec["recommendation"] == "urgent_scale_up"
    assert rec["instances_to_add"] == 3
    assert rec["urgency"] == "critical"


def test_urgent_scale_up_high_sla(pipeline):
    """sla_risk > 70 → urgent_scale_up regardless of CPU prediction"""
    df = make_latest_df(cpu_usage=40, sla_risk=71)
    rec = pipeline.generate_scaling_recommendation(df, prediction=50)
    assert rec["recommendation"] == "urgent_scale_up"
    assert rec["urgency"] == "critical"


# ── SCALE UP ─────────────────────────────────────────────────

def test_scale_up(pipeline):
    """prediction between 75 and 85 (inclusive) → scale_up"""
    df = make_latest_df(cpu_usage=60, sla_risk=30)
    rec = pipeline.generate_scaling_recommendation(df, prediction=78)
    assert rec["recommendation"] == "scale_up"
    assert rec["instances_to_add"] == 2
    assert rec["urgency"] == "high"


def test_boundary_75(pipeline):
    """prediction == 75 exactly → scale_up"""
    df = make_latest_df(cpu_usage=60, sla_risk=30)
    rec = pipeline.generate_scaling_recommendation(df, prediction=75)
    assert rec["recommendation"] == "scale_up"


def test_boundary_85(pipeline):
    """prediction == 85 exactly → scale_up (not urgent, since condition is > 85)"""
    df = make_latest_df(cpu_usage=60, sla_risk=30)
    rec = pipeline.generate_scaling_recommendation(df, prediction=85)
    assert rec["recommendation"] == "scale_up"


# ── MONITOR ──────────────────────────────────────────────────

def test_monitor(pipeline):
    """prediction between 60 and 75 → monitor"""
    df = make_latest_df(cpu_usage=50, sla_risk=25)
    rec = pipeline.generate_scaling_recommendation(df, prediction=65)
    assert rec["recommendation"] == "monitor"
    assert rec["urgency"] == "medium"


def test_boundary_60(pipeline):
    """prediction == 60 exactly → monitor"""
    df = make_latest_df(cpu_usage=50, sla_risk=25)
    rec = pipeline.generate_scaling_recommendation(df, prediction=60)
    assert rec["recommendation"] == "monitor"


# ── SCALE DOWN ───────────────────────────────────────────────

def test_scale_down(pipeline):
    """prediction < 35 AND cost > 3 → scale_down"""
    df = make_latest_df(cpu_usage=30, sla_risk=10, cost=4.0)
    rec = pipeline.generate_scaling_recommendation(df, prediction=30)
    assert rec["recommendation"] == "scale_down"
    assert rec["instances_to_remove"] == 1
    assert rec["urgency"] == "low"


def test_boundary_35_not_scale_down(pipeline):
    """prediction == 35 (not < 35) → maintain, NOT scale_down"""
    df = make_latest_df(cpu_usage=30, sla_risk=10, cost=4.0)
    rec = pipeline.generate_scaling_recommendation(df, prediction=35)
    assert rec["recommendation"] == "maintain"


def test_low_cpu_low_cost_maintain(pipeline):
    """prediction < 35 but cost <= 3 → maintain (cost doesn't justify scaling down)"""
    df = make_latest_df(cpu_usage=20, sla_risk=10, cost=2.0)
    rec = pipeline.generate_scaling_recommendation(df, prediction=25)
    assert rec["recommendation"] == "maintain"


# ── MAINTAIN ─────────────────────────────────────────────────

def test_maintain(pipeline):
    """Normal healthy state → maintain"""
    df = make_latest_df(cpu_usage=45, sla_risk=20, cost=2.5)
    rec = pipeline.generate_scaling_recommendation(df, prediction=50)
    assert rec["recommendation"] == "maintain"
    assert rec["urgency"] == "low"


# ── INSTANCE MATH ────────────────────────────────────────────

def test_scale_down_minimum_one_instance(pipeline):
    """When scaling down from 1 instance, should not go below 1."""
    df = make_latest_df(cpu_usage=20, sla_risk=5, active_instances=1, cost=4.0)
    rec = pipeline.generate_scaling_recommendation(df, prediction=20)
    assert rec["recommendation"] == "scale_down"
    assert rec["target_instances"] >= 1


def test_urgent_scale_up_adds_three(pipeline):
    """Urgent scale up should add exactly 3 to current instances."""
    df = make_latest_df(cpu_usage=90, sla_risk=80, active_instances=7)
    rec = pipeline.generate_scaling_recommendation(df, prediction=92)
    assert rec["target_instances"] == 10
    assert rec["current_instances"] == 7
