-- Reproducibility and SQL execution metadata.
CREATE TABLE audit.ingestion_runs (
    build_run_id VARCHAR PRIMARY KEY,
    build_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    configuration_hash VARCHAR NOT NULL,
    build_timestamp TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL
);

CREATE TABLE audit.source_files (
    source_name VARCHAR PRIMARY KEY,
    source_path VARCHAR NOT NULL,
    source_sha256 VARCHAR NOT NULL,
    expected_rows BIGINT,
    loaded_rows BIGINT,
    hash_verified BOOLEAN NOT NULL,
    build_run_id VARCHAR NOT NULL
);

CREATE TABLE audit.table_build_manifest (
    table_name VARCHAR PRIMARY KEY,
    row_count BIGINT NOT NULL,
    distinct_primary_keys BIGINT,
    build_run_id VARCHAR NOT NULL,
    sql_version VARCHAR NOT NULL
);

CREATE TABLE audit.sql_execution_log (
    execution_order INTEGER NOT NULL,
    sql_file VARCHAR NOT NULL,
    sql_sha256 VARCHAR NOT NULL,
    executed_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL,
    PRIMARY KEY (execution_order, sql_file)
);

CREATE TABLE audit.source_lineage (
    target_table VARCHAR NOT NULL,
    source_name VARCHAR NOT NULL,
    source_path VARCHAR NOT NULL,
    source_sha256 VARCHAR NOT NULL,
    build_run_id VARCHAR NOT NULL,
    configuration_hash VARCHAR NOT NULL,
    sql_file VARCHAR NOT NULL,
    transformation_summary VARCHAR NOT NULL
);
