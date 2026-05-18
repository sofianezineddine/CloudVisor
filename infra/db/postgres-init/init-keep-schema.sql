-- ============================================================================
-- Keep AIOps Schema Initialization
-- ============================================================================
-- This script creates the 'keep' schema used by the Keep AIOps service
-- to isolate its tables from CloudVisor's default public schema.
--
-- Execution:
--   - Automatically runs on first PostgreSQL container initialization
--     (when data directory is empty) via /docker-entrypoint-initdb.d/
--   - For existing deployments, run manually:
--     psql -U cvadmin -d cloudvisor -f init-keep-schema.sql
-- ============================================================================

-- Create the keep schema if it doesn't already exist
CREATE SCHEMA IF NOT EXISTS keep;

-- Grant full access to the cvadmin user on the keep schema
GRANT ALL PRIVILEGES ON SCHEMA keep TO cvadmin;

-- Grant default privileges so future tables/sequences created in the keep schema
-- are also accessible by cvadmin
ALTER DEFAULT PRIVILEGES IN SCHEMA keep
    GRANT ALL PRIVILEGES ON TABLES TO cvadmin;

ALTER DEFAULT PRIVILEGES IN SCHEMA keep
    GRANT ALL PRIVILEGES ON SEQUENCES TO cvadmin;

ALTER DEFAULT PRIVILEGES IN SCHEMA keep
    GRANT ALL PRIVILEGES ON FUNCTIONS TO cvadmin;

-- Set the search_path for the keep service connections
-- This ensures that when Keep connects, it uses the keep schema by default
ALTER ROLE cvadmin SET search_path TO public, keep;
