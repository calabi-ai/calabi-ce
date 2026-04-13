-- =============================================================================
-- Calabi CE v1.0 — PostgreSQL init
-- Creates databases for CE modules (Catalogue + BI)
-- Runs on first startup via docker-entrypoint-initdb.d
-- =============================================================================

-- Catalogue (OpenMetadata) — calabi_catalogue created by POSTGRES_DB env
GRANT ALL PRIVILEGES ON DATABASE calabi_catalogue TO calabi;

-- ExamIQ BI (Superset)
CREATE DATABASE calabi_bi;
GRANT ALL PRIVILEGES ON DATABASE calabi_bi TO calabi;
