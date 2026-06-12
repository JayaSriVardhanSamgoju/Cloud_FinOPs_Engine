CREATE TABLE telemetry_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    cpu_usage FLOAT NOT NULL,
    ram_usage FLOAT NOT NULL,
    disk_io FLOAT NOT NULL,
    network_in FLOAT NOT NULL,
    network_out FLOAT NOT NULL,
    request_rate FLOAT NOT NULL,
    error_rate FLOAT NOT NULL,
    active_instances INT NOT NULL,
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