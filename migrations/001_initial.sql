-- Migration 001: Initial schema for gstack-auto-as-a-service
-- Run with: sqlite3 instance/app.db < migrations/001_initial.sql

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    google_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    avatar_url TEXT,
    is_approved INTEGER DEFAULT 0,
    is_admin INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    last_login TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT,
    status TEXT DEFAULT 'active',
    spec_markdown TEXT,
    template_id INTEGER REFERENCES templates(id),
    created_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS builds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    session_id INTEGER REFERENCES sessions(id),
    build_token TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'pending',
    scores_json TEXT,
    round_results_json TEXT,
    phases_json TEXT,
    conductor_url TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    system_prompt_addition TEXT,
    example_conversation TEXT,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS nonces (
    nonce TEXT PRIMARY KEY,
    build_id INTEGER NOT NULL REFERENCES builds(id),
    created_at TEXT DEFAULT (datetime('now')),
    used INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS spend_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    tokens_used INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sessions_user_created ON sessions(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_builds_user ON builds(user_id);
CREATE INDEX IF NOT EXISTS idx_builds_token ON builds(build_token);
CREATE INDEX IF NOT EXISTS idx_spend_log_date ON spend_log(created_at);
CREATE INDEX IF NOT EXISTS idx_nonces_created ON nonces(created_at);

-- Seed default templates
INSERT OR IGNORE INTO templates (id, name, description, category, system_prompt_addition, sort_order) VALUES
(1, 'SaaS Web App', 'Full-stack web application with auth, dashboard, and API', 'saas',
 'Focus on: user authentication, clean dashboard UI, RESTful API design, database schema.', 1),
(2, 'Landing Page', 'Marketing site with hero, features, pricing, and CTA', 'landing',
 'Focus on: compelling copy, responsive design, fast load times, clear conversion funnel.', 2),
(3, 'CLI Tool', 'Command-line utility with argument parsing and structured output', 'tool',
 'Focus on: argument parsing, error messages, help text, composability with other tools.', 3),
(4, 'API Service', 'Backend API with endpoints, auth, and documentation', 'api',
 'Focus on: RESTful design, input validation, error responses, API documentation.', 4),
(5, 'Blank Canvas', 'Start from scratch — describe anything you want to build', 'blank',
 '', 5);
