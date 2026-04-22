-- =============================================================================
-- Calabi Starter v1.0 — PostgreSQL init
-- Creates databases for Starter modules (Catalogue + BI + Airflow Pipelines)
-- Runs on first startup via docker-entrypoint-initdb.d
-- =============================================================================

-- Calabi Catalogue — created by POSTGRES_DB env
GRANT ALL PRIVILEGES ON DATABASE calabi_catalogue TO calabi;

-- CalabiIQ BI
CREATE DATABASE calabi_bi;
GRANT ALL PRIVILEGES ON DATABASE calabi_bi TO calabi;

-- Calabi Airflow (Starter-only — orchestration metadata)
CREATE DATABASE calabi_pipelines;
GRANT ALL PRIVILEGES ON DATABASE calabi_pipelines TO calabi;
