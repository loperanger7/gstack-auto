"""Tests for migration tracking and idempotency."""

import sqlite3
import os
import tempfile


def test_migrations_idempotent(app):
    """Running init_db twice doesn't fail (migrations tracked)."""
    from app.models import init_db

    # init_db already ran once during app creation
    # Run it again — should be idempotent
    init_db(app)

    # Verify tracking table exists and has entries
    db_path = app.config['DATABASE']
    if db_path == ':memory:':
        return  # Can't test with :memory: — init_db skips it

    conn = sqlite3.connect(db_path)
    rows = conn.execute('SELECT name FROM _migrations ORDER BY name').fetchall()
    conn.close()
    assert len(rows) >= 1
    assert rows[0][0] == '001_initial.sql'


def test_migration_002_adds_columns():
    """Migration 002 adds iteration columns to builds and sessions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Run migration 001 manually
        migration_dir = os.path.join(os.path.dirname(__file__), '..', 'migrations')
        with open(os.path.join(migration_dir, '001_initial.sql')) as f:
            conn.executescript(f.read())

        # Run migration 002
        with open(os.path.join(migration_dir, '002_iteration.sql')) as f:
            conn.executescript(f.read())

        # Verify new columns exist
        info = conn.execute('PRAGMA table_info(builds)').fetchall()
        col_names = [row['name'] for row in info]
        assert 'parent_build_id' in col_names
        assert 'root_session_id' in col_names
        assert 'iteration_summary' in col_names
        assert 'fly_app_name' in col_names
        assert 'deploy_status' in col_names

        info = conn.execute('PRAGMA table_info(sessions)').fetchall()
        col_names = [row['name'] for row in info]
        assert 'parent_build_id' in col_names

        info = conn.execute('PRAGMA table_info(users)').fetchall()
        col_names = [row['name'] for row in info]
        assert 'deploy_config' in col_names

        # Verify indexes
        indexes = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        idx_names = [row['name'] for row in indexes]
        assert 'idx_builds_parent' in idx_names
        assert 'idx_builds_root_session' in idx_names

        conn.close()


def test_root_session_backfill():
    """Migration 002 backfills root_session_id for existing builds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        migration_dir = os.path.join(os.path.dirname(__file__), '..', 'migrations')
        with open(os.path.join(migration_dir, '001_initial.sql')) as f:
            conn.executescript(f.read())

        # Insert a build before migration 002
        conn.execute(
            "INSERT INTO users (google_id, email, name) VALUES ('g1', 'u@t.com', 'U')"
        )
        conn.execute(
            "INSERT INTO sessions (user_id, title) VALUES (1, 'Test')"
        )
        conn.execute(
            "INSERT INTO builds (user_id, session_id, build_token) VALUES (1, 1, 'tok')"
        )
        conn.commit()

        # Run migration 002
        with open(os.path.join(migration_dir, '002_iteration.sql')) as f:
            conn.executescript(f.read())

        # Verify backfill: root_session_id should equal session_id
        build = conn.execute('SELECT * FROM builds WHERE id = 1').fetchone()
        assert build['root_session_id'] == build['session_id']

        conn.close()
