-- Migration 002: Iteration support + deploy config
-- Depends on: 001_initial.sql

-- Iteration columns on builds
ALTER TABLE builds ADD COLUMN parent_build_id INTEGER REFERENCES builds(id);
ALTER TABLE builds ADD COLUMN root_session_id INTEGER REFERENCES sessions(id);
ALTER TABLE builds ADD COLUMN iteration_summary TEXT;
ALTER TABLE builds ADD COLUMN fly_app_name TEXT;
ALTER TABLE builds ADD COLUMN deploy_status TEXT;

-- Iteration support on sessions (for Iterate → office hours flow)
ALTER TABLE sessions ADD COLUMN parent_build_id INTEGER REFERENCES builds(id);

-- Deploy config on users (Fernet-encrypted JSON)
ALTER TABLE users ADD COLUMN deploy_config TEXT;

-- Backfill root_session_id for existing builds
UPDATE builds SET root_session_id = session_id WHERE root_session_id IS NULL;

-- Indexes for lineage queries
CREATE INDEX IF NOT EXISTS idx_builds_parent ON builds(parent_build_id);
CREATE INDEX IF NOT EXISTS idx_builds_root_session ON builds(root_session_id);
