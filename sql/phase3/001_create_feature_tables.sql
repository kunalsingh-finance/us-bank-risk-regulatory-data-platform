-- Phase 3 writes a separate database and attaches the immutable Phase 2 database read-only.
ATTACH '{{input_database_path}}' AS phase2 (READ_ONLY);
CREATE SCHEMA staging;
CREATE SCHEMA core;
CREATE SCHEMA quality;
CREATE SCHEMA audit;
CREATE SCHEMA reporting;

CREATE TABLE audit.feature_build_runs (
    feature_build_run_id VARCHAR PRIMARY KEY,
    build_timestamp TIMESTAMP NOT NULL,
    risk_configuration_hash VARCHAR NOT NULL,
    peer_configuration_hash VARCHAR NOT NULL,
    quality_configuration_hash VARCHAR NOT NULL,
    input_database_sha256 VARCHAR NOT NULL,
    status VARCHAR NOT NULL
);

CREATE TABLE audit.feature_sql_execution_log (
    execution_order INTEGER NOT NULL,
    sql_file VARCHAR NOT NULL,
    sql_sha256 VARCHAR NOT NULL,
    feature_build_run_id VARCHAR NOT NULL
);
