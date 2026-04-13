-- =============================================================================
-- Calabi CE v1.0 — PostgreSQL init
-- Creates databases for CE modules (Catalogue + BI)
-- Runs on first startup via docker-entrypoint-initdb.d
-- =============================================================================

-- Calabi Catalogue — created by POSTGRES_DB env
GRANT ALL PRIVILEGES ON DATABASE calabi_catalogue TO calabi;

-- CalabiIQ BI
CREATE DATABASE calabi_bi;
GRANT ALL PRIVILEGES ON DATABASE calabi_bi TO calabi;
