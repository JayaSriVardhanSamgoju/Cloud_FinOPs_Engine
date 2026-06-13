CREATE TABLE telemetry_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    region VARCHAR(50),
    workload_type VARCHAR(100),
    cpu_usage FLOAT,
    ram_usage FLOAT,
    disk_io FLOAT,
    network_in FLOAT,
    network_out FLOAT,
    request_rate FLOAT,
    error_rate FLOAT,
    response_latency_ms FLOAT,
    resource_pressure_score FLOAT,
    sla_breach_risk FLOAT,
    active_instances INT,
    instance_type VARCHAR(50),
    cost_per_hour FLOAT,
    special_event VARCHAR(100),
    is_anomaly BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE model_predictions (
    prediction_id SERIAL PRIMARY KEY,
    prediction_timestamp TIMESTAMP NOT NULL,
    horizon_minutes INT NOT NULL,
    predicted_cpu FLOAT,
    predicted_ram FLOAT,
    predicted_requests FLOAT,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE scaling_recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    current_instances INT,
    recommended_instances INT,
    predicted_cpu FLOAT,
    decision_type VARCHAR(50),
    reason TEXT,
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE model_training_logs (
    training_id SERIAL PRIMARY KEY,
    model_name VARCHAR(100),
    rmse FLOAT,
    mae FLOAT,
    mape FLOAT,
    training_time FLOAT,
    model_version VARCHAR(50),
    dataset_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE drift_reports (
    report_id SERIAL PRIMARY KEY,
    drift_score FLOAT,
    drift_detected BOOLEAN,
    report_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_telemetry_ts_reg ON telemetry_metrics(timestamp, region);