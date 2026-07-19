-- Phase 4 writes a standalone database and attaches immutable Phase 2/3 inputs read-only.
ATTACH '{{phase2_database_path}}' AS phase2 (READ_ONLY);
ATTACH '{{phase3_database_path}}' AS phase3 (READ_ONLY);
CREATE SCHEMA core;
CREATE SCHEMA quality;
CREATE SCHEMA audit;
CREATE SCHEMA reporting;

CREATE TABLE audit.label_build_runs (
    label_build_run_id VARCHAR PRIMARY KEY,
    build_timestamp TIMESTAMP NOT NULL,
    label_configuration_hash VARCHAR NOT NULL,
    distress_configuration_hash VARCHAR NOT NULL,
    protocol_sha256 VARCHAR NOT NULL,
    phase2_database_sha256 VARCHAR NOT NULL,
    phase3_database_sha256 VARCHAR NOT NULL,
    status VARCHAR NOT NULL
);

CREATE TABLE audit.label_sql_execution_log (
    execution_order INTEGER NOT NULL,
    sql_file VARCHAR NOT NULL,
    sql_sha256 VARCHAR NOT NULL,
    label_build_run_id VARCHAR NOT NULL
);

CREATE TABLE audit.label_control_results (
    control_id VARCHAR NOT NULL,
    control_name VARCHAR NOT NULL,
    expected_value BIGINT,
    observed_value BIGINT,
    status VARCHAR NOT NULL,
    label_build_run_id VARCHAR NOT NULL
);
